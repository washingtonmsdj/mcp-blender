"""Blender --background --factory-startup --python-exit-code 1 --python this.py -- OUTPUT_DIR."""
import json
import runpy
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import patch, Mock
from types import SimpleNamespace

import bpy

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
companion = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_live_companion.py'))
cube = bpy.data.objects['Cube']
cube.scale = (1.5, .6, 2)
cube.location = (2, -1, .5)
modifier = cube.modifiers.new('Preview bevel', 'BEVEL')
modifier.width = .15
modifier.segments = 3
bpy.context.view_layer.update()
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = .01


def original_state():
    return {'camera': bpy.context.scene.camera.name, 'scene': bpy.context.scene.name,
            'render_path': bpy.context.scene.render.filepath,
            'engine': bpy.context.scene.render.engine,
            'selected': [o.name for o in bpy.context.selected_objects],
            'transform': [list(row) for row in cube.matrix_world],
            'counts': [len(data) for data in (bpy.data.scenes, bpy.data.objects, bpy.data.meshes,
                                             bpy.data.cameras, bpy.data.worlds)]}


before = original_state()
session = companion['start'](str(root))['session']
try:
    for style in ('solid', 'silhouette'):
        command_id = uuid.uuid4().hex
        request = {'id': command_id, 'session': session, 'deadline': time.time() + 120,
                   'action': 'capture', 'arguments': {'objects': ['Cube'], 'style': style, 'size': 256}}
        (root / '.ordax/blender/inbox' / f'{command_id}.json').write_text(json.dumps(request))
        companion['_tick']()
        result = json.loads((root / '.ordax/blender/responses' / f'{command_id}.json').read_text())
        assert result['ok'], result
        assert abs(result['data']['unit_scale_m'] - .01) < .000001
        folder = root / '.ordax/blender/captures' / command_id
        for view in result['data']['views']:
            image = folder / view['filename']
            assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        assert before == original_state(), (before, original_state())
        assert bpy.data.filepath == ''
        print(json.dumps({'style': style, 'folder': str(folder), 'views': 4, 'scene_preserved': True}))
    capture = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_multiview.py'))['capture']
    failing_bpy = SimpleNamespace(data=bpy.data, context=bpy.context, app=bpy.app,
        ops=SimpleNamespace(render=SimpleNamespace(render=Mock(side_effect=RuntimeError('Simulated render failure')))))
    with patch.dict(capture.__globals__, {'bpy': failing_bpy}):
        try:
            capture({'objects': ['Cube']}, root / 'failed-capture')
        except RuntimeError as error:
            assert str(error) == 'Simulated render failure'
        else:
            raise AssertionError('Expected injected render failure')
    assert before == original_state(), 'Temporary datablocks leaked after failed render'
    print('Cleanup after render failure: OK')
finally:
    companion['stop']()
