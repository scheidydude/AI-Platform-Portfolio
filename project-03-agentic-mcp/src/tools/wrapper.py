"""ToolResult wrapper — structured error handling for all MCP tool calls.

No raw exception ever reaches the agent context. Every call returns a ToolResult.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any

import httpx
from mcp import ClientSession

from src.models import ToolResult

logger = logging.getLogger(__name__)

# Retry config for rate-limit errors
_MAX_RETRIES = 3
_BASE_BACKOFF = 1.0  # seconds


async def call_tool_safe(
    session: ClientSession,
    tool_name: str,
    arguments: dict[str, Any],
) -> ToolResult:
    """Call an MCP tool, returning a ToolResult regardless of outcome."""
    retries = 0
    last_error: Exception | None = None

    while retries <= _MAX_RETRIES:
        try:
            result = await session.call_tool(tool_name, arguments)
            text = _extract_text(result)
            return ToolResult(success=True, data=text)

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                retries += 1
                if retries > _MAX_RETRIES:
                    return ToolResult(
                        success=False,
                        error_class="rate_limit",
                        error_message=f"Rate limited after {_MAX_RETRIES} retries",
                        retries_attempted=retries,
                    )
                wait = _backoff(retries)
                logger.warning("Rate limited on %s, retry %d in %.1fs", tool_name, retries, wait)
                await asyncio.sleep(wait)
                last_error = exc
                continue

            if status == 404:
                return ToolResult(
                    success=False,
                    error_class="not_found",
                    error_message=f"Resource not found: {exc.request.url}",
                )

            return ToolResult(
                success=False,
                error_class="bad_output",
                error_message=f"HTTP {status}: {exc}",
            )

        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            logger.warning("Timeout on tool %s: %s", tool_name, exc)
            return ToolResult(
                success=False,
                error_class="timeout",
                error_message=f"Tool call timed out: {tool_name}",
            )

        except (httpx.ConnectError, httpx.NetworkError, ConnectionRefusedError) as exc:
            logger.error("Tool unavailable %s: %s", tool_name, exc)
            return ToolResult(
                success=False,
                error_class="unavailable",
                error_message=f"Tool server unreachable: {exc}",
            )

        except Exception as exc:  # noqa: BLE001
            # Catch-all — validate if it looks like bad output, otherwise unavailable
            logger.exception("Unexpected error calling tool %s", tool_name)
            error_class = "bad_output" if _looks_like_bad_output(exc) else "unavailable"
            return ToolResult(
                success=False,
                error_class=error_class,
                error_message=str(exc),
            )

    # Should not reach here, but satisfy type checker
    return ToolResult(
        success=False,
        error_class="rate_limit",
        error_message=str(last_error),
        retries_attempted=retries,
    )


def tool_result_for_claude(result: ToolResult, tool_use_id: str) -> dict:
    """Convert ToolResult to Anthropic tool_result message block."""
    if result.success:
        content = result.data or ""
    else:
        content = _error_summary(result)

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": str(content),
        "is_error": not result.success,
    }


def mcp_tools_to_openai(mcp_tools: list) -> list[dict]:
    """Convert MCP Tool objects to OpenAI function-calling tool dicts."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools
    ]


def _extract_text(result: Any) -> str:
    """Pull text out of an MCP CallToolResult."""
    if hasattr(result, "content"):
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts)
    return str(result)


def _error_summary(result: ToolResult) -> str:
    prefix = {
        "rate_limit": "[Rate limited]",
        "not_found": "[Not found]",
        "timeout": "[Timeout]",
        "bad_output": "[Bad output]",
        "unavailable": "[Tool unavailable]",
    }.get(result.error_class or "", "[Error]")
    return f"{prefix} {result.error_message}"


def _backoff(attempt: int) -> float:
    """Exponential backoff with jitter."""
    return _BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0, 0.5)


def _looks_like_bad_output(exc: Exception) -> bool:
    return isinstance(exc, (json.JSONDecodeError, ValueError, KeyError, AttributeError))
