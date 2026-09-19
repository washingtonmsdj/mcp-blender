"""Run with Blender --background --factory-startup --python <this file>.

Checks the actual bpy integration in a disposable scene, not GUI timer scheduling.
"""
import hashlib
import json
import runpy
import tempfile
import time
import uuid
from pathlib import Path

import bpy

companion_path = Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_live_companion.py'
companion = runpy.run_path(str(companion_path))
with tempfile.TemporaryDirectory(prefix='ordax-live-check-') as temporary:
    root = Path(temporary)
    scripts = root / 'automation/blender'
    scripts.mkdir(parents=True)
    script = scripts / 'edit.py'
    script.write_text("bpy.data.objects['Cube'].location.x = 7.25", encoding='utf-8')
    session = companion['start'](str(root), allow_scripts=True)['session']
    try:
        assert bpy.app.timers.is_registered(companion['_tick'])
        for action, arguments in [('inspect', {}), ('run_script', {
            'script': str(script), 'sha256': hashlib.sha256(script.read_bytes()).hexdigest()
        }), ('inspect', {})]:
            command_id = uuid.uuid4().hex
            request = {'id': command_id, 'session': session, 'deadline': time.time() + 20,
                       'action': action, 'arguments': arguments}
            (root / '.ordax/blender/inbox' / f'{command_id}.json').write_text(json.dumps(request))
            companion['_tick']()
            result = json.loads((root / '.ordax/blender/responses' / f'{command_id}.json').read_text())
            assert result['ok'], result
        cube = next(o for o in result['data']['objects'] if o['name'] == 'Cube')
        assert cube['location'][0] == 7.25
        assert bpy.data.filepath == '', 'The scene must remain unsaved'
        print(json.dumps({'ok': True, 'blender': bpy.app.version_string,
                          'commands': 3, 'same_session': session == result['data']['session'],
                          'unsaved_cube_x': cube['location'][0]}))
    finally:
        companion['stop']()
