"""GitHub MCP server — runs as a stdio subprocess.

Implements search_repositories, get_file_contents, search_code
via the GitHub REST API. Reads GITHUB_TOKEN from environment.
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

GITHUB_API = "https://api.github.com"
MAX_RESULTS = 8
MAX_FILE_CHARS = 15_000

app = Server("github")

def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_repositories",
            description=(
                "Search GitHub for repositories matching a query. "
                "Returns name, description, URL, stars, and language."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GitHub repository search query (supports qualifiers like language:python)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max repositories to return (default 5, max 8)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_file_contents",
            description=(
                "Read the contents of a specific file in a GitHub repository. "
                "Use owner/repo format and a file path relative to the repo root."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner (username or org)"},
                    "repo": {"type": "string", "description": "Repository name"},
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "ref": {
                        "type": "string",
                        "description": "Branch, tag, or commit SHA (default: repo default branch)",
                    },
                },
                "required": ["owner", "repo", "path"],
            },
        ),
        types.Tool(
            name="search_code",
            description=(
                "Search for code across GitHub repositories. "
                "Returns file paths, repository names, and URLs. "
                "Requires GITHUB_TOKEN for authentication."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Code search query. Supports qualifiers like "
                            "repo:owner/name, language:python, path:src/"
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (default 5, max 8)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_repositories":
        return await _search_repositories(
            query=arguments["query"],
            max_results=min(int(arguments.get("max_results", 5)), MAX_RESULTS),
        )
    if name == "get_file_contents":
        return await _get_file_contents(
            owner=arguments["owner"],
            repo=arguments["repo"],
            path=arguments["path"],
            ref=arguments.get("ref"),
        )
    if name == "search_code":
        return await _search_code(
            query=arguments["query"],
            max_results=min(int(arguments.get("max_results", 5)), MAX_RESULTS),
        )
    raise ValueError(f"Unknown tool: {name}")


async def _search_repositories(query: str, max_results: int) -> list[types.TextContent]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{GITHUB_API}/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": max_results},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    if not items:
        return [types.TextContent(type="text", text=f"No repositories found for: {query}")]

    lines = [f"GitHub repository search: {query} ({data.get('total_count', 0)} total)\n"]
    for i, r in enumerate(items, 1):
        lines.append(f"{i}. {r['full_name']} ⭐ {r.get('stargazers_count', 0)}")
        if r.get("description"):
            lines.append(f"   {r['description']}")
        lines.append(f"   URL: {r['html_url']}")
        lang = r.get("language")
        if lang:
            lines.append(f"   Language: {lang}")
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _get_file_contents(
    owner: str, repo: str, path: str, ref: str | None
) -> list[types.TextContent]:
    params = {}
    if ref:
        params["ref"] = ref

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path.lstrip('/')}",
            params=params,
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        # Directory listing
        names = [f"  {'[dir] ' if item['type'] == 'dir' else ''}{item['name']}" for item in data]
        text = f"Directory: {owner}/{repo}/{path}\n" + "\n".join(names)
        return [types.TextContent(type="text", text=text)]

    encoding = data.get("encoding", "")
    if encoding == "base64":
        raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    else:
        raw = data.get("content", "")

    raw = raw[:MAX_FILE_CHARS]
    truncated = len(data.get("content", "")) > MAX_FILE_CHARS
    header = f"File: {owner}/{repo}/{path}"
    if ref:
        header += f" @ {ref}"
    if truncated:
        raw += f"\n\n[truncated at {MAX_FILE_CHARS} chars]"

    return [types.TextContent(type="text", text=f"{header}\n\n{raw}")]


async def _search_code(query: str, max_results: int) -> list[types.TextContent]:
    if not os.environ.get("GITHUB_TOKEN"):
        return [types.TextContent(
            type="text",
            text="[Error] search_code requires GITHUB_TOKEN — unauthenticated code search is not supported by GitHub API.",
        )]

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GITHUB_API}/search/code",
            params={"q": query, "per_page": max_results},
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    if not items:
        return [types.TextContent(type="text", text=f"No code found for: {query}")]

    lines = [f"GitHub code search: {query} ({data.get('total_count', 0)} total)\n"]
    for i, item in enumerate(items, 1):
        repo = item.get("repository", {}).get("full_name", "unknown")
        lines.append(f"{i}. {item['path']} in {repo}")
        lines.append(f"   URL: {item['html_url']}")
        lines.append("")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
