"""Geometry previews from evaluated live objects, rendered in a disposable scene."""
import json
import math
import time

import bpy
from mathutils import Vector

VIEWS = {'front': (0, -1, 0), 'right': (1, 0, 0), 'top': (0, 0, 1),
         'perspective': (1, -1, .75), 'back': (0, 1, 0), 'left': (-1, 0, 0)}


def capture(arguments, output):
    views = arguments.get('views', ['front', 'right', 'top', 'perspective'])
    if not isinstance(views, list) or not 1 <= len(views) <= 6 or any(v not in VIEWS for v in views) or len(set(views)) != len(views):
        raise ValueError('views must contain 1-6 unique supported view names')
    size = max(128, min(1536, int(arguments.get('size', 512))))
    style = arguments.get('style', 'solid')
    if style not in ('solid', 'silhouette'):
        raise ValueError('style must be solid or silhouette')
    source = bpy.context.scene
    names = arguments.get('objects')
    if names is not None:
        if not isinstance(names, list) or not 1 <= len(names) <= 64 or not all(isinstance(n, str) for n in names):
            raise ValueError('objects must contain 1-64 object names')
        if len(set(names)) != len(names) or any(n not in source.objects for n in names):
            raise ValueError('Object names must be unique and exist in the current scene')
        targets = [source.objects[n] for n in names]
    else:
        targets = [o for o in source.objects if o.visible_get() and o.type in ('MESH', 'CURVE', 'SURFACE', 'FONT')]
    if not 1 <= len(targets) <= 64 or any(o.type not in ('MESH', 'CURVE', 'SURFACE', 'FONT') for o in targets):
        raise ValueError('Choose 1-64 mesh/curve/surface/font objects')
    if bpy.context.mode != 'OBJECT':
        raise ValueError('Switch to Object Mode before capture; Edit/Sculpt Mode is not changed automatically')
    if bpy.app.is_job_running('RENDER'):
        raise ValueError('A Blender render is already running')
    output.mkdir(parents=True, exist_ok=False)
    scene = bpy.data.scenes.new('OrdaX Preview')
    created_objects, meshes = [], []
    camera_data = None
    started = time.monotonic()
    try:
        graph = bpy.context.evaluated_depsgraph_get()
        low = Vector((float('inf'),) * 3)
        high = Vector((float('-inf'),) * 3)
        total_vertices = 0
        for obj in targets:
            evaluated = obj.evaluated_get(graph)
            mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=graph)
            meshes.append(mesh)
            total_vertices += len(mesh.vertices)
            if total_vertices > 2_000_000:
                raise ValueError('Preview exceeds 2 million vertices; select fewer objects')
            copy = bpy.data.objects.new('OrdaX ' + obj.name, mesh)
            created_objects.append(copy)
            scene.collection.objects.link(copy)
            copy.matrix_world = evaluated.matrix_world.copy()
            for vertex in mesh.vertices:
                point = copy.matrix_world @ vertex.co
                for axis in range(3):
                    low[axis] = min(low[axis], point[axis])
                    high[axis] = max(high[axis], point[axis])
        if not total_vertices or not all(math.isfinite(v) for v in (*low, *high)):
            raise ValueError('Objects contain no finite preview geometry')
        center = (low + high) / 2
        radius = max((high - low).length / 2, .0001)
        camera_data = bpy.data.cameras.new('OrdaX Preview Camera')
        camera = bpy.data.objects.new('OrdaX Preview Camera', camera_data)
        created_objects.append(camera)
        scene.collection.objects.link(camera)
        scene.camera = camera
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = scene.render.resolution_y = size
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.film_transparent = False
        scene.render.use_file_extension = True
        scene.display.render_aa = '8'
        shading = scene.display.shading
        shading.light = 'FLAT' if style == 'silhouette' else 'STUDIO'
        shading.color_type = 'SINGLE'
        shading.single_color = (0, 0, 0) if style == 'silhouette' else (.65, .65, .65)
        shading.background_type = 'WORLD'
        # A disposable world keeps the preview independent of the user's world.
        world = bpy.data.worlds.new('OrdaX Preview World')
        scene.world = world
        world.color = (1, 1, 1)
        shading.show_shadows = style == 'solid'
        shading.show_cavity = style == 'solid'
        shading.show_specular_highlight = style == 'solid'
        evidence = []
        for view in views:
            direction = Vector(VIEWS[view]).normalized()
            camera_data.type = 'PERSP' if view == 'perspective' else 'ORTHO'
            camera_data.lens = 50
            camera_data.ortho_scale = radius * 2.2
            distance = radius * 1.1 / math.sin(camera_data.angle / 2)
            camera.location = center + direction * distance
            camera.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
            camera_data.clip_start = max(radius * .0001, .000001)
            camera_data.clip_end = distance + radius * 4
            image = output / f'{view}.png'
            scene.render.filepath = str(image)
            bpy.ops.render.render(write_still=True, scene=scene.name)
            if not image.is_file():
                raise RuntimeError('Preview render did not produce an image')
            evidence.append({'view': view, 'filename': image.name,
                             'projection': camera_data.type, 'camera_position': list(camera.location),
                             'camera_rotation': list(camera.rotation_euler),
                             'ortho_scale': camera_data.ortho_scale, 'lens_mm': camera_data.lens})
        result = {'views': evidence, 'objects': [o.name for o in targets],
                  'source_scene': source.name, 'source_file': bpy.data.filepath,
                  'frame': source.frame_current, 'size': size, 'style': style,
                  'unit_scale_m': source.unit_settings.scale_length if source.unit_settings.system != 'NONE' else None,
                  'bounds_world': {'min': list(low), 'max': list(high)},
                  'duration_seconds': round(time.monotonic() - started, 3),
                  'render_engine': 'BLENDER_WORKBENCH',
                  'limitations': ['geometry preview, not material/lighting validation',
                                  'unrealized instances are not included',
                                  'temporary datablocks may mark the document dirty']}
        (output / 'snapshot.json').write_text(json.dumps(result), encoding='utf-8')
        return result
    finally:
        world = scene.world
        bpy.data.scenes.remove(scene)
        for obj in created_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            bpy.data.meshes.remove(mesh)
        if camera_data is not None:
            bpy.data.cameras.remove(camera_data)
        if world is not None:
            bpy.data.worlds.remove(world)
