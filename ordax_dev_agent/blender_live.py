"""Local file IPC with a Blender companion running on its main thread."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

from .models import ActionResult
from .assets.blender_modeling import SCHEMAS, validate
from .assets.blender_checkpoints import listing, identifier


class BlenderLive:
    def __init__(self, project):
        self.project = project
        self.root = project.path('.ordax/blender', must_exist=False)

    def status(self):
        path = self.root / 'presence.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            age = max(0, time.time() - path.stat().st_mtime)
            return {**data, 'age_seconds': round(age, 3), 'connected': age < 5,
                    'project': self.project.slug, 'transport': 'blender-live'}
        except (OSError, ValueError):
            return {'connected': False, 'project': self.project.slug,
                    'transport': 'blender-live'}

    def result(self, command_id):
        if not isinstance(command_id, str) or uuid.UUID(command_id).hex != command_id:
            raise ValueError('command_id must be a UUID hex string')
        path = self.root / 'responses' / f'{command_id}.json'
        if not path.is_file():
            return ActionResult(False, 'No completed response; do not repeat a mutation',
                                {'command_id': command_id, 'outcome_unknown': True})
        data = json.loads(path.read_text(encoding='utf-8'))
        return ActionResult(data['ok'], data['summary'], data['data'])

    def request(self, action, arguments, timeout=15):
        status = self.status()
        if not status['connected']:
            return ActionResult(False, 'Blender live companion is not connected', status)
        timeout = max(1, min(300, float(timeout)))
        command_id = uuid.uuid4().hex
        inbox = self.root / 'inbox'
        inbox.mkdir(parents=True, exist_ok=True)
        pending = inbox / f'{command_id}.tmp'
        pending.write_text(json.dumps({'id': command_id, 'session': status['session'],
                                      'deadline': time.time() + timeout, 'action': action,
                                      'arguments': arguments}), encoding='utf-8')
        pending.replace(pending.with_suffix('.json'))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if (self.root / 'responses' / f'{command_id}.json').is_file():
                return self.result(command_id)
            time.sleep(.1)
        return ActionResult(False, 'Blender response timed out; query blender.live_result before retrying',
                            {'command_id': command_id, 'outcome_unknown': True,
                             'session': status['session'], 'transport': 'blender-live'})


class BlenderLiveActions:
    def blender_checkpoint_list(self, payload):
        project = self._project(payload)
        return ActionResult(True, 'Local Blender checkpoints (not uploaded)', {
            'project': project.slug, **listing(project.root, payload.get('limit', 20))})

    def blender_checkpoint_create(self, payload):
        project = self._project(payload)
        if project.blender.get('allow_checkpoints') is not True:
            raise ValueError('Checkpoint creation requires local allow_checkpoints: true')
        return BlenderLive(project).request('checkpoint_create', {'label': payload.get('label', 'manual')},
                                            payload.get('timeout_seconds', 120))

    def blender_checkpoint_restore(self, payload):
        project = self._project(payload)
        if project.blender.get('allow_restore') is not True or project.blender.get('allow_checkpoints') is not True:
            raise ValueError('Restore requires local allow_restore and allow_checkpoints: true')
        identifier(payload.get('checkpoint_id'))
        digest = payload.get('expected_sha256')
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('expected_sha256 from checkpoint metadata is required')
        if payload.get('confirm_replace_scene') is not True:
            raise ValueError('confirm_replace_scene: true is required')
        return BlenderLive(project).request('checkpoint_restore', {
            key: payload[key] for key in ('checkpoint_id', 'expected_sha256', 'confirm_replace_scene')
        }, payload.get('timeout_seconds', 120))

    def blender_modeling_tools(self, payload):
        project = self._project(payload)
        return ActionResult(True, 'Explicit modeling schemas; inspect before changing objects', {
            'project': project.slug, 'enabled_locally': project.blender.get('allow_modeling') is True,
            'tools': {f'blender.model_{name}': schema for name, schema in SCHEMAS.items()},
            'coordinates': 'object-local transforms; rotation input in XYZ degrees; lengths in scene units',
            'safety': 'No delete, apply modifier, file save or automatic retry. Check live_result after timeout.'})

    def blender_object_info(self, payload):
        name = payload.get('object')
        if not isinstance(name, str) or not name or len(name.encode('utf-8')) > 63:
            raise ValueError('object must be a valid object name')
        return BlenderLive(self._project(payload)).request('object_info', {'object': name})

    def _blender_model(self, operation, payload):
        project = self._project(payload)
        if project.blender.get('allow_modeling') is not True:
            raise ValueError('Modeling requires allow_modeling: true in local project settings')
        arguments = {key: value for key, value in payload.items() if key not in ('project', 'timeout_seconds')}
        validate(operation, arguments)
        protect = project.blender.get('checkpoint_before_modeling') is True
        if protect and project.blender.get('allow_checkpoints') is not True:
            raise ValueError('Automatic protection requires local allow_checkpoints: true')
        return BlenderLive(project).request('model', {'operation': operation, 'arguments': arguments,
                                            'checkpoint_before': protect},
                                            payload.get('timeout_seconds', 60))

    def blender_model_create(self, payload):
        return self._blender_model('create', payload)

    def blender_model_transform(self, payload):
        return self._blender_model('transform', payload)

    def blender_model_modifier(self, payload):
        return self._blender_model('modifier', payload)

    def _live_capture_artifacts(self, project, result):
        if not result.ok or 'views' not in result.data:
            return result
        command_id = result.data['command_id']
        if uuid.UUID(command_id).hex != command_id:
            raise ValueError('Invalid capture identifier')
        source = project.path(f'.ordax/blender/captures/{command_id}')
        target = self.config.state_dir / 'artifacts' / project.slug / command_id
        target.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for view in result.data['views']:
            name = view['view']
            if name not in ('front', 'right', 'top', 'perspective', 'back', 'left'):
                raise ValueError('Unsupported capture view')
            path = project.path(str(source / f'{name}.png'))
            if path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError('Capture image exceeds 20 MiB')
            content = path.read_bytes()
            if not content.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('Capture image is not a PNG')
            destination = target / f'{name}.png'
            destination.write_bytes(content)
            view['artifact'] = str(destination)
            view['sha256'] = hashlib.sha256(content).hexdigest()
            artifacts.append({'path': str(destination), 'kind': 'visual-frame', 'view': name})
        snapshot = target / 'snapshot.json'
        snapshot.write_text(json.dumps(result.data), encoding='utf-8')
        artifacts.append({'path': str(snapshot), 'kind': 'scene-snapshot'})
        result.data.update(artifacts=artifacts, snapshot_path=str(snapshot),
                           artifact=artifacts[0]['path'], project=project.slug)
        return result

    def blender_live_capture(self, payload):
        project = self._project(payload)
        arguments = {key: payload[key] for key in ('views', 'objects', 'size', 'style') if key in payload}
        result = BlenderLive(project).request('capture', arguments, payload.get('timeout_seconds', 120))
        return self._live_capture_artifacts(project, result)

    def blender_live_status(self, payload):
        data = BlenderLive(self._project(payload)).status()
        data['companion_path'] = str(Path(__file__).parent / 'assets' / 'blender_live_companion.py')
        return ActionResult(data['connected'], 'Blender live session status', data)

    def blender_live_inspect(self, payload):
        return BlenderLive(self._project(payload)).request(
            'inspect', {'limit': max(1, min(1000, int(payload.get('limit', 64))))},
            payload.get('timeout_seconds', 15))

    def blender_live_result(self, payload):
        project = self._project(payload)
        result = BlenderLive(project).result(payload.get('command_id'))
        return self._live_capture_artifacts(project, result)

    def blender_live_run_python(self, payload):
        project = self._project(payload)
        if not project.blender.get('allow_live_scripts', False):
            raise ValueError('Live scripts must be enabled in local project settings')
        script = project.path(str(payload.get('script_path', '')))
        allowed = project.path(project.blender.get('scripts_dir', 'automation/blender'))
        if not script.is_relative_to(allowed) or script.suffix.lower() != '.py' or not script.is_file():
            raise ValueError('Script must be a .py file inside the configured scripts_dir')
        return BlenderLive(project).request('run_script', {
            'script': str(script), 'sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
        }, payload.get('timeout_seconds', 60))
