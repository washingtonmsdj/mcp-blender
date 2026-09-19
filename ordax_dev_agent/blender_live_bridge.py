from __future__ import annotations

import json
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from mcp_blender_unity.config import find_blender

from .models import ActionResult


class BlenderLiveBridge:
    """File-protocol bridge to one visible Blender session per registered project."""

    def __init__(self, config, project):
        self.config = config
        self.project = project
        self.root = (config.state_dir / "blender-live" / project.slug).resolve()
        self.inbox = self.root / "inbox"
        self.responses = self.root / "responses"
        self.presence = self.root / "presence.json"
        self.artifacts_root = (config.state_dir / "artifacts" / project.slug).resolve()
        self.scripts_root = project.path(
            project.blender.get("scripts_dir", "automation/blender"),
            must_exist=False,
        )
        self.companion = (
            Path(__file__).resolve().parent
            / "assets"
            / "blender_live_companion.py"
        )

    def _ensure_dirs(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.responses.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

    def presence_is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        try:
            age = time.time() - self.presence.stat().st_mtime
            return 0 <= age <= max_age_seconds
        except OSError:
            return False

    def status(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "project": self.project.slug,
            "presence_fresh": self.presence_is_fresh(),
            "presence_path": str(self.presence),
            "control_root": str(self.root),
            "scripts_root": str(self.scripts_root),
        }
        if self.presence.is_file():
            try:
                data["presence"] = json.loads(
                    self.presence.read_text(encoding="utf-8-sig")
                )
            except Exception as error:
                data["presence_error"] = str(error)
        return data

    def start(
        self,
        *,
        blend_file: str | None = None,
        wait_seconds: float = 30.0,
    ) -> ActionResult:
        if self.presence_is_fresh():
            return ActionResult(
                True,
                "Visible Blender live session already running",
                self.status(),
            )

        blender = find_blender()
        if blender is None:
            return ActionResult(False, "Blender executable not found")
        if not self.companion.is_file():
            return ActionResult(False, f"Blender live companion missing: {self.companion}")

        self._ensure_dirs()
        for stale in self.inbox.glob("*.json"):
            try:
                stale.unlink()
            except OSError:
                pass

        command = [
            str(blender),
            "--factory-startup",
            "--disable-autoexec",
        ]

        if blend_file:
            blend = self.project.path(blend_file)
            if blend.suffix.lower() != ".blend":
                return ActionResult(False, "blend_file must be a .blend file")
            command.append(str(blend))

        command.extend(
            [
                "--python",
                str(self.companion),
                "--",
                "--ordax-control-root",
                str(self.root),
                "--ordax-project-root",
                str(self.project.root.resolve()),
                "--ordax-scripts-root",
                str(self.scripts_root.resolve()),
                "--ordax-artifacts-root",
                str(self.artifacts_root),
                "--ordax-project-slug",
                self.project.slug,
            ]
        )

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(
            command,
            cwd=str(self.project.root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=creationflags,
        )

        deadline = time.monotonic() + max(3.0, wait_seconds)
        while time.monotonic() < deadline:
            if self.presence_is_fresh():
                data = self.status()
                data["pid"] = process.pid
                data["transport"] = "blender-visible-companion"
                return ActionResult(True, "Visible Blender live session started", data)
            if process.poll() is not None:
                return ActionResult(
                    False,
                    f"Blender exited before live companion became ready: {process.returncode}",
                    {"pid": process.pid, "returncode": process.returncode},
                )
            time.sleep(0.35)

        return ActionResult(
            False,
            "Blender opened but live companion did not become ready in time",
            {"pid": process.pid, **self.status()},
        )

    def request(
        self,
        operation: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout_seconds: float = 120.0,
    ) -> ActionResult:
        if not self.presence_is_fresh():
            return ActionResult(False, "Visible Blender live session is not running", self.status())

        self._ensure_dirs()
        command_id = uuid.uuid4().hex
        command_path = self.inbox / f"{command_id}.json"
        temp_path = self.inbox / f"{command_id}.tmp"
        response_path = self.responses / f"{command_id}.json"

        body = {"id": command_id, "operation": operation, **(payload or {})}
        temp_path.write_text(json.dumps(body), encoding="utf-8")
        temp_path.replace(command_path)

        deadline = time.monotonic() + max(1.0, timeout_seconds)
        while time.monotonic() < deadline:
            if response_path.is_file():
                try:
                    response = json.loads(
                        response_path.read_text(encoding="utf-8-sig")
                    )
                finally:
                    try:
                        response_path.unlink()
                    except OSError:
                        pass

                ok = bool(response.get("ok"))
                return ActionResult(
                    ok,
                    str(response.get("summary") or "Blender live response"),
                    {
                        "transport": "blender-visible-companion",
                        **response,
                    },
                )

            if not self.presence_is_fresh(max_age_seconds=12.0):
                return ActionResult(
                    False,
                    "Blender live session stopped responding",
                    self.status(),
                )
            time.sleep(0.2)

        try:
            command_path.unlink()
        except OSError:
            pass

        return ActionResult(
            False,
            f"Blender live operation timed out: {operation}",
            self.status(),
        )
