"""MultiServerClient — connects to multiple MCP servers simultaneously.

Aggregates tool listings across all servers and routes each tool call
to the correct server. Uses AsyncExitStack to manage subprocess lifetimes.
"""
from __future__ import annotations

import logging
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    name: str
    script: Path
    env: dict[str, str] | None = None


class MultiServerClient:
    """Manages multiple MCP server connections behind a single interface."""

    def __init__(self, servers: list[ServerConfig]) -> None:
        self._servers = servers
        self._sessions: dict[str, ClientSession] = {}
        self._tool_to_session: dict[str, ClientSession] = {}
        self._tools: list = []
        self._stack = AsyncExitStack()

    async def __aenter__(self) -> MultiServerClient:
        await self._stack.__aenter__()
        for server in self._servers:
            try:
                params = StdioServerParameters(
                    command=sys.executable,
                    args=[str(server.script)],
                    env=server.env,
                )
                read, write = await self._stack.enter_async_context(
                    stdio_client(params)
                )
                session = await self._stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                tools_resp = await session.list_tools()

                self._sessions[server.name] = session
                for tool in tools_resp.tools:
                    self._tool_to_session[tool.name] = session
                    self._tools.append(tool)

                logger.info(
                    "Connected to MCP server '%s' — %d tools: %s",
                    server.name,
                    len(tools_resp.tools),
                    [t.name for t in tools_resp.tools],
                )
            except Exception as exc:
                logger.error("Failed to start MCP server '%s': %s", server.name, exc)
                # Continue without this server — partial tool set is better than crash
                raise

        return self

    async def __aexit__(self, *args) -> None:
        await self._stack.__aexit__(*args)

    async def list_tools(self) -> list:
        return self._tools

    async def call_tool(self, name: str, arguments: dict):
        session = self._tool_to_session.get(name)
        if session is None:
            raise ValueError(f"No MCP server registered for tool: {name!r}")
        return await session.call_tool(name, arguments)

    @property
    def tool_names(self) -> list[str]:
        return list(self._tool_to_session.keys())
