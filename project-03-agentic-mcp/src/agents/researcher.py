"""Researcher agent.

Takes a ResearchTask, executes it using MCP tools, returns a ResearchFinding.
Enforces AgentConstraints: max_tool_calls, loop detection, partial return on exceed.

Uses OpenAI-compatible API (llama.cpp at http://ai.scheidy.com:8082).
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from src.models import AgentConstraints, ResearchFinding, ResearchTask, Source
from src.tools.wrapper import call_tool_safe, mcp_tools_to_openai

logger = logging.getLogger(__name__)

LLM_BASE_URL = "http://ai.scheidy.com:8082/v1"
MODEL = "Qwen3.6-35B-A3B-MXFP4_MOE.gguf"
SEARXNG_SERVER = Path(__file__).parent.parent / "mcp_servers" / "searxng_server.py"

SYSTEM_PROMPT = """/no_think
You are a Researcher agent. Your job is to execute a specific research task using the tools available to you.

Be methodical:
1. Search for relevant information using web_search
2. Fetch key pages with fetch_page when you need more detail
3. Synthesize what you find into a clear, factual answer
4. Cite your sources (include URLs)

When you have enough information to answer the task's success criteria, stop using tools and write your final answer.
If you cannot find what you need, say so clearly and explain what gaps remain."""


class ResearcherAgent:
    def __init__(self, constraints: AgentConstraints | None = None) -> None:
        self.constraints = constraints or AgentConstraints()
        self.client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key="no-key")

    async def run(self, task: ResearchTask) -> ResearchFinding:
        logger.info("Researcher starting task %s: %s", task.task_id, task.description)
        start = time.monotonic()
        effective_max_calls = min(task.max_tool_calls, self.constraints.max_tool_calls)

        async with self._mcp_session() as session:
            mcp_tools_resp = await session.list_tools()
            openai_tools = mcp_tools_to_openai(mcp_tools_resp.tools)

            messages: list[dict] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_task_prompt(task)},
            ]

            tool_calls_used = 0
            iterations = 0
            sources: list[Source] = []
            seen_calls: set[str] = set()
            final_text = ""
            partial = False

            while iterations < self.constraints.max_iterations:
                elapsed = time.monotonic() - start
                if elapsed > self.constraints.max_wall_time_seconds:
                    logger.warning("Wall time exceeded for task %s", task.task_id)
                    partial = True
                    break

                iterations += 1
                response = await self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=openai_tools if tool_calls_used < effective_max_calls else [],
                    max_tokens=4096,
                )

                choice = response.choices[0]
                finish_reason = choice.finish_reason

                if finish_reason == "stop" or not choice.message.tool_calls:
                    final_text = choice.message.content or ""
                    break

                # Append assistant message with tool_calls
                messages.append(choice.message.model_dump(exclude_unset=False))

                # Process each tool call
                for tc in choice.message.tool_calls:
                    if tool_calls_used >= effective_max_calls:
                        logger.warning(
                            "Tool call budget exhausted (%d/%d) for task %s",
                            tool_calls_used,
                            effective_max_calls,
                            task.task_id,
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": (
                                "[Budget exhausted] No more tool calls allowed. "
                                "Summarize what you have found so far."
                            ),
                        })
                        partial = True
                        continue

                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # Loop detection
                    call_key = _call_key(tool_name, arguments)
                    if call_key in seen_calls:
                        logger.warning("Duplicate tool call: %s %s", tool_name, arguments)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": (
                                "[Loop detected] You already made this exact call. "
                                "Try a different query or approach."
                            ),
                        })
                        continue

                    seen_calls.add(call_key)
                    result = await call_tool_safe(session, tool_name, arguments)
                    tool_calls_used += 1

                    if result.success and result.data:
                        url = _extract_url(tool_name, arguments)
                        if url:
                            sources.append(Source(
                                url=url,
                                title=f"Result from {tool_name}",
                                tool=tool_name,
                                retrieved_at=datetime.utcnow(),
                            ))

                    content = result.data if result.success else _error_content(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(content),
                    })

                # If budget hit, get wrap-up from model
                if partial:
                    wrap_up = await self.client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=[],
                        max_tokens=2048,
                    )
                    final_text = wrap_up.choices[0].message.content or ""
                    break
            else:
                partial = True
                final_text = "Max iterations reached before task completion."

        confidence = _assess_confidence(final_text, sources, partial)
        gaps = _identify_gaps(task, final_text, partial)

        finding = ResearchFinding(
            task_id=task.task_id,
            content=final_text or "No content produced.",
            sources=sources,
            confidence=confidence,
            gaps=gaps,
            tool_calls_used=tool_calls_used,
            partial=partial,
        )

        logger.info(
            "Task %s complete: confidence=%s, sources=%d, tool_calls=%d, partial=%s",
            task.task_id,
            confidence,
            len(finding.sources),
            tool_calls_used,
            partial,
        )
        return finding

    def _build_task_prompt(self, task: ResearchTask) -> str:
        criteria = "\n".join(f"- {c}" for c in task.success_criteria)
        return (
            f"Research Task ID: {task.task_id}\n\n"
            f"Task: {task.description}\n\n"
            f"Success criteria (your answer must address all of these):\n{criteria}\n\n"
            f"Tool call budget: {task.max_tool_calls} calls maximum."
        )

    @asynccontextmanager
    async def _mcp_session(self):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(SEARXNG_SERVER)],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


def _call_key(tool_name: str, args: dict) -> str:
    digest = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16]
    return f"{tool_name}:{digest}"


def _extract_url(tool_name: str, args: dict) -> str | None:
    if tool_name == "fetch_page":
        return args.get("url")
    if tool_name == "web_search":
        return f"search: {args.get('query', '')}"
    return None


def _error_content(result) -> str:
    prefix = {
        "rate_limit": "[Rate limited]",
        "not_found": "[Not found]",
        "timeout": "[Timeout]",
        "bad_output": "[Bad output]",
        "unavailable": "[Tool unavailable]",
    }.get(result.error_class or "", "[Error]")
    return f"{prefix} {result.error_message}"


def _assess_confidence(text: str, sources: list[Source], partial: bool) -> str:
    if partial or not text:
        return "low"
    if len(sources) >= 2 and len(text) > 200:
        return "high"
    if sources or len(text) > 100:
        return "medium"
    return "low"


def _identify_gaps(task: ResearchTask, text: str, partial: bool) -> list[str]:
    gaps = []
    if partial:
        gaps.append("Response is partial — tool call budget or time limit reached")
    text_lower = text.lower()
    for criterion in task.success_criteria:
        key_words = [w for w in criterion.lower().split() if len(w) > 4]
        if not any(w in text_lower for w in key_words):
            gaps.append(f"Success criterion may not be fully addressed: {criterion}")
    return gaps
