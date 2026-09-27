from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ActionResult


class DeviceAuthorizationError(RuntimeError):
    """The supervisor must reauthenticate this device before restarting."""


class TransientDeliveryError(RuntimeError):
    """Transport failure eligible for an identical terminal-report retry."""


def read_secret(path: Path) -> str | None:
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def decode_job_payload(row: dict[str, Any]) -> dict[str, Any]:
    encoded = row.get("payload_canonical_b64")
    expected = str(row.get("payload_sha256") or "").lower()
    if not isinstance(encoded, str) or len(expected) != 64:
        raise RuntimeError("remote job payload envelope is incomplete")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as error:
        raise RuntimeError("remote job payload is not valid base64") from error

    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise RuntimeError("remote job payload digest mismatch")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("remote job payload is not valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError("remote job payload must be an object")
    return payload


def dispatch_job(
    row: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], str | None]:
    capability = str(row.get("capability") or row.get("operation") or "")
    if capability == "ordax.dev.adapter.invoke":
        allowed = {"adapter", "action", "payload", "project"}
        if set(payload) - allowed:
            raise RuntimeError("adapter invocation contains unsupported fields")

        adapter = payload.get("adapter")
        action = payload.get("action")
        action_payload = payload.get("payload", {})
        project = payload.get("project")

        if not isinstance(action_payload, dict):
            raise RuntimeError("adapter invocation payload must be an object")
        if project is not None and not isinstance(project, str):
            raise RuntimeError("adapter invocation project must be a string")

        if adapter == "blender":
            if not isinstance(action, str) or not action.startswith("blender."):
                raise RuntimeError("adapter invocation action is not a Blender action")
            return action, action_payload, project

        if adapter == "workspace":
            if action != "workspace.bind_project":
                raise RuntimeError("adapter invocation workspace action is not allowed")
            if project is not None:
                raise RuntimeError("workspace binding must not target an existing project")
            return action, action_payload, None

        raise RuntimeError("adapter invocation is not an allowed capability")

    if capability.startswith(
        (
            "blender.",
            "unity.",
            "git.",
            "project.",
            "projects.",
            "artifact.",
            "observation.",
            "game_assets.",
            "geo.",
            "visual.",
            "agent.",
        )
    ):
        project = payload.get("project")
        return capability, payload, project if isinstance(project, str) else None

    raise RuntimeError(f"remote capability is not owned by Device Agent: {capability}")


def canonical_result(result: ActionResult) -> tuple[dict[str, Any], str]:
    body = {
        "ok": bool(result.ok),
        "summary": str(result.summary),
        "data": result.data if isinstance(result.data, dict) else {},
    }
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return body, hashlib.sha256(encoded).hexdigest()
