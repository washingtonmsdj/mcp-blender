from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class BlenderConnectionMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_blender_connection_is_a_real_mcp_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (root / "agent-settings.json").write_text(
                json.dumps({
                    "default_project": "demo",
                    "projects": {"demo": {"path": str(project), "apps": []}},
                }),
                encoding="utf-8",
            )
            server = StdioServerParameters(
                command=sys.executable,
                args=["-m", "ordax_studio.mcp_server"],
                env={
                    **os.environ,
                    "ORDAX_AGENT_STATE_DIR": directory,
                    "ORDAX_MEMORY_DB": str(root / "memory.db"),
                },
                cwd=str(Path(__file__).resolve().parents[1]),
            )
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    initialized = await session.initialize()
                    self.assertEqual("ordax-studio", initialized.serverInfo.name)
                    tools = await session.list_tools()
                    self.assertIn(
                        "prepare_blender_connection",
                        {tool.name for tool in tools.tools},
                    )
                    response = await session.call_tool(
                        "prepare_blender_connection",
                        {"project": "demo"},
                    )
                    self.assertFalse(response.isError)
                    payload = json.loads(response.content[0].text)
                    self.assertTrue(payload["ok"])
                    self.assertEqual("not_blender", payload["data"]["state"])
                    self.assertFalse(payload["data"]["can_start"])
                    self.assertFalse(payload["data"]["can_capture"])


if __name__ == "__main__":
    unittest.main()
