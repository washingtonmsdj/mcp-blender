from __future__ import annotations

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(project_path: str | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    python = repo_root / ".venv" / "Scripts" / "python.exe"

    if not python.is_file():
        print("ERROR: .venv Python not found. Run scripts\\windows\\mcp-start.ps1 first.")
        return 2

    server = StdioServerParameters(
        command=str(python),
        args=["-m", "mcp_blender_unity.server"],
        cwd=str(repo_root),
        # This is our own trusted local bridge. Unity/UPM needs the normal
        # Windows user environment (USERPROFILE/APPDATA/LOCALAPPDATA/etc.).
        env=dict(os.environ),
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]

            print("MCP CONNECTED")
            print("Tools:", ", ".join(tool_names))

            arguments = {"project_path": project_path} if project_path else {}
            result = await session.call_tool("toolchain_status", arguments=arguments)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("project_path", nargs="?")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.project_path)))
