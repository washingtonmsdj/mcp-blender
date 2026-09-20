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


MODELING_SCHEMAS = {
    "create_primitive": {
        "status": "pending_blender_smoke",
        "description": (
            "Planned typed primitive creation. Not remotely executable until "
            "the current Blender companion implementation passes a real Blender smoke."
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
    "add_modifier": {
        "status": "pending_blender_smoke",
        "runtime_guards": {
            "max_modifier_stack": MAX_MODIFIER_STACK,
            "max_evaluated_faces": MAX_EVALUATED_FACES,
            "max_projected_subsurf_faces": MAX_PROJECTED_SUBSURF_FACES,
        },
        "description": (
            "Planned typed modifier insertion. Not remotely executable until "
            "the current Blender companion implementation passes a real Blender smoke."
        ),
        "required": ["name", "type"],
        "selectors": ["object_name", "ordax_object_id"],
        "properties": {
            "name": {"type": "string", "max_utf8_bytes": 63},
            "type": {"enum": ["BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR"]},
            "width": {"type": "number", "minimum": 0, "maximum": 100},
            "segments": {"type": "integer", "minimum": 1, "maximum": 6},
            "levels": {"type": "integer", "minimum": 0, "maximum": 2},
            "thickness": {"type": "number", "minimum": -100, "maximum": 100},
            "axis": {"enum": ["X", "Y", "Z"]},
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


def _reject_unknown_fields(payload: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(payload) - allowed - _HOST_META_FIELDS)
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


def normalize_transform_request(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_unknown_fields(
        payload,
        {"object_name", "ordax_object_id"} | _TRANSFORM_FIELDS,
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
    }
    _reject_unknown_fields(payload, allowed)

    selector = normalize_object_selector(payload)
    name = _bounded_string(payload.get("name"), "name")
    modifier_type = str(payload.get("type") or "").strip().upper()
    if modifier_type not in {"BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR"}:
        raise ValueError(
            "type must be BEVEL, SUBSURF, SOLIDIFY, or MIRROR"
        )

    arguments: dict[str, Any] = {
        **selector,
        "name": name,
        "type": modifier_type,
    }
    if modifier_type == "BEVEL":
        forbidden = {"levels", "thickness", "axis"} & set(payload)
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
        forbidden = {"width", "segments", "thickness", "axis"} & set(payload)
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
        forbidden = {"width", "segments", "levels", "axis"} & set(payload)
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
    else:
        forbidden = {"width", "segments", "levels", "thickness"} & set(payload)
        if forbidden:
            raise ValueError(
                "unsupported field(s) for MIRROR: "
                + ", ".join(sorted(forbidden))
            )
        axis = str(payload.get("axis", "X")).strip().upper()
        if axis not in {"X", "Y", "Z"}:
            raise ValueError("axis must be X, Y, or Z")
        arguments["axis"] = axis
    return arguments


def evaluate_modifier_runtime_budget(
    *,
    modifier_type: Any,
    modifier_count: Any,
    evaluated_faces: Any,
    levels: Any = 1,
) -> dict[str, Any]:
    normalized_type = str(modifier_type or "").strip().upper()
    if normalized_type not in {"BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR"}:
        raise ValueError(
            "modifier_type must be BEVEL, SUBSURF, SOLIDIFY, or MIRROR"
        )
    count = _bounded_number(
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

    reasons: list[str] = []
    if count >= MAX_MODIFIER_STACK:
        reasons.append("modifier stack limit reached")
    if faces > MAX_EVALUATED_FACES:
        reasons.append("evaluated mesh exceeds interactive face budget")

    projected_faces = int(faces)
    if normalized_type == "SUBSURF":
        projected_faces = int(faces * (4 ** int(normalized_levels)))
        if projected_faces > MAX_PROJECTED_SUBSURF_FACES:
            reasons.append("projected SUBSURF mesh exceeds interactive face budget")

    return {
        "allowed": not reasons,
        "modifier_type": normalized_type,
        "modifier_count": int(count),
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


def plan_modeling_operation(operation: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("modeling payload must be an object")
    normalized_operation = str(operation or "").strip().lower()
    if normalized_operation not in MODELING_SCHEMAS:
        raise ValueError(
            "operation must be create_primitive, object_transform, or add_modifier"
        )

    if normalized_operation == "create_primitive":
        arguments = _plan_create_primitive(payload)
    elif normalized_operation == "object_transform":
        arguments = normalize_transform_request(payload)
    else:
        arguments = _plan_modifier(payload)

    schema = MODELING_SCHEMAS[normalized_operation]
    executable = schema["status"] == "available"
    result = {
        "operation": normalized_operation,
        "status": schema["status"],
        "executable": executable,
        "action": schema.get("action") if executable else None,
        "requires_real_blender_smoke": not executable,
        "arguments": arguments,
    }
    if "runtime_guards" in schema:
        result["runtime_guards"] = copy.deepcopy(schema["runtime_guards"])
    return result
