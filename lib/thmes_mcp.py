"""thmes_mcp — MCP client integration for thmes ecosystem.

Loads MCP server definitions from ~/.thmes/mcp.json, spawns them via stdio,
exposes their tools through a uniform `MCPManager.call_tool(name, args)` API.

mcp.json format (compatible with Claude Code):
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/you"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "..."}
    }
  }
}
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


THMES_HOME = Path.home() / ".thmes"
MCP_CONFIG = THMES_HOME / "mcp.json"


class MCPManager:
    """Manages multiple MCP server connections and routes tool calls."""

    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, dict] = {}  # name → {server, description, schema}
        self.exit_stack = AsyncExitStack()
        self._loop = None
        self._thread = None
        self._ready = asyncio.Event() if False else None
        self.config: dict = {}

    @classmethod
    def load_config(cls) -> dict:
        if not MCP_CONFIG.exists():
            return {}
        try:
            return json.loads(MCP_CONFIG.read_text())
        except json.JSONDecodeError:
            return {}

    async def start(self):
        """Connect to all configured MCP servers."""
        cfg = self.load_config()
        servers = cfg.get("mcpServers", {})
        if not servers:
            return

        for name, spec in servers.items():
            if not spec.get("command"):
                continue
            try:
                params = StdioServerParameters(
                    command=spec["command"],
                    args=spec.get("args", []),
                    env={**os.environ, **(spec.get("env") or {})},
                )
                # Note: stdio_client + ClientSession need exit_stack management
                transport = await self.exit_stack.enter_async_context(stdio_client(params))
                read, write = transport
                session = await self.exit_stack.enter_async_context(
                    ClientSession(read, write))
                await session.initialize()
                self.sessions[name] = session
                # Discover tools
                tools_resp = await session.list_tools()
                for t in tools_resp.tools:
                    # Prefix tool name with server to avoid collision
                    qualified = f"{name}.{t.name}"
                    self.tools[qualified] = {
                        "server": name,
                        "name": t.name,
                        "description": t.description or "",
                        "input_schema": t.inputSchema if hasattr(t, "inputSchema") else {},
                    }
            except Exception as e:
                print(f"[MCP] failed to start '{name}': {e}", file=sys.stderr)

    async def call_tool(self, qualified_name: str, arguments: dict) -> Any:
        """Call a tool via its qualified name 'server.tool'."""
        if qualified_name not in self.tools:
            raise KeyError(f"Unknown MCP tool: {qualified_name}")
        info = self.tools[qualified_name]
        session = self.sessions[info["server"]]
        result = await session.call_tool(info["name"], arguments=arguments)
        # Concatenate text content blocks
        out = []
        for block in result.content:
            if hasattr(block, "text"):
                out.append(block.text)
            else:
                out.append(str(block))
        return "\n".join(out)

    async def close(self):
        await self.exit_stack.aclose()

    def list_tools(self) -> list[dict]:
        return [{
            "name": qn,                 # qualified: "server.tool"
            "server": info["server"],
            "tool": info["name"],       # raw name on server
            "description": info["description"],
            "input_schema": info.get("input_schema", {}),
        } for qn, info in self.tools.items()]


# ── Sync wrapper for non-async callers (thmes legacy / threads) ────────
class SyncMCPClient:
    """Runs MCPManager in a dedicated background loop, exposes sync call_tool().

    Why: thmes's tool execution is synchronous. MCP is async. This wrapper
    bridges them by keeping a background asyncio loop alive in a thread.
    """
    def __init__(self):
        import threading
        self.mgr = MCPManager()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready_evt = threading.Event()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _submit(self, coro):
        """Submit coro to the background loop and wait for result (sync)."""
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=60)

    def start(self) -> int:
        """Connect to MCP servers. Returns number of tools discovered."""
        self._submit(self.mgr.start())
        return len(self.mgr.tools)

    def call(self, qualified_name: str, args: dict, timeout: float = 60) -> str:
        fut = asyncio.run_coroutine_threadsafe(
            self.mgr.call_tool(qualified_name, args), self._loop)
        return fut.result(timeout=timeout)

    def tools(self) -> list[dict]:
        return self.mgr.list_tools()

    def close(self):
        try:
            self._submit(self.mgr.close())
        except Exception: pass
        self._loop.call_soon_threadsafe(self._loop.stop)
