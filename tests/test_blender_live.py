import hashlib
import json
import runpy
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ordax_dev_agent.blender_live import BlenderLive, BlenderLiveActions
from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.projects import Project

COMPANION = Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_live_companion.py'


class BlenderLiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bpy = SimpleNamespace(
            data=SimpleNamespace(filepath='', is_dirty=True),
            context=SimpleNamespace(scene=SimpleNamespace(name='Unsaved', objects=[]), mode='OBJECT'),
            app=SimpleNamespace(version_string='test', timers=Mock()))
        with patch.dict('sys.modules', {'bpy': self.bpy}):
            self.companion = runpy.run_path(str(COMPANION))
        self.companion['start'](str(self.root), allow_scripts=True)
        self.addCleanup(self.companion['stop'])
        self.client = BlenderLive(Project('test', self.root, ('blender',)))

    def command(self, action='inspect', args=None, **overrides):
        command_id = uuid.uuid4().hex
        request = {'id': command_id, 'session': self.client.status()['session'],
                   'deadline': time.time() + 20, 'action': action, 'arguments': args or {}}
        request.update(overrides)
        (self.client.root / 'inbox' / f'{command_id}.json').write_text(json.dumps(request))
        self.companion['_tick']()
        return self.client.result(command_id), request

    def test_inspects_unsaved_live_scene(self):
        result, _ = self.command()
        self.assertTrue(result.ok)
        self.assertEqual(result.data['scene'], 'Unsaved')
        self.assertTrue(result.data['unsaved_changes'])
        self.assertEqual(result.data['file'], '')

    def test_client_round_trip_without_new_blender_process(self):
        with patch('ordax_dev_agent.blender_live.time.sleep', side_effect=lambda _: self.companion['_tick']()):
            result = self.client.request('inspect', {})
        self.assertTrue(result.ok)

    def test_rejects_old_session_and_expired_command(self):
        self.assertFalse(self.command(session='old')[0].ok)
        self.assertFalse(self.command(deadline=0)[0].ok)

    def test_refuses_different_project_opened_after_pairing(self):
        self.bpy.data.filepath = str(self.root.parent / 'other.blend')
        self.assertFalse(self.command()[0].ok)

    def test_script_changes_live_state_and_is_not_replayed(self):
        directory = self.root / 'automation/blender'
        directory.mkdir(parents=True)
        script = directory / 'edit.py'
        script.write_text("bpy.context.scene.name += ' changed'")
        args = {'script': str(script), 'sha256': hashlib.sha256(script.read_bytes()).hexdigest()}
        result, request = self.command('run_script', args)
        self.assertTrue(result.ok)
        (self.client.root / 'inbox' / f"{request['id']}.json").write_text(json.dumps(request))
        self.companion['_tick']()
        self.assertEqual(self.bpy.context.scene.name, 'Unsaved changed')
        self.assertFalse(self.command('run_script', {**args, 'sha256': 'changed'})[0].ok)

    def test_scripts_require_explicit_local_permission(self):
        self.companion['stop']()
        self.companion['start'](str(self.root))
        self.assertFalse(self.command('run_script', {})[0].ok)

    def test_second_companion_cannot_take_project(self):
        with patch.dict('sys.modules', {'bpy': self.bpy}):
            other = runpy.run_path(str(COMPANION))
        with self.assertRaises(RuntimeError):
            other['start'](str(self.root))

    def test_missing_response_is_unknown_not_retry_permission(self):
        result = self.client.result(uuid.uuid4().hex)
        self.assertTrue(result.data['outcome_unknown'])
        with self.assertRaises(ValueError):
            self.client.result('../escape')

    def capture_result(self):
        command_id = uuid.uuid4().hex
        folder = self.root / '.ordax/blender/captures' / command_id
        folder.mkdir(parents=True)
        (folder / 'front.png').write_bytes(b'\x89PNG\r\n\x1a\nexample')
        result = ActionResult(True, 'capture', {'command_id': command_id,
                                              'views': [{'view': 'front', 'filename': 'front.png'}]})
        agent = BlenderLiveActions()
        agent.config = SimpleNamespace(state_dir=self.root / 'state')
        return agent, result, folder

    def test_capture_images_are_exported_to_mcp_artifact_root(self):
        agent, result, _ = self.capture_result()
        exported = agent._live_capture_artifacts(self.client.project, result)
        image = Path(exported.data['views'][0]['artifact'])
        self.assertTrue(image.is_relative_to(agent.config.state_dir / 'artifacts/test'))
        self.assertEqual(len(exported.data['artifacts']), 2)
        self.assertTrue(Path(exported.data['snapshot_path']).is_file())

    def test_rejects_capture_view_path_traversal(self):
        agent, result, _ = self.capture_result()
        result.data['views'][0]['view'] = '../secret'
        with self.assertRaises(ValueError):
            agent._live_capture_artifacts(self.client.project, result)

    def test_rejects_invalid_image_content(self):
        agent, result, folder = self.capture_result()
        (folder / 'front.png').write_bytes(b'not an image')
        with self.assertRaises(ValueError):
            agent._live_capture_artifacts(self.client.project, result)

    def test_late_capture_result_exports_images(self):
        agent, result, _ = self.capture_result()
        agent._project = lambda payload: self.client.project
        with patch.object(BlenderLive, 'result', return_value=result):
            exported = agent.blender_live_result({'command_id': result.data['command_id']})
        self.assertTrue(Path(exported.data['artifact']).is_file())


if __name__ == '__main__':
    unittest.main()
