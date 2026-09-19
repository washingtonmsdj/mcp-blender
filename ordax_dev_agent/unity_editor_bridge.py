from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .models import ActionResult


class UnityEditorBridge:
    def __init__(self, project_path: Path):
        self.project = project_path.resolve()
        self.root = self.project / "Library" / "OrdaXAgent"
        self.inbox = self.root / "inbox"
        self.responses = self.root / "responses"
        self.presence = self.root / "editor-presence.json"

    def presence_is_fresh(self, max_age_seconds: float = 4.0) -> bool:
        try:
            age = time.time() - self.presence.stat().st_mtime
            return 0 <= age <= max_age_seconds
        except OSError:
            return False

    def request(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout_seconds: float = 120.0,
    ) -> ActionResult | None:
        if not self.presence_is_fresh():
            return None

        self.inbox.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(parents=True, exist_ok=True)

        command_id = uuid.uuid4().hex
        response_path = self.responses / f"{command_id}.json"
        command_path = self.inbox / f"{command_id}.json"
        temp_path = self.inbox / f"{command_id}.tmp"

        body = {
            "id": command_id,
            "action": action,
            **(payload or {}),
        }
        temp_path.write_text(json.dumps(body), encoding="utf-8")
        temp_path.replace(command_path)

        deadline = time.monotonic() + max(1.0, timeout_seconds)
        while time.monotonic() < deadline:
            if response_path.is_file():
                try:
                    response = json.loads(response_path.read_text(encoding="utf-8-sig"))
                finally:
                    try:
                        response_path.unlink()
                    except OSError:
                        pass

                ok = bool(response.get("ok"))
                return ActionResult(
                    ok,
                    str(response.get("summary") or "Unity Editor bridge response"),
                    {
                        "transport": "unity-editor-companion",
                        **response,
                    },
                )

            if not self.presence_is_fresh(max_age_seconds=12.0):
                break
            time.sleep(0.2)

        try:
            command_path.unlink()
        except OSError:
            pass

        return None
