from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from mcp_blender_unity.config import find_blender

from .config import AgentConfig
from .models import ActionResult
from .unity_editor_bridge import UnityEditorBridge


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
            "agent.update": self.agent_update,
            "artifact.preview": self.artifact_preview,
            "git.status": self.git_status,
            "git.sync": self.git_sync,
            "unity.editor_status": self.unity_editor_status,
            "unity.refresh_editor": self.unity_refresh_editor,
            "unity.stop_play": self.unity_stop_play,
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

    def agent_update(self, payload: dict[str, Any]) -> ActionResult:
        repo = self.config.agent_repo_path.resolve()
        if not (repo / ".git").is_dir():
            return ActionResult(False, f"managed agent repository not found: {repo}")

        branch = "feat/ordax-dev-agent"
        status = _run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
            timeout=60,
        )
        if not status.ok:
            return status
        if status.data.get("stdout", "").strip():
            return ActionResult(
                False,
                "managed agent has local tracked changes; update refused",
                {"status": status.data["stdout"]},
            )

        before = _run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            timeout=30,
        )
        if not before.ok:
            return before
        before_head = before.data.get("stdout", "").strip()

        fetch = _run(
            ["git", "-C", str(repo), "fetch", "--quiet", "origin", branch],
            timeout=180,
        )
        if not fetch.ok:
            return fetch

        current = _run(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
            timeout=30,
        )
        if not current.ok:
            return current

        if current.data.get("stdout", "").strip() != branch:
            checkout = _run(
                ["git", "-C", str(repo), "checkout", "-B", branch, f"origin/{branch}"],
                timeout=120,
            )
            if not checkout.ok:
                return checkout
        else:
            merge = _run(
                ["git", "-C", str(repo), "merge", "--ff-only", "--quiet", f"origin/{branch}"],
                timeout=120,
            )
            if not merge.ok:
                return merge

        head = _run(["git", "-C", str(repo), "rev-parse", "HEAD"], timeout=30)
        if not head.ok:
            return ActionResult(
                False,
                "agent update completed but HEAD lookup failed",
                head.data,
            )

        after_head = head.data.get("stdout", "").strip()
        dependency_refresh = False

        if before_head and after_head and before_head != after_head:
            dependency_diff = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "diff",
                    "--quiet",
                    before_head,
                    after_head,
                    "--",
                    "pyproject.toml",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                shell=False,
            )
            if dependency_diff.returncode == 1:
                dependency_refresh = True
            elif dependency_diff.returncode not in (0, 1):
                return ActionResult(
                    False,
                    "could not determine whether agent dependencies changed",
                    {
                        "returncode": dependency_diff.returncode,
                        "stdout": dependency_diff.stdout[-4000:],
                        "stderr": dependency_diff.stderr[-4000:],
                    },
                )

        if dependency_refresh:
            install = _run(
                [sys.executable, "-m", "pip", "install", "-e", str(repo)],
                timeout=600,
            )
            if not install.ok:
                return install

        return ActionResult(
            True,
            "agent updated; restart required",
            {
                "branch": branch,
                "head": after_head,
                "restart_required": True,
                "dependencies_refreshed": dependency_refresh,
            },
        )

    def artifact_preview(self, payload: dict[str, Any]) -> ActionResult:
        name = str(payload.get("artifact_name", "hordax-prototype.png"))
        allowed = {
            "hordax-prototype.png",
            "hordax-prototype.json",
        }
        if name not in allowed:
            return ActionResult(False, f"artifact not allowed: {name}")

        path = (self.config.state_dir / "artifacts" / name).resolve()
        root = (self.config.state_dir / "artifacts").resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return ActionResult(False, "artifact path escaped managed directory")

        if not path.is_file():
            return ActionResult(False, f"artifact not found: {path}")

        data = path.read_bytes()
        max_bytes = int(payload.get("max_bytes", 65536))
        max_bytes = max(1024, min(max_bytes, 131072))
        if len(data) > max_bytes:
            return ActionResult(
                False,
                f"artifact is too large for inline preview: {len(data)} > {max_bytes}",
                {
                    "path": str(path),
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            )

        return ActionResult(
            True,
            "artifact preview ready",
            {
                "artifact_name": name,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "base64": base64.b64encode(data).decode("ascii"),
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
        candidates = [
            self.config.agent_repo_path / "scripts" / "windows" / name,
            self.config.bridge_path / "scripts" / "windows" / name,
        ]
        for script in candidates:
            if script.is_file():
                return script
        raise FileNotFoundError(candidates[0])

    def _request_live_unity_editor(
        self,
        editor: UnityEditorBridge,
        action: str,
        payload: dict[str, Any] | None,
        *,
        timeout_seconds: float,
    ) -> ActionResult | None:
        """Use the already-open Unity Editor safely.

        Returns None only when the project is not open, which allows the caller
        to use the batch-mode fallback. If the project is open, batch mode is
        deliberately never attempted because Unity forbids two Editors on the
        same project.
        """
        if not editor.project_appears_open():
            return None

        deadline = time.monotonic() + max(5.0, timeout_seconds)
        nudged = False

        while time.monotonic() < deadline:
            status = editor.status()
            presence = status.get("presence") or {}
            ready = (
                editor.presence_is_fresh(max_age_seconds=12.0)
                and not bool(presence.get("compiling"))
            )
            if ready:
                remaining = max(5.0, deadline - time.monotonic())
                result = editor.request(
                    action,
                    payload or {},
                    timeout_seconds=remaining,
                )
                if result is not None:
                    return result

            if not nudged:
                editor.nudge_companion(
                    wait_seconds=min(15.0, max(1.0, deadline - time.monotonic()))
                )
                nudged = True

            time.sleep(0.5)

        return ActionResult(
            False,
            "Unity Editor is open but its OrdaX companion did not become ready; "
            "batch fallback was refused to avoid a second Unity instance",
            editor.status(),
        )

    def unity_editor_status(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        editor = UnityEditorBridge(project)
        if not editor.presence_is_fresh() and editor.project_appears_open():
            editor.nudge_companion(
                wait_seconds=float(payload.get("wait_seconds", 30)),
            )
        status = editor.status()
        ready = bool(status.get("presence_fresh"))
        return ActionResult(
            ready,
            "Unity Editor companion ready" if ready else "Unity Editor companion not ready",
            status,
        )

    def unity_refresh_editor(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        editor = UnityEditorBridge(project)

        force = bool(payload.get("force", False))
        if editor.presence_is_fresh() and not force:
            return ActionResult(
                True,
                "Unity Editor companion already ready",
                editor.status(),
            )

        if not editor.project_appears_open():
            return ActionResult(
                False,
                "Unity project does not appear to be open",
                editor.status(),
            )

        script = self._bridge_script("unity-editor-refresh.ps1")
        refresh = _run(
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
            timeout=60,
        )
        if not refresh.ok:
            return refresh

        wait_seconds = float(payload.get("wait_seconds", 45))
        deadline = time.monotonic() + max(2.0, wait_seconds)
        editor.nudge_companion(wait_seconds=min(wait_seconds, 15.0))

        ready = False
        status = editor.status()
        while time.monotonic() < deadline:
            status = editor.status()
            presence = status.get("presence") or {}
            ready = (
                editor.presence_is_fresh(max_age_seconds=12.0)
                and not bool(presence.get("compiling"))
            )
            if ready:
                break
            time.sleep(0.5)

        status["refresh_stdout"] = refresh.data.get("stdout", "")
        status["refresh_stderr"] = refresh.data.get("stderr", "")

        return ActionResult(
            ready,
            "Unity Editor refreshed, scripts settled, and companion ready"
            if ready
            else "Unity Editor refresh sent, but scripts did not settle in time",
            status,
        )

    def unity_stop_play(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        editor = UnityEditorBridge(project)
        status = editor.status()
        presence = status.get("presence") or {}

        if not bool(presence.get("playing")):
            return ActionResult(
                True,
                "Unity Editor is already outside Play Mode",
                status,
            )

        script = self._bridge_script("unity-editor-toggle-play.ps1")
        toggle = _run(
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
            timeout=60,
        )
        if not toggle.ok:
            return toggle

        deadline = time.monotonic() + float(payload.get("wait_seconds", 30))
        while time.monotonic() < deadline:
            current = editor.status()
            current_presence = current.get("presence") or {}
            if editor.presence_is_fresh(max_age_seconds=8.0) and not bool(
                current_presence.get("playing")
            ):
                current["toggle_stdout"] = toggle.data.get("stdout", "")
                current["toggle_stderr"] = toggle.data.get("stderr", "")
                return ActionResult(
                    True,
                    "Unity Editor exited Play Mode",
                    current,
                )
            time.sleep(0.35)

        final_status = editor.status()
        final_status["toggle_stdout"] = toggle.data.get("stdout", "")
        final_status["toggle_stderr"] = toggle.data.get("stderr", "")
        return ActionResult(
            False,
            "Play toggle was sent, but Unity did not leave Play Mode in time",
            final_status,
        )

    def unity_compile(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        timeout = int(payload.get("timeout_seconds", 1800))

        editor = UnityEditorBridge(project)
        editor_result = self._request_live_unity_editor(
            editor,
            "validate",
            {},
            timeout_seconds=min(timeout, 600),
        )
        if editor_result is not None:
            if editor_result.ok:
                editor_result.summary = "Unity Editor loaded current scripts and validation passed"
            return editor_result

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
            timeout=timeout,
        )

    def unity_validate(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        timeout = int(payload.get("timeout_seconds", 1800))
        method = payload.get("execute_method", "HORDAX.EditorTools.CiValidation.Run")
        if method != "HORDAX.EditorTools.CiValidation.Run":
            return ActionResult(False, f"execute method not allowed: {method}")

        editor = UnityEditorBridge(project)
        editor_result = self._request_live_unity_editor(
            editor,
            "validate",
            {},
            timeout_seconds=min(timeout, 600),
        )
        if editor_result is not None:
            return editor_result

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
            timeout=timeout,
        )

    def unity_capture(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        output = self.config.state_dir / "artifacts" / "hordax-prototype.png"
        output.parent.mkdir(parents=True, exist_ok=True)

        editor = UnityEditorBridge(project)
        editor_result = self._request_live_unity_editor(
            editor,
            "capture",
            {
                "outputPath": str(output),
                "width": int(payload.get("width", 1280)),
                "height": int(payload.get("height", 720)),
                "warmupFrames": int(payload.get("warmup_frames", 120)),
                "warmupSeconds": float(payload.get("warmup_seconds", 0.0)),
                "timeScale": float(payload.get("time_scale", 1.0)),
                "captureOnTerminal": bool(payload.get("capture_on_terminal", True)),
                "captureOnBoss": bool(payload.get("capture_on_boss", False)),
            },
            timeout_seconds=float(payload.get("timeout_seconds", 900)),
        )
        if editor_result is not None:
            if editor_result.ok:
                editor_result.data["artifact"] = str(output)
                snapshot = output.with_suffix(".json")
                if snapshot.is_file():
                    try:
                        editor_result.data["snapshot"] = json.loads(
                            snapshot.read_text(encoding="utf-8-sig")
                        )
                        editor_result.data["snapshot_path"] = str(snapshot)
                    except Exception as error:
                        editor_result.data["snapshot_error"] = str(error)
            return editor_result

        script = self._bridge_script("unity-capture.ps1")
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
