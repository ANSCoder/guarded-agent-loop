"""Milestone 3: connect to MCP servers over stdio and expose their tools as runtime tools."""

import asyncio
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agent_runtime.tools.base import Tool

STARTUP_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class ServerSpec:
    """One MCP server to start over stdio."""

    name: str
    command: str
    args: tuple[str, ...]


def load_servers(path: Path) -> list[ServerSpec]:
    """Read the [servers.<name>] tables. Entries with no command are skipped."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    servers: list[ServerSpec] = []
    for name, row in data.get("servers", {}).items():
        if "command" not in row:
            print(f"warning: MCP server {name!r} has no command, skipped", file=sys.stderr)
            continue
        servers.append(ServerSpec(name, row["command"], tuple(row.get("args", []))))
    return servers


async def _list(spec: ServerSpec) -> list[Any]:
    async with stdio_client(StdioServerParameters(command=spec.command, args=list(spec.args))) as (
        read,
        write,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return list((await session.list_tools()).tools)


async def _call(spec: ServerSpec, tool: str, args: dict[str, Any]) -> str:
    # shortcut: starts the server process for every call, upgrade to one session per server
    params = StdioServerParameters(command=spec.command, args=list(spec.args))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
    text = "".join(getattr(c, "text", "") for c in result.content)
    if result.isError:
        raise RuntimeError(text)
    return text


def _runner(spec: ServerSpec, tool: str) -> Callable[[dict[str, Any]], str]:
    def run(args: dict[str, Any]) -> str:
        return asyncio.run(_call(spec, tool, args))

    return run


def mcp_tools(servers: list[ServerSpec]) -> list[Tool]:
    """Start each server and wrap its tools as <server>__<tool>. Failing servers are skipped."""
    tools: list[Tool] = []
    for spec in servers:
        try:
            remote_tools = asyncio.run(asyncio.wait_for(_list(spec), STARTUP_TIMEOUT_S))
        except Exception as exc:  # one broken server must not stop the others or the CLI
            print(f"warning: MCP server {spec.name!r} skipped: {exc!r}", file=sys.stderr)
            continue
        for remote in remote_tools:
            tools.append(
                Tool(
                    name=f"{spec.name}__{remote.name}",
                    description=remote.description or "",
                    input_schema=remote.inputSchema,
                    run=_runner(spec, remote.name),
                )
            )
    return tools
