"""Read-only capability contract inventory exposed by agent.status."""
from __future__ import annotations

from typing import Any

from .assets.blender_modeling_contracts import modeling_schemas


def capability_contracts() -> dict[str, Any]:
    modeling = {}
    for name, schema in modeling_schemas().items():
        modeling[name] = {
            "status": schema.get("status"),
            "action": schema.get("action"),
            "requires_real_blender_smoke": schema.get("status") != "available",
            "runtime_requirements": list(schema.get("runtime_requirements", [])),
            "runtime_guards": dict(schema.get("runtime_guards", {})),
            "failure_policy": list(schema.get("failure_policy", [])),
        }

    return {
        "blender_modeling": {
            "operations": modeling,
            "available_actions": sorted(
                item["action"]
                for item in modeling.values()
                if item.get("status") == "available" and item.get("action")
            ),
            "pending_operations": sorted(
                name
                for name, item in modeling.items()
                if item.get("status") != "available"
            ),
        }
    }
