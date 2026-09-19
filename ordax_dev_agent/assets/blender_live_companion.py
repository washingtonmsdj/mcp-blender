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
import sys
import time
from pathlib import Path

import bpy
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

PROTOCOL_VERSION = 3
CAPABILITIES = [
    "ping",
    "inspect",
    "scene_snapshot",
    "scene_reset",
    "object_inspect",
    "contact_audit",
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
        elif operation == "contact_audit":
            _contact_audit(command)
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
