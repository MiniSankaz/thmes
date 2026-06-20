#!/usr/bin/env python3
"""builtin_mcp_server — Expose thmes's built-in tools as an MCP server.

Run via stdio. Used by thmes-pro to test MCP integration without external deps.
Configured in ~/.thmes/mcp.json (or ~/.thmes/mcp.json) as:

  "gemma-builtin": {
    "command": "thmes",
    "args": ["--mcp"]
  }
"""
import asyncio
import importlib.util
import importlib.machinery
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types


def _find_core_bin() -> Path:
    """Auto-detect the main thmes binary."""
    for name in ("thmes",):
        p = Path.home() / ".local/bin" / name
        if p.exists():
            return p
    return Path.home() / ".local/bin" / "thmes"


# Load thmes core to reuse its tools
_PATH = _find_core_bin()
_spec = importlib.util.spec_from_loader(
    "thmes_core",
    importlib.machinery.SourceFileLoader("thmes_core", str(_PATH))
)
core = importlib.util.module_from_spec(_spec)
sys.modules["thmes_core"] = core
_spec.loader.exec_module(core)

TOOLS = core.TOOLS


server = Server("gemma-builtin")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=name,
            description=info["desc"],
            inputSchema={
                "type": "object",
                "properties": {
                    k: {"type": "string", "description": v}
                    for k, v in info["params"].items()
                },
                "required": list(info["params"].keys())[:1],  # first param required
            },
        )
        for name, info in TOOLS.items()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name not in TOOLS:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    try:
        result = str(TOOLS[name]["fn"](**arguments))
    except Exception as e:
        result = f"Error: {type(e).__name__}: {e}"
    return [types.TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
