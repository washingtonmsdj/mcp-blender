# OrdaX Dev Agent - visible Blender companion.
# Runs inside an interactive Blender window and executes only typed commands
# emitted by the local allow-listed agent.
from __future__ import annotations

import argparse
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

PROTOCOL_VERSION = 2
CAPABILITIES = [
    "ping",
    "inspect",
    "scene_snapshot",
    "object_inspect",
    "contact_audit",
    "object_transform",
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
    selected = [obj.name for obj in bpy.context.selected_objects[:40]]
    active = bpy.context.view_layer.objects.active
    return {
        "project": CFG.ordax_project_slug,
        "timestamp": time.time(),
        "blender_version": ".".join(str(v) for v in bpy.app.version),
        "file": bpy.data.filepath or "",
        "is_dirty": bool(getattr(bpy.data, "is_dirty", False)),
        "scene": bpy.context.scene.name if bpy.context.scene else "",
        "frame": int(bpy.context.scene.frame_current) if bpy.context.scene else 0,
        "mode": getattr(bpy.context, "mode", "UNKNOWN"),
        "objects": len(bpy.data.objects),
        "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials),
        "selected": selected,
        "active_object": active.name if active else None,
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
    body = {
        "id": command_id,
        "ok": ok,
        "summary": summary,
        **data,
        "snapshot": _scene_snapshot(),
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

    def tree_for(obj):
        if obj.name not in cache:
            if obj.type != "MESH":
                cache[obj.name] = None
            else:
                cache[obj.name] = BVHTree.FromObject(obj, depsgraph, epsilon=0.00001)
        return cache[obj.name]

    results = []
    invalid = []
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
            results.append(
                {
                    "a": item[0],
                    "b": item[1],
                    "ok": False,
                    "error": "object_not_found",
                }
            )
            continue

        left_tree = tree_for(left)
        right_tree = tree_for(right)
        if left_tree is None or right_tree is None:
            results.append(
                {
                    "a": left.name,
                    "b": right.name,
                    "ok": False,
                    "error": "mesh_required",
                }
            )
            continue

        overlaps = left_tree.overlap(right_tree)
        count = len(overlaps)
        intersects = count > 0
        if intersects:
            intersection_pairs += 1
        results.append(
            {
                "a": left.name,
                "b": right.name,
                "ok": True,
                "intersects": intersects,
                "triangle_overlap_count": count,
                "a_bounds": _world_bounds(left),
                "b_bounds": _world_bounds(right),
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

    _response(
        command_id,
        intersection_pairs == 0,
        "Blender contact audit passed"
        if intersection_pairs == 0
        else f"Blender contact audit found {intersection_pairs} intersecting object pair(s)",
        audited_pairs=len(results),
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
        runpy.run_path(str(script), run_name="__main__")
        _response(
            command_id,
            True,
            "Live Blender script executed",
            script_path=str(script),
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
        elif operation == "object_inspect":
            _object_inspect(command)
        elif operation == "contact_audit":
            _contact_audit(command)
        elif operation == "object_transform":
            _object_transform(command)
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
