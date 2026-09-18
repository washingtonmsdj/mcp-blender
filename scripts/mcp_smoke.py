from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    python = repo_root / ".venv" / "Scripts" / "python.exe"

    if not python.is_file():
        print("ERROR: .venv Python not found. Run scripts\\windows\\mcp-start.ps1 first.")
        return 2

    server = StdioServerParameters(
        command=str(python),
        args=["-m", "mcp_blender_unity.server"],
        cwd=str(repo_root),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]

            print("MCP CONNECTED")
            print("Tools:", ", ".join(tool_names))

            result = await session.call_tool("toolchain_status", arguments={})
            print("toolchain_status:")

            for item in result.content:
                text = getattr(item, "text", None)
                if text:
                    try:
                        print(json.dumps(json.loads(text), indent=2, ensure_ascii=False))
                    except Exception:
                        print(text)

            if getattr(result, "isError", False):
                print("ERROR: toolchain_status returned an MCP error.")
                return 3

    print("MCP SMOKE TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
