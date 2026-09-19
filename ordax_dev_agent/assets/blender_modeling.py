"""Bounded modeling operations. Imports bpy only inside Blender, not on the host."""
import math

SCHEMAS = {
    'create': {'required': ['name', 'primitive'], 'properties': {
        'name': {'type': 'string', 'minLength': 1, 'maxLength': 63},
        'primitive': {'enum': ['cube', 'sphere', 'cylinder']},
        'location': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
        'size': {'type': 'number', 'minimum': .0001, 'maximum': 10000, 'default': 2},
        'radius': {'type': 'number', 'minimum': .0001, 'maximum': 10000, 'default': 1},
        'depth': {'type': 'number', 'minimum': .0001, 'maximum': 10000, 'default': 2},
        'segments': {'type': 'integer', 'minimum': 8, 'maximum': 64, 'default': 32}}},
    'transform': {'required': ['object'], 'properties': {
        'object': {'type': 'string', 'minLength': 1, 'maxLength': 63},
        'location': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
        'rotation_degrees': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
        'scale': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3}}},
    'modifier': {'required': ['object', 'name', 'type'], 'properties': {
        'object': {'type': 'string', 'minLength': 1, 'maxLength': 63},
        'name': {'type': 'string', 'minLength': 1, 'maxLength': 63},
        'type': {'enum': ['BEVEL', 'SUBSURF', 'SOLIDIFY', 'MIRROR']},
        'width': {'type': 'number', 'minimum': 0, 'maximum': 100, 'default': .05},
        'segments': {'type': 'integer', 'minimum': 1, 'maximum': 6, 'default': 2},
        'levels': {'type': 'integer', 'minimum': 0, 'maximum': 2, 'default': 1},
        'thickness': {'type': 'number', 'minimum': -100, 'maximum': 100, 'default': .01},
        'axis': {'enum': ['X', 'Y', 'Z'], 'default': 'X'}}},
}
for _schema in SCHEMAS.values():
    _schema.update(type='object', additionalProperties=False)
    for _key, _spec in _schema['properties'].items():
        if _spec.get('type') == 'array':
            _spec['items'].update(minimum=.0001 if _key == 'scale' else -100000,
                                  maximum=1000 if _key == 'scale' else 100000)
SCHEMAS['create']['description'] = 'cube accepts size; sphere accepts radius/segments; cylinder accepts radius/depth/segments. Names are limited to 63 UTF-8 bytes.'
SCHEMAS['modifier']['description'] = 'BEVEL accepts width/segments; SUBSURF accepts levels; SOLIDIFY accepts thickness; MIRROR accepts axis. Adds an editable modifier; never applies or overwrites it.'
SCHEMAS['transform']['description'] = 'Supply at least one transform. Absolute object-local values; rotation switches to XYZ Euler in degrees. Parented objects remain parented.'


def validate(operation, arguments):
    if operation not in SCHEMAS or not isinstance(arguments, dict):
        raise ValueError('Unsupported modeling operation or arguments')
    schema = SCHEMAS[operation]
    if set(arguments) - schema['properties'].keys() or set(schema['required']) - arguments.keys():
        raise ValueError('Unknown or missing modeling parameters; query blender.modeling_tools')
    for key, value in arguments.items():
        spec = schema['properties'][key]
        if 'enum' in spec:
            if value not in spec['enum']:
                raise ValueError(f'Unsupported {key}')
        elif spec['type'] == 'string':
            if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > 63 or any(ord(c) < 32 for c in value):
                raise ValueError(f'Invalid {key}')
        elif spec['type'] == 'array':
            if not isinstance(value, list) or len(value) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 100000 for v in value):
                raise ValueError(f'{key} requires three bounded finite numbers')
            if key == 'scale' and any(v < .0001 or v > 1000 for v in value):
                raise ValueError('Scale components must be within 0.0001..1000')
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'Invalid numeric {key}')
            if spec['type'] == 'integer' and not isinstance(value, int):
                raise ValueError(f'{key} must be an integer')
            if not spec['minimum'] <= value <= spec['maximum']:
                raise ValueError(f'{key} is outside supported range')
    if operation == 'transform' and not set(arguments) & {'location', 'rotation_degrees', 'scale'}:
        raise ValueError('Provide at least one transform field')
    if operation == 'create':
        allowed = {'cube': {'size'}, 'sphere': {'radius', 'segments'}, 'cylinder': {'radius', 'depth', 'segments'}}[arguments['primitive']]
        if set(arguments) - {'name', 'primitive', 'location'} - allowed:
            raise ValueError('Parameter does not apply to this primitive')
    if operation == 'modifier':
        allowed = {'BEVEL': {'width', 'segments'}, 'SUBSURF': {'levels'}, 'SOLIDIFY': {'thickness'}, 'MIRROR': {'axis'}}[arguments['type']]
        if set(arguments) - {'object', 'name', 'type'} - allowed:
            raise ValueError('Parameter does not apply to this modifier')


def info(obj):
    props = ('width', 'segments', 'levels', 'render_levels', 'thickness', 'use_axis')
    return {'name': obj.name, 'type': obj.type, 'location': list(obj.location),
            'rotation_mode': obj.rotation_mode, 'rotation_euler': list(obj.rotation_euler),
            'rotation_quaternion': list(obj.rotation_quaternion), 'rotation_axis_angle': list(obj.rotation_axis_angle),
            'scale': list(obj.scale), 'dimensions': list(obj.dimensions),
            'parent': obj.parent.name if obj.parent else None,
            'vertices': len(obj.data.vertices) if obj.type == 'MESH' else None,
            'modifiers': [{'name': m.name, 'type': m.type, **{
                key: list(getattr(m, key)) if key == 'use_axis' else getattr(m, key)
                for key in props if hasattr(m, key)}} for m in obj.modifiers]}


def execute(operation, arguments):
    import bpy
    validate(operation, arguments)
    if bpy.context.mode != 'OBJECT' or bpy.app.is_job_running('RENDER'):
        raise ValueError('Modeling requires Object Mode and no running render')
    if operation == 'create':
        import bmesh
        if arguments['name'] in bpy.data.objects:
            raise ValueError('Object name already exists; creation refused')
        bm = bmesh.new()
        mesh = obj = None
        try:
            primitive = arguments['primitive']
            if primitive == 'cube':
                bmesh.ops.create_cube(bm, size=arguments.get('size', 2))
            elif primitive == 'sphere':
                segments = arguments.get('segments', 32)
                bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=max(4, segments // 2), radius=arguments.get('radius', 1))
            else:
                radius = arguments.get('radius', 1)
                bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=arguments.get('segments', 32), radius1=radius, radius2=radius, depth=arguments.get('depth', 2))
            mesh = bpy.data.meshes.new(arguments['name'])
            bm.to_mesh(mesh)
            obj = bpy.data.objects.new(arguments['name'], mesh)
            bpy.context.scene.collection.objects.link(obj)
            obj.location = arguments.get('location', [0, 0, 0])
            bpy.context.view_layer.update()
            return {'operation': operation, 'before': None, 'after': info(obj)}
        except Exception:
            if obj is not None:
                bpy.data.objects.remove(obj, do_unlink=True)
            if mesh is not None:
                bpy.data.meshes.remove(mesh)
            raise
        finally:
            bm.free()
    obj = bpy.context.scene.objects.get(arguments['object'])
    if obj is None or obj.type != 'MESH' or obj.library or obj.override_library or obj.data.library:
        raise ValueError('Operation requires an existing local, non-linked mesh object')
    if obj.animation_data or obj.constraints:
        raise ValueError('Animated or constrained objects require a dedicated workflow')
    before = info(obj)
    if operation == 'transform':
        saved = (obj.location.copy(), obj.rotation_mode, obj.rotation_euler.copy(),
                 obj.rotation_quaternion.copy(), list(obj.rotation_axis_angle), obj.scale.copy())
        try:
            if 'location' in arguments:
                obj.location = arguments['location']
            if 'rotation_degrees' in arguments:
                obj.rotation_mode = 'XYZ'
                obj.rotation_euler = [math.radians(v) for v in arguments['rotation_degrees']]
            if 'scale' in arguments:
                obj.scale = arguments['scale']
            bpy.context.view_layer.update()
            return {'operation': operation, 'before': before, 'after': info(obj)}
        except Exception:
            obj.location, obj.rotation_mode, obj.rotation_euler, obj.rotation_quaternion, obj.rotation_axis_angle, obj.scale = saved
            bpy.context.view_layer.update()
            raise
    if arguments['name'] in obj.modifiers:
        raise ValueError('Modifier name already exists; overwriting refused')
    if len(obj.modifiers) >= 8:
        raise ValueError('Modifier stack limit reached')
    # Evaluate the existing stack before estimating the added subdivision cost.
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    faces = len(evaluated.data.polygons)
    if faces > 200000 or (arguments['type'] == 'SUBSURF' and faces * 4 ** arguments.get('levels', 1) > 500000):
        raise ValueError('Mesh exceeds conservative interactive modifier budget')
    modifier = obj.modifiers.new(arguments['name'], arguments['type'])
    try:
        if modifier.type == 'BEVEL':
            modifier.width = arguments.get('width', .05)
            modifier.segments = arguments.get('segments', 2)
        elif modifier.type == 'SUBSURF':
            modifier.levels = modifier.render_levels = arguments.get('levels', 1)
        elif modifier.type == 'SOLIDIFY':
            modifier.thickness = arguments.get('thickness', .01)
        else:
            modifier.use_axis = [axis == arguments.get('axis', 'X') for axis in 'XYZ']
        bpy.context.view_layer.update()
        return {'operation': operation, 'before': before, 'after': info(obj)}
    except Exception:
        obj.modifiers.remove(modifier)
        bpy.context.view_layer.update()
        raise
