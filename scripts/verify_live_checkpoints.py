"""Blender --background --factory-startup --python-exit-code 1 --python this.py."""
import hashlib
import base64
import json
import runpy
import tempfile
import time
import uuid
from pathlib import Path

import bpy

companion = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_live_companion.py'))
with tempfile.TemporaryDirectory(prefix='ordax-checkpoints-') as temporary:
    root = Path(temporary)
    original = root / 'original.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(original))
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    texture = root / 'texture.png'
    texture.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1cAAAAASUVORK5CYII='))
    external = bpy.data.images.load(str(texture))
    external.filepath = '//texture.png'
    external.use_fake_user = True
    bpy.ops.mesh.primitive_cube_add(size=.25, location=(0, 0, 10))
    dirty_before = bpy.data.is_dirty
    companion['start'](str(root), allow_checkpoints=True, allow_restore=True,
                       allow_modeling=True, checkpoint_before_modeling=True)
    try:
        def command(action, arguments, session=None):
            session = session or json.loads((root / '.ordax/blender/presence.json').read_text())['session']
            command_id = uuid.uuid4().hex
            request = {'id': command_id, 'session': session, 'deadline': time.time() + 60,
                       'action': action, 'arguments': arguments}
            (root / '.ordax/blender/inbox' / f'{command_id}.json').write_text(json.dumps(request))
            companion['_tick']()
            return json.loads((root / '.ordax/blender/responses' / f'{command_id}.json').read_text())

        result = command('checkpoint_create', {'label': 'baseline'})
        assert result['ok'], result
        target = result['data']['checkpoint']
        assert bpy.data.filepath == str(original)
        assert bpy.data.is_dirty == dirty_before, 'Save Copy must preserve the unsaved-change flag'
        assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
        changed = command('model', {'operation': 'transform', 'arguments': {'object': 'Cube', 'location': [8, 0, 0]}})
        assert changed['ok'] and changed['data']['checkpoint'], changed
        assert bpy.data.objects['Cube'].location.x == 8
        old_session = result['data']['session']
        args = {'checkpoint_id': target['checkpoint_id'], 'expected_sha256': target['sha256'], 'confirm_replace_scene': True}
        corrupt = command('checkpoint_restore', {**args, 'expected_sha256': '0' * 64})
        assert not corrupt['ok'] and bpy.data.objects['Cube'].location.x == 8
        restored = command('checkpoint_restore', args)
        assert restored['ok'], restored
        assert bpy.data.objects['Cube'].location.x == 0
        assert Path(bpy.path.abspath(bpy.data.images['texture.png'].filepath)).resolve() == texture
        assert restored['data']['session'] != old_session
        assert Path(bpy.data.filepath) == Path(restored['data']['working_file'])
        assert not command('model', {'operation': 'transform', 'arguments': {'object': 'Cube', 'location': [99, 0, 0]}}, old_session)['ok']
        companion['_tick']()  # Publish the new session heartbeat after loading.
        backup = restored['data']['safety_checkpoint']
        recovered = command('checkpoint_restore', {'checkpoint_id': backup['checkpoint_id'],
            'expected_sha256': backup['sha256'], 'confirm_replace_scene': True})
        assert recovered['ok'], recovered
        assert bpy.data.objects['Cube'].location.x == 8
        assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
        immutable = root / '.ordax/blender/checkpoints' / target['checkpoint_id'] / 'checkpoint.blend'
        assert hashlib.sha256(immutable.read_bytes()).hexdigest() == target['sha256']
        assert bpy.app.timers.is_registered(companion['_tick'])
        print(json.dumps({'ok': True, 'restored_baseline': True, 'recovered_unsaved_change': True,
                          'old_session_rejected': True, 'original_unchanged': True, 'timer_survived_restore': True}))
    finally:
        companion['stop']()
