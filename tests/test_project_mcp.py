import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProjectMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_action_and_image_over_real_stdio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'agent-settings.json').write_text(json.dumps({
                'default_project': 'test', 'projects': {'test': {'path': str(root), 'apps': ['unity']}}
            }))
            image = root / 'artifacts/test/frame.png'
            image.parent.mkdir(parents=True)
            png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1cAAAAASUVORK5CYII=')
            image.write_bytes(png)
            server = StdioServerParameters(command=sys.executable,
                args=['-m', 'ordax_dev_agent.mcp_server'],
                env={**os.environ, 'ORDAX_AGENT_STATE_DIR': directory},
                cwd=str(Path(__file__).resolve().parents[1]))
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    names = [tool.name for tool in (await session.list_tools()).tools]
                    self.assertIn('artifact_image', names)
                    response = await session.call_tool('projects_list', {})
                    self.assertFalse(response.isError)
                    self.assertIn('test', response.content[0].text)
                    response = await session.call_tool('artifact_image', {'project': 'test', 'artifact_path': str(image)})
                    self.assertFalse(response.isError)
                    self.assertEqual(base64.b64decode(response.content[1].data), png)
                    response = await session.call_tool('artifact_image', {'project': 'test', 'artifact_path': str(root / 'secret.png')})
                    self.assertTrue(response.isError)
                    response = await session.call_tool('action_execute', {'action': 'project.observe', 'project': 'missing'})
                    self.assertIn('project not registered', response.content[0].text)
