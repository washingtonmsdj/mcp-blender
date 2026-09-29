"""Typed modeling contracts shared by the host and Blender runtime.

Mutation implementations remain deliberately separate from validation. This
module contains no bpy imports and is safe to unit-test in ordinary Python.
"""
from __future__ import annotations

import copy
import math
from typing import Any


MAX_MODIFIER_STACK = 8
MAX_EVALUATED_FACES = 200000
MAX_PROJECTED_SUBSURF_FACES = 500000
MAX_ARRAY_COUNT = 64
MAX_PROJECTED_ARRAY_FACES = 500000
MAX_SCATTER_INSTANCES = 5000
MAX_SCATTER_DENSITY = 1000.0
MAX_SCATTER_SOURCE_FACES = 100000
MAX_PROJECTED_SCATTER_FACES = 2000000
MAX_CUTTER_PROFILES = 8
MAX_CUTTER_SEGMENTS = 64
MAX_CUTTER_POLYGON_POINTS = 16
MAX_CUTTER_GENERATED_FACES = 12000


MODELING_SCHEMAS = {
    "create_primitive": {
        "status": "available",
        "action": "blender.live_create_primitive",
        "runtime_requirements": [
            "object_mode",
            "no_render_job",
            "unique_object_name",
        ],
        "failure_policy": [
            "remove_partial_object_on_failure",
            "remove_partial_mesh_on_failure",
        ],
        "description": (
            "Typed primitive creation validated by BlenderBench on Blender 5.2.2. "
            "Supports cube, sphere and cylinder creation under runtime guards."
        ),
        "required": ["name", "primitive"],
        "properties": {
            "name": {"type": "string", "max_utf8_bytes": 63},
            "primitive": {"enum": ["cube", "sphere", "cylinder"]},
            "location": {"type": "vector3", "minimum": -100000, "maximum": 100000},
            "size": {"type": "number", "minimum": 0.0001, "maximum": 10000},
            "radius": {"type": "number", "minimum": 0.0001, "maximum": 10000},
            "depth": {"type": "number", "minimum": 0.0001, "maximum": 10000},
            "segments": {"type": "integer", "minimum": 8, "maximum": 64},
        },
    },
    "object_transform": {
        "status": "available",
        "action": "blender.live_object_transform",
        "description": (
            "Existing typed transform action. Provide exactly one object selector "
            "and at least one transform field."
        ),
        "selectors": ["object_name", "ordax_object_id"],
        "properties": {
            "location": {"type": "vector3", "minimum": -100000, "maximum": 100000},
            "rotation_euler": {
                "type": "vector3",
                "unit": "radians",
                "minimum": -100000,
                "maximum": 100000,
            },
            "scale": {"type": "vector3", "minimum": 0.0001, "maximum": 1000},
            "dimensions": {"type": "vector3", "minimum": 0.0001, "maximum": 100000},
        },
    },
    "surface_scatter": {
        "status": "available",
        "action": "blender.live_surface_scatter",
        "runtime_requirements": [
            "object_mode",
            "no_render_job",
            "local_nonlinked_mesh_target",
            "local_nonlinked_mesh_source",
            "unique_modifier_name",
            "source_and_target_must_differ",
            "animated_or_constrained_target_requires_dedicated_workflow",
        ],
        "failure_policy": [
            "remove_new_modifier_on_failure",
            "remove_new_node_group_on_failure",
            "preserve_source_object",
            "preserve_existing_modifier_stack",
        ],
        "runtime_guards": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_target_faces": MAX_EVALUATED_FACES,
            "max_source_faces": MAX_SCATTER_SOURCE_FACES,
            "max_instances": MAX_SCATTER_INSTANCES,
            "max_density": MAX_SCATTER_DENSITY,
            "max_projected_instance_faces": MAX_PROJECTED_SCATTER_FACES,
        },
        "description": (
            "Fixed-seed Geometry Nodes surface scatter using preserved instances, "
            "validated by BlenderBench on Blender 5.2.2 with hard instance and projected-geometry budgets."
        ),
        "required": ["name", "source_object_name"],
        "selectors": ["object_name", "ordax_object_id"],
        "properties": {
            "name": {"type": "string", "max_utf8_bytes": 63},
            "source_object_name": {"type": "string", "max_utf8_bytes": 63},
            "density": {"type": "number", "minimum": 0.0001, "maximum": MAX_SCATTER_DENSITY},
            "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647},
            "max_instances": {"type": "integer", "minimum": 1, "maximum": MAX_SCATTER_INSTANCES},
            "scale_min": {"type": "number", "minimum": 0.001, "maximum": 100},
            "scale_max": {"type": "number", "minimum": 0.001, "maximum": 100},
            "align_to_normal": {"type": "boolean"},
            "keep_surface": {"type": "boolean"},
        },
    },
    "boolean_cut_preview": {
        "status": "available",
        "action": "blender.live_boolean_cut_preview",
        "workflow_actions": {
            "commit": "blender.live_boolean_cut_commit",
            "cancel": "blender.live_boolean_cut_cancel",
        },
        "runtime_requirements": [
            "object_mode",
            "no_render_job",
            "local_nonlinked_mesh_target",
            "animated_or_constrained_target_requires_dedicated_workflow",
            "bounded_exact_boolean_profiles",
        ],
        "failure_policy": [
            "remove_preview_modifiers_on_failure",
            "remove_preview_cutters_on_failure",
            "preserve_target_mesh",
            "preserve_existing_modifier_stack",
        ],
        "runtime_guards": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_target_faces": MAX_EVALUATED_FACES,
            "max_profiles": MAX_CUTTER_PROFILES,
            "max_segments": MAX_CUTTER_SEGMENTS,
            "max_polygon_points": MAX_CUTTER_POLYGON_POINTS,
            "max_generated_cutter_faces": MAX_CUTTER_GENERATED_FACES,
        },
        "description": (
            "Non-destructive exact-boolean preview with bounded box, circle, slot, "
            "convex polygon and vent profiles. Commit keeps modifiers live and hides "
            "cutters; cancel removes the whole preview in one operation. Validated by "
            "BlenderBench on Blender 5.2.2 across box/circle/slot/polygon/vent profiles."
        ),
        "required": ["name", "profiles"],
        "selectors": ["object_name", "ordax_object_id"],
        "properties": {
            "name": {"type": "string", "max_utf8_bytes": 63},
            "profiles": {"type": "array", "minimum_items": 1, "maximum_items": MAX_CUTTER_PROFILES},
        },
    },
    "mesh_cleanup": {
        "status": "available",
        "action": "blender.live_mesh_cleanup",
        "runtime_requirements": [
            "object_mode",
            "no_render_job",
            "local_nonlinked_mesh_target",
            "single_user_mesh_data",
            "no_shape_keys",
            "no_modifiers",
            "expected_base_geometry_sha256_matches",
            "animated_or_constrained_target_requires_dedicated_workflow",
        ],
        "failure_policy": [
            "mutate_working_mesh_copy_only",
            "swap_mesh_datablock_only_after_success",
            "restore_original_mesh_on_failure",
        ],
        "description": (
            "Revision-guarded topology cleanup validated by BlenderBench on Blender 5.2.2. "
            "The promoted repair removes only truly isolated loose vertices; broader topology "
            "edits remain diagnostic-only."
        ),
        "required": ["repair", "expected_base_geometry_sha256"],
        "selectors": ["object_name", "ordax_object_id"],
        "properties": {
            "repair": {"enum": ["remove_loose_vertices"]},
            "expected_base_geometry_sha256": {"type": "sha256"},
            "expected_loose_vertices": {"type": "integer", "minimum": 1, "maximum": 1000000},
        },
    },
    "add_modifier": {
        "status": "available",
        "action": "blender.live_add_modifier",
        "runtime_requirements": [
            "object_mode",
            "no_render_job",
            "local_nonlinked_mesh_target",
            "unique_modifier_name",
            "animated_or_constrained_target_requires_dedicated_workflow",
        ],
        "failure_policy": [
            "remove_new_modifier_on_failure",
            "preserve_existing_modifier_stack",
        ],
        "runtime_guards": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_evaluated_faces": MAX_EVALUATED_FACES,
            "max_projected_subsurf_faces": MAX_PROJECTED_SUBSURF_FACES,
        },
        "type_overrides": {
            "ARRAY": {
                "status": "available",
                "runtime_requirements": [
                    "object_mode",
                    "no_render_job",
                    "local_nonlinked_mesh_target",
                    "unique_modifier_name",
                    "animated_or_constrained_target_requires_dedicated_workflow",
                    "fixed_count_linear_array_only",
                ],
                "runtime_guards": {
                    "max_array_count": MAX_ARRAY_COUNT,
                    "max_evaluated_faces": MAX_EVALUATED_FACES,
                    "max_projected_array_faces": MAX_PROJECTED_ARRAY_FACES,
                },
                "failure_policy": [
                    "remove_new_modifier_on_failure",
                    "preserve_existing_modifier_stack",
                ],
                "description": (
                    "Non-destructive fixed-count linear array, "
                    "validated by BlenderBench on Blender 5.2.2 with count and rollback guards."
                ),
            }
        },
        "description": (
            "Typed modifier insertion validated by BlenderBench on Blender 5.2.2. "
            "Supports BEVEL, SUBSURF, SOLIDIFY and MIRROR under runtime budgets. "
            "ARRAY is available as a fixed-count linear variant under bounded runtime budgets."
        ),
        "required": ["name", "type"],
        "selectors": ["object_name", "ordax_object_id"],
        "properties": {
            "name": {"type": "string", "max_utf8_bytes": 63},
            "type": {"enum": ["BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR", "ARRAY"]},
            "width": {"type": "number", "minimum": 0, "maximum": 100},
            "segments": {"type": "integer", "minimum": 1, "maximum": 6},
            "levels": {"type": "integer", "minimum": 0, "maximum": 2},
            "thickness": {"type": "number", "minimum": -100, "maximum": 100},
            "axis": {"enum": ["X", "Y", "Z"]},
            "count": {"type": "integer", "minimum": 2, "maximum": MAX_ARRAY_COUNT},
            "relative_offset": {"type": "vector3", "minimum": -100, "maximum": 100},
            "constant_offset": {"type": "vector3", "minimum": -10000, "maximum": 10000},
        },
    },
}

_HOST_META_FIELDS = {"project", "timeout_seconds"}
_TRANSFORM_FIELDS = {"location", "rotation_euler", "scale", "dimensions"}


def modeling_schemas() -> dict[str, Any]:
    return copy.deepcopy(MODELING_SCHEMAS)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must contain only finite numbers")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must contain only finite numbers")
    return result


def _bounded_number(
    value: Any,
    field: str,
    minimum: float,
    maximum: float,
    *,
    integer: bool = False,
) -> int | float:
    numeric = _finite_number(value, field)
    if integer:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{field} must be an integer")
        result: int | float = int(value)
    else:
        result = numeric
    if result < minimum or result > maximum:
        raise ValueError(
            f"{field} must be between {minimum:g} and {maximum:g}"
        )
    return result


def _bounded_string(value: Any, field: str, *, max_utf8_bytes: int = 63) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    result = value.strip()
    if (
        not result
        or len(result.encode("utf-8")) > max_utf8_bytes
        or any(ord(character) < 32 for character in result)
    ):
        raise ValueError(f"{field} must be a non-empty bounded UTF-8 string")
    return result


def _sha256(value: Any, field: str) -> str:
    result = _bounded_string(value, field, max_utf8_bytes=64).lower()
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValueError(f"{field} must be a 64-character SHA-256 hex digest")
    return result


def _vector3(
    value: Any,
    field: str,
    minimum: float,
    maximum: float,
) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{field} must be a list of three finite numbers")
    normalized = [_finite_number(item, field) for item in value]
    if any(item < minimum or item > maximum for item in normalized):
        raise ValueError(
            f"{field} components must be between {minimum:g} and {maximum:g}"
        )
    return normalized


def _reject_unknown_fields(
    payload: dict[str, Any],
    allowed: set[str],
    *,
    meta_fields: set[str] | None = None,
) -> None:
    ignored = _HOST_META_FIELDS if meta_fields is None else set(meta_fields)
    unknown = sorted(set(payload) - allowed - ignored)
    if unknown:
        raise ValueError("unsupported field(s): " + ", ".join(unknown))


def normalize_object_selector(payload: dict[str, Any]) -> dict[str, str]:
    raw_name = payload.get("object_name")
    raw_id = payload.get("ordax_object_id")
    name_present = raw_name is not None and raw_name != ""
    id_present = raw_id is not None and raw_id != ""
    if isinstance(raw_name, str) and not raw_name.strip():
        name_present = False
    if isinstance(raw_id, str) and not raw_id.strip():
        id_present = False
    if name_present == id_present:
        raise ValueError("provide exactly one of object_name or ordax_object_id")

    if name_present:
        return {
            "object_name": _bounded_string(
                raw_name,
                "object_name",
                max_utf8_bytes=63,
            )
        }
    return {
        "ordax_object_id": _bounded_string(
            raw_id,
            "ordax_object_id",
            max_utf8_bytes=255,
        )
    }


def normalize_transform_fields(payload: dict[str, Any]) -> dict[str, list[float]]:
    result: dict[str, list[float]] = {}
    bounds = {
        "location": (-100000.0, 100000.0),
        "rotation_euler": (-100000.0, 100000.0),
        "scale": (0.0001, 1000.0),
        "dimensions": (0.0001, 100000.0),
    }

    for key, (minimum, maximum) in bounds.items():
        if key not in payload:
            continue
        result[key] = _vector3(payload.get(key), key, minimum, maximum)

    if not result:
        raise ValueError("at least one transform field is required")
    return result


def normalize_transform_request(
    payload: dict[str, Any],
    *,
    transport_fields: set[str] | None = None,
) -> dict[str, Any]:
    _reject_unknown_fields(
        payload,
        {"object_name", "ordax_object_id"} | _TRANSFORM_FIELDS,
        meta_fields=transport_fields,
    )
    return {
        **normalize_object_selector(payload),
        **normalize_transform_fields(payload),
    }


def _plan_create_primitive(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "name",
        "primitive",
        "location",
        "size",
        "radius",
        "depth",
        "segments",
    }
    _reject_unknown_fields(payload, allowed)

    name = _bounded_string(payload.get("name"), "name")
    primitive = str(payload.get("primitive") or "").strip().lower()
    if primitive not in {"cube", "sphere", "cylinder"}:
        raise ValueError("primitive must be cube, sphere, or cylinder")

    location = (
        _vector3(payload["location"], "location", -100000.0, 100000.0)
        if "location" in payload
        else [0.0, 0.0, 0.0]
    )
    arguments: dict[str, Any] = {
        "name": name,
        "primitive": primitive,
        "location": location,
    }

    if primitive == "cube":
        forbidden = {"radius", "depth", "segments"} & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for cube: " + ", ".join(sorted(forbidden))
            )
        arguments["size"] = _bounded_number(
            payload.get("size", 2.0),
            "size",
            0.0001,
            10000.0,
        )
    elif primitive == "sphere":
        forbidden = {"size", "depth"} & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for sphere: " + ", ".join(sorted(forbidden))
            )
        arguments["radius"] = _bounded_number(
            payload.get("radius", 1.0),
            "radius",
            0.0001,
            10000.0,
        )
        arguments["segments"] = _bounded_number(
            payload.get("segments", 32),
            "segments",
            8,
            64,
            integer=True,
        )
    else:
        forbidden = {"size"} & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for cylinder: "
                + ", ".join(sorted(forbidden))
            )
        arguments["radius"] = _bounded_number(
            payload.get("radius", 1.0),
            "radius",
            0.0001,
            10000.0,
        )
        arguments["depth"] = _bounded_number(
            payload.get("depth", 2.0),
            "depth",
            0.0001,
            10000.0,
        )
        arguments["segments"] = _bounded_number(
            payload.get("segments", 32),
            "segments",
            8,
            64,
            integer=True,
        )
    return arguments


def _plan_surface_scatter(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "object_name", "ordax_object_id", "name", "source_object_name",
        "density", "seed", "max_instances", "scale_min", "scale_max",
        "align_to_normal", "keep_surface",
    }
    _reject_unknown_fields(payload, allowed)
    selector = normalize_object_selector(payload)
    name = _bounded_string(payload.get("name"), "name")
    source_object_name = _bounded_string(
        payload.get("source_object_name"), "source_object_name"
    )
    if selector.get("object_name") == source_object_name:
        raise ValueError("surface scatter source and target must be different objects")
    density = _bounded_number(
        payload.get("density", 1.0), "density", 0.0001, MAX_SCATTER_DENSITY
    )
    seed = _bounded_number(
        payload.get("seed", 0), "seed", 0, 2147483647, integer=True
    )
    max_instances = _bounded_number(
        payload.get("max_instances", 1000),
        "max_instances", 1, MAX_SCATTER_INSTANCES, integer=True,
    )
    scale_min = _bounded_number(
        payload.get("scale_min", 1.0), "scale_min", 0.001, 100.0
    )
    scale_max = _bounded_number(
        payload.get("scale_max", 1.0), "scale_max", 0.001, 100.0
    )
    if scale_max < scale_min:
        raise ValueError("scale_max must be greater than or equal to scale_min")
    align_to_normal = payload.get("align_to_normal", True)
    keep_surface = payload.get("keep_surface", True)
    if not isinstance(align_to_normal, bool):
        raise ValueError("align_to_normal must be boolean")
    if not isinstance(keep_surface, bool):
        raise ValueError("keep_surface must be boolean")
    return {
        **selector,
        "name": name,
        "source_object_name": source_object_name,
        "density": float(density),
        "seed": int(seed),
        "max_instances": int(max_instances),
        "scale_min": float(scale_min),
        "scale_max": float(scale_max),
        "align_to_normal": align_to_normal,
        "keep_surface": keep_surface,
    }


def evaluate_surface_scatter_runtime_budget(
    *, modifier_count: Any, target_faces: Any, source_faces: Any, max_instances: Any
) -> dict[str, Any]:
    modifier_stack_count = _bounded_number(
        modifier_count, "modifier_count", 0, MAX_MODIFIER_STACK, integer=True
    )
    target_face_count = _bounded_number(
        target_faces, "target_faces", 0, 1000000000, integer=True
    )
    source_face_count = _bounded_number(
        source_faces, "source_faces", 0, 1000000000, integer=True
    )
    instance_cap = _bounded_number(
        max_instances, "max_instances", 1, MAX_SCATTER_INSTANCES, integer=True
    )
    projected_faces = int(source_face_count) * int(instance_cap)
    reasons: list[str] = []
    if modifier_stack_count >= MAX_MODIFIER_STACK:
        reasons.append("modifier stack limit reached")
    if target_face_count > MAX_EVALUATED_FACES:
        reasons.append("scatter target exceeds interactive face budget")
    if source_face_count <= 0:
        reasons.append("scatter source must contain mesh faces")
    if source_face_count > MAX_SCATTER_SOURCE_FACES:
        reasons.append("scatter source exceeds source face budget")
    if projected_faces > MAX_PROJECTED_SCATTER_FACES:
        reasons.append("projected scatter geometry exceeds interactive face budget")
    return {
        "allowed": not reasons,
        "modifier_count": int(modifier_stack_count),
        "target_faces": int(target_face_count),
        "source_faces": int(source_face_count),
        "max_instances": int(instance_cap),
        "projected_instance_faces": projected_faces,
        "limits": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_target_faces": MAX_EVALUATED_FACES,
            "max_source_faces": MAX_SCATTER_SOURCE_FACES,
            "max_instances": MAX_SCATTER_INSTANCES,
            "max_projected_instance_faces": MAX_PROJECTED_SCATTER_FACES,
        },
        "reasons": reasons,
    }


def _plan_boolean_cut_preview(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {"object_name", "ordax_object_id", "name", "profiles"}
    _reject_unknown_fields(payload, allowed)
    selector = normalize_object_selector(payload)
    name = _bounded_string(payload.get("name"), "name")
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list) or not (1 <= len(raw_profiles) <= MAX_CUTTER_PROFILES):
        raise ValueError(f"profiles must contain 1 to {MAX_CUTTER_PROFILES} entries")

    profiles: list[dict[str, Any]] = []
    expanded_cutters = 0
    generated_faces = 0
    for index, raw in enumerate(raw_profiles):
        if not isinstance(raw, dict):
            raise ValueError(f"profiles[{index}] must be an object")
        kind = str(raw.get("type") or "").strip().lower()
        if kind not in {"box", "circle", "slot", "polygon", "vent"}:
            raise ValueError(f"profiles[{index}].type must be box, circle, slot, polygon, or vent")
        common = {"type", "offset", "rotation_euler"}
        type_fields = {
            "box": {"dimensions"},
            "circle": {"radius", "depth", "segments"},
            "slot": {"length", "width", "depth", "segments"},
            "polygon": {"points", "depth"},
            "vent": {"length", "width", "depth", "segments", "count", "spacing", "axis"},
        }[kind]
        unknown = sorted(set(raw) - common - type_fields)
        if unknown:
            raise ValueError(f"profiles[{index}] unsupported field(s): " + ", ".join(unknown))
        offset = _vector3(raw.get("offset", [0, 0, 0]), f"profiles[{index}].offset", -10000.0, 10000.0)
        rotation = _vector3(raw.get("rotation_euler", [0, 0, 0]), f"profiles[{index}].rotation_euler", -100000.0, 100000.0)
        item: dict[str, Any] = {"type": kind, "offset": offset, "rotation_euler": rotation}
        if kind == "box":
            item["dimensions"] = _vector3(raw.get("dimensions"), f"profiles[{index}].dimensions", 0.001, 1000.0)
            expanded = 1
            faces = 6
        elif kind == "circle":
            item["radius"] = float(_bounded_number(raw.get("radius"), f"profiles[{index}].radius", 0.0005, 1000.0))
            item["depth"] = float(_bounded_number(raw.get("depth"), f"profiles[{index}].depth", 0.001, 1000.0))
            item["segments"] = int(_bounded_number(raw.get("segments", 32), f"profiles[{index}].segments", 8, MAX_CUTTER_SEGMENTS, integer=True))
            expanded = 1
            faces = item["segments"] + 2
        elif kind == "slot":
            item["length"] = float(_bounded_number(raw.get("length"), f"profiles[{index}].length", 0.001, 1000.0))
            item["width"] = float(_bounded_number(raw.get("width"), f"profiles[{index}].width", 0.001, 1000.0))
            if item["length"] < item["width"]:
                raise ValueError(f"profiles[{index}].length must be greater than or equal to width")
            item["depth"] = float(_bounded_number(raw.get("depth"), f"profiles[{index}].depth", 0.001, 1000.0))
            item["segments"] = int(_bounded_number(raw.get("segments", 24), f"profiles[{index}].segments", 8, MAX_CUTTER_SEGMENTS, integer=True))
            expanded = 1
            faces = item["segments"] + 2
        elif kind == "polygon":
            points = raw.get("points")
            if not isinstance(points, list) or not (3 <= len(points) <= MAX_CUTTER_POLYGON_POINTS):
                raise ValueError(f"profiles[{index}].points must contain 3 to {MAX_CUTTER_POLYGON_POINTS} points")
            normalized_points: list[list[float]] = []
            for point_index, point in enumerate(points):
                if not isinstance(point, list) or len(point) != 2:
                    raise ValueError(f"profiles[{index}].points[{point_index}] must contain two numbers")
                normalized_points.append([
                    float(_bounded_number(point[0], f"profiles[{index}].points[{point_index}]", -1000.0, 1000.0)),
                    float(_bounded_number(point[1], f"profiles[{index}].points[{point_index}]", -1000.0, 1000.0)),
                ])
            signs = []
            for point_index in range(len(normalized_points)):
                a, b, c = normalized_points[point_index - 2], normalized_points[point_index - 1], normalized_points[point_index]
                cross = (b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0])
                if abs(cross) > 1e-9:
                    signs.append(1 if cross > 0 else -1)
            if not signs or min(signs) != max(signs):
                raise ValueError(f"profiles[{index}].points must form a non-degenerate convex polygon")
            item["points"] = normalized_points
            item["depth"] = float(_bounded_number(raw.get("depth"), f"profiles[{index}].depth", 0.001, 1000.0))
            expanded = 1
            faces = len(normalized_points) + 2
        else:
            item["length"] = float(_bounded_number(raw.get("length"), f"profiles[{index}].length", 0.001, 1000.0))
            item["width"] = float(_bounded_number(raw.get("width"), f"profiles[{index}].width", 0.001, 1000.0))
            if item["length"] < item["width"]:
                raise ValueError(f"profiles[{index}].length must be greater than or equal to width")
            item["depth"] = float(_bounded_number(raw.get("depth"), f"profiles[{index}].depth", 0.001, 1000.0))
            item["segments"] = int(_bounded_number(raw.get("segments", 24), f"profiles[{index}].segments", 8, MAX_CUTTER_SEGMENTS, integer=True))
            item["count"] = int(_bounded_number(raw.get("count", 3), f"profiles[{index}].count", 2, MAX_CUTTER_PROFILES, integer=True))
            item["spacing"] = float(_bounded_number(raw.get("spacing"), f"profiles[{index}].spacing", 0.001, 1000.0))
            axis = str(raw.get("axis", "Y")).strip().upper()
            if axis not in {"X", "Y"}:
                raise ValueError(f"profiles[{index}].axis must be X or Y")
            item["axis"] = axis
            expanded = item["count"]
            faces = expanded * (item["segments"] + 2)
        expanded_cutters += expanded
        generated_faces += faces
        if expanded_cutters > MAX_CUTTER_PROFILES:
            raise ValueError(f"profiles expand to more than {MAX_CUTTER_PROFILES} cutter objects")
        profiles.append(item)
    return {
        **selector,
        "name": name,
        "profiles": profiles,
        "expanded_cutters": expanded_cutters,
        "estimated_cutter_faces": generated_faces,
    }


def evaluate_boolean_cut_runtime_budget(*, modifier_count: Any, target_faces: Any, expanded_cutters: Any, generated_cutter_faces: Any) -> dict[str, Any]:
    stack = int(_bounded_number(modifier_count, "modifier_count", 0, MAX_MODIFIER_STACK, integer=True))
    target = int(_bounded_number(target_faces, "target_faces", 0, 1000000000, integer=True))
    cutters = int(_bounded_number(expanded_cutters, "expanded_cutters", 1, MAX_CUTTER_PROFILES, integer=True))
    faces = int(_bounded_number(generated_cutter_faces, "generated_cutter_faces", 1, 1000000000, integer=True))
    reasons: list[str] = []
    if stack + cutters > MAX_MODIFIER_STACK:
        reasons.append("boolean preview would exceed modifier stack limit")
    if target > MAX_EVALUATED_FACES:
        reasons.append("boolean target exceeds interactive face budget")
    if faces > MAX_CUTTER_GENERATED_FACES:
        reasons.append("generated cutter geometry exceeds interactive face budget")
    return {
        "allowed": not reasons,
        "modifier_count": stack,
        "target_faces": target,
        "expanded_cutters": cutters,
        "generated_cutter_faces": faces,
        "limits": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_target_faces": MAX_EVALUATED_FACES,
            "max_profiles": MAX_CUTTER_PROFILES,
            "max_generated_cutter_faces": MAX_CUTTER_GENERATED_FACES,
        },
        "reasons": reasons,
    }


def _plan_mesh_cleanup(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "object_name",
        "ordax_object_id",
        "repair",
        "expected_base_geometry_sha256",
        "expected_loose_vertices",
    }
    _reject_unknown_fields(payload, allowed)
    selector = normalize_object_selector(payload)
    repair = str(payload.get("repair") or "").strip().lower()
    if repair != "remove_loose_vertices":
        raise ValueError("repair must be remove_loose_vertices")
    expected_sha256 = _sha256(
        payload.get("expected_base_geometry_sha256"),
        "expected_base_geometry_sha256",
    )
    arguments: dict[str, Any] = {
        **selector,
        "repair": repair,
        "expected_base_geometry_sha256": expected_sha256,
    }
    if "expected_loose_vertices" in payload:
        arguments["expected_loose_vertices"] = int(
            _bounded_number(
                payload.get("expected_loose_vertices"),
                "expected_loose_vertices",
                1,
                1000000,
                integer=True,
            )
        )
    return arguments


def _plan_modifier(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "object_name",
        "ordax_object_id",
        "name",
        "type",
        "width",
        "segments",
        "levels",
        "thickness",
        "axis",
        "count",
        "relative_offset",
        "constant_offset",
    }
    _reject_unknown_fields(payload, allowed)

    selector = normalize_object_selector(payload)
    name = _bounded_string(payload.get("name"), "name")
    modifier_type = str(payload.get("type") or "").strip().upper()
    if modifier_type not in {"BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR", "ARRAY"}:
        raise ValueError(
            "type must be BEVEL, SUBSURF, SOLIDIFY, MIRROR, or ARRAY"
        )

    arguments: dict[str, Any] = {
        **selector,
        "name": name,
        "type": modifier_type,
    }
    if modifier_type == "BEVEL":
        forbidden = {
            "levels",
            "thickness",
            "axis",
            "count",
            "relative_offset",
            "constant_offset",
        } & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for BEVEL: " + ", ".join(sorted(forbidden))
            )
        arguments["width"] = _bounded_number(
            payload.get("width", 0.05),
            "width",
            0.0,
            100.0,
        )
        arguments["segments"] = _bounded_number(
            payload.get("segments", 2),
            "segments",
            1,
            6,
            integer=True,
        )
    elif modifier_type == "SUBSURF":
        forbidden = {
            "width",
            "segments",
            "thickness",
            "axis",
            "count",
            "relative_offset",
            "constant_offset",
        } & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for SUBSURF: "
                + ", ".join(sorted(forbidden))
            )
        arguments["levels"] = _bounded_number(
            payload.get("levels", 1),
            "levels",
            0,
            2,
            integer=True,
        )
    elif modifier_type == "SOLIDIFY":
        forbidden = {
            "width",
            "segments",
            "levels",
            "axis",
            "count",
            "relative_offset",
            "constant_offset",
        } & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for SOLIDIFY: "
                + ", ".join(sorted(forbidden))
            )
        arguments["thickness"] = _bounded_number(
            payload.get("thickness", 0.01),
            "thickness",
            -100.0,
            100.0,
        )
    elif modifier_type == "MIRROR":
        forbidden = {
            "width",
            "segments",
            "levels",
            "thickness",
            "count",
            "relative_offset",
            "constant_offset",
        } & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for MIRROR: "
                + ", ".join(sorted(forbidden))
            )
        axis = str(payload.get("axis", "X")).strip().upper()
        if axis not in {"X", "Y", "Z"}:
            raise ValueError("axis must be X, Y, or Z")
        arguments["axis"] = axis
    else:
        forbidden = {"width", "segments", "levels", "thickness", "axis"} & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for ARRAY: " + ", ".join(sorted(forbidden))
            )
        arguments["count"] = _bounded_number(
            payload.get("count", 2),
            "count",
            2,
            MAX_ARRAY_COUNT,
            integer=True,
        )
        arguments["relative_offset"] = (
            _vector3(payload["relative_offset"], "relative_offset", -100.0, 100.0)
            if "relative_offset" in payload
            else [1.0, 0.0, 0.0]
        )
        if "constant_offset" in payload:
            arguments["constant_offset"] = _vector3(
                payload["constant_offset"], "constant_offset", -10000.0, 10000.0
            )
        if not any(arguments["relative_offset"]) and not any(
            arguments.get("constant_offset", [0.0, 0.0, 0.0])
        ):
            raise ValueError(
                "ARRAY requires a non-zero relative_offset or constant_offset"
            )
    return arguments


def evaluate_modifier_runtime_budget(
    *,
    modifier_type: Any,
    modifier_count: Any,
    evaluated_faces: Any,
    levels: Any = 1,
    array_count: Any = 1,
) -> dict[str, Any]:
    normalized_type = str(modifier_type or "").strip().upper()
    if normalized_type not in {"BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR", "ARRAY"}:
        raise ValueError(
            "modifier_type must be BEVEL, SUBSURF, SOLIDIFY, MIRROR, or ARRAY"
        )
    modifier_stack_count = _bounded_number(
        modifier_count,
        "modifier_count",
        0,
        MAX_MODIFIER_STACK,
        integer=True,
    )
    faces = _bounded_number(
        evaluated_faces,
        "evaluated_faces",
        0,
        1000000000,
        integer=True,
    )
    normalized_levels = 1
    if normalized_type == "SUBSURF":
        normalized_levels = _bounded_number(
            levels,
            "levels",
            0,
            2,
            integer=True,
        )
    normalized_count = 1
    if normalized_type == "ARRAY":
        normalized_count = _bounded_number(
            array_count,
            "array_count",
            1,
            MAX_ARRAY_COUNT,
            integer=True,
        )

    reasons: list[str] = []
    if modifier_stack_count >= MAX_MODIFIER_STACK:
        reasons.append("modifier stack limit reached")
    if faces > MAX_EVALUATED_FACES:
        reasons.append("evaluated mesh exceeds interactive face budget")

    projected_faces = int(faces)
    if normalized_type == "SUBSURF":
        projected_faces = int(faces * (4 ** int(normalized_levels)))
        if projected_faces > MAX_PROJECTED_SUBSURF_FACES:
            reasons.append("projected SUBSURF mesh exceeds interactive face budget")
    elif normalized_type == "ARRAY":
        projected_faces = int(faces * int(normalized_count))
        if projected_faces > MAX_PROJECTED_ARRAY_FACES:
            reasons.append("projected ARRAY mesh exceeds interactive face budget")

    result = {
        "allowed": not reasons,
        "modifier_type": normalized_type,
        "modifier_count": int(modifier_stack_count),
        "evaluated_faces": int(faces),
        "levels": int(normalized_levels) if normalized_type == "SUBSURF" else None,
        "projected_faces": projected_faces,
        "limits": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_evaluated_faces": MAX_EVALUATED_FACES,
            "max_projected_subsurf_faces": MAX_PROJECTED_SUBSURF_FACES,
        },
        "reasons": reasons,
    }
    if normalized_type == "ARRAY":
        result["count"] = int(normalized_count)
        result["limits"].update(
            {
                "max_array_count": MAX_ARRAY_COUNT,
                "max_projected_array_faces": MAX_PROJECTED_ARRAY_FACES,
            }
        )
    return result


def plan_modeling_operation(operation: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("modeling payload must be an object")
    normalized_operation = str(operation or "").strip().lower()
    if normalized_operation not in MODELING_SCHEMAS:
        raise ValueError(
            "operation must be create_primitive, object_transform, surface_scatter, boolean_cut_preview, mesh_cleanup, or add_modifier"
        )

    if normalized_operation == "create_primitive":
        arguments = _plan_create_primitive(payload)
    elif normalized_operation == "object_transform":
        arguments = normalize_transform_request(payload)
    elif normalized_operation == "surface_scatter":
        arguments = _plan_surface_scatter(payload)
    elif normalized_operation == "boolean_cut_preview":
        arguments = _plan_boolean_cut_preview(payload)
    elif normalized_operation == "mesh_cleanup":
        arguments = _plan_mesh_cleanup(payload)
    else:
        arguments = _plan_modifier(payload)

    schema = MODELING_SCHEMAS[normalized_operation]
    type_override = (
        schema.get("type_overrides", {}).get(arguments.get("type"))
        if normalized_operation == "add_modifier"
        else None
    )
    status = type_override.get("status") if type_override else schema["status"]
    executable = status == "available"
    result = {
        "operation": normalized_operation,
        "status": status,
        "executable": executable,
        "action": schema.get("action") if executable else None,
        "requires_real_blender_smoke": not executable,
        "arguments": arguments,
    }
    for metadata_key in (
        "runtime_requirements",
        "runtime_guards",
        "failure_policy",
        "workflow_actions",
    ):
        metadata_source = type_override if type_override else schema
        if metadata_key in metadata_source:
            result[metadata_key] = copy.deepcopy(metadata_source[metadata_key])
    return result
