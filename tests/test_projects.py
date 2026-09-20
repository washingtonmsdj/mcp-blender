import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch, Mock

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.execution_lock import ExecutionLock
from ordax_dev_agent.models import AgentJob, ActionResult
from ordax_dev_agent.projects import load_projects
from ordax_dev_agent.unity_editor_bridge import UnityEditorBridge


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.config = AgentConfig('test', None, None, 5, self.root / 'state', self.root / 'agent',
                                  self.root / 'hordax', self.root / 'bridge',
                                  projects={'model': {'path': str(self.project), 'apps': ['blender', 'unity']}},
                                  default_project='model')

    def test_legacy_hordax_and_explicit_empty_registry(self):
        self.assertIn('hordax', load_projects(replace(self.config, projects=None)))
        self.assertEqual(load_projects(replace(self.config, projects={})), {})

    def test_invalid_settings_never_fall_back_to_another_project(self):
        self.config.state_dir.mkdir()
        (self.config.state_dir / 'agent-settings.json').write_text('{broken')
        with patch.dict(os.environ, {'ORDAX_AGENT_STATE_DIR': str(self.config.state_dir)}):
            with self.assertRaises(ValueError):
                AgentConfig.from_env()

    def test_custom_companion_source_is_used(self):
        registry = ActionRegistry(replace(self.config, projects={'model': {
            'path': str(self.project), 'apps': ['unity'],
            'unity': {'companion_source': 'Assets/Editor/Custom.cs'}}}))
        self.assertEqual(
            registry._editor({}).companion_source_path,
            (self.project / 'Assets/Editor/Custom.cs').resolve(),
        )


    def test_generic_project_never_falls_back_to_hordax_companion(self):
        registry = ActionRegistry(self.config)
        self.assertEqual(
            registry._editor({}).companion_source_path,
            (self.project / 'Assets/OrdaX/Editor/OrdaXGenericAgent.cs').resolve(),
        )

    def test_hordax_profile_routes_to_dedicated_companion(self):
        registry = ActionRegistry(replace(self.config, projects={'model': {
            'path': str(self.project), 'apps': ['unity'],
            'unity': {'profile': 'hordax'}}}))
        self.assertEqual(
            registry._editor({}).companion_source_path,
            (self.project / 'Assets/HORDAX/Editor/OrdaXEditorAgent.cs').resolve(),
        )

    def test_jobs_route_to_registered_project_without_git(self):
        job = AgentJob('id', 'project.observe', project_slug='model')
        registry = ActionRegistry(self.config)
        self.assertEqual(registry._project_path(job.action_payload()), self.project.resolve())
        self.assertFalse(registry.execute('project.observe', {'project': 'unknown'}).ok)
        with self.assertRaises(ValueError):
            AgentJob('id', 'git.sync', {'project': 'other'}, project_slug='model').action_payload()

    def test_paths_cannot_escape_project(self):
        project = load_projects(self.config)['model']
        for path in ['../secret', str(self.root / 'secret')]:
            with self.assertRaises(ValueError):
                project.path(path, must_exist=False)

    def test_app_must_be_enabled(self):
        registry = ActionRegistry(replace(self.config, projects={'model': {'path': str(self.project), 'apps': []}}))
        self.assertFalse(registry.execute('unity.install_companion', {}).ok)

    def test_capture_paths_are_unique_and_project_scoped(self):
        registry = ActionRegistry(self.config)
        first = registry._capture_output({})
        second = registry._capture_output({})
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_relative_to(self.config.state_dir / 'artifacts/model'))

    def test_companion_install_is_idempotent_and_preserves_edits(self):
        (self.project / 'Assets').mkdir()
        registry = ActionRegistry(self.config)
        result = registry.execute('unity.install_companion', {})
        self.assertTrue(result.ok)
        self.assertTrue(registry.execute('unity.install_companion', {}).ok)
        target = Path(result.data['path'])
        target.write_text('// user changes')
        self.assertFalse(registry.execute('unity.install_companion', {}).ok)
        self.assertEqual(target.read_text(), '// user changes')

    def test_blender_snapshot_survives_failed_render(self):
        blend = self.project / 'scene.blend'
        blend.touch()
        def run(command, **kwargs):
            request = json.loads(Path(command[-1]).read_text())
            Path(request['snapshot']).write_text('{"camera": null}')
            return {'ok': False, 'returncode': 1, 'stderr': 'No camera'}
        registry = ActionRegistry(self.config)
        with patch('ordax_dev_agent.observations.find_blender', return_value=Path('blender')), \
             patch('ordax_dev_agent.observations.run_process', side_effect=run):
            result = registry.execute('blender.render_preview', {'blend_file': 'scene.blend'})
        self.assertFalse(result.ok)
        self.assertIn('snapshot_path', result.data)
        self.assertNotIn('artifact', result.data)

    def test_observation_stops_on_failure(self):
        registry = ActionRegistry(self.config)
        with patch.object(registry, 'blender_render_preview', return_value=ActionResult(False, 'no camera')) as render:
            result = registry.execute('observation.capture', {'app': 'blender', 'frames': 12})
        self.assertFalse(result.ok)
        self.assertEqual(render.call_count, 1)

    def test_frame_progress_is_emitted_before_sequence_finishes(self):
        registry = ActionRegistry(self.config)
        progress = []
        registry.on_observation = lambda item: progress.append(item['index'])
        def capture(payload):
            self.assertEqual(len(progress), capture.calls)
            capture.calls += 1
            return ActionResult(True, 'frame')
        capture.calls = 0
        with patch.object(registry, 'blender_render_preview', side_effect=capture), patch('ordax_dev_agent.observations.time.sleep'):
            result = registry.execute('observation.capture', {'app': 'blender', 'frames': 3})
        self.assertTrue(result.ok)
        self.assertEqual(progress, [0, 1, 2])

    def test_adapter_is_locally_enabled_and_project_scoped(self):
        entry = Mock()
        entry.name = 'example'
        handler = Mock(return_value=ActionResult(True, 'observed'))
        entry.load.return_value = lambda config: {'observe': handler}
        config = replace(self.config, adapters=('example',))
        with patch('ordax_dev_agent.actions.entry_points', return_value=[entry]):
            registry = ActionRegistry(config)
        self.assertFalse(registry.execute('example.observe', {}).ok)
        handler.assert_not_called()
        config = replace(config, projects={'model': {'path': str(self.project), 'apps': ['example']}})
        with patch('ordax_dev_agent.actions.entry_points', return_value=[entry]):
            registry = ActionRegistry(config)
        self.assertTrue(registry.execute('example.observe', {}).ok)
        self.assertEqual(handler.call_args.args[0].slug, 'model')

    def test_latest_preview_never_crosses_projects(self):
        registry = ActionRegistry(self.config)
        output = registry._capture_output({})
        output.write_bytes(b'frame')
        registry._record_capture({}, output)
        self.assertTrue(registry.execute('artifact.preview', {}).ok)
        self.assertFalse(registry.execute('artifact.preview', {'artifact_name': '../../secret'}).ok)

    def test_cloud_upload_cache_deduplicates_progress_and_final_result(self):
        from ordax_dev_agent.main import _upload_result_artifacts
        image = self.root / 'capture.png'
        image.write_bytes(b'frame')
        control = Mock()
        control.upload_artifact.return_value = {'artifact_id': 'id'}
        job = AgentJob('id', 'observation.capture', project_slug='model')
        cache = {}
        first = _upload_result_artifacts(control, job, ActionResult(True, 'frame', {'artifact': str(image)}), cache)
        final = _upload_result_artifacts(control, job, ActionResult(True, 'done', {'artifacts': [{'path': str(image)}]}), cache)
        self.assertEqual(first, final)
        self.assertEqual(control.upload_artifact.call_count, 1)

    def test_process_lock_excludes_second_client(self):
        first, second = ExecutionLock(self.config.state_dir), ExecutionLock(self.config.state_dir)
        self.assertTrue(first.acquire())
        try:
            self.assertFalse(second.acquire())
            self.assertFalse(ActionRegistry(self.config).execute('project.observe', {}).ok)
        finally:
            first.release()
        self.assertTrue(second.acquire())
        second.release()

    def test_unity_timeout_does_not_return_retryable_none(self):
        bridge = UnityEditorBridge(self.project)
        with patch.object(bridge, 'presence_is_fresh', side_effect=[True, False]):
            result = bridge.request('capture', {'id': '../bad', 'action': 'bad'}, timeout_seconds=1)
        self.assertFalse(result.ok)
        self.assertTrue(result.data['outcome_unknown'])
        self.assertFalse(list(bridge.inbox.glob('*.json')))


    def test_unity_editor_status_is_observational_and_never_nudges(self):
        registry = ActionRegistry(self.config)
        editor = Mock()
        editor.status.return_value = {
            "project_appears_open": True,
            "presence_fresh": False,
        }

        with patch.object(registry, "_editor", return_value=editor):
            result = registry.unity_editor_status({"project": "model"})

        self.assertFalse(result.ok)
        self.assertEqual("Unity Editor companion not ready", result.summary)
        editor.status.assert_called_once_with()
        editor.nudge_companion.assert_not_called()

    def test_unity_refresh_prefers_typed_companion_without_foreground_helper(self):
        registry = ActionRegistry(self.config)
        presence = self.root / "editor-presence.json"
        presence.write_text("{}", encoding="utf-8")
        initial_mtime = presence.stat().st_mtime

        editor = Mock()
        editor.presence = presence
        editor.project_appears_open.return_value = True
        editor.presence_is_fresh.return_value = True
        editor.status.return_value = {"presence": {"compiling": False}}

        def request(action, payload, timeout_seconds):
            self.assertEqual("refresh", action)
            os.utime(presence, (initial_mtime + 2.0, initial_mtime + 2.0))
            return ActionResult(True, "Asset refresh requested", {"transport": "unity-editor-companion"})

        editor.request.side_effect = request

        with (
            patch.object(registry, "_editor", return_value=editor),
            patch("ordax_dev_agent.unity_actions._run") as foreground_helper,
        ):
            result = registry.unity_refresh_editor(
                {"project": "model", "force": True, "wait_seconds": 5}
            )

        self.assertTrue(result.ok)
        self.assertEqual("unity-editor-companion", result.data["refresh_transport"])
        foreground_helper.assert_not_called()


if __name__ == '__main__':
    unittest.main()
