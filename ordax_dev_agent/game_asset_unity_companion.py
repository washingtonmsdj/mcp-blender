"""Managed transport for the isolated Unity game-asset Editor companion."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .models import ActionResult


GAME_ASSET_COMPANION_PROTOCOL = "ordax-game-assets-v1"
_GAME_ASSET_COMPANION_TARGET = "Assets/OrdaX/Editor/OrdaXGameAssetAgent.cs"


def _fresh(path: Path, max_age_seconds: float = 8.0) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
        return 0 <= age <= max_age_seconds
    except OSError:
        return False


def install_game_asset_companion(project) -> tuple[Path, bool]:
    source = Path(__file__).parent / "assets" / "OrdaXGameAssetAgent.cs"
    if not source.is_file():
        raise FileNotFoundError("packaged Unity game asset companion is missing")
    target = project.path(_GAME_ASSET_COMPANION_TARGET, must_exist=False)
    content = source.read_bytes()
    before = target.read_bytes() if target.is_file() else None
    if before is not None and before != content:
        try:
            existing = before.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(
                "existing Unity game asset companion is not valid UTF-8; refusing overwrite"
            ) from error
        markers = (
            "class OrdaXGameAssetAgent",
            GAME_ASSET_COMPANION_PROTOCOL,
            "namespace OrdaX.EditorTools",
        )
        if not all(marker in existing for marker in markers):
            raise ValueError(
                "existing Unity game asset companion is not OrdaX-managed; refusing overwrite"
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    changed = before != content
    if changed:
        temporary = target.with_name(target.name + f".ordax-{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
            if temporary.read_bytes() != content:
                raise OSError("temporary Unity game asset companion verification failed")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target, changed


def request_game_asset_companion(
    *,
    project,
    refresh_editor: Callable[[dict[str, Any]], ActionResult],
    action: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> ActionResult:
    try:
        companion, changed = install_game_asset_companion(project)
    except (ValueError, OSError, FileNotFoundError) as error:
        return ActionResult(False, str(error))

    root = project.root / "Library" / "OrdaXAgent" / "game-assets"
    presence = root / "presence.json"
    if changed or not _fresh(presence):
        refreshed = refresh_editor(
            {
                "project": project.slug,
                "force": True,
                "wait_seconds": min(120.0, timeout_seconds),
            }
        )
        if not refreshed.ok:
            return ActionResult(
                False,
                "Unity game asset companion was installed but Editor refresh was not confirmed",
                {
                    "retryable": True,
                    "companion_path": str(companion),
                    "refresh": refreshed.data,
                },
            )
        deadline = time.monotonic() + min(timeout_seconds, 120.0)
        while time.monotonic() < deadline and not _fresh(presence):
            time.sleep(0.25)
    if not _fresh(presence):
        return ActionResult(
            False,
            "Unity game asset telemetry companion did not become ready",
            {
                "retryable": True,
                "companion_path": str(companion),
                "presence_path": str(presence),
            },
        )

    inbox = root / "inbox"
    responses = root / "responses"
    inbox.mkdir(parents=True, exist_ok=True)
    responses.mkdir(parents=True, exist_ok=True)
    command_id = uuid.uuid4().hex
    command_path = inbox / f"{command_id}.json"
    temp_path = inbox / f"{command_id}.tmp"
    response_path = responses / f"{command_id}.json"
    command = {"id": command_id, "action": action, **payload}
    temp_path.write_text(json.dumps(command), encoding="utf-8")
    temp_path.replace(command_path)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if response_path.is_file():
            try:
                response = json.loads(response_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError) as error:
                return ActionResult(False, f"Unity game asset telemetry response is invalid: {error}")
            finally:
                response_path.unlink(missing_ok=True)
            if not isinstance(response, dict):
                return ActionResult(False, "Unity game asset telemetry response must be an object")
            if response.get("protocol") != GAME_ASSET_COMPANION_PROTOCOL:
                return ActionResult(
                    False,
                    "Unity game asset telemetry companion protocol is incompatible",
                    {"retryable": True, "response": response},
                )
            if not bool(response.get("ok")):
                return ActionResult(
                    False,
                    str(response.get("summary") or "Unity game asset telemetry failed"),
                    response,
                )
            return ActionResult(
                True,
                str(response.get("summary") or "Unity game asset companion action completed"),
                {
                    "transport": "unity-game-asset-companion",
                    **response,
                },
            )
        time.sleep(0.2)

    command_path.unlink(missing_ok=True)
    return ActionResult(
        False,
        "Unity game asset telemetry timed out; inspect Editor state before retrying",
        {
            "retryable": True,
            "outcome_unknown": True,
            "command_id": command_id,
            "action": action,
        },
    )
