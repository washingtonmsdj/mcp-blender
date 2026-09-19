"""Blender --background --factory-startup --python-exit-code 1 --python this.py."""
import json
import runpy
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import patch, Mock

import bpy

companion = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_live_companion.py'))
with tempfile.TemporaryDirectory(prefix='ordax-modeling-') as directory:
    root = Path(directory)
    def command(action, args):
        session = json.loads((root / '.ordax/blender/presence.json').read_text())['session']
        identifier = uuid.uuid4().hex
        request = {'id': identifier, 'session': session, 'deadline': time.time() + 30,
                   'action': action, 'arguments': args}
        (root / '.ordax/blender/inbox' / f'{identifier}.json').write_text(json.dumps(request))
        companion['_tick']()
        return json.loads((root / '.ordax/blender/responses' / f'{identifier}.json').read_text())

    companion['start'](str(root))
    assert not command('model', {'operation': 'create', 'arguments': {'name': 'Body', 'primitive': 'cube'}})['ok']
    companion['stop']()
    companion['start'](str(root), allow_modeling=True)  # arbitrary scripts remain disabled
    selected = [o.name for o in bpy.context.selected_objects]
    camera = bpy.context.scene.camera
    try:
        operations = [('create', {'name': 'Body', 'primitive': 'cube'}),
            ('create', {'name': 'Sphere', 'primitive': 'sphere', 'segments': 16}),
            ('create', {'name': 'Cylinder', 'primitive': 'cylinder', 'radius': .5, 'depth': 3}),
            ('transform', {'object': 'Body', 'location': [1, 2, 3], 'rotation_degrees': [0, 0, 90], 'scale': [1, 2, 1]})]
        operations += [('modifier', {'object': 'Body', 'name': kind, 'type': kind}) for kind in ('BEVEL', 'SUBSURF', 'SOLIDIFY', 'MIRROR')]
        for operation, arguments in operations:
            result = command('model', {'operation': operation, 'arguments': arguments})
            assert result['ok'], result
            expected_name = arguments['name'] if operation == 'create' else 'Body'
            assert result['data']['after']['name'] == expected_name
        assert list(bpy.data.objects['Body'].location) == [1, 2, 3]
        assert len(bpy.data.objects['Body'].modifiers) == 4
        assert command('object_info', {'object': 'Body'})['data']['object']['modifiers'][0]['type'] == 'BEVEL'
        counts = (len(bpy.data.objects), len(bpy.data.meshes))
        assert not command('model', {'operation': 'create', 'arguments': {'name': 'Body', 'primitive': 'cube'}})['ok']
        assert counts == (len(bpy.data.objects), len(bpy.data.meshes))
        assert not command('model', {'operation': 'modifier', 'arguments': {'object': 'Body', 'name': 'BEVEL', 'type': 'BEVEL'}})['ok']
        assert not command('run_script', {})['ok']
        assert [o.name for o in bpy.context.selected_objects] == selected
        assert bpy.context.scene.camera == camera
        assert bpy.data.filepath == ''
        helper = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'ordax_dev_agent/assets/blender_modeling.py'))
        execute, info = helper['execute'], helper['info']
        before = info(bpy.data.objects['Body'])
        for operation, arguments in [('transform', {'object': 'Body', 'location': [99, 99, 99]}),
                                     ('modifier', {'object': 'Body', 'name': 'Temporary', 'type': 'BEVEL'})]:
            with patch.dict(execute.__globals__, {'info': Mock(side_effect=[before, RuntimeError('Injected')])}):
                try:
                    execute(operation, arguments)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Expected injected failure')
            assert info(bpy.data.objects['Body']) == before, 'Rollback failed'
        with patch.dict(execute.__globals__, {'info': Mock(side_effect=RuntimeError('Injected'))}):
            try:
                execute('create', {'name': 'Temporary', 'primitive': 'cube'})
            except RuntimeError:
                pass
            else:
                raise AssertionError('Expected injected creation failure')
        assert counts == (len(bpy.data.objects), len(bpy.data.meshes)), 'Creation leaked datablocks'
        print(json.dumps({'ok': True, 'modeling_commands': len(operations), 'scripts_disabled': True,
                          'selection_preserved': True, 'source_unsaved': True, 'rollback_checks': 3}))
    finally:
        companion['stop']()
