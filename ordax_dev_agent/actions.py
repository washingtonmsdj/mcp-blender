from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from mcp_blender_unity.config import find_blender

from .config import AgentConfig
from .models import ActionResult


Action = Callable[[dict[str, Any]], ActionResult]


def _run(command: list[str], *, cwd: Path | None = None, timeout: int = 1800) -> ActionResult:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    data = {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-40000:],
        "stderr": completed.stderr[-40000:],
        "command": command,
    }
    return ActionResult(
        ok=completed.returncode == 0,
        summary="command completed" if completed.returncode == 0 else "command failed",
        data=data,
    )


class ActionRegistry:
    """Strict allow-list. No arbitrary remote shell command is accepted."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._actions: dict[str, Action] = {
            "agent.status": self.agent_status,
            "git.status": self.git_status,
            "git.sync": self.git_sync,
            "unity.compile": self.unity_compile,
            "unity.validate": self.unity_validate,
            "unity.capture": self.unity_capture,
            "unity.run_method": self.unity_run_method,
            "blender.version": self.blender_version,
            "blender.run_python": self.blender_run_python,
        }

    @property
    def names(self) -> list[str]:
        return sorted(self._actions)

    def execute(self, action: str, payload: dict[str, Any]) -> ActionResult:
        handler = self._actions.get(action)
        if handler is None:
            return ActionResult(False, f"action not allowed: {action}")
        return handler(payload or {})

    def agent_status(self, payload: dict[str, Any]) -> ActionResult:
        return ActionResult(
            True,
            "agent ready",
            {
                **self.config.public_status(),
                "actions": self.names,
            },
        )

    def _project_path(self, payload: dict[str, Any]) -> Path:
        slug = payload.get("project", "hordax")
        if slug != "hordax":
            raise ValueError(f"project not allowed: {slug}")
        path = self.config.hordax_path.resolve()
        if not (path / ".git").is_dir():
            raise FileNotFoundError(f"Git project not found: {path}")
        return path

    def git_status(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        return _run(["git", "-C", str(project), "status", "--short"], timeout=60)

    def git_sync(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        branch = payload.get("branch", "dev/unity6-gameplay-pass-1")
        allowed = {
            "dev/unity6-gameplay-pass-1",
            "upgrade/unity-6000.6.1f1",
        }
        if branch not in allowed:
            return ActionResult(False, f"branch not allowed: {branch}")

        status = _run(
            ["git", "-C", str(project), "status", "--porcelain", "--untracked-files=no"],
            timeout=60,
        )
        if not status.ok:
            return status
        if status.data.get("stdout", "").strip():
            return ActionResult(
                False,
                "local tracked changes exist; sync refused",
                {"status": status.data["stdout"]},
            )

        fetch = _run(
            ["git", "-C", str(project), "fetch", "--quiet", "origin", branch],
            timeout=180,
        )
        if not fetch.ok:
            return fetch

        current = _run(
            ["git", "-C", str(project), "rev-parse", "--abbrev-ref", "HEAD"],
            timeout=30,
        )
        if not current.ok:
            return current

        current_branch = current.data["stdout"].strip()
        if current_branch != branch:
            checkout = _run(
                ["git", "-C", str(project), "checkout", "-B", branch, f"origin/{branch}"],
                timeout=120,
            )
            if not checkout.ok:
                return checkout
        else:
            merge = _run(
                ["git", "-C", str(project), "merge", "--ff-only", "--quiet", f"origin/{branch}"],
                timeout=120,
            )
            if not merge.ok:
                return merge

        head = _run(["git", "-C", str(project), "rev-parse", "HEAD"], timeout=30)
        return ActionResult(
            head.ok,
            "repository synchronized" if head.ok else "sync completed but HEAD lookup failed",
            {"branch": branch, "head": head.data.get("stdout", "").strip()},
        )

    def _bridge_script(self, name: str) -> Path:
        script = self.config.bridge_path / "scripts" / "windows" / name
        if not script.is_file():
            raise FileNotFoundError(script)
        return script

    def unity_compile(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        script = self._bridge_script("unity-run.ps1")
        return _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ProjectPath",
                str(project),
            ],
            timeout=int(payload.get("timeout_seconds", 1800)),
        )

    def unity_validate(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        script = self._bridge_script("unity-run.ps1")
        method = payload.get("execute_method", "HORDAX.EditorTools.CiValidation.Run")
        if method != "HORDAX.EditorTools.CiValidation.Run":
            return ActionResult(False, f"execute method not allowed: {method}")
        return _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ProjectPath",
                str(project),
                "-ExecuteMethod",
                method,
            ],
            timeout=int(payload.get("timeout_seconds", 1800)),
        )

    def unity_capture(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        script = self._bridge_script("unity-capture.ps1")
        output = self.config.state_dir / "artifacts" / "hordax-prototype.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        result = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ProjectPath",
                str(project),
                "-OutputPath",
                str(output),
                "-Width",
                str(int(payload.get("width", 1280))),
                "-Height",
                str(int(payload.get("height", 720))),
                "-WarmupFrames",
                str(int(payload.get("warmup_frames", 120))),
            ],
            timeout=int(payload.get("timeout_seconds", 900)),
        )
        result.data["artifact"] = str(output)
        snapshot = output.with_suffix(".json")
        if snapshot.is_file():
            try:
                result.data["snapshot"] = json.loads(snapshot.read_text(encoding="utf-8"))
                result.data["snapshot_path"] = str(snapshot)
            except Exception as error:
                result.data["snapshot_error"] = str(error)
        return result

    def unity_run_method(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        method = payload.get("execute_method", "")
        allowed = {
            "HORDAX.EditorTools.CiValidation.Run",
            "HORDAX.EditorTools.AutomationCapture.CapturePrototype",
        }
        if method not in allowed:
            return ActionResult(False, f"execute method not allowed: {method}")

        script = self._bridge_script("unity-run.ps1")
        return _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ProjectPath",
                str(project),
                "-ExecuteMethod",
                method,
            ],
            timeout=int(payload.get("timeout_seconds", 1800)),
        )

    def blender_version(self, payload: dict[str, Any]) -> ActionResult:
        blender = find_blender()
        if blender is None:
            return ActionResult(False, "Blender executable not found")
        return _run([str(blender), "--version"], timeout=120)

    def blender_run_python(self, payload: dict[str, Any]) -> ActionResult:
        blender = find_blender()
        if blender is None:
            return ActionResult(False, "Blender executable not found")

        raw_script = payload.get("script_path")
        if not raw_script:
            return ActionResult(False, "script_path is required")

        script = Path(raw_script).expanduser().resolve()
        allowed_root = (self.config.bridge_path / "automation" / "blender").resolve()
        try:
            script.relative_to(allowed_root)
        except ValueError:
            return ActionResult(
                False,
                f"Blender script must be inside {allowed_root}",
            )
        if not script.is_file():
            return ActionResult(False, f"Blender script not found: {script}")

        command = [str(blender), "--background"]
        raw_blend = payload.get("blend_file")
        if raw_blend:
            blend = Path(raw_blend).expanduser().resolve()
            if not blend.is_file():
                return ActionResult(False, f"Blend file not found: {blend}")
            command.append(str(blend))
        command.extend(["--python", str(script)])
        return _run(
            command,
            timeout=int(payload.get("timeout_seconds", 1800)),
        )
