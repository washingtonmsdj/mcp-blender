# OrdaX Dev Agent - visible Blender companion.
# Runs inside an interactive Blender window and executes only typed commands
# emitted by the local allow-listed agent.
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib
import json
import re
import runpy
import struct
import sys
import time
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--ordax-control-root", required=True)
    parser.add_argument("--ordax-project-root", required=True)
    parser.add_argument("--ordax-scripts-root", required=True)
    parser.add_argument("--ordax-artifacts-root", required=True)
    parser.add_argument("--ordax-project-slug", required=True)
    return parser.parse_args(argv)


COMPANION_FINGERPRINT = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

CFG = _args()
CONTROL_ROOT = Path(CFG.ordax_control_root).resolve()
PROJECT_ROOT = Path(CFG.ordax_project_root).resolve()
SCRIPTS_ROOT = Path(CFG.ordax_scripts_root).resolve()
ARTIFACTS_ROOT = Path(CFG.ordax_artifacts_root).resolve()
CHECKPOINTS = ARTIFACTS_ROOT / "checkpoints"
TRAJECTORY = CONTROL_ROOT / "trajectory.jsonl"
INBOX = CONTROL_ROOT / "inbox"
RESPONSES = CONTROL_ROOT / "responses"
RESULTS = CONTROL_ROOT / "results"
INFLIGHT = CONTROL_ROOT / "inflight"
PRESENCE = CONTROL_ROOT / "presence.json"

PROTOCOL_VERSION = 7
CAPABILITIES = [
    "ping",
    "inspect",
    "scene_snapshot",
    "scene_reset",
    "object_inspect",
    "object_fingerprints",
    "contact_audit",
    "quality_gate",
    "object_transform",
    "object_metadata",
    "api_schema",
    "api_lookup",
    "node_schema",
    "export_scene",
    "checkpoint_create",
    "checkpoint_restore",
    "checkpoint_list",
    "run_script",
    "capture_viewport",
    "multiview_capture",
    "save",
    "quit",
]
_LAST_PRESENCE_AT = 0.0

for path in (CONTROL_ROOT, INBOX, RESPONSES, RESULTS, INFLIGHT, ARTIFACTS_ROOT, CHECKPOINTS):
    path.mkdir(parents=True, exist_ok=True)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _write_json_atomic(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


def _scene_snapshot() -> dict:
    try:
        selected = [obj.name for obj in bpy.context.selected_objects[:40]]
    except (ReferenceError, RuntimeError):
        selected = []

    active_name = None
    try:
        active = bpy.context.view_layer.objects.active
        if active is not None:
            active_name = active.name
    except (ReferenceError, RuntimeError):
        active_name = None

    scene = bpy.context.scene
    return {
        "project": CFG.ordax_project_slug,
        "timestamp": time.time(),
        "blender_version": ".".join(str(v) for v in bpy.app.version),
        "file": bpy.data.filepath or "",
        "is_dirty": bool(getattr(bpy.data, "is_dirty", False)),
        "scene": scene.name if scene else "",
        "frame": int(scene.frame_current) if scene else 0,
        "mode": getattr(bpy.context, "mode", "UNKNOWN"),
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
        "selected": selected,
        "active_object": active_name,
    }


def _write_presence(force: bool = False) -> None:
    global _LAST_PRESENCE_AT
    now = time.time()
    if not force and now - _LAST_PRESENCE_AT < 1.0:
        return
    _write_json_atomic(
        PRESENCE,
        {
            "ok": True,
            "summary": "OrdaX visible Blender companion ready",
            "protocol_version": PROTOCOL_VERSION,
            "companion_fingerprint": COMPANION_FINGERPRINT,
            "capabilities": CAPABILITIES,
            **_scene_snapshot(),
        },
    )
    _LAST_PRESENCE_AT = now


def _prune_results(limit: int = 200) -> None:
    try:
        entries = sorted(
            (p for p in RESULTS.glob("*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in entries[limit:]:
            stale.unlink(missing_ok=True)
    except OSError:
        pass


def _response(command_id: str, ok: bool, summary: str, **data) -> None:
    snapshot = _scene_snapshot()
    # Heavy Blender operations pause the timer heartbeat. Refresh presence
    # synchronously before publishing the response so the next typed command
    # cannot observe a stale session between two successful operations.
    _write_presence(force=True)
    body = {
        "id": command_id,
        "ok": ok,
        "summary": summary,
        **data,
        "snapshot": snapshot,
        "completed_at": time.time(),
    }
    # Persist first. The response inbox is ephemeral; results survive timeouts,
    # agent restarts and Blender closing so callers can query before retrying.
    _write_json_atomic(RESULTS / f"{command_id}.json", body)
    _write_json_atomic(RESPONSES / f"{command_id}.json", body)
    _prune_results()


def _ordax_properties(owner) -> dict:
    data = {}
    try:
        keys = owner.keys()
    except Exception:
        return data
    for key in keys:
        if not str(key).startswith("ordax_"):
            continue
        try:
            value = owner.get(key)
            if value is None or isinstance(value, (str, int, float, bool)):
                data[str(key)] = value
            elif isinstance(value, (list, tuple)):
                data[str(key)] = list(value)[:50]
            else:
                data[str(key)] = str(value)
        except Exception:
            continue
    return data


def _round_vector(values, digits: int = 6) -> list[float]:
    return [round(float(value), digits) for value in values]


def _world_bounds(obj) -> dict:
    try:
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        xs = [corner.x for corner in corners]
        ys = [corner.y for corner in corners]
        zs = [corner.z for corner in corners]
        return {
            "aabb_min": [round(min(xs), 6), round(min(ys), 6), round(min(zs), 6)],
            "aabb_max": [round(max(xs), 6), round(max(ys), 6), round(max(zs), 6)],
            "dimensions": _round_vector(obj.dimensions),
        }
    except Exception:
        return {}


def _object_details(obj) -> dict:
    world = obj.matrix_world
    details = {
        "name": obj.name,
        "type": obj.type,
        "visible": bool(obj.visible_get()),
        "selected": bool(obj.select_get()),
        "location": _round_vector(obj.location),
        "rotation_euler": _round_vector(obj.rotation_euler),
        "scale": _round_vector(obj.scale),
        "world_location": _round_vector(world.translation),
        "world_rotation_euler": _round_vector(world.to_euler()),
        "parent": obj.parent.name if obj.parent else None,
        "children": [child.name for child in list(obj.children)[:100]],
        "collections": [collection.name for collection in list(obj.users_collection)[:50]],
        "ordax": _ordax_properties(obj),
        **_world_bounds(obj),
    }

    material_names = []
    for slot in list(getattr(obj, "material_slots", []))[:50]:
        material = getattr(slot, "material", None)
        material_names.append(material.name if material else None)
    if material_names:
        details["materials"] = material_names

    modifiers = []
    for modifier in list(getattr(obj, "modifiers", []))[:50]:
        modifiers.append(
            {
                "name": modifier.name,
                "type": modifier.type,
                "show_viewport": bool(getattr(modifier, "show_viewport", True)),
                "show_render": bool(getattr(modifier, "show_render", True)),
            }
        )
    if modifiers:
        details["modifiers"] = modifiers

    constraints = []
    for constraint in list(getattr(obj, "constraints", []))[:50]:
        target = getattr(constraint, "target", None)
        constraints.append(
            {
                "name": constraint.name,
                "type": constraint.type,
                "target": target.name if target else None,
                "influence": round(float(getattr(constraint, "influence", 1.0)), 6),
            }
        )
    if constraints:
        details["constraints"] = constraints

    if obj.type == "MESH" and getattr(obj, "data", None) is not None:
        mesh = obj.data
        details["mesh"] = {
            "name": mesh.name,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
        }

    animation = getattr(obj, "animation_data", None)
    if animation is not None:
        action = getattr(animation, "action", None)
        details["animation"] = {
            "action": action.name if action else None,
            "drivers": len(getattr(animation, "drivers", []) or []),
            "nla_tracks": [
                track.name for track in list(getattr(animation, "nla_tracks", []) or [])[:20]
            ],
        }

    return details


def _scene_objects(command: dict, *, default_limit: int = 200):
    try:
        limit = max(1, min(500, int(command.get("max_objects", default_limit))))
    except (TypeError, ValueError):
        raise ValueError("max_objects must be an integer")

    requested = command.get("object_names")
    if requested is not None:
        if not isinstance(requested, list) or not all(isinstance(name, str) for name in requested):
            raise ValueError("object_names must be a list of object names")
        wanted = set(requested[:500])
        source = [obj for obj in bpy.context.scene.objects if obj.name in wanted]
    else:
        source = list(bpy.context.scene.objects)
    return source[:limit], len(source) > limit


def _scene_snapshot_rich(command: dict) -> None:
    command_id = command["id"]
    try:
        objects, truncated = _scene_objects(command)
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    scene = bpy.context.scene
    camera = scene.camera
    _response(
        command_id,
        True,
        "Rich Blender scene snapshot ready",
        object_count=len(scene.objects),
        returned_objects=len(objects),
        truncated=truncated,
        objects=[_object_details(obj) for obj in objects],
        collections=[
            {
                "name": collection.name,
                "objects": len(collection.objects),
                "children": len(collection.children),
            }
            for collection in list(bpy.data.collections)[:200]
        ],
        active_camera=(
            {
                "name": camera.name,
                "location": _round_vector(camera.matrix_world.translation),
                "rotation_euler": _round_vector(camera.matrix_world.to_euler()),
                "lens": round(float(getattr(camera.data, "lens", 0.0)), 6),
                "sensor_width": round(float(getattr(camera.data, "sensor_width", 0.0)), 6),
            }
            if camera
            else None
        ),
        scene_ordax=_ordax_properties(scene),
    )


def _scene_reset(command: dict) -> None:
    command_id = command["id"]
    try:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in list(bpy.context.scene.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        for collection in list(bpy.data.collections):
            if collection.users == 0:
                try:
                    bpy.data.collections.remove(collection)
                except Exception:
                    pass

        for blocks in (
            bpy.data.meshes,
            bpy.data.curves,
            bpy.data.cameras,
            bpy.data.lights,
        ):
            for block in list(blocks):
                if block.users == 0 and not getattr(block, "use_fake_user", False):
                    try:
                        blocks.remove(block)
                    except Exception:
                        pass

        bpy.context.scene.frame_set(1)
        _response(
            command_id,
            True,
            "Blender scene reset for isolated generation",
            removed_to_object_count=len(bpy.context.scene.objects),
        )
    except Exception as error:
        _response(
            command_id,
            False,
            f"{type(error).__name__}: {error}",
        )



def _digest_text(digest, value: str) -> None:
    digest.update(str(value).encode("utf-8", errors="surrogatepass"))
    digest.update(b"\0")


def _transform_fingerprint(obj) -> str:
    digest = hashlib.sha256()
    _digest_text(digest, obj.type)
    for row in obj.matrix_world:
        for value in row:
            digest.update(struct.pack("<d", float(value)))
    return digest.hexdigest()


def _mesh_fingerprint(obj, *, evaluated: bool = False) -> tuple[str | None, dict]:
    if obj.type != "MESH":
        return None, {}

    evaluated_obj = None
    mesh = None
    must_clear = False
    try:
        if evaluated:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated_obj = obj.evaluated_get(depsgraph)
            mesh = evaluated_obj.to_mesh()
            must_clear = True
        else:
            mesh = obj.data

        if mesh is None:
            return None, {}

        digest = hashlib.sha256()
        _digest_text(digest, "evaluated" if evaluated else "base")
        digest.update(struct.pack(
            "<QQQ",
            int(len(mesh.vertices)),
            int(len(mesh.edges)),
            int(len(mesh.polygons)),
        ))

        for vertex in mesh.vertices:
            co = vertex.co
            digest.update(struct.pack("<3d", float(co.x), float(co.y), float(co.z)))

        for edge in mesh.edges:
            vertices = tuple(int(index) for index in edge.vertices)
            digest.update(struct.pack("<2Q", vertices[0], vertices[1]))

        for polygon in mesh.polygons:
            vertices = tuple(int(index) for index in polygon.vertices)
            digest.update(struct.pack("<Q", len(vertices)))
            for index in vertices:
                digest.update(struct.pack("<Q", index))

        return digest.hexdigest(), {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
        }
    finally:
        if must_clear and evaluated_obj is not None:
            try:
                evaluated_obj.to_mesh_clear()
            except Exception:
                pass


def _fingerprint_selector(selector: dict) -> tuple[str, object]:
    object_name = str(selector.get("object_name") or "").strip()
    object_id = str(selector.get("ordax_object_id") or "").strip()
    if bool(object_name) == bool(object_id):
        raise ValueError(
            "each fingerprint selector must provide exactly one of object_name or ordax_object_id"
        )
    obj = _resolve_object(
        {"object_name": object_name} if object_name else {"ordax_object_id": object_id}
    )
    key = f"name:{object_name}" if object_name else f"id:{object_id}"
    return key, obj


def _object_fingerprint_entry(selector: dict) -> dict:
    key, obj = _fingerprint_selector(selector)
    evaluated = bool(selector.get("evaluated", True))
    transform_sha256 = _transform_fingerprint(obj)
    geometry_sha256, mesh_counts = _mesh_fingerprint(obj, evaluated=evaluated)

    digest = hashlib.sha256()
    _digest_text(digest, obj.type)
    _digest_text(digest, transform_sha256)
    _digest_text(digest, geometry_sha256 or "")
    combined = digest.hexdigest()

    return {
        "selector_key": key,
        "object_name": obj.name,
        "ordax_object_id": str(obj.get("ordax_object_id") or "") or None,
        "type": obj.type,
        "evaluated": evaluated,
        "transform_sha256": transform_sha256,
        "geometry_sha256": geometry_sha256,
        "combined_sha256": combined,
        "mesh": mesh_counts,
    }


def _object_fingerprints(command: dict) -> None:
    command_id = command["id"]
    selectors = command.get("selectors")
    if not isinstance(selectors, list) or not selectors:
        _response(command_id, False, "selectors must be a non-empty list")
        return
    if len(selectors) > 100:
        _response(command_id, False, "fingerprint request is limited to 100 objects")
        return

    fingerprints = []
    seen = set()
    try:
        for index, selector in enumerate(selectors):
            if not isinstance(selector, dict):
                raise ValueError(f"fingerprint selector {index} must be an object")
            key, _ = _fingerprint_selector(selector)
            if key in seen:
                raise ValueError(f"duplicate fingerprint selector: {key}")
            seen.add(key)
            fingerprints.append(_object_fingerprint_entry(selector))
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    _response(
        command_id,
        True,
        "Blender object fingerprints ready",
        fingerprints=fingerprints,
    )


def _object_inspect(command: dict) -> None:
    command_id = command["id"]
    try:
        obj = _resolve_object(command)
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    _response(
        command_id,
        True,
        "Blender object inspected",
        object=_object_details(obj),
    )


def _evaluated_world_bvh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world.copy()
        vertices = [matrix @ vertex.co for vertex in mesh.vertices]
        polygons = [tuple(poly.vertices) for poly in mesh.polygons if len(poly.vertices) >= 3]
        if not vertices or not polygons:
            return None, []
        tree = BVHTree.FromPolygons(
            vertices,
            polygons,
            all_triangles=False,
            epsilon=0.00001,
        )
        return tree, vertices
    finally:
        evaluated.to_mesh_clear()


def _sample_points(points, limit: int = 160):
    if len(points) <= limit:
        return points
    step = max(1, len(points) // limit)
    return points[::step][:limit]


def _point_inside_closed_surface(tree, point, tolerance: float = 1e-5) -> bool:
    try:
        nearest = tree.find_nearest(point)
    except Exception:
        return False
    if not nearest:
        return False
    surface_point, normal, _, distance = nearest
    if surface_point is None or normal is None or distance is None:
        return False
    # For consistently outward-facing closed meshes, an interior point lies
    # behind the closest surface plane relative to its outward normal.
    signed = (point - surface_point).dot(normal)
    return signed < -max(tolerance, float(distance) * 1e-6)


def _approx_surface_clearance(source_points, target_tree) -> float | None:
    minimum = None
    for point in _sample_points(source_points, 96):
        try:
            nearest = target_tree.find_nearest(point)
        except Exception:
            continue
        if not nearest or nearest[3] is None:
            continue
        distance = float(nearest[3])
        minimum = distance if minimum is None else min(minimum, distance)
    return minimum


def _aabb_overlap(left: dict, right: dict) -> bool:
    left_min, left_max = left.get("aabb_min"), left.get("aabb_max")
    right_min, right_max = right.get("aabb_min"), right.get("aabb_max")
    if not all((left_min, left_max, right_min, right_max)):
        return False
    return all(
        left_min[axis] <= right_max[axis]
        and left_max[axis] >= right_min[axis]
        for axis in range(3)
    )


def _contact_audit(command: dict) -> None:
    command_id = command["id"]
    raw_pairs = command.get("pairs")
    if not isinstance(raw_pairs, list) or not raw_pairs:
        _response(command_id, False, "pairs must be a non-empty list of [object_a, object_b]")
        return
    if len(raw_pairs) > 200:
        _response(command_id, False, "pairs is limited to 200 object pairs")
        return

    depsgraph = bpy.context.evaluated_depsgraph_get()
    cache = {}

    def geometry_for(obj):
        if obj.name not in cache:
            if obj.type != "MESH":
                cache[obj.name] = (None, [])
            else:
                cache[obj.name] = _evaluated_world_bvh(obj, depsgraph)
        return cache[obj.name]

    results = []
    invalid = []
    resolution_errors = 0
    intersection_pairs = 0

    for item in raw_pairs:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(name, str) and name for name in item)
        ):
            invalid.append(item)
            continue

        left = bpy.context.scene.objects.get(item[0])
        right = bpy.context.scene.objects.get(item[1])
        if left is None or right is None:
            resolution_errors += 1
            results.append(
                {
                    "a": item[0],
                    "b": item[1],
                    "ok": False,
                    "error": "object_not_found",
                }
            )
            continue

        left_tree, left_points = geometry_for(left)
        right_tree, right_points = geometry_for(right)
        if left_tree is None or right_tree is None:
            resolution_errors += 1
            results.append(
                {
                    "a": left.name,
                    "b": right.name,
                    "ok": False,
                    "error": "mesh_required",
                }
            )
            continue

        left_bounds = _world_bounds(left)
        right_bounds = _world_bounds(right)
        broad_phase_overlap = _aabb_overlap(left_bounds, right_bounds)

        overlaps = left_tree.overlap(right_tree)
        triangle_overlap_count = len(overlaps)
        surface_intersection = triangle_overlap_count > 0

        left_inside_right = False
        right_inside_left = False
        if broad_phase_overlap and not surface_intersection:
            left_inside_right = any(
                _point_inside_closed_surface(right_tree, point)
                for point in _sample_points(left_points)
            )
            right_inside_left = any(
                _point_inside_closed_surface(left_tree, point)
                for point in _sample_points(right_points)
            )

        contained = left_inside_right or right_inside_left
        intersects = surface_intersection or contained
        if intersects:
            intersection_pairs += 1

        left_to_right = _approx_surface_clearance(left_points, right_tree)
        right_to_left = _approx_surface_clearance(right_points, left_tree)
        clearances = [
            distance
            for distance in (left_to_right, right_to_left)
            if distance is not None
        ]
        min_clearance = min(clearances) if clearances else None

        reason = None
        if surface_intersection:
            reason = "surface_intersection"
        elif contained:
            reason = "containment"

        results.append(
            {
                "a": left.name,
                "b": right.name,
                "ok": True,
                "intersects": intersects,
                "reason": reason,
                "broad_phase_aabb_overlap": broad_phase_overlap,
                "triangle_overlap_count": triangle_overlap_count,
                "left_inside_right": left_inside_right,
                "right_inside_left": right_inside_left,
                "approx_min_surface_distance": (
                    round(min_clearance, 6)
                    if min_clearance is not None
                    else None
                ),
                "a_bounds": left_bounds,
                "b_bounds": right_bounds,
            }
        )

    if invalid:
        _response(
            command_id,
            False,
            "One or more contact audit pairs are invalid",
            invalid_pairs=invalid[:20],
            results=results,
        )
        return

    passed = resolution_errors == 0 and intersection_pairs == 0
    if resolution_errors:
        summary = (
            f"Blender contact audit could not resolve {resolution_errors} pair(s)"
        )
    elif intersection_pairs:
        summary = (
            f"Blender contact audit found {intersection_pairs} intersecting object pair(s)"
        )
    else:
        summary = "Blender contact audit passed"

    _response(
        command_id,
        passed,
        summary,
        audited_pairs=len(results),
        resolution_errors=resolution_errors,
        intersection_pairs=intersection_pairs,
        results=results,
    )


def _resolve_object(command: dict):
    name = str(command.get("object_name") or "").strip()
    object_id = str(command.get("ordax_object_id") or "").strip()

    if bool(name) == bool(object_id):
        raise ValueError("provide exactly one of object_name or ordax_object_id")

    if name:
        obj = bpy.context.scene.objects.get(name)
        if obj is None:
            raise ValueError(f"object not found in current scene: {name}")
        return obj

    matches = [
        obj
        for obj in bpy.context.scene.objects
        if str(obj.get("ordax_object_id") or "") == object_id
    ]
    if not matches:
        raise ValueError(f"ordax_object_id not found: {object_id}")
    if len(matches) > 1:
        raise ValueError(f"ordax_object_id is not unique: {object_id}")
    return matches[0]


def _coerce_vector(command: dict, key: str, *, allow_none: bool = True):
    value = command.get(key)
    if value is None and allow_none:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(isinstance(item, (int, float)) for item in value)
    ):
        raise ValueError(f"{key} must be a list of three numbers")
    return [float(item) for item in value]


def _object_transform(command: dict) -> None:
    command_id = command["id"]
    try:
        obj = _resolve_object(command)
        location = _coerce_vector(command, "location")
        rotation = _coerce_vector(command, "rotation_euler")
        scale = _coerce_vector(command, "scale")
        dimensions = _coerce_vector(command, "dimensions")
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    if all(value is None for value in (location, rotation, scale, dimensions)):
        _response(command_id, False, "at least one transform field is required")
        return

    if scale is not None and any(abs(value) < 1e-8 for value in scale):
        _response(command_id, False, "scale components must be non-zero")
        return
    if dimensions is not None and any(value <= 0 for value in dimensions):
        _response(command_id, False, "dimensions components must be positive")
        return

    before = _object_details(obj)
    try:
        if location is not None:
            obj.location = location
        if rotation is not None:
            obj.rotation_mode = "XYZ"
            obj.rotation_euler = rotation
        if scale is not None:
            obj.scale = scale
        if dimensions is not None:
            obj.dimensions = dimensions
        bpy.context.view_layer.update()
    except Exception as error:
        _response(command_id, False, f"{type(error).__name__}: {error}", before=before)
        return

    _response(
        command_id,
        True,
        "Blender object transform updated",
        before=before,
        object=_object_details(obj),
    )


_OBJECT_METADATA_KEYS = frozenset(
    {
        "ordax_asset",
        "ordax_component",
        "ordax_role",
        "ordax_object_id",
        "ordax_standard_version",
        "ordax_source_provider",
        "ordax_source_asset_id",
        "ordax_source_license",
        "ordax_source_url",
    }
)


def _object_metadata(command: dict) -> None:
    command_id = command["id"]
    try:
        obj = _resolve_object(command)
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    metadata = command.get("metadata")
    if not isinstance(metadata, dict) or not metadata:
        _response(command_id, False, "metadata must be a non-empty object")
        return

    unsupported = sorted(set(metadata) - _OBJECT_METADATA_KEYS)
    if unsupported:
        _response(
            command_id,
            False,
            "unsupported metadata key(s): " + ", ".join(unsupported),
        )
        return

    normalized = {}
    for key, value in metadata.items():
        if value is None:
            normalized[key] = None
            continue
        if not isinstance(value, (str, int, float, bool)):
            _response(command_id, False, f"{key} must be a scalar or null")
            return
        if isinstance(value, str) and len(value) > 1024:
            _response(command_id, False, f"{key} exceeds 1024 characters")
            return
        normalized[key] = value

    new_id = normalized.get("ordax_object_id")
    if isinstance(new_id, str) and new_id:
        duplicate = next(
            (
                candidate
                for candidate in bpy.context.scene.objects
                if candidate != obj
                and str(candidate.get("ordax_object_id") or "") == new_id
            ),
            None,
        )
        if duplicate is not None:
            _response(
                command_id,
                False,
                f"ordax_object_id already belongs to {duplicate.name}",
            )
            return

    before = _object_details(obj)
    for key, value in normalized.items():
        if value is None:
            try:
                del obj[key]
            except KeyError:
                pass
        else:
            obj[key] = value

    _response(
        command_id,
        True,
        "Blender object metadata updated",
        before=before,
        object=_object_details(obj),
    )



_QUALITY_AXES = {"x": 0, "y": 1, "z": 2}
_QUALITY_TYPES = {"dimensions", "symmetry", "proportion", "containment", "mesh_quality"}


def _quality_axis(value, field: str) -> tuple[str, int]:
    axis = str(value or "").strip().lower()
    if axis not in _QUALITY_AXES:
        raise ValueError(f"{field} must be one of x, y, z")
    return axis, _QUALITY_AXES[axis]


def _quality_tolerance(check: dict, default: float = 0.01) -> float:
    try:
        tolerance = float(check.get("tolerance", default))
    except (TypeError, ValueError):
        raise ValueError("tolerance must be a number")
    if tolerance < 0 or tolerance > 1000000:
        raise ValueError("tolerance must be between 0 and 1000000")
    return tolerance


def _quality_object(name, field: str):
    object_name = str(name or "").strip()
    if not object_name:
        raise ValueError(f"{field} is required")
    obj = bpy.context.scene.objects.get(object_name)
    if obj is None:
        raise ValueError(f"{field} was not found: {object_name}")
    return obj


def _world_extents(obj) -> dict:
    bounds = _world_bounds(obj)
    mins = bounds.get("aabb_min")
    maxs = bounds.get("aabb_max")
    if not mins or not maxs:
        raise ValueError(f"could not measure world bounds for {obj.name}")
    dimensions = [float(maxs[i]) - float(mins[i]) for i in range(3)]
    center = [(float(maxs[i]) + float(mins[i])) / 2.0 for i in range(3)]
    return {
        "min": _round_vector(mins),
        "max": _round_vector(maxs),
        "dimensions": _round_vector(dimensions),
        "center": _round_vector(center),
    }


def _quality_dimensions(check: dict) -> dict:
    obj = _quality_object(check.get("object_name"), "object_name")
    expected = check.get("expected")
    if (
        not isinstance(expected, list)
        or len(expected) != 3
        or not all(isinstance(item, (int, float)) for item in expected)
    ):
        raise ValueError("dimensions.expected must contain exactly three numbers")

    tolerance = _quality_tolerance(check)
    world_space = bool(check.get("world_space", False))
    actual = (
        _world_extents(obj)["dimensions"]
        if world_space
        else _round_vector(obj.dimensions)
    )
    expected_values = [float(item) for item in expected]
    errors = [abs(float(actual[i]) - expected_values[i]) for i in range(3)]
    passed = all(error <= tolerance for error in errors)
    return {
        "type": "dimensions",
        "passed": passed,
        "object_name": obj.name,
        "world_space": world_space,
        "expected": _round_vector(expected_values),
        "actual": _round_vector(actual),
        "absolute_error": _round_vector(errors),
        "max_error": round(max(errors), 6),
        "tolerance": tolerance,
    }


def _quality_symmetry(check: dict) -> dict:
    left = _quality_object(check.get("left_object"), "left_object")
    right = _quality_object(check.get("right_object"), "right_object")
    axis, axis_index = _quality_axis(check.get("axis"), "axis")
    tolerance = _quality_tolerance(check)
    try:
        mirror_coordinate = float(check.get("mirror_coordinate", 0.0))
    except (TypeError, ValueError):
        raise ValueError("mirror_coordinate must be a number")

    left_bounds = _world_extents(left)
    right_bounds = _world_extents(right)
    left_center = left_bounds["center"]
    right_center = right_bounds["center"]
    left_dimensions = left_bounds["dimensions"]
    right_dimensions = right_bounds["dimensions"]

    center_errors = []
    for index in range(3):
        if index == axis_index:
            expected_left = (2.0 * mirror_coordinate) - float(right_center[index])
            center_errors.append(abs(float(left_center[index]) - expected_left))
        else:
            center_errors.append(abs(float(left_center[index]) - float(right_center[index])))
    dimension_errors = [
        abs(float(left_dimensions[index]) - float(right_dimensions[index]))
        for index in range(3)
    ]
    max_error = max(center_errors + dimension_errors)
    return {
        "type": "symmetry",
        "passed": max_error <= tolerance,
        "left_object": left.name,
        "right_object": right.name,
        "axis": axis,
        "mirror_coordinate": mirror_coordinate,
        "left_center": left_center,
        "right_center": right_center,
        "center_error": _round_vector(center_errors),
        "dimension_error": _round_vector(dimension_errors),
        "max_error": round(max_error, 6),
        "tolerance": tolerance,
    }


def _quality_proportion(check: dict) -> dict:
    obj = _quality_object(check.get("object_name"), "object_name")
    axis_a, axis_a_index = _quality_axis(check.get("axis_a"), "axis_a")
    tolerance = _quality_tolerance(check, default=0.02)
    try:
        expected_ratio = float(check.get("expected_ratio"))
    except (TypeError, ValueError):
        raise ValueError("expected_ratio must be a number")
    if not (expected_ratio >= 0):
        raise ValueError("expected_ratio must be non-negative")

    world_space = bool(check.get("world_space", False))
    object_dimensions = (
        _world_extents(obj)["dimensions"]
        if world_space
        else _round_vector(obj.dimensions)
    )
    numerator = float(object_dimensions[axis_a_index])

    reference_name = str(check.get("reference_object") or "").strip()
    if reference_name:
        reference = _quality_object(reference_name, "reference_object")
        reference_axis, reference_axis_index = _quality_axis(
            check.get("reference_axis"), "reference_axis"
        )
        reference_dimensions = (
            _world_extents(reference)["dimensions"]
            if world_space
            else _round_vector(reference.dimensions)
        )
        denominator = float(reference_dimensions[reference_axis_index])
        denominator_label = f"{reference.name}.{reference_axis}"
    else:
        axis_b, axis_b_index = _quality_axis(check.get("axis_b"), "axis_b")
        denominator = float(object_dimensions[axis_b_index])
        denominator_label = f"{obj.name}.{axis_b}"

    if abs(denominator) <= 1e-12:
        raise ValueError("proportion denominator is zero")

    actual_ratio = numerator / denominator
    error = abs(actual_ratio - expected_ratio)
    return {
        "type": "proportion",
        "passed": error <= tolerance,
        "object_name": obj.name,
        "numerator": f"{obj.name}.{axis_a}",
        "denominator": denominator_label,
        "world_space": world_space,
        "expected_ratio": expected_ratio,
        "actual_ratio": round(actual_ratio, 6),
        "absolute_error": round(error, 6),
        "tolerance": tolerance,
    }


def _quality_containment(check: dict) -> dict:
    inner = _quality_object(check.get("inner_object"), "inner_object")
    outer = _quality_object(check.get("outer_object"), "outer_object")
    tolerance = _quality_tolerance(check)
    try:
        min_clearance = float(check.get("min_clearance", 0.0))
    except (TypeError, ValueError):
        raise ValueError("min_clearance must be a number")
    if min_clearance < 0:
        raise ValueError("min_clearance must be non-negative")

    inner_bounds = _world_extents(inner)
    outer_bounds = _world_extents(outer)
    lower_clearance = [
        float(inner_bounds["min"][i]) - float(outer_bounds["min"][i])
        for i in range(3)
    ]
    upper_clearance = [
        float(outer_bounds["max"][i]) - float(inner_bounds["max"][i])
        for i in range(3)
    ]
    clearances = lower_clearance + upper_clearance
    minimum_actual = min(clearances)
    deficit = max(0.0, min_clearance - minimum_actual)
    passed = minimum_actual + tolerance >= min_clearance
    return {
        "type": "containment",
        "passed": passed,
        "method": "world_aabb",
        "inner_object": inner.name,
        "outer_object": outer.name,
        "required_clearance": min_clearance,
        "minimum_actual_clearance": round(minimum_actual, 6),
        "clearance_deficit": round(deficit, 6),
        "lower_clearance": _round_vector(lower_clearance),
        "upper_clearance": _round_vector(upper_clearance),
        "tolerance": tolerance,
    }




def _quality_mesh(check: dict) -> dict:
    obj = _quality_object(check.get("object_name"), "object_name")
    if obj.type != "MESH":
        raise ValueError(f"mesh_quality requires a MESH object: {obj.name}")

    evaluated = bool(check.get("evaluated", True))
    try:
        epsilon = float(check.get("epsilon", 1e-10))
    except (TypeError, ValueError):
        raise ValueError("epsilon must be a number")
    if epsilon <= 0 or epsilon > 1.0:
        raise ValueError("epsilon must be greater than 0 and at most 1")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated_obj = None
    mesh = None
    must_clear = False
    bm = None
    try:
        if evaluated:
            evaluated_obj = obj.evaluated_get(depsgraph)
            mesh = evaluated_obj.to_mesh()
            must_clear = True
        else:
            mesh = obj.data

        if mesh is None:
            raise ValueError(f"mesh data is unavailable for {obj.name}")

        try:
            mesh.calc_loop_triangles()
        except Exception:
            pass

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        triangle_count = len(getattr(mesh, "loop_triangles", []))
        face_count = len(bm.faces)
        triangle_faces = sum(1 for face in bm.faces if len(face.verts) == 3)
        quad_faces = sum(1 for face in bm.faces if len(face.verts) == 4)
        ngon_faces = sum(1 for face in bm.faces if len(face.verts) > 4)
        quad_ratio = (quad_faces / face_count) if face_count else 0.0

        boundary_edges = sum(1 for edge in bm.edges if edge.is_boundary)
        wire_edges = sum(1 for edge in bm.edges if edge.is_wire)
        non_manifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
        loose_vertices = sum(1 for vert in bm.verts if not vert.link_edges)
        degenerate_faces = sum(1 for face in bm.faces if float(face.calc_area()) <= epsilon)
        zero_length_edges = sum(
            1 for edge in bm.edges
            if float((edge.verts[0].co - edge.verts[1].co).length) <= epsilon
        )
        uv_layers = len(getattr(mesh, "uv_layers", []))
        material_slots = len(getattr(obj, "material_slots", []))

        metrics = {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": face_count,
            "triangles": triangle_count,
            "triangle_faces": triangle_faces,
            "quad_faces": quad_faces,
            "ngon_faces": ngon_faces,
            "quad_ratio": round(quad_ratio, 6),
            "boundary_edges": boundary_edges,
            "wire_edges": wire_edges,
            "non_manifold_edges": non_manifold_edges,
            "loose_vertices": loose_vertices,
            "degenerate_faces": degenerate_faces,
            "zero_length_edges": zero_length_edges,
            "uv_layers": uv_layers,
            "material_slots": material_slots,
        }

        rules = []

        def maximum(field: str, actual: int) -> None:
            if field not in check or check.get(field) is None:
                return
            raw = check.get(field)
            if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
                raise ValueError(f"{field} must be a non-negative integer")
            rules.append({
                "rule": field,
                "passed": actual <= raw,
                "expected_max": raw,
                "actual": actual,
            })

        maximum("max_triangles", triangle_count)
        maximum("max_ngons", ngon_faces)
        maximum("max_boundary_edges", boundary_edges)
        maximum("max_wire_edges", wire_edges)
        maximum("max_non_manifold_edges", non_manifold_edges)
        maximum("max_loose_vertices", loose_vertices)
        maximum("max_degenerate_faces", degenerate_faces)
        maximum("max_zero_length_edges", zero_length_edges)

        if "min_quad_ratio" in check and check.get("min_quad_ratio") is not None:
            try:
                minimum_quad_ratio = float(check.get("min_quad_ratio"))
            except (TypeError, ValueError):
                raise ValueError("min_quad_ratio must be a number")
            if minimum_quad_ratio < 0 or minimum_quad_ratio > 1:
                raise ValueError("min_quad_ratio must be between 0 and 1")
            rules.append({
                "rule": "min_quad_ratio",
                "passed": quad_ratio >= minimum_quad_ratio,
                "expected_min": minimum_quad_ratio,
                "actual": round(quad_ratio, 6),
            })

        if bool(check.get("require_uv", False)):
            rules.append({
                "rule": "require_uv",
                "passed": uv_layers > 0,
                "expected_min": 1,
                "actual": uv_layers,
            })

        if bool(check.get("require_material", False)):
            rules.append({
                "rule": "require_material",
                "passed": material_slots > 0,
                "expected_min": 1,
                "actual": material_slots,
            })

        if bool(check.get("require_manifold", False)):
            rules.append({
                "rule": "require_manifold",
                "passed": non_manifold_edges == 0,
                "expected_max": 0,
                "actual": non_manifold_edges,
            })

        if not rules:
            raise ValueError(
                "mesh_quality requires at least one threshold or requirement"
            )

        failed = [rule for rule in rules if not rule["passed"]]
        return {
            "type": "mesh_quality",
            "passed": not failed,
            "object_name": obj.name,
            "evaluated": evaluated,
            "epsilon": epsilon,
            "metrics": metrics,
            "rules": rules,
            "failed_rules": len(failed),
        }
    finally:
        if bm is not None:
            try:
                bm.free()
            except Exception:
                pass
        if must_clear and evaluated_obj is not None:
            try:
                evaluated_obj.to_mesh_clear()
            except Exception:
                pass


def _quality_gate(command: dict) -> None:
    command_id = command["id"]
    checks = command.get("checks")
    if not isinstance(checks, list) or not checks:
        _response(command_id, False, "checks must be a non-empty list")
        return
    if len(checks) > 100:
        _response(command_id, False, "quality gate is limited to 100 checks")
        return

    results = []
    evaluators = {
        "dimensions": _quality_dimensions,
        "symmetry": _quality_symmetry,
        "proportion": _quality_proportion,
        "containment": _quality_containment,
        "mesh_quality": _quality_mesh,
    }
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            _response(command_id, False, f"quality check {index} must be an object")
            return
        if any(key in check for key in ("passed", "ok", "result")):
            _response(
                command_id,
                False,
                f"quality check {index} cannot provide its own completion claim",
            )
            return
        kind = str(check.get("type") or "").strip().lower()
        if kind not in _QUALITY_TYPES:
            _response(
                command_id,
                False,
                f"quality check {index} type must be one of: {', '.join(sorted(_QUALITY_TYPES))}",
            )
            return
        try:
            result = evaluators[kind](check)
        except ValueError as error:
            _response(
                command_id,
                False,
                f"quality check {index} is invalid: {error}",
                failed_check=index,
                check_type=kind,
            )
            return
        results.append(result)

    failed = [result for result in results if not result["passed"]]
    passed = not failed
    _response(
        command_id,
        passed,
        "Blender deterministic quality gate passed"
        if passed
        else "Blender deterministic quality gate failed",
        passed=passed,
        total_checks=len(results),
        passed_checks=len(results) - len(failed),
        failed_checks=len(failed),
        checks=results,
    )

def _checkpoint_name(label: str, command_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label.strip()).strip("-._")
    if not cleaned:
        cleaned = "checkpoint"
    return f"{int(time.time())}-{cleaned[:80]}-{command_id[:8]}.blend"


def _checkpoint_create(command: dict) -> None:
    command_id = command["id"]
    label = str(command.get("label") or "checkpoint")
    target = (CHECKPOINTS / _checkpoint_name(label, command_id)).resolve()
    if not _inside(target, CHECKPOINTS):
        _response(command_id, False, "checkpoint path escaped managed directory")
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True)
        metadata = {
            "id": target.stem,
            "label": label,
            "file": str(target),
            "created_at": time.time(),
            "source_file": bpy.data.filepath or "",
            "snapshot": _scene_snapshot(),
        }
        _write_json_atomic(target.with_suffix(".json"), metadata)
        _response(
            command_id,
            True,
            "Blender checkpoint created",
            checkpoint=metadata,
        )
    except Exception as error:
        _response(command_id, False, f"{type(error).__name__}: {error}")


def _checkpoint_list(command: dict) -> None:
    command_id = command["id"]
    entries = []
    for path in sorted(CHECKPOINTS.glob("*.blend"), key=lambda item: item.stat().st_mtime, reverse=True)[:100]:
        meta_path = path.with_suffix(".json")
        metadata = {}
        if meta_path.is_file():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8-sig"))
            except Exception:
                metadata = {}
        entries.append(
            {
                "id": path.stem,
                "file": str(path),
                "size_bytes": path.stat().st_size,
                "modified_at": path.stat().st_mtime,
                **metadata,
            }
        )

    _response(
        command_id,
        True,
        "Blender checkpoints listed",
        checkpoints=entries,
    )


def _checkpoint_restore(command: dict) -> None:
    command_id = command["id"]
    checkpoint_id = str(command.get("checkpoint_id") or "").strip()
    if not checkpoint_id or not re.fullmatch(r"[A-Za-z0-9._-]+", checkpoint_id):
        _response(command_id, False, "checkpoint_id is required and contains unsupported characters")
        return

    target = (CHECKPOINTS / f"{checkpoint_id}.blend").resolve()
    if not _inside(target, CHECKPOINTS) or not target.is_file():
        _response(command_id, False, "checkpoint does not exist in the managed checkpoint directory")
        return

    if bool(getattr(bpy.data, "is_dirty", False)) and not bool(command.get("discard_unsaved", False)):
        _response(
            command_id,
            False,
            "current Blender file has unsaved changes; set discard_unsaved=true to restore explicitly",
        )
        return

    _response(
        command_id,
        True,
        "Blender checkpoint restore scheduled",
        checkpoint_id=checkpoint_id,
        file=str(target),
    )

    def _restore_later():
        try:
            bpy.ops.wm.open_mainfile(filepath=str(target), load_ui=False)
        except Exception:
            pass
        return None

    bpy.app.timers.register(_restore_later, first_interval=0.20, persistent=True)


def _trajectory_append(event: dict) -> None:
    try:
        with TRAJECTORY.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError:
        pass


def _inspect(command: dict) -> None:
    command_id = command["id"]
    try:
        objects, truncated = _scene_objects(command)
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    _response(
        command_id,
        True,
        "Visible Blender scene inspected",
        object_count=len(bpy.context.scene.objects),
        returned_objects=len(objects),
        truncated=truncated,
        objects=[
            {
                "name": obj.name,
                "type": obj.type,
                "visible": bool(obj.visible_get()),
                "selected": bool(obj.select_get()),
                "location": _round_vector(obj.location),
                "rotation_euler": _round_vector(obj.rotation_euler),
                "scale": _round_vector(obj.scale),
                "parent": obj.parent.name if obj.parent else None,
                "dimensions": _round_vector(obj.dimensions),
                "ordax": _ordax_properties(obj),
            }
            for obj in objects
        ],
        collections=[collection.name for collection in bpy.data.collections[:200]],
        scene_ordax=_ordax_properties(bpy.context.scene),
    )



def _purge_script_modules() -> list[str]:
    """Drop cached project-script modules before a live generation pass.

    Blender Live is intentionally persistent. Python's normal import cache would
    otherwise keep modules loaded before a Git sync, making a newly-synced
    generation script execute stale dependencies until Blender restarts.
    """
    importlib.invalidate_caches()
    removed: list[str] = []
    scripts_root = SCRIPTS_ROOT.resolve()
    for name, module in list(sys.modules.items()):
        if not name or module is None:
            continue
        raw_file = getattr(module, "__file__", None)
        if not raw_file:
            continue
        try:
            module_path = Path(raw_file).expanduser().resolve()
            module_path.relative_to(scripts_root)
        except (OSError, RuntimeError, ValueError):
            continue
        sys.modules.pop(name, None)
        removed.append(name)
    importlib.invalidate_caches()
    return sorted(set(removed))

def _run_script(command: dict) -> None:
    command_id = command["id"]
    raw = str(command.get("script_path") or "")
    script = Path(raw).expanduser().resolve()

    if script.suffix.lower() != ".py" or not script.is_file():
        _response(command_id, False, "Live Blender script does not exist")
        return
    if not _inside(script, SCRIPTS_ROOT):
        _response(command_id, False, "Live Blender script is outside approved scripts directory")
        return

    before = _scene_snapshot()
    try:
        reloaded_modules = _purge_script_modules()
        runpy.run_path(str(script), run_name="__main__")
        _response(
            command_id,
            True,
            "Live Blender script executed",
            script_path=str(script),
            reloaded_modules=reloaded_modules,
            before=before,
        )
    except Exception as error:
        _response(
            command_id,
            False,
            f"{type(error).__name__}: {error}",
            script_path=str(script),
            before=before,
        )



def _serialize_rna_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return [float(item) for item in value]
    except Exception:
        return str(value)


def _rna_property_schema(prop) -> dict:
    data = {
        "identifier": str(getattr(prop, "identifier", "")),
        "name": str(getattr(prop, "name", "")),
        "description": str(getattr(prop, "description", "")),
        "type": str(getattr(prop, "type", "")),
        "subtype": str(getattr(prop, "subtype", "")),
        "is_readonly": bool(getattr(prop, "is_readonly", False)),
        "is_array": bool(getattr(prop, "is_array", False)),
        "array_length": int(getattr(prop, "array_length", 0) or 0),
    }
    if hasattr(prop, "default"):
        try:
            data["default"] = _serialize_rna_value(prop.default)
        except Exception:
            pass
    if str(getattr(prop, "type", "")) == "ENUM":
        try:
            data["enum_items"] = [
                {
                    "identifier": item.identifier,
                    "name": item.name,
                    "description": item.description,
                    "value": int(item.value),
                }
                for item in prop.enum_items
            ][:200]
        except Exception:
            pass
    for key in ("hard_min", "hard_max", "soft_min", "soft_max"):
        if hasattr(prop, key):
            try:
                data[key] = float(getattr(prop, key))
            except Exception:
                pass
    return data


def _api_schema(command: dict) -> None:
    command_id = command["id"]
    type_name = str(command.get("type_name") or "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", type_name):
        _response(command_id, False, "type_name must be a bpy.types class name")
        return
    blender_type = getattr(bpy.types, type_name, None)
    rna = getattr(blender_type, "bl_rna", None)
    if blender_type is None or rna is None:
        _response(command_id, False, f"Unknown Blender RNA type: {type_name}")
        return
    try:
        limit = max(1, min(500, int(command.get("max_properties", 200))))
    except (TypeError, ValueError):
        _response(command_id, False, "max_properties must be an integer")
        return

    properties = [
        _rna_property_schema(prop)
        for prop in list(rna.properties)
        if str(getattr(prop, "identifier", "")) != "rna_type"
    ]
    _response(
        command_id,
        True,
        "Blender RNA schema ready",
        type_name=type_name,
        base=str(getattr(rna, "base", None)),
        property_count=len(properties),
        truncated=len(properties) > limit,
        properties=properties[:limit],
    )



def _rna_function_schema(function) -> dict:
    parameters = []
    returns = []
    try:
        raw_parameters = list(function.parameters)
    except Exception:
        raw_parameters = []
    for param in raw_parameters:
        data = _rna_property_schema(param)
        if bool(getattr(param, "is_output", False)):
            returns.append(data)
        else:
            parameters.append(data)
    return {
        "identifier": str(getattr(function, "identifier", "")),
        "name": str(getattr(function, "name", "")),
        "description": str(getattr(function, "description", "")),
        "parameters": parameters,
        "returns": returns,
    }


def _did_you_mean(value: str, candidates, limit: int = 8) -> list[str]:
    normalized = [str(item) for item in candidates if str(item)]
    return difflib.get_close_matches(value, normalized, n=limit, cutoff=0.45)


def _api_lookup(command: dict) -> None:
    command_id = command["id"]
    query = str(command.get("query") or "").strip()
    if not query or len(query) > 300:
        _response(command_id, False, "query is required and must be at most 300 characters")
        return

    normalized = query
    for prefix in ("bpy.types.", "bpy."):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]

    # Operators: bpy.ops.mesh.primitive_cube_add
    if normalized.startswith("ops."):
        parts = normalized.split(".")
        if len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) for part in parts[1:]):
            _response(command_id, False, "Operator query must look like bpy.ops.mesh.primitive_cube_add")
            return
        category_name, operator_name = parts[1], parts[2]
        category = getattr(bpy.ops, category_name, None)
        operator = getattr(category, operator_name, None) if category is not None else None
        if operator is None:
            candidates = []
            if category is not None:
                try:
                    candidates = dir(category)
                except Exception:
                    pass
            _response(
                command_id,
                False,
                f"Unknown Blender operator: {query}",
                did_you_mean=_did_you_mean(operator_name, candidates),
            )
            return
        try:
            rna = operator.get_rna_type()
            properties = [
                _rna_property_schema(prop)
                for prop in list(rna.properties)
                if str(getattr(prop, "identifier", "")) != "rna_type"
            ]
            _response(
                command_id,
                True,
                "Blender operator schema ready",
                query=query,
                kind="operator",
                identifier=f"bpy.ops.{category_name}.{operator_name}",
                description=str(getattr(rna, "description", "")),
                parameters=properties,
            )
        except Exception as error:
            _response(command_id, False, f"{type(error).__name__}: {error}")
        return

    parts = normalized.split(".")
    type_name = parts[0]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", type_name):
        _response(command_id, False, "Type query must start with a bpy.types class name")
        return

    blender_type = getattr(bpy.types, type_name, None)
    rna = getattr(blender_type, "bl_rna", None)
    if blender_type is None or rna is None:
        candidates = [
            name for name in dir(bpy.types)
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name)
        ]
        _response(
            command_id,
            False,
            f"Unknown Blender RNA type: {type_name}",
            did_you_mean=_did_you_mean(type_name, candidates),
        )
        return

    if len(parts) == 1:
        properties = [
            _rna_property_schema(prop)
            for prop in list(rna.properties)
            if str(getattr(prop, "identifier", "")) != "rna_type"
        ]
        functions = [_rna_function_schema(fn) for fn in list(rna.functions)]
        _response(
            command_id,
            True,
            "Blender RNA type lookup ready",
            query=query,
            kind="type",
            type_name=type_name,
            properties=properties[:500],
            functions=functions[:300],
        )
        return

    if len(parts) != 2 or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", parts[1]):
        _response(command_id, False, "Member query must look like Object.ray_cast or Material.diffuse_color")
        return

    member = parts[1]
    prop = rna.properties.get(member)
    if prop is not None:
        _response(
            command_id,
            True,
            "Blender RNA property lookup ready",
            query=query,
            kind="property",
            type_name=type_name,
            property=_rna_property_schema(prop),
        )
        return

    function = rna.functions.get(member)
    if function is not None:
        _response(
            command_id,
            True,
            "Blender RNA function lookup ready",
            query=query,
            kind="function",
            type_name=type_name,
            function=_rna_function_schema(function),
        )
        return

    candidates = [
        str(getattr(prop, "identifier", "")) for prop in list(rna.properties)
    ] + [
        str(getattr(fn, "identifier", "")) for fn in list(rna.functions)
    ]
    _response(
        command_id,
        False,
        f"Unknown member on {type_name}: {member}",
        did_you_mean=_did_you_mean(member, candidates),
    )

def _socket_schema(socket) -> dict:
    data = {
        "name": str(getattr(socket, "name", "")),
        "identifier": str(getattr(socket, "identifier", "")),
        "bl_idname": str(getattr(socket, "bl_idname", "")),
        "enabled": bool(getattr(socket, "enabled", True)),
        "hide": bool(getattr(socket, "hide", False)),
        "is_linked": bool(getattr(socket, "is_linked", False)),
    }
    if hasattr(socket, "default_value"):
        try:
            data["default_value"] = _serialize_rna_value(socket.default_value)
        except Exception:
            pass
    for key in ("min_value", "max_value"):
        if hasattr(socket, key):
            try:
                data[key] = float(getattr(socket, key))
            except Exception:
                pass
    return data


def _node_schema(command: dict) -> None:
    command_id = command["id"]
    node_type = str(command.get("node_type") or "").strip()
    tree_type = str(command.get("tree_type") or "ShaderNodeTree").strip()
    overrides = command.get("property_overrides") or {}
    allowed_trees = {"ShaderNodeTree", "GeometryNodeTree", "CompositorNodeTree"}
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", node_type):
        _response(command_id, False, "node_type must be a Blender node bl_idname")
        return
    if tree_type not in allowed_trees:
        _response(command_id, False, "tree_type must be ShaderNodeTree, GeometryNodeTree, or CompositorNodeTree")
        return
    if not isinstance(overrides, dict) or len(overrides) > 30:
        _response(command_id, False, "property_overrides must be an object with at most 30 entries")
        return
    for key, value in overrides.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            _response(command_id, False, "property_overrides contains an invalid property name")
            return
        if not isinstance(value, (str, int, float, bool)):
            _response(command_id, False, "property_overrides values must be scalar")
            return

    group = None
    try:
        group = bpy.data.node_groups.new(
            name=f"__ORDAX_SCHEMA_{command_id[:8]}",
            type=tree_type,
        )
        node = group.nodes.new(node_type)
        applied = {}
        for key, value in overrides.items():
            if not hasattr(node, key):
                raise ValueError(f"Node {node_type} has no property: {key}")
            setattr(node, key, value)
            applied[key] = _serialize_rna_value(getattr(node, key))
        _response(
            command_id,
            True,
            "Blender node schema ready",
            node_type=node_type,
            tree_type=tree_type,
            node_name=node.name,
            label=str(getattr(node, "bl_label", "")),
            applied_overrides=applied,
            inputs=[_socket_schema(socket) for socket in node.inputs],
            outputs=[_socket_schema(socket) for socket in node.outputs],
        )
    except Exception as error:
        _response(command_id, False, f"{type(error).__name__}: {error}")
    finally:
        if group is not None:
            try:
                bpy.data.node_groups.remove(group)
            except Exception:
                pass


def _export_scene(command: dict) -> None:
    command_id = command["id"]
    raw = str(command.get("output_path") or "").strip()
    output = Path(raw).expanduser().resolve()
    export_format = str(command.get("format") or output.suffix.lstrip(".")).lower()

    expected_suffix = {"glb": ".glb", "fbx": ".fbx"}.get(export_format)
    if expected_suffix is None:
        _response(command_id, False, "format must be glb or fbx")
        return
    if output.suffix.lower() != expected_suffix:
        _response(command_id, False, f"output_path must end with {expected_suffix}")
        return
    if not _inside(output, PROJECT_ROOT):
        _response(command_id, False, "Export target must be inside registered project")
        return

    requested = command.get("object_names")
    if requested is not None and (
        not isinstance(requested, list)
        or len(requested) > 500
        or not all(isinstance(name, str) and name.strip() for name in requested)
    ):
        _response(command_id, False, "object_names must be a list of at most 500 object names")
        return

    previous_selected = []
    previous_active = None
    try:
        previous_selected = [obj.name for obj in bpy.context.selected_objects]
        previous_active = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
    except Exception:
        pass

    output.parent.mkdir(parents=True, exist_ok=True)
    exported_names = []
    try:
        use_selection = False
        if requested is not None:
            bpy.ops.object.select_all(action="DESELECT")
            missing = []
            for name in requested:
                obj = bpy.context.scene.objects.get(name.strip())
                if obj is None:
                    missing.append(name.strip())
                    continue
                obj.select_set(True)
                exported_names.append(obj.name)
            if missing:
                _response(command_id, False, "Some export objects were not found", missing=missing)
                return
            use_selection = True
        elif bool(command.get("selected_only", False)):
            use_selection = True
            exported_names = [obj.name for obj in bpy.context.selected_objects]

        animations = bool(command.get("animations", True))
        if export_format == "glb":
            bpy.ops.export_scene.gltf(
                filepath=str(output),
                check_existing=False,
                export_format="GLB",
                use_selection=use_selection,
                export_extras=True,
                export_apply=bool(command.get("apply_modifiers", False)),
                export_animations=animations,
            )
        else:
            bpy.ops.export_scene.fbx(
                filepath=str(output),
                check_existing=False,
                use_selection=use_selection,
                use_custom_props=True,
                use_mesh_modifiers=bool(command.get("apply_modifiers", True)),
                bake_anim=animations,
                add_leaf_bones=False,
            )

        ok = output.is_file() and output.stat().st_size > 0
        _response(
            command_id,
            ok,
            "Blender scene exported" if ok else "Blender export did not create a file",
            artifact=str(output),
            format=export_format,
            size_bytes=output.stat().st_size if ok else 0,
            sha256=hashlib.sha256(output.read_bytes()).hexdigest() if ok else None,
            exported_objects=exported_names,
            selection_only=use_selection,
        )
    except Exception as error:
        _response(command_id, False, f"{type(error).__name__}: {error}")
    finally:
        try:
            bpy.ops.object.select_all(action="DESELECT")
            for name in previous_selected:
                obj = bpy.context.scene.objects.get(name)
                if obj is not None:
                    obj.select_set(True)
            bpy.context.view_layer.objects.active = (
                bpy.context.scene.objects.get(previous_active)
                if previous_active
                else None
            )
        except Exception:
            pass


_MULTIVIEW_DIRECTIONS = {
    "front": (0.0, -1.0, 0.0),
    "back": (0.0, 1.0, 0.0),
    "left": (-1.0, 0.0, 0.0),
    "right": (1.0, 0.0, 0.0),
    "top": (0.0, 0.0, 1.0),
    "bottom": (0.0, 0.0, -1.0),
    "three_quarter": (1.0, -1.0, 0.75),
    "three_quarter_back": (-1.0, 1.0, 0.75),
}
_MULTIVIEW_DEFAULTS = (
    "front",
    "back",
    "left",
    "right",
    "top",
    "three_quarter",
)


def _multiview_target_objects(command: dict):
    requested = command.get("object_names")
    if requested is not None:
        if (
            not isinstance(requested, list)
            or not requested
            or len(requested) > 200
            or not all(isinstance(name, str) and name.strip() for name in requested)
        ):
            raise ValueError(
                "object_names must be a non-empty list of at most 200 object names"
            )
        missing = []
        objects = []
        allowed_types = {
            "MESH",
            "CURVE",
            "SURFACE",
            "META",
            "FONT",
            "VOLUME",
            "GREASEPENCIL",
        }
        unsupported = []
        for raw_name in requested:
            name = raw_name.strip()
            obj = bpy.context.scene.objects.get(name)
            if obj is None:
                missing.append(name)
            elif obj.type not in allowed_types:
                unsupported.append(f"{name}:{obj.type}")
            else:
                objects.append(obj)
        if missing:
            raise ValueError(
                "multiview objects were not found: " + ", ".join(missing[:20])
            )
        if unsupported:
            raise ValueError(
                "multiview objects are not renderable geometry: "
                + ", ".join(unsupported[:20])
            )
        return objects

    allowed_types = {
        "MESH",
        "CURVE",
        "SURFACE",
        "META",
        "FONT",
        "VOLUME",
        "GREASEPENCIL",
    }
    objects = [
        obj
        for obj in bpy.context.scene.objects
        if (
            obj.type in allowed_types
            and bool(obj.visible_get())
            and not bool(getattr(obj, "hide_render", False))
        )
    ]
    if not objects:
        raise ValueError("no visible renderable objects are available for multiview")
    return objects[:200]


def _multiview_world_corners(objects) -> tuple[list[Vector], list[str]]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners: list[Vector] = []
    used: list[str] = []
    for obj in objects:
        try:
            evaluated = obj.evaluated_get(depsgraph)
            bound_box = list(evaluated.bound_box)
            if len(bound_box) != 8:
                continue
            matrix = evaluated.matrix_world
            object_corners = [matrix @ Vector(corner) for corner in bound_box]
            if not all(all(abs(float(value)) < 1e15 for value in corner) for corner in object_corners):
                continue
            corners.extend(object_corners)
            used.append(obj.name)
        except Exception:
            continue
    if not corners:
        raise ValueError("selected multiview objects do not expose usable world bounds")
    return corners, used


def _multiview_bounds(corners: list[Vector]) -> dict:
    mins = Vector((
        min(point.x for point in corners),
        min(point.y for point in corners),
        min(point.z for point in corners),
    ))
    maxs = Vector((
        max(point.x for point in corners),
        max(point.y for point in corners),
        max(point.z for point in corners),
    ))
    center = (mins + maxs) * 0.5
    dimensions = maxs - mins
    return {
        "min": _round_vector(mins),
        "max": _round_vector(maxs),
        "center": _round_vector(center),
        "dimensions": _round_vector(dimensions),
        "diagonal": round(float(dimensions.length), 6),
    }


def _multiview_render_engine(
    scene,
    *,
    require_workbench: bool = False,
) -> tuple[str, str]:
    original = str(scene.render.engine)
    for candidate in ("BLENDER_WORKBENCH_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = candidate
            return original, candidate
        except Exception:
            continue
    scene.render.engine = original
    if require_workbench:
        raise RuntimeError(
            "silhouette multiview requires a supported Blender Workbench render engine"
        )
    return original, original


def _multiview_shading_state(scene) -> tuple[object | None, dict]:
    display = getattr(scene, "display", None)
    shading = getattr(display, "shading", None) if display is not None else None
    if shading is None:
        return None, {}
    state = {}
    for field in (
        "light",
        "color_type",
        "single_color",
        "background_type",
        "background_color",
        "show_shadows",
        "show_cavity",
        "show_specular_highlight",
    ):
        if not hasattr(shading, field):
            continue
        try:
            value = getattr(shading, field)
            if field in {"single_color", "background_color"}:
                value = tuple(float(item) for item in value)
            state[field] = value
        except Exception:
            continue
    return shading, state


def _multiview_restore_shading(shading, state: dict) -> None:
    if shading is None:
        return
    for field, value in state.items():
        try:
            setattr(shading, field, value)
        except Exception:
            pass


def _multiview_apply_silhouette(scene) -> None:
    display = getattr(scene, "display", None)
    shading = getattr(display, "shading", None) if display is not None else None
    if shading is None:
        raise RuntimeError("silhouette multiview requires scene display shading")
    required = {
        "light": "FLAT",
        "color_type": "SINGLE",
        "single_color": (0.0, 0.0, 0.0),
        "background_type": "VIEWPORT",
        "background_color": (1.0, 1.0, 1.0),
        "show_shadows": False,
        "show_cavity": False,
        "show_specular_highlight": False,
    }
    for field, value in required.items():
        if not hasattr(shading, field):
            raise RuntimeError(
                f"silhouette multiview requires Workbench shading property: {field}"
            )
        setattr(shading, field, value)


def _multiview_capture(command: dict) -> None:
    command_id = command["id"]
    raw_dir = str(command.get("output_dir") or "").strip()
    output_dir = Path(raw_dir).expanduser().resolve()
    if not raw_dir or not _inside(output_dir, ARTIFACTS_ROOT):
        _response(
            command_id,
            False,
            "Multiview output_dir must be inside the managed artifact directory",
        )
        return

    raw_views = command.get("views", list(_MULTIVIEW_DEFAULTS))
    if (
        not isinstance(raw_views, list)
        or not raw_views
        or len(raw_views) > len(_MULTIVIEW_DIRECTIONS)
    ):
        _response(command_id, False, "views must be a non-empty bounded list")
        return
    views = []
    for raw in raw_views:
        view = str(raw or "").strip().lower()
        if view not in _MULTIVIEW_DIRECTIONS:
            _response(
                command_id,
                False,
                "unsupported multiview view: " + view,
                supported_views=sorted(_MULTIVIEW_DIRECTIONS),
            )
            return
        if view in views:
            _response(command_id, False, "multiview views must be unique")
            return
        views.append(view)

    mode = str(command.get("mode") or "material").strip().lower()
    if mode not in {"material", "silhouette"}:
        _response(command_id, False, "multiview mode must be material or silhouette")
        return

    try:
        width = int(command.get("width", 768))
        height = int(command.get("height", 768))
        margin = float(command.get("margin", 1.15))
    except (TypeError, ValueError):
        _response(command_id, False, "width, height and margin must be numeric")
        return
    if width < 128 or width > 4096 or height < 128 or height > 4096:
        _response(command_id, False, "multiview resolution must be between 128 and 4096")
        return
    if margin < 1.0 or margin > 3.0:
        _response(command_id, False, "multiview margin must be between 1.0 and 3.0")
        return

    try:
        objects = _multiview_target_objects(command)
        corners, used_objects = _multiview_world_corners(objects)
    except ValueError as error:
        _response(command_id, False, str(error))
        return

    bounds = _multiview_bounds(corners)
    center = Vector(bounds["center"])
    diagonal = max(float(bounds["diagonal"]), 0.001)
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene
    original_camera = scene.camera
    old_path = scene.render.filepath
    old_format = scene.render.image_settings.file_format
    old_resolution_x = scene.render.resolution_x
    old_resolution_y = scene.render.resolution_y
    old_resolution_percentage = scene.render.resolution_percentage
    old_film_transparent = bool(getattr(scene.render, "film_transparent", False))
    old_engine = str(scene.render.engine)
    shading, shading_state = _multiview_shading_state(scene)

    camera_data = None
    camera = None
    engine_used = old_engine
    records = []
    error = None
    requested_names = command.get("object_names")
    render_visibility = {
        obj.name: bool(getattr(obj, "hide_render", False))
        for obj in bpy.context.scene.objects
    }
    try:
        if requested_names is not None:
            target_names = {obj.name for obj in objects}
            for scene_object in bpy.context.scene.objects:
                try:
                    scene_object.hide_render = scene_object.name not in target_names
                except Exception:
                    pass
        camera_data = bpy.data.cameras.new(f"__ORDAX_MULTIVIEW_CAMERA_{command_id[:8]}")
        camera = bpy.data.objects.new(
            f"__ORDAX_MULTIVIEW_CAMERA_{command_id[:8]}",
            camera_data,
        )
        scene.collection.objects.link(camera)
        scene.camera = camera
        camera_data.type = "ORTHO"

        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        if hasattr(scene.render, "film_transparent"):
            scene.render.film_transparent = False

        _, engine_used = _multiview_render_engine(
            scene,
            require_workbench=(mode == "silhouette"),
        )
        if mode == "silhouette":
            _multiview_apply_silhouette(scene)
        distance = max(diagonal * 2.5, 2.0)
        aspect = float(width) / float(height)

        for view in views:
            direction = Vector(_MULTIVIEW_DIRECTIONS[view]).normalized()
            camera.location = center + (direction * distance)
            look_direction = center - camera.location
            camera.rotation_euler = look_direction.to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()

            camera_inverse = camera.matrix_world.inverted()
            projected = [camera_inverse @ corner for corner in corners]
            xs = [point.x for point in projected]
            ys = [point.y for point in projected]
            projected_width = max(xs) - min(xs)
            projected_height = max(ys) - min(ys)
            camera_data.ortho_scale = max(
                projected_height,
                projected_width / aspect,
                0.001,
            ) * margin
            camera_data.clip_start = max(0.001, distance - (diagonal * 1.5))
            camera_data.clip_end = max(
                camera_data.clip_start + 1.0,
                distance + (diagonal * 1.5),
            )

            output = output_dir / f"{view}.png"
            scene.render.filepath = str(output)
            bpy.ops.render.render(write_still=True)
            if not output.is_file() or output.stat().st_size <= 0:
                raise RuntimeError(f"multiview render did not create {view}.png")

            records.append({
                "view": view,
                "artifact": str(output),
                "size_bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "camera_location": _round_vector(camera.location),
                "camera_rotation_euler": _round_vector(camera.rotation_euler),
                "ortho_scale": round(float(camera_data.ortho_scale), 6),
                "direction_from_target": _round_vector(direction),
            })

        manifest = {
            "project": CFG.ordax_project_slug,
            "views": records,
            "objects": used_objects,
            "bounds": bounds,
            "resolution": [width, height],
            "margin": margin,
            "projection": "orthographic",
            "render_engine": engine_used,
            "mode": mode,
        }
        manifest_path = output_dir / "multiview.json"
        _write_json_atomic(manifest_path, manifest)
    except Exception as caught:
        error = caught
    finally:
        scene.camera = original_camera
        scene.render.filepath = old_path
        scene.render.image_settings.file_format = old_format
        scene.render.resolution_x = old_resolution_x
        scene.render.resolution_y = old_resolution_y
        scene.render.resolution_percentage = old_resolution_percentage
        _multiview_restore_shading(shading, shading_state)
        try:
            scene.render.engine = old_engine
        except Exception:
            pass
        if hasattr(scene.render, "film_transparent"):
            scene.render.film_transparent = old_film_transparent
        for object_name, hidden in render_visibility.items():
            obj = bpy.context.scene.objects.get(object_name)
            if obj is not None:
                try:
                    obj.hide_render = hidden
                except Exception:
                    pass
        if camera is not None:
            try:
                bpy.data.objects.remove(camera, do_unlink=True)
            except Exception:
                pass
        if camera_data is not None:
            try:
                bpy.data.cameras.remove(camera_data)
            except Exception:
                pass

    if error is not None:
        _response(
            command_id,
            False,
            f"{type(error).__name__}: {error}",
            artifacts=records,
            bounds=bounds,
            render_engine=engine_used,
            mode=mode,
        )
        return

    manifest_path = output_dir / "multiview.json"
    primary = next(
        (item["artifact"] for item in records if item["view"] == "three_quarter"),
        records[0]["artifact"] if records else None,
    )
    _response(
        command_id,
        bool(records),
        "Deterministic Blender multiview captured",
        artifacts=records,
        primary_artifact=primary,
        manifest=str(manifest_path),
        bounds=bounds,
        objects=used_objects,
        resolution=[width, height],
        margin=margin,
        projection="orthographic",
        render_engine=engine_used,
        mode=mode,
    )


def _capture_viewport(command: dict) -> None:
    command_id = command["id"]
    raw = str(command.get("output_path") or "")
    output = Path(raw).expanduser().resolve()

    if output.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        _response(command_id, False, "Viewport output must be PNG or JPEG")
        return
    if not _inside(output, ARTIFACTS_ROOT):
        _response(command_id, False, "Viewport output is outside managed artifact directory")
        return

    output.parent.mkdir(parents=True, exist_ok=True)

    window = bpy.context.window
    screen = window.screen if window else None
    area = next((a for a in screen.areas if a.type == "VIEW_3D"), None) if screen else None
    region = next((r for r in area.regions if r.type == "WINDOW"), None) if area else None
    if not window or not area or not region:
        _response(command_id, False, "No visible 3D viewport is available")
        return

    scene = bpy.context.scene
    old_path = scene.render.filepath
    old_format = scene.render.image_settings.file_format
    try:
        scene.render.filepath = str(output)
        scene.render.image_settings.file_format = "PNG"
        with bpy.context.temp_override(window=window, area=area, region=region):
            bpy.ops.render.opengl(write_still=True, view_context=True)
        _response(
            command_id,
            output.is_file() and output.stat().st_size > 0,
            "Visible Blender viewport captured",
            artifact=str(output),
        )
    except Exception as error:
        _response(command_id, False, f"{type(error).__name__}: {error}")
    finally:
        scene.render.filepath = old_path
        scene.render.image_settings.file_format = old_format


def _save(command: dict) -> None:
    command_id = command["id"]
    raw = str(command.get("target_path") or "").strip()

    if raw:
        target = Path(raw).expanduser().resolve()
        if target.suffix.lower() != ".blend" or not _inside(target, PROJECT_ROOT):
            _response(command_id, False, "Save target must be a .blend inside registered project")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            bpy.ops.wm.save_as_mainfile(filepath=str(target))
            _response(command_id, True, "Visible Blender file saved", file=str(target))
        except Exception as error:
            _response(command_id, False, f"{type(error).__name__}: {error}")
        return

    current = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if current is None or not _inside(current, PROJECT_ROOT):
        _response(command_id, False, "Current Blender file is not inside registered project")
        return

    try:
        bpy.ops.wm.save_mainfile()
        _response(command_id, True, "Visible Blender file saved", file=str(current))
    except Exception as error:
        _response(command_id, False, f"{type(error).__name__}: {error}")


def _process(path: Path) -> None:
    try:
        command = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        return

    command_id = str(command.get("id") or "")
    operation = str(command.get("operation") or "")
    try:
        path.unlink()
    except OSError:
        pass

    if not command_id:
        return

    before_snapshot = _scene_snapshot()
    started_at = time.time()
    inflight_path = INFLIGHT / (command_id + ".json")
    _write_json_atomic(
        inflight_path,
        {
            "id": command_id,
            "operation": operation,
            "started_at": time.time(),
            "project": CFG.ordax_project_slug,
        },
    )

    try:
        if operation == "ping":
            _response(command_id, True, "Visible Blender companion ready")
        elif operation == "inspect":
            _inspect(command)
        elif operation == "scene_snapshot":
            _scene_snapshot_rich(command)
        elif operation == "scene_reset":
            _scene_reset(command)
        elif operation == "object_inspect":
            _object_inspect(command)
        elif operation == "object_fingerprints":
            _object_fingerprints(command)
        elif operation == "contact_audit":
            _contact_audit(command)
        elif operation == "quality_gate":
            _quality_gate(command)
        elif operation == "object_transform":
            _object_transform(command)
        elif operation == "object_metadata":
            _object_metadata(command)
        elif operation == "api_schema":
            _api_schema(command)
        elif operation == "api_lookup":
            _api_lookup(command)
        elif operation == "node_schema":
            _node_schema(command)
        elif operation == "export_scene":
            _export_scene(command)
        elif operation == "checkpoint_create":
            _checkpoint_create(command)
        elif operation == "checkpoint_restore":
            _checkpoint_restore(command)
        elif operation == "checkpoint_list":
            _checkpoint_list(command)
        elif operation == "run_script":
            _run_script(command)
        elif operation == "capture_viewport":
            _capture_viewport(command)
        elif operation == "multiview_capture":
            _multiview_capture(command)
        elif operation == "save":
            _save(command)
        elif operation == "quit":
            _response(command_id, True, "Visible Blender session closing")

            def _quit_later():
                bpy.ops.wm.quit_blender()
                return None

            bpy.app.timers.register(_quit_later, first_interval=0.15)
        else:
            _response(command_id, False, f"Unsupported Blender live operation: {operation}")
    finally:
        result_path = RESULTS / f"{command_id}.json"
        result = {}
        if result_path.is_file():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8-sig"))
            except Exception:
                result = {}
        _trajectory_append(
            {
                "id": command_id,
                "operation": operation,
                "started_at": started_at,
                "completed_at": time.time(),
                "ok": bool(result.get("ok")),
                "summary": result.get("summary"),
                "before": before_snapshot,
                "after": result.get("snapshot") or _scene_snapshot(),
            }
        )
        try:
            inflight_path.unlink()
        except OSError:
            pass


def _tick():
    try:
        _write_presence()
        commands = sorted(INBOX.glob("*.json"))
        if commands:
            _process(commands[0])
            _write_presence(force=True)
    except Exception:
        # Keep the visible Blender session alive; the next presence write will
        # show whether the companion recovered.
        pass
    return 0.1


for stale in INFLIGHT.glob("*.json"):
    try:
        stale.unlink()
    except OSError:
        pass

_write_presence(force=True)
if not bpy.app.timers.is_registered(_tick):
    bpy.app.timers.register(_tick, first_interval=0.10, persistent=True)
