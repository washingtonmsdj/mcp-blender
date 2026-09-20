"""Typed modeling contracts shared by the host and Blender runtime.

Mutation implementations remain deliberately separate from validation. This
module contains no bpy imports and is safe to unit-test in ordinary Python.
"""
from __future__ import annotations

import copy
import math
from typing import Any


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


def modeling_schemas() -> dict[str, Any]:
    return copy.deepcopy(MODELING_SCHEMAS)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must contain only finite numbers")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must contain only finite numbers")
    return result


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
        value = payload.get(key)
        if not isinstance(value, list) or len(value) != 3:
            raise ValueError(f"{key} must be a list of three finite numbers")

        normalized = [_finite_number(item, key) for item in value]
        if any(item < minimum or item > maximum for item in normalized):
            raise ValueError(
                f"{key} components must be between {minimum:g} and {maximum:g}"
            )
        result[key] = normalized

    if not result:
        raise ValueError("at least one transform field is required")
    return result
