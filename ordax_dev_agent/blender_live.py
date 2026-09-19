"""Local file IPC with a Blender companion running on its main thread."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

from .models import ActionResult


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
    def blender_live_status(self, payload):
        data = BlenderLive(self._project(payload)).status()
        data['companion_path'] = str(Path(__file__).parent / 'assets' / 'blender_live_companion.py')
        return ActionResult(data['connected'], 'Blender live session status', data)

    def blender_live_inspect(self, payload):
        return BlenderLive(self._project(payload)).request(
            'inspect', {'limit': max(1, min(1000, int(payload.get('limit', 64))))},
            payload.get('timeout_seconds', 15))

    def blender_live_result(self, payload):
        return BlenderLive(self._project(payload)).result(payload.get('command_id'))

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
