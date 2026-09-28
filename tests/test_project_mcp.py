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
                env={**os.environ, 'ORDAX_AGENT_STATE_DIR': directory,
                     'ORDAX_MEMORY_DB': str(root / 'memory.db')},
                cwd=str(Path(__file__).resolve().parents[1]))
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    names = [tool.name for tool in (await session.list_tools()).tools]
                    self.assertIn('artifact_image', names)
                    self.assertIn('blender_live_view', names)
                    self.assertIn('blender_live_multiview', names)
                    self.assertIn('session_context', names)
                    self.assertIn('project_health', names)
                    self.assertIn('session_resume', names)
                    self.assertIn('session_finish', names)
                    self.assertIn('memory_remember', names)
                    self.assertIn('session_checkpoint', names)
                    self.assertIn('project_preview_image', names)
                    self.assertIn('project_preview_start', names)
                    self.assertIn('project_preview_stop', names)
                    response = await session.call_tool('projects_list', {})
                    self.assertFalse(response.isError)
                    self.assertIn('test', response.content[0].text)
                    health = await session.call_tool('project_health', {'project': 'test'})
                    self.assertFalse(health.isError)
                    self.assertIn('memory', health.content[0].text)
                    resumed = await session.call_tool('session_resume', {'project': 'test'})
                    self.assertFalse(resumed.isError)
                    resumed_payload = json.loads(resumed.content[0].text)
                    session_id = resumed_payload['data']['session_id']
                    response = await session.call_tool('memory_remember', {'project': 'test', 'content': 'resume me'})
                    self.assertFalse(response.isError)
                    response = await session.call_tool('session_context', {'project': 'test'})
                    self.assertFalse(response.isError)
                    self.assertIn('resume me', response.content[0].text)
                    response = await session.call_tool('session_checkpoint', {'project': 'test', 'summary': 'stdio checkpoint'})
                    self.assertFalse(response.isError)
                    finished = await session.call_tool('session_finish', {'session_id': session_id})
                    self.assertFalse(finished.isError)
                    preview = await session.call_tool('project_preview_image', {'project': 'test'})
                    self.assertFalse(preview.isError)
                    self.assertEqual('image', preview.content[1].type)
                    response = await session.call_tool('artifact_image', {'project': 'test', 'artifact_path': str(image)})
                    self.assertFalse(response.isError)
                    self.assertEqual(base64.b64decode(response.content[1].data), png)
                    response = await session.call_tool('artifact_image', {'project': 'test', 'artifact_path': str(root / 'secret.png')})
                    self.assertTrue(response.isError)
                    response = await session.call_tool('action_execute', {'action': 'project.observe', 'project': 'missing'})
                    self.assertIn('project not registered', response.content[0].text)
