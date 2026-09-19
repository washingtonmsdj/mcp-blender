from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import time
import threading
import re
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable

from mcp_blender_unity.config import find_blender

from .config import AgentConfig
from .models import ActionResult
from .unity_editor_bridge import UnityEditorBridge
from .projects import load_projects, Project
from .observations import ObservationActions
from .execution_lock import ExecutionLock
from .blender_live import BlenderLiveActions
from .references import ReferenceActions


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


class ActionRegistry(ObservationActions, BlenderLiveActions, ReferenceActions):
    """Strict allow-list. No arbitrary remote shell command is accepted."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.projects = load_projects(config)
        self.on_observation = None
        self._execution_lock = threading.Lock()
        self._actions: dict[str, Action] = {
            "projects.list": self.projects_list,
            "project.references": self.project_references,
            "project.reference_images": self.project_reference_images,
            "blender.reference_review": self.blender_reference_review,
            "project.observe": self.project_observe,
            "observation.capture": self.observation_capture,
            "blender.inspect": self.blender_inspect,
            "blender.live_status": self.blender_live_status,
            "blender.live_inspect": self.blender_live_inspect,
            "blender.modeling_tools": self.blender_modeling_tools,
            "blender.checkpoint_list": self.blender_checkpoint_list,
            "blender.checkpoint_create": self.blender_checkpoint_create,
            "blender.checkpoint_restore": self.blender_checkpoint_restore,
            "blender.object_info": self.blender_object_info,
            "blender.model_create": self.blender_model_create,
            "blender.model_transform": self.blender_model_transform,
            "blender.model_modifier": self.blender_model_modifier,
            "blender.live_capture": self.blender_live_capture,
            "blender.live_run_python": self.blender_live_run_python,
            "blender.live_result": self.blender_live_result,
            "blender.render_preview": self.blender_render_preview,
            "unity.install_companion": self.unity_install_companion,
            "agent.status": self.agent_status,
            "agent.update": self.agent_update,
            "agent.self_test": self.agent_self_test,
            "artifact.preview": self.artifact_preview,
            "git.status": self.git_status,
            "git.sync": self.git_sync,
            "unity.editor_status": self.unity_editor_status,
            "unity.refresh_editor": self.unity_refresh_editor,
            "unity.play_start": self.unity_play_start,
            "unity.play_stop": self.unity_play_stop,
            "unity.stop_play": self.unity_play_stop,
            "unity.compile": self.unity_compile,
            "unity.validate": self.unity_validate,
            "unity.capture": self.unity_capture,
            "unity.run_method": self.unity_run_method,
            "blender.version": self.blender_version,
            "blender.run_python": self.blender_run_python,
        }
        self._app_prefixes = {"unity", "blender"}
        available = {entry.name: entry for entry in entry_points(group="ordax_dev_agent.adapters")}
        for name in config.adapters:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in {"agent", "artifact", "git", "project", "projects", "observation", "unity", "blender"}:
                raise ValueError(f"invalid or reserved adapter name: {name}")
            if name not in available:
                raise ValueError(f"configured adapter is not installed: {name}")
            # Local installed plugin, explicitly enabled by workstation settings.
            handlers = available[name].load()(config)
            for operation, handler in handlers.items():
                if not re.fullmatch(r"[a-z][a-z0-9_]*", operation) or not callable(handler):
                    raise ValueError(f"invalid action in adapter {name}: {operation}")
                self._actions[f"{name}.{operation}"] = (
                    lambda payload, fn=handler: fn(self._project(payload), payload))
            self._app_prefixes.add(name)

    @property
    def names(self) -> list[str]:
        return sorted(self._actions)

    def execute(self, action: str, payload: dict[str, Any]) -> ActionResult:
        handler = self._actions.get(action)
        if handler is None:
            return ActionResult(False, f"action not allowed: {action}")
        payload = payload or {}
        if action in ("agent.status", "projects.list"):
            return handler(payload)
        # A busy application must not receive a second editor/render operation.
        if not self._execution_lock.acquire(blocking=False):
            return ActionResult(False, "Agent is busy; retry after the current action", {"retryable": True})
        process_lock = ExecutionLock(self.config.state_dir)
        try:
            if not process_lock.acquire():
                return ActionResult(False, "Another agent/MCP action is running", {"retryable": True})
            if action.split('.')[0] in self._app_prefixes and action != "blender.version":
                project = self._project(payload)
                if action.split('.')[0] not in project.apps:
                    raise ValueError(f"application not enabled for project {project.slug}")
            result = handler(payload)
            return result
        except (ValueError, FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
            return ActionResult(False, f"{type(error).__name__}: {error}")
        finally:
            process_lock.release()
            self._execution_lock.release()

    def agent_status(self, payload: dict[str, Any]) -> ActionResult:
        return ActionResult(
            True,
            "agent ready",
            {
                **self.config.public_status(),
                "actions": self.names,
                "projects": [project.public() for project in self.projects.values()],
                "default_project": self.config.default_project,
                "busy": self._execution_lock.locked(),
            },
        )

    def agent_self_test(self, payload: dict[str, Any]) -> ActionResult:
        repo = self.config.agent_repo_path.resolve()
        if not (repo / "tests").is_dir():
            return ActionResult(False, f"agent test suite not found: {repo / 'tests'}")

        compile_result = _run(
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "mcp_blender_unity",
                "ordax_dev_agent",
            ],
            cwd=repo,
            timeout=300,
        )
        if not compile_result.ok:
            compile_result.summary = "agent Python compile check failed"
            return compile_result

        tests = _run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
                "-v",
            ],
            cwd=repo,
            timeout=int(payload.get("timeout_seconds", 900)),
        )
        if not tests.ok:
            return ActionResult(
                False,
                "agent unit/integration tests failed",
                {
                    "compile": compile_result.data,
                    "tests": tests.data,
                },
            )

        data = {
            "compile": compile_result.data,
            "tests": tests.data,
        }

        if bool(payload.get("visual", False)):
            visual = _run(
                [sys.executable, "scripts/verify_visual_agent.py"],
                cwd=repo,
                timeout=int(payload.get("visual_timeout_seconds", 600)),
            )
            data["visual"] = visual.data
            if not visual.ok:
                return ActionResult(
                    False,
                    "agent tests passed, but real Blender visual smoke failed",
                    data,
                )

        return ActionResult(
            True,
            "agent compile, tests, and requested visual smoke passed",
            data,
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
        root = (self.config.state_dir / "artifacts" / self._project(payload).slug).resolve()
        if name in {"hordax-prototype.png", "hordax-prototype.json", "latest.png", "latest.json"}:
            manifest = root / 'latest.json'
            if not manifest.is_file():
                return ActionResult(False, "No successful capture for this project yet")
            latest = json.loads(manifest.read_text(encoding='utf-8'))
            path = Path(latest['snapshot_path' if name.endswith('.json') else 'artifact']).resolve()
        else:
            path = (root / name).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return ActionResult(False, "artifact path escaped managed directory")

        if not path.is_file():
            return ActionResult(False, f"artifact not found: {path}")

        max_bytes = int(payload.get("max_bytes", 65536))
        max_bytes = max(1024, min(max_bytes, 2 * 1024 * 1024))
        size = path.stat().st_size
        if size > max_bytes:
            return ActionResult(
                False,
                f"artifact is too large for inline preview: {size} > {max_bytes}",
                {
                    "path": str(path),
                    "size_bytes": size,
                },
            )

        data = path.read_bytes()
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
        return self._project(payload).root

    def _project(self, payload: dict[str, Any]) -> Project:
        slug = payload.get("project") or self.config.default_project
        if slug not in self.projects:
            raise ValueError(f"project not registered: {slug}")
        project = self.projects[slug]
        if not project.root.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project.root}")
        return project

    def _editor(self, payload: dict[str, Any]) -> UnityEditorBridge:
        project = self._project(payload)
        source = project.unity.get("companion_source")
        if source:
            source = project.path(source, must_exist=False)
        return UnityEditorBridge(project.root, source)

    def git_status(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        return _run(["git", "-C", str(project), "status", "--short"], timeout=60)

    def git_sync(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        allowed = self._project(payload).allowed_branches
        branch = payload.get("branch") or (allowed[0] if allowed else None)
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
            exists = _run(["git", "-C", str(project), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], timeout=30)
            switch = (["git", "-C", str(project), "switch", branch] if exists.ok else
                      ["git", "-C", str(project), "switch", "--track", "-c", branch, f"origin/{branch}"])
            checkout = _run(
                switch,
                timeout=120,
            )
            if not checkout.ok:
                return checkout
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
        editor = self._editor(payload)
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
        editor = self._editor(payload)

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

    def unity_play_start(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        editor = self._editor(payload)
        wait_seconds = float(payload.get("wait_seconds", 45))

        status = editor.status()
        presence = status.get("presence") or {}
        if bool(presence.get("playing")):
            return ActionResult(
                True,
                "Unity Editor is already in Play Mode",
                status,
            )

        result = self._request_live_unity_editor(
            editor,
            "play_start",
            {},
            timeout_seconds=min(wait_seconds, 30.0),
        )
        if result is None:
            return ActionResult(
                False,
                "Unity project is not open; background Play Mode requires the open Editor companion",
                editor.status(),
            )
        if not result.ok:
            return result

        deadline = time.monotonic() + max(5.0, wait_seconds)
        while time.monotonic() < deadline:
            current = editor.status()
            current_presence = current.get("presence") or {}
            if (
                editor.presence_is_fresh(max_age_seconds=12.0)
                and bool(current_presence.get("playing"))
            ):
                return ActionResult(
                    True,
                    "Unity Play Mode is running in the background",
                    current,
                )
            time.sleep(0.35)

        return ActionResult(
            False,
            "Play Mode start was requested, but Unity did not enter Play Mode in time",
            editor.status(),
        )

    def unity_play_stop(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        editor = self._editor(payload)
        wait_seconds = float(payload.get("wait_seconds", 30))

        status = editor.status()
        presence = status.get("presence") or {}
        if not bool(presence.get("playing")):
            return ActionResult(
                True,
                "Unity Editor is already outside Play Mode",
                status,
            )

        result = self._request_live_unity_editor(
            editor,
            "play_stop",
            {},
            timeout_seconds=min(wait_seconds, 20.0),
        )
        if result is None:
            return ActionResult(
                False,
                "Unity Editor companion is unavailable; focus-stealing fallback is disabled",
                editor.status(),
            )
        if not result.ok:
            return result

        deadline = time.monotonic() + max(5.0, wait_seconds)
        while time.monotonic() < deadline:
            current = editor.status()
            current_presence = current.get("presence") or {}
            if (
                editor.presence_is_fresh(max_age_seconds=12.0)
                and not bool(current_presence.get("playing"))
            ):
                return ActionResult(
                    True,
                    "Unity Play Mode stopped without foreground focus",
                    current,
                )
            time.sleep(0.35)

        return ActionResult(
            False,
            "Play Mode stop was requested, but Unity did not exit Play Mode in time",
            editor.status(),
        )

    def unity_compile(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        timeout = int(payload.get("timeout_seconds", 1800))

        editor = self._editor(payload)
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
            ],
            timeout=timeout,
        )

    def unity_validate(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        timeout = int(payload.get("timeout_seconds", 1800))
        settings = self._project(payload).unity
        method = payload.get("execute_method", settings.get("validate_method"))
        if method and method not in settings.get("allowed_methods", []):
            return ActionResult(False, f"execute method not allowed: {method}")

        editor = self._editor(payload)
        if method and settings.get("profile") != "hordax" and editor.project_appears_open():
            return ActionResult(False, "Custom validation methods require a project-specific live companion; close the Editor to run this allow-listed batch method")
        editor_result = self._request_live_unity_editor(
            editor,
            "validate",
            {},
            timeout_seconds=min(timeout, 600),
        )
        if editor_result is not None:
            return editor_result

        if not method:
            return self.unity_compile(payload)
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
        output = self._capture_output(payload)
        output.parent.mkdir(parents=True, exist_ok=True)

        editor = self._editor(payload)
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
                if not output.is_file() or output.stat().st_size == 0:
                    return ActionResult(False, "Unity reported success without producing a fresh image", editor_result.data)
                editor_result.data["artifact"] = str(output)
                self._record_capture(payload, output)
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

        if self._project(payload).unity.get("profile") != "hordax":
            return ActionResult(False, "Open Unity and install its generic companion to capture this project")
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
        if result.ok and output.is_file() and output.stat().st_size > 0:
            self._record_capture(payload, output)
        else:
            result.ok = False
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
        allowed = self._project(payload).unity.get("allowed_methods", [])
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

        registered = self._project(payload)
        script = registered.path(raw_script)
        allowed_root = registered.path(registered.blender.get("scripts_dir", "automation/blender"), must_exist=False)
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
            blend = registered.path(raw_blend)
            if not blend.is_file():
                return ActionResult(False, f"Blend file not found: {blend}")
            command.append(str(blend))
        command.extend(["--python-exit-code", "1", "--python", str(script)])
        return _run(
            command,
            timeout=int(payload.get("timeout_seconds", 1800)),
        )
