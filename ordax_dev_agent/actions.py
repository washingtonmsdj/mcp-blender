from __future__ import annotations

import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import threading
import re
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable

from mcp_blender_unity.config import find_blender, find_unity

from .config import AgentConfig
from .models import ActionResult
from .unity_editor_bridge import UnityEditorBridge
from .unity_knowledge import capability_report as unity_capability_report, project_profile as unity_project_profile, skill_catalog as unity_skill_catalog
from .unity_assets import asset_inventory as unity_asset_inventory
from .unity_cli import (
    cli_status as unity_cli_status,
    install_pipeline as unity_install_pipeline,
    pipeline_catalog as unity_pipeline_catalog,
    pipeline_command as unity_pipeline_command,
)
from .blender_live_bridge import BlenderLiveBridge
from .blender_asset_sources import polyhaven_file_manifest, search_polyhaven
from .projects import load_projects, Project
from .observations import ObservationActions
from .execution_lock import ExecutionLock


Action = Callable[[dict[str, Any]], ActionResult]


def _run(command: list[str], *, cwd: Path | None = None, timeout: int = 1800) -> ActionResult:
    creationflags = 0
    start_new_session = False
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        start_new_session = True

    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if sys.platform == "win32":
            # Kill the full descendant tree. Killing only the immediate Python
            # process can leave Blender/Unity/Git children holding stdout/stderr
            # pipe handles open, which makes communicate() wait forever.
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
                shell=False,
            )
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            stdout, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

    data = {
        "returncode": process.returncode,
        "stdout": (stdout or "")[-40000:],
        "stderr": (stderr or "")[-40000:],
        "command": command,
        "timed_out": timed_out,
        "timeout_seconds": timeout if timed_out else None,
    }
    return ActionResult(
        ok=(process.returncode == 0 and not timed_out),
        summary=(
            f"command timed out after {timeout}s"
            if timed_out
            else ("command completed" if process.returncode == 0 else "command failed")
        ),
        data=data,
    )


def _unity_process_ids_for_project(project: Path) -> list[int]:
    """Return Unity process IDs whose command line references this project."""
    target = str(project.resolve()).replace("\\", "/").lower()
    if sys.platform == "win32":
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='Unity.exe'\" | "
                "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return []
        try:
            raw = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return []
        records = raw if isinstance(raw, list) else [raw]
        result: list[int] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            command = str(record.get("CommandLine") or "").replace("\\", "/").lower()
            if target and target in command:
                try:
                    result.append(int(record.get("ProcessId")))
                except (TypeError, ValueError):
                    pass
        return result

    completed = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        capture_output=True,
        text=True,
        timeout=20,
        shell=False,
    )
    if completed.returncode != 0:
        return []
    result: list[int] = []
    for line in completed.stdout.splitlines():
        normalized = line.replace("\\", "/").lower()
        if "unity" not in normalized or target not in normalized:
            continue
        head = line.strip().split(None, 1)[0]
        try:
            result.append(int(head))
        except ValueError:
            pass
    return result


class ActionRegistry(ObservationActions):
    """Strict allow-list. No arbitrary remote shell command is accepted."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.projects = load_projects(config)
        self.on_observation = None
        self._execution_lock = threading.Lock()
        self._actions: dict[str, Action] = {
            "projects.list": self.projects_list,
            "project.observe": self.project_observe,
            "observation.capture": self.observation_capture,
            "blender.inspect": self.blender_inspect,
            "blender.render_preview": self.blender_render_preview,
            "blender.live_start": self.blender_live_start,
            "blender.live_status": self.blender_live_status,
            "blender.live_inspect": self.blender_live_inspect,
            "blender.live_scene_snapshot": self.blender_live_scene_snapshot,
            "blender.live_scene_reset": self.blender_live_scene_reset,
            "blender.live_object_inspect": self.blender_live_object_inspect,
            "blender.live_object_fingerprints": self.blender_live_object_fingerprints,
            "blender.live_contact_audit": self.blender_live_contact_audit,
            "blender.live_quality_gate": self.blender_live_quality_gate,
            "blender.live_object_transform": self.blender_live_object_transform,
            "blender.live_object_metadata": self.blender_live_object_metadata,
            "blender.live_api_schema": self.blender_live_api_schema,
            "blender.live_api_lookup": self.blender_live_api_lookup,
            "blender.live_node_schema": self.blender_live_node_schema,
            "blender.live_export": self.blender_live_export,
            "blender.live_checkpoint_create": self.blender_live_checkpoint_create,
            "blender.live_checkpoint_list": self.blender_live_checkpoint_list,
            "blender.live_checkpoint_restore": self.blender_live_checkpoint_restore,
            "blender.live_trajectory": self.blender_live_trajectory,
            "blender.live_generation_pass": self.blender_live_generation_pass,
            "blender.live_result": self.blender_live_result,
            "blender.live_run_script": self.blender_live_run_script,
            "blender.live_capture": self.blender_live_capture,
            "blender.live_multiview_capture": self.blender_live_multiview_capture,
            "blender.live_save": self.blender_live_save,
            "blender.live_stop": self.blender_live_stop,
            "blender.asset_search": self.blender_asset_search,
            "blender.asset_manifest": self.blender_asset_manifest,
            "blender.multiview_compare": self.blender_multiview_compare,
            "unity.install_companion": self.unity_install_companion,
            "unity.project_profile": self.unity_project_profile,
            "unity.capabilities": self.unity_capabilities,
            "unity.skill_catalog": self.unity_skill_catalog,
            "unity.cli_status": self.unity_cli_status,
            "unity.pipeline_install": self.unity_pipeline_install,
            "unity.pipeline_catalog": self.unity_pipeline_catalog,
            "unity.pipeline_command": self.unity_pipeline_command,
            "unity.asset_inventory": self.unity_asset_inventory,
            "unity.scene_open": self.unity_scene_open,
            "unity.scene_summary": self.unity_scene_summary,
            "unity.physics_audit": self.unity_physics_audit,
            "unity.benchmark_islands_generate": self.unity_benchmark_islands_generate,
            "agent.status": self.agent_status,
            "agent.update": self.agent_update,
            "agent.self_test": self.agent_self_test,
            "artifact.preview": self.artifact_preview,
            "git.status": self.git_status,
            "git.diff": self.git_diff,
            "git.sync": self.git_sync,
            "unity.editor_status": self.unity_editor_status,
            "unity.editor_start": self.unity_editor_start,
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
        live_apps: dict[str, dict[str, Any]] = {}
        for slug, project in self.projects.items():
            if not project.root.is_dir():
                continue

            app_state: dict[str, Any] = {}
            if "unity" in project.apps:
                try:
                    app_state["unity"] = self._editor({"project": slug}).status()
                except Exception as error:
                    app_state["unity"] = {"presence_fresh": False, "error": str(error)}

            if "blender" in project.apps:
                try:
                    app_state["blender"] = BlenderLiveBridge(
                        self.config,
                        project,
                    ).status()
                except Exception as error:
                    app_state["blender"] = {"presence_fresh": False, "error": str(error)}

            if app_state:
                live_apps[slug] = app_state

        return ActionResult(
            True,
            "agent ready",
            {
                **self.config.public_status(),
                "actions": self.names,
                "projects": [project.public() for project in self.projects.values()],
                "default_project": self.config.default_project,
                "busy": self._execution_lock.locked(),
                "live_apps": live_apps,
            },
        )

    def agent_self_test(self, payload: dict[str, Any]) -> ActionResult:
        repo = self.config.agent_repo_path.resolve()
        tests_root = repo / "tests"
        if not tests_root.is_dir():
            return ActionResult(False, f"agent test suite not found: {tests_root}")

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
            timeout=min(int(payload.get("compile_timeout_seconds", 120)), 300),
        )
        if not compile_result.ok:
            compile_result.summary = "agent Python compile check failed"
            return compile_result

        per_file_timeout = max(
            10,
            min(int(payload.get("per_test_file_timeout_seconds", 120)), 600),
        )
        test_files = sorted(tests_root.glob("test_*.py"))
        if not test_files:
            return ActionResult(False, "agent test suite contains no test_*.py files")

        test_runs: list[dict[str, Any]] = []
        for test_file in test_files:
            try:
                test_result = _run(
                    [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-p",
                        test_file.name,
                        "-v",
                    ],
                    cwd=repo,
                    timeout=per_file_timeout,
                )
            except subprocess.TimeoutExpired as error:
                return ActionResult(
                    False,
                    f"agent test file timed out: {test_file.name}",
                    {
                        "compile": compile_result.data,
                        "test_file": test_file.name,
                        "timeout_seconds": error.timeout,
                        "completed_test_files": test_runs,
                    },
                )

            test_runs.append(
                {
                    "file": test_file.name,
                    "ok": test_result.ok,
                    "returncode": test_result.data.get("returncode"),
                    "stdout": test_result.data.get("stdout", ""),
                    "stderr": test_result.data.get("stderr", ""),
                }
            )
            if not test_result.ok:
                return ActionResult(
                    False,
                    f"agent test file failed: {test_file.name}",
                    {
                        "compile": compile_result.data,
                        "tests": test_runs,
                    },
                )

        data = {
            "compile": compile_result.data,
            "test_files": test_runs,
            "test_file_count": len(test_runs),
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
            "agent compile, per-file tests, and requested visual smoke passed",
            data,
        )


    def agent_update(self, payload: dict[str, Any]) -> ActionResult:
        repo = self.config.agent_repo_path.resolve()
        if not (repo / ".git").is_dir():
            return ActionResult(False, f"managed agent repository not found: {repo}")

        branch = "feat/ordax-dev-agent"
        git = ["git", "-c", "core.fsmonitor=false", "-C", str(repo)]

        def quiet_check(args: list[str], *, timeout: int = 20) -> tuple[int, str]:
            try:
                completed = subprocess.run(
                    [*git, *args],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                    shell=False,
                )
                return completed.returncode, completed.stderr[-4000:]
            except subprocess.TimeoutExpired as error:
                return 124, f"timed out after {error.timeout} seconds"

        # We only care about tracked edits. Avoid `git status` here: on some
        # Windows worktrees its index refresh can stall behind filesystem
        # monitors for minutes even with untracked scanning disabled.
        unstaged_rc, unstaged_error = quiet_check(["diff-files", "--quiet", "--"])
        staged_rc, staged_error = quiet_check(
            ["diff-index", "--cached", "--quiet", "HEAD", "--"]
        )
        if unstaged_rc not in (0, 1) or staged_rc not in (0, 1):
            return ActionResult(
                False,
                "managed agent tracked-change check failed",
                {
                    "unstaged_returncode": unstaged_rc,
                    "unstaged_error": unstaged_error,
                    "staged_returncode": staged_rc,
                    "staged_error": staged_error,
                },
            )
        if unstaged_rc == 1 or staged_rc == 1:
            changed = _run(
                [*git, "diff", "--name-status", "HEAD", "--"],
                timeout=30,
            )
            return ActionResult(
                False,
                "managed agent has local tracked changes; update refused",
                {
                    "status": changed.data.get("stdout", "") if changed.ok else "",
                    "unstaged": unstaged_rc == 1,
                    "staged": staged_rc == 1,
                },
            )

        before = _run([*git, "rev-parse", "HEAD"], timeout=20)
        if not before.ok:
            return before
        before_head = before.data.get("stdout", "").strip()

        fetch = _run(
            [*git, "fetch", "--quiet", "origin", branch],
            timeout=180,
        )
        if not fetch.ok:
            return fetch

        current = _run(
            [*git, "rev-parse", "--abbrev-ref", "HEAD"],
            timeout=20,
        )
        if not current.ok:
            return current

        if current.data.get("stdout", "").strip() != branch:
            checkout = _run(
                [*git, "checkout", "-B", branch, f"origin/{branch}"],
                timeout=120,
            )
            if not checkout.ok:
                return checkout
        else:
            merge = _run(
                [*git, "merge", "--ff-only", "--quiet", f"origin/{branch}"],
                timeout=120,
            )
            if not merge.ok:
                return merge

        head = _run([*git, "rev-parse", "HEAD"], timeout=20)
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
                    *git,
                    "diff",
                    "--quiet",
                    before_head,
                    after_head,
                    "--",
                    "pyproject.toml",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
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
                "tracked_check": "diff-files+diff-index",
            },
        )

    def artifact_preview(self, payload: dict[str, Any]) -> ActionResult:
        project_artifact = str(payload.get("project_artifact_path") or "").strip()
        if project_artifact:
            project = self._project(payload)
            root = (project.root / "Artifacts").resolve()
            path = (root / project_artifact).resolve()
        else:
            name = str(payload.get("artifact_name", "hordax-prototype.png"))
            root = (self.config.state_dir / "artifacts" / self._project(payload).slug).resolve()
            if name in {"hordax-prototype.png", "hordax-prototype.json", "latest.png", "latest.json"}:
                manifest = root / "latest.json"
                if not manifest.is_file():
                    return ActionResult(False, "No successful capture for this project yet")
                latest = json.loads(manifest.read_text(encoding="utf-8"))
                path = Path(
                    latest["snapshot_path" if name.endswith(".json") else "artifact"]
                ).resolve()
            else:
                path = (root / name).resolve()

        try:
            path.relative_to(root)
        except ValueError:
            return ActionResult(False, "artifact path escaped allowed root")

        if not path.is_file():
            return ActionResult(False, f"artifact not found: {path}")

        data = path.read_bytes()
        source_size = len(data)
        thumbnail = bool(payload.get("thumbnail", False))
        output_format = path.suffix.lower().lstrip(".")
        mime_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "json": "application/json",
        }.get(output_format, "application/octet-stream")

        thumbnail_size = None
        if thumbnail:
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                return ActionResult(False, "thumbnail is supported only for raster images")
            try:
                import io
                from PIL import Image
            except ImportError:
                return ActionResult(False, "Pillow is required for artifact thumbnails")

            max_width = max(64, min(int(payload.get("max_width", 480)), 1600))
            max_height = max(64, min(int(payload.get("max_height", 320)), 1200))
            quality = max(30, min(int(payload.get("quality", 72)), 92))

            with Image.open(path) as image:
                image = image.convert("RGB")
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                thumbnail_size = [image.width, image.height]
                buffer = io.BytesIO()
                image.save(
                    buffer,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
                data = buffer.getvalue()
            output_format = "jpeg"
            mime_type = "image/jpeg"

        max_bytes = int(payload.get("max_bytes", 262144))
        max_bytes = max(4096, min(max_bytes, 2 * 1024 * 1024))
        if len(data) > max_bytes:
            return ActionResult(
                False,
                f"artifact is too large for inline preview: {len(data)} > {max_bytes}",
                {
                    "path": str(path),
                    "source_size_bytes": source_size,
                    "preview_size_bytes": len(data),
                    "thumbnail": thumbnail,
                },
            )

        return ActionResult(
            True,
            "artifact preview ready",
            {
                "artifact_name": path.name,
                "path": str(path),
                "source_size_bytes": source_size,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "mime_type": mime_type,
                "format": output_format,
                "thumbnail": thumbnail,
                "thumbnail_size": thumbnail_size,
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

    def unity_project_profile(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        profile = unity_project_profile(project.root)
        ok = bool(profile.get("unity_version")) and bool(profile.get("has_project_settings"))
        return ActionResult(
            ok,
            "Unity project profile ready" if ok else "Unity project profile is incomplete",
            {
                "project": project.slug,
                **profile,
            },
        )

    def unity_capabilities(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        report = unity_capability_report(project.root)
        profile = report.get("profile") or {}
        supported = bool(profile.get("unity_6_or_newer"))
        return ActionResult(
            supported,
            "Unity 6 capability report ready"
            if supported
            else "Unity project detected, but Unity 6+ is required for the first-party skill baseline",
            {
                "project": project.slug,
                **report,
            },
        )

    def unity_skill_catalog(self, payload: dict[str, Any]) -> ActionResult:
        return ActionResult(
            True,
            "Unity first-party capability catalog ready; no Codex runtime dependency",
            unity_skill_catalog(),
        )


    def unity_cli_status(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        result = unity_cli_status(
            project.root,
            timeout_seconds=float(payload.get("timeout_seconds", 60)),
        )
        result.data.setdefault("project", project.slug)
        return result

    def unity_pipeline_install(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        result = unity_install_pipeline(
            project.root,
            force=bool(payload.get("force", False)),
            timeout_seconds=float(payload.get("timeout_seconds", 240)),
        )
        result.data.setdefault("project", project.slug)
        return result

    def unity_pipeline_catalog(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        result = unity_pipeline_catalog(
            project.root,
            timeout_seconds=float(payload.get("timeout_seconds", 60)),
        )
        result.data.setdefault("project", project.slug)
        return result

    def unity_pipeline_command(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        command_name = str(payload.get("command") or "").strip()
        if not command_name:
            return ActionResult(False, "command is required")

        arguments = payload.get("arguments", [])
        if not isinstance(arguments, list) or len(arguments) > 200:
            return ActionResult(False, "arguments must be a list with at most 200 items")
        if not all(isinstance(item, (str, int, float, bool)) for item in arguments):
            return ActionResult(False, "arguments must contain only scalar values")

        result = unity_pipeline_command(
            project.root,
            command_name,
            [str(item) for item in arguments],
            timeout_seconds=float(payload.get("timeout_seconds", 120)),
        )
        result.data.setdefault("project", project.slug)
        return result

    def unity_asset_inventory(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw_terms = payload.get("terms", [])
        if isinstance(raw_terms, str):
            raw_terms = [raw_terms]
        if not isinstance(raw_terms, list) or not all(isinstance(item, str) for item in raw_terms):
            return ActionResult(False, "terms must be a string or list of strings")
        report = unity_asset_inventory(
            project.root,
            terms=raw_terms,
            max_results=int(payload.get("max_results", 500)),
        )
        return ActionResult(
            bool(report.get("exists")),
            "Unity asset inventory ready",
            {"project": project.slug, **report},
        )

    def _unity_live_inspection(
        self,
        payload: dict[str, Any],
        action: str,
        summary: str,
    ) -> ActionResult:
        editor = self._editor(payload)
        result = self._request_live_unity_editor(
            editor,
            action,
            {},
            timeout_seconds=float(payload.get("timeout_seconds", 60)),
        )
        if result is None:
            return ActionResult(
                False,
                "Unity Editor must be open for live scene inspection",
                editor.status(),
            )
        if result.ok:
            result.summary = summary
        return result

    def unity_scene_open(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw = str(payload.get("scene_path") or "").strip()
        if not raw:
            return ActionResult(False, "scene_path is required")

        scene = project.path(raw)
        if scene.suffix.lower() != ".unity":
            return ActionResult(False, "scene_path must point to a .unity scene inside the registered project")

        relative = str(scene.relative_to(project.root)).replace("\\", "/")
        editor = self._editor(payload)
        result = self._request_live_unity_editor(
            editor,
            "scene_open",
            {"scenePath": relative},
            timeout_seconds=float(payload.get("timeout_seconds", 90)),
        )
        if result is None:
            return ActionResult(False, "Unity Editor must be open to open a scene", editor.status())
        if result.ok:
            result.summary = f"Unity scene opened: {relative}"
        return result

    def unity_scene_summary(self, payload: dict[str, Any]) -> ActionResult:
        return self._unity_live_inspection(
            payload,
            "scene_summary",
            "Unity live scene summary ready",
        )

    def unity_physics_audit(self, payload: dict[str, Any]) -> ActionResult:
        return self._unity_live_inspection(
            payload,
            "physics_audit",
            "Unity physics audit passed",
        )

    def unity_benchmark_islands_generate(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        if project.unity.get("profile") != "hordax":
            return ActionResult(False, "Island benchmark generator is currently registered for the HORDAX Unity profile")

        timeout = int(payload.get("timeout_seconds", 1200))
        artifact = (
            project.root
            / "Artifacts"
            / "Unity"
            / "IslandReferenceBenchmark"
            / "island-reference.png"
        )
        report = artifact.with_suffix(".json")
        scene = project.root / "Assets" / "HORDAX" / "Scenes" / "Benchmarks" / "IslandReferenceBenchmark.unity"

        editor = self._editor(payload)
        live = self._request_live_unity_editor(
            editor,
            "benchmark_islands_generate",
            {},
            timeout_seconds=min(timeout, 600),
        )
        if live is not None:
            if not live.ok:
                return live
            if not artifact.is_file() or not report.is_file() or not scene.is_file():
                return ActionResult(
                    False,
                    "Live Unity benchmark completed but expected artifacts are missing",
                    {
                        **live.data,
                        "artifact_exists": artifact.is_file(),
                        "report_exists": report.is_file(),
                        "scene_exists": scene.is_file(),
                    },
                )
            try:
                report_data = json.loads(report.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                report_data = {}
            return ActionResult(
                True,
                "Unity island reference benchmark generated in live Editor",
                {
                    **live.data,
                    "artifact": str(artifact),
                    "snapshot_path": str(report),
                    "scene_path": str(scene),
                    "benchmark": report_data,
                    "transport": "unity-editor-companion",
                },
            )

        script = self._bridge_script("unity-run.ps1")
        execute_method = "HORDAX.EditorTools.IslandReferenceBenchmark.Generate"
        result = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ProjectPath",
                str(project.root),
                "-ExecuteMethod",
                execute_method,
            ],
            timeout=timeout,
        )
        if not result.ok:
            result.summary = "Unity island benchmark generation failed"
            return result

        if not artifact.is_file() or not report.is_file() or not scene.is_file():
            return ActionResult(
                False,
                "Unity benchmark method completed but expected artifacts are missing",
                {
                    **result.data,
                    "artifact_exists": artifact.is_file(),
                    "report_exists": report.is_file(),
                    "scene_exists": scene.is_file(),
                },
            )

        try:
            report_data = json.loads(report.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            report_data = {}

        return ActionResult(
            True,
            "Unity island reference benchmark generated",
            {
                **result.data,
                "artifact": str(artifact),
                "snapshot_path": str(report),
                "scene_path": str(scene),
                "benchmark": report_data,
                "execute_method": execute_method,
                "transport": "unity-batch",
            },
        )

    def git_status(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        return _run(["git", "-C", str(project), "status", "--short"], timeout=60)

    def git_diff(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        raw_paths = payload.get("paths", [])
        if raw_paths is None:
            raw_paths = []
        if not isinstance(raw_paths, list) or len(raw_paths) > 50:
            return ActionResult(False, "paths must be a list with at most 50 entries")

        paths: list[str] = []
        project_root = project.resolve()
        for raw in raw_paths:
            if not isinstance(raw, str) or not raw.strip():
                return ActionResult(False, "paths must contain only non-empty strings")
            candidate = (project_root / raw.strip()).resolve()
            try:
                candidate.relative_to(project_root)
            except ValueError:
                return ActionResult(False, f"path escapes project root: {raw}")
            paths.append(raw.strip().replace("\\", "/"))

        command = ["git", "-C", str(project), "diff", "--no-ext-diff", "--no-color"]
        if paths:
            command += ["--", *paths]
        result = _run(command, timeout=60)
        if result.ok:
            result.summary = "tracked Git diff inspected"
        return result

    def git_sync(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project_path(payload)
        allowed = self._project(payload).allowed_branches
        branch = payload.get("branch") or (allowed[0] if allowed else None)
        if branch not in allowed:
            return ActionResult(False, f"branch not allowed: {branch}")

        current = _run(
            ["git", "-C", str(project), "rev-parse", "--abbrev-ref", "HEAD"],
            timeout=30,
        )
        if not current.ok:
            return current
        current_branch = current.data["stdout"].strip()

        # Fetch first so we can distinguish a genuinely dirty tree from a local
        # worktree that already contains exactly the content now committed to the
        # authorized remote branch (for example after Unity CLI edits manifest.json).
        fetch = _run(
            ["git", "-C", str(project), "fetch", "--quiet", "origin", branch],
            timeout=180,
        )
        if not fetch.ok:
            return fetch

        status = _run(
            ["git", "-C", str(project), "status", "--porcelain", "--untracked-files=no"],
            timeout=60,
        )
        if not status.ok:
            return status

        tracked_status = status.data.get("stdout", "").strip()
        reconciled_remote_worktree = False
        if tracked_status:
            if current_branch != branch:
                return ActionResult(
                    False,
                    "local tracked changes exist on a different branch; sync refused",
                    {"status": tracked_status, "branch": current_branch},
                )

            changed_paths_result = _run(
                [
                    "git",
                    "-C",
                    str(project),
                    "diff",
                    "--name-only",
                    "HEAD",
                    "--",
                ],
                timeout=60,
            )
            if not changed_paths_result.ok:
                return changed_paths_result
            changed_paths = [
                line.strip()
                for line in changed_paths_result.data.get("stdout", "").splitlines()
                if line.strip()
            ]
            if not changed_paths:
                return ActionResult(
                    False,
                    "tracked status was dirty but no modified tracked paths could be resolved",
                    {"status": tracked_status},
                )

            # Compare only paths modified locally. Remote changes on other paths
            # must not make a safe reconciliation look divergent merely because
            # the local branch is behind the authorized remote branch.
            matches_remote = subprocess.run(
                [
                    "git",
                    "-C",
                    str(project),
                    "diff",
                    "--quiet",
                    f"origin/{branch}",
                    "--",
                    *changed_paths,
                ],
                capture_output=True,
                text=True,
                timeout=60,
                shell=False,
            )
            if matches_remote.returncode not in (0, 1):
                return ActionResult(
                    False,
                    "could not compare local worktree with remote branch",
                    {
                        "returncode": matches_remote.returncode,
                        "stdout": matches_remote.stdout[-4000:],
                        "stderr": matches_remote.stderr[-4000:],
                        "changed_paths": changed_paths,
                    },
                )

            ahead = _run(
                [
                    "git",
                    "-C",
                    str(project),
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"HEAD...origin/{branch}",
                ],
                timeout=30,
            )
            if not ahead.ok:
                return ahead
            try:
                local_ahead, _remote_ahead = [
                    int(value) for value in ahead.data.get("stdout", "").split()
                ]
            except (TypeError, ValueError):
                return ActionResult(
                    False,
                    "could not parse local/remote Git divergence",
                    {"stdout": ahead.data.get("stdout", "")},
                )

            if matches_remote.returncode != 0 or local_ahead != 0:
                return ActionResult(
                    False,
                    "local tracked changes differ from the authorized remote branch; sync refused",
                    {
                        "status": tracked_status,
                        "local_ahead": local_ahead,
                        "matches_remote_target": matches_remote.returncode == 0,
                        "changed_paths": changed_paths,
                    },
                )

            reset = _run(
                ["git", "-C", str(project), "reset", "--hard", f"origin/{branch}"],
                timeout=120,
            )
            if not reset.ok:
                return reset
            reconciled_remote_worktree = True

        if current_branch != branch:
            exists = _run(
                [
                    "git",
                    "-C",
                    str(project),
                    "show-ref",
                    "--verify",
                    "--quiet",
                    f"refs/heads/{branch}",
                ],
                timeout=30,
            )
            switch = (
                ["git", "-C", str(project), "switch", branch]
                if exists.ok
                else [
                    "git",
                    "-C",
                    str(project),
                    "switch",
                    "--track",
                    "-c",
                    branch,
                    f"origin/{branch}",
                ]
            )
            checkout = _run(switch, timeout=120)
            if not checkout.ok:
                return checkout

        merge = _run(
            [
                "git",
                "-C",
                str(project),
                "merge",
                "--ff-only",
                "--quiet",
                f"origin/{branch}",
            ],
            timeout=120,
        )
        if not merge.ok:
            return merge

        head = _run(["git", "-C", str(project), "rev-parse", "HEAD"], timeout=30)
        return ActionResult(
            head.ok,
            "repository synchronized" if head.ok else "sync completed but HEAD lookup failed",
            {
                "branch": branch,
                "head": head.data.get("stdout", "").strip(),
                "reconciled_remote_worktree": reconciled_remote_worktree,
            },
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

    def unity_editor_start(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        editor = self._editor(payload)

        if editor.presence_is_fresh(max_age_seconds=12.0):
            return ActionResult(True, "Unity Editor already open and companion ready", editor.status())

        stale_lock_cleared = False
        if editor.project_appears_open():
            pids = _unity_process_ids_for_project(project.root)
            if pids:
                editor.nudge_companion(wait_seconds=float(payload.get("wait_seconds", 45)))
                status = editor.status()
                status["unity_process_ids"] = pids
                return ActionResult(
                    bool(status.get("presence_fresh")),
                    "Unity Editor project is open and companion ready"
                    if status.get("presence_fresh")
                    else "Unity process is running for this project but companion is not ready",
                    status,
                )

            # A stale Temp/UnityLockfile can survive a crashed or killed batch.
            # Only remove it after verifying there is no Unity process for this project.
            try:
                editor.project_lock_path.unlink(missing_ok=True)
                stale_lock_cleared = True
            except OSError as error:
                return ActionResult(
                    False,
                    f"Unity lock appears stale but could not be cleared: {error}",
                    editor.status(),
                )

        unity = find_unity(project.root)
        if unity is None:
            return ActionResult(False, "Unity executable not found for registered project")

        command = [str(unity), "-projectPath", str(project.root)]
        popen_kwargs = {
            "cwd": str(project.root),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "shell": False,
        }
        if sys.platform == "win32":
            creationflags = 0
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            popen_kwargs["creationflags"] = creationflags
        else:
            popen_kwargs["start_new_session"] = True

        process = subprocess.Popen(command, **popen_kwargs)
        wait_seconds = max(1.0, min(240.0, float(payload.get("wait_seconds", 120))))
        deadline = time.monotonic() + wait_seconds
        status = editor.status()
        while time.monotonic() < deadline:
            status = editor.status()
            if editor.presence_is_fresh(max_age_seconds=12.0):
                return ActionResult(
                    True,
                    "Unity Editor started and OrdaX companion ready",
                    {
                        **status,
                        "launched": True,
                        "pid": process.pid,
                        "command": command,
                        "stale_lock_cleared": stale_lock_cleared,
                    },
                )
            time.sleep(0.5)

        return ActionResult(
            False,
            "Unity Editor was launched but companion did not become ready in time",
            {
                **status,
                "launched": True,
                "pid": process.pid,
                "command": command,
                "stale_lock_cleared": stale_lock_cleared,
            },
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
        wait_seconds = max(5.0, float(payload.get("wait_seconds", 45)))
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

        # Prefer the typed Editor companion. This does not focus the Unity
        # window, send keyboard shortcuts, or start a second Editor process.
        if not editor.presence_is_fresh(max_age_seconds=12.0):
            editor.nudge_companion(wait_seconds=min(wait_seconds, 15.0))

        if editor.presence_is_fresh(max_age_seconds=12.0):
            try:
                presence_before = editor.presence.stat().st_mtime
            except OSError:
                presence_before = 0.0

            refresh = editor.request(
                "refresh",
                {},
                timeout_seconds=min(max(wait_seconds, 15.0), 120.0),
            )
            if refresh is not None:
                if not refresh.ok:
                    return refresh

                deadline = time.monotonic() + wait_seconds
                status = editor.status()
                while time.monotonic() < deadline:
                    status = editor.status()
                    presence = status.get("presence") or {}
                    try:
                        presence_advanced = (
                            editor.presence.stat().st_mtime > presence_before
                        )
                    except OSError:
                        presence_advanced = False

                    ready = (
                        presence_advanced
                        and editor.presence_is_fresh(max_age_seconds=12.0)
                        and not bool(presence.get("compiling"))
                    )
                    if ready:
                        status["refresh_transport"] = "unity-editor-companion"
                        status["refresh_ack"] = refresh.data
                        return ActionResult(
                            True,
                            "Unity Editor refreshed through typed companion and scripts settled",
                            status,
                        )
                    time.sleep(0.25)

                status["refresh_transport"] = "unity-editor-companion"
                status["refresh_ack"] = refresh.data
                return ActionResult(
                    False,
                    "Unity Editor accepted the typed refresh, but scripts did not settle in time",
                    status,
                )

        # Recovery fallback for projects whose companion has not loaded yet.
        # This path may focus the Editor and send Ctrl+R; it is intentionally
        # not used when the typed companion is reachable.
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
            timeout=min(max(int(wait_seconds), 15), 60),
        )
        if not refresh.ok:
            return refresh

        deadline = time.monotonic() + wait_seconds
        editor.nudge_companion(wait_seconds=min(wait_seconds, 15.0))
        status = editor.status()
        while time.monotonic() < deadline:
            status = editor.status()
            presence = status.get("presence") or {}
            if (
                editor.presence_is_fresh(max_age_seconds=12.0)
                and not bool(presence.get("compiling"))
            ):
                status["refresh_transport"] = "foreground-shortcut-fallback"
                status["refresh_stdout"] = refresh.data.get("stdout", "")
                status["refresh_stderr"] = refresh.data.get("stderr", "")
                return ActionResult(
                    True,
                    "Unity Editor refreshed through recovery fallback and scripts settled",
                    status,
                )
            time.sleep(0.5)

        status["refresh_transport"] = "foreground-shortcut-fallback"
        status["refresh_stdout"] = refresh.data.get("stdout", "")
        status["refresh_stderr"] = refresh.data.get("stderr", "")
        return ActionResult(
            False,
            "Unity Editor refresh fallback was sent, but scripts did not settle in time",
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

    def _blender_live(self, payload: dict[str, Any]) -> BlenderLiveBridge:
        return BlenderLiveBridge(self.config, self._project(payload))

    def blender_live_start(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        live = BlenderLiveBridge(self.config, project)
        raw_blend = payload.get("blend_file") or project.blender.get("blend_file")
        blend_file = str(raw_blend) if raw_blend else None
        wait_seconds = float(
            payload.get(
                "wait_seconds",
                payload.get("timeout_seconds", 60),
            )
        )
        return live.start(
            blend_file=blend_file,
            wait_seconds=wait_seconds,
        )

    def blender_live_status(self, payload: dict[str, Any]) -> ActionResult:
        live = self._blender_live(payload)
        data = live.status()
        ready = bool(data.get("presence_fresh"))
        return ActionResult(
            ready,
            "Visible Blender live session ready"
            if ready
            else "Visible Blender live session is not running",
            data,
        )

    def blender_live_inspect(self, payload: dict[str, Any]) -> ActionResult:
        return self._blender_live(payload).request(
            "inspect",
            {"max_objects": int(payload.get("max_objects", 200))},
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_scene_snapshot(self, payload: dict[str, Any]) -> ActionResult:
        request = {
            "max_objects": int(payload.get("max_objects", 200)),
        }
        object_names = payload.get("object_names")
        if object_names is not None:
            if not isinstance(object_names, list) or not all(isinstance(name, str) for name in object_names):
                return ActionResult(False, "object_names must be a list of object names")
            request["object_names"] = object_names[:500]

        return self._blender_live(payload).request(
            "scene_snapshot",
            request,
            timeout_seconds=float(payload.get("timeout_seconds", 45)),
        )

    def blender_live_scene_reset(self, payload: dict[str, Any]) -> ActionResult:
        return self._blender_live(payload).request(
            "scene_reset",
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_object_inspect(self, payload: dict[str, Any]) -> ActionResult:
        object_name = str(payload.get("object_name") or "").strip()
        object_id = str(payload.get("ordax_object_id") or "").strip()
        if bool(object_name) == bool(object_id):
            return ActionResult(False, "provide exactly one of object_name or ordax_object_id")
        request = (
            {"object_name": object_name}
            if object_name
            else {"ordax_object_id": object_id}
        )
        return self._blender_live(payload).request(
            "object_inspect",
            request,
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )


    def blender_live_object_fingerprints(self, payload: dict[str, Any]) -> ActionResult:
        raw = payload.get("selectors")
        if not isinstance(raw, list) or not raw:
            return ActionResult(False, "selectors must be a non-empty list")
        if len(raw) > 100:
            return ActionResult(False, "fingerprint request is limited to 100 objects")

        selectors: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(raw):
            if isinstance(item, str):
                item = {"object_name": item}
            if not isinstance(item, dict):
                return ActionResult(False, f"fingerprint selector {index} must be a string or object")
            object_name = str(item.get("object_name") or "").strip()
            object_id = str(item.get("ordax_object_id") or "").strip()
            if bool(object_name) == bool(object_id):
                return ActionResult(
                    False,
                    f"fingerprint selector {index} must provide exactly one of object_name or ordax_object_id",
                )
            key = f"name:{object_name}" if object_name else f"id:{object_id}"
            if key in seen:
                return ActionResult(False, f"duplicate fingerprint selector: {key}")
            seen.add(key)
            selector = (
                {"object_name": object_name}
                if object_name
                else {"ordax_object_id": object_id}
            )
            selector["evaluated"] = bool(item.get("evaluated", True))
            selectors.append(selector)

        return self._blender_live(payload).request(
            "object_fingerprints",
            {"selectors": selectors},
            timeout_seconds=float(payload.get("timeout_seconds", 60)),
        )

    def blender_live_contact_audit(self, payload: dict[str, Any]) -> ActionResult:
        pairs = payload.get("pairs")
        if not isinstance(pairs, list) or not pairs:
            return ActionResult(False, "pairs must be a non-empty list of [object_a, object_b]")
        if len(pairs) > 200:
            return ActionResult(False, "pairs is limited to 200 object pairs")

        normalized = []
        for item in pairs:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not all(isinstance(name, str) and name.strip() for name in item)
            ):
                return ActionResult(False, "each contact pair must contain exactly two non-empty object names")
            normalized.append([item[0].strip(), item[1].strip()])

        return self._blender_live(payload).request(
            "contact_audit",
            {"pairs": normalized},
            timeout_seconds=float(payload.get("timeout_seconds", 60)),
        )


    def blender_live_quality_gate(self, payload: dict[str, Any]) -> ActionResult:
        checks = payload.get("checks")
        if not isinstance(checks, list) or not checks:
            return ActionResult(False, "checks must be a non-empty list")
        if len(checks) > 100:
            return ActionResult(False, "quality gate is limited to 100 checks")

        supported = {"dimensions", "symmetry", "proportion", "containment", "mesh_quality"}
        normalized: list[dict[str, Any]] = []
        for index, check in enumerate(checks):
            if not isinstance(check, dict):
                return ActionResult(False, f"quality check {index} must be an object")
            if any(key in check for key in ("passed", "ok", "result")):
                return ActionResult(
                    False,
                    f"quality check {index} cannot provide its own completion claim",
                )
            kind = str(check.get("type") or "").strip().lower()
            if kind not in supported:
                return ActionResult(
                    False,
                    f"quality check {index} type must be one of: {', '.join(sorted(supported))}",
                )
            normalized.append({**check, "type": kind})

        return self._blender_live(payload).request(
            "quality_gate",
            {"checks": normalized},
            timeout_seconds=float(payload.get("timeout_seconds", 60)),
        )

    def blender_live_object_transform(self, payload: dict[str, Any]) -> ActionResult:
        request: dict[str, Any] = {}
        object_name = str(payload.get("object_name") or "").strip()
        object_id = str(payload.get("ordax_object_id") or "").strip()
        if bool(object_name) == bool(object_id):
            return ActionResult(False, "provide exactly one of object_name or ordax_object_id")
        if object_name:
            request["object_name"] = object_name
        else:
            request["ordax_object_id"] = object_id

        for key in ("location", "rotation_euler", "scale", "dimensions"):
            if key not in payload:
                continue
            value = payload.get(key)
            if (
                not isinstance(value, list)
                or len(value) != 3
                or not all(isinstance(item, (int, float)) for item in value)
            ):
                return ActionResult(False, f"{key} must be a list of three numbers")
            request[key] = [float(item) for item in value]

        if not any(key in request for key in ("location", "rotation_euler", "scale", "dimensions")):
            return ActionResult(False, "at least one transform field is required")

        return self._blender_live(payload).request(
            "object_transform",
            request,
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_object_metadata(self, payload: dict[str, Any]) -> ActionResult:
        object_name = str(payload.get("object_name") or "").strip()
        object_id = str(payload.get("ordax_object_id") or "").strip()
        if bool(object_name) == bool(object_id):
            return ActionResult(False, "provide exactly one of object_name or ordax_object_id")

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict) or not metadata:
            return ActionResult(False, "metadata must be a non-empty object")

        request = {
            "metadata": metadata,
        }
        if object_name:
            request["object_name"] = object_name
        else:
            request["ordax_object_id"] = object_id

        return self._blender_live(payload).request(
            "object_metadata",
            request,
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )


    def blender_live_api_schema(self, payload: dict[str, Any]) -> ActionResult:
        type_name = str(payload.get("type_name") or "").strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", type_name):
            return ActionResult(False, "type_name must be a bpy.types class name")
        return self._blender_live(payload).request(
            "api_schema",
            {
                "type_name": type_name,
                "max_properties": int(payload.get("max_properties", 200)),
            },
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_api_lookup(self, payload: dict[str, Any]) -> ActionResult:
        query = str(payload.get("query") or "").strip()
        if not query or len(query) > 300:
            return ActionResult(
                False,
                "query is required and must be at most 300 characters",
            )
        return self._blender_live(payload).request(
            "api_lookup",
            {"query": query},
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_node_schema(self, payload: dict[str, Any]) -> ActionResult:
        node_type = str(payload.get("node_type") or "").strip()
        tree_type = str(payload.get("tree_type") or "ShaderNodeTree").strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", node_type):
            return ActionResult(False, "node_type must be a Blender node bl_idname")
        if tree_type not in {"ShaderNodeTree", "GeometryNodeTree", "CompositorNodeTree"}:
            return ActionResult(
                False,
                "tree_type must be ShaderNodeTree, GeometryNodeTree, or CompositorNodeTree",
            )
        overrides = payload.get("property_overrides") or {}
        if not isinstance(overrides, dict) or len(overrides) > 30:
            return ActionResult(
                False,
                "property_overrides must be an object with at most 30 entries",
            )
        for key, value in overrides.items():
            if (
                not isinstance(key, str)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
                or not isinstance(value, (str, int, float, bool))
            ):
                return ActionResult(
                    False,
                    "property_overrides must contain scalar values under valid property names",
                )

        return self._blender_live(payload).request(
            "node_schema",
            {
                "node_type": node_type,
                "tree_type": tree_type,
                "property_overrides": overrides,
            },
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_export(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw_output = str(payload.get("output_path") or "").strip()
        if not raw_output:
            return ActionResult(False, "output_path is required")
        output = project.path(raw_output, must_exist=False)
        export_format = str(
            payload.get("format") or output.suffix.lstrip(".")
        ).strip().lower()
        expected = {"glb": ".glb", "fbx": ".fbx"}.get(export_format)
        if expected is None:
            return ActionResult(False, "format must be glb or fbx")
        if output.suffix.lower() != expected:
            return ActionResult(False, f"output_path must end with {expected}")

        object_names = payload.get("object_names")
        if object_names is not None and (
            not isinstance(object_names, list)
            or len(object_names) > 500
            or not all(isinstance(name, str) and name.strip() for name in object_names)
        ):
            return ActionResult(
                False,
                "object_names must be a list of at most 500 object names",
            )

        request = {
            "output_path": str(output),
            "format": export_format,
            "selected_only": bool(payload.get("selected_only", False)),
            "animations": bool(payload.get("animations", True)),
            "apply_modifiers": bool(payload.get("apply_modifiers", True)),
        }
        if object_names is not None:
            request["object_names"] = [name.strip() for name in object_names]

        return self._blender_live(payload).request(
            "export_scene",
            request,
            timeout_seconds=float(payload.get("timeout_seconds", 180)),
        )


    def blender_live_checkpoint_create(self, payload: dict[str, Any]) -> ActionResult:
        label = str(payload.get("label") or "checkpoint").strip()
        return self._blender_live(payload).request(
            "checkpoint_create",
            {"label": label},
            timeout_seconds=float(payload.get("timeout_seconds", 120)),
        )

    def blender_live_checkpoint_list(self, payload: dict[str, Any]) -> ActionResult:
        return self._blender_live(payload).request(
            "checkpoint_list",
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_checkpoint_restore(self, payload: dict[str, Any]) -> ActionResult:
        checkpoint_id = str(payload.get("checkpoint_id") or "").strip()
        if not checkpoint_id:
            return ActionResult(False, "checkpoint_id is required")
        return self._blender_live(payload).request(
            "checkpoint_restore",
            {
                "checkpoint_id": checkpoint_id,
                "discard_unsaved": bool(payload.get("discard_unsaved", False)),
            },
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )

    def blender_live_trajectory(self, payload: dict[str, Any]) -> ActionResult:
        return self._blender_live(payload).trajectory(
            limit=int(payload.get("limit", 50)),
        )

    def blender_live_generation_pass(self, payload: dict[str, Any]) -> ActionResult:
        """Run one recoverable Blender generation pass in the visible session."""
        project = self._project(payload)
        raw_script = payload.get("script_path")
        if not raw_script:
            return ActionResult(False, "script_path is required")

        script = project.path(str(raw_script))
        allowed_root = project.path(
            project.blender.get("scripts_dir", "automation/blender"),
            must_exist=False,
        ).resolve()
        try:
            script.relative_to(allowed_root)
        except ValueError:
            return ActionResult(
                False,
                f"Blender live script must be inside {allowed_root}",
            )
        if script.suffix.lower() != ".py":
            return ActionResult(False, "Blender live script must be a .py file")

        pairs = payload.get("contact_pairs", [])
        if pairs is None:
            pairs = []
        if not isinstance(pairs, list) or len(pairs) > 200:
            return ActionResult(False, "contact_pairs must be a list with at most 200 pairs")
        normalized_pairs = []
        for item in pairs:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not all(isinstance(name, str) and name.strip() for name in item)
            ):
                return ActionResult(
                    False,
                    "each contact pair must contain exactly two non-empty object names",
                )
            normalized_pairs.append([item[0].strip(), item[1].strip()])


        raw_quality_checks = payload.get("quality_checks", [])
        if raw_quality_checks is None:
            raw_quality_checks = []
        if not isinstance(raw_quality_checks, list) or len(raw_quality_checks) > 100:
            return ActionResult(
                False,
                "quality_checks must be a list with at most 100 checks",
            )
        supported_quality_types = {"dimensions", "symmetry", "proportion", "containment", "mesh_quality"}
        quality_checks: list[dict[str, Any]] = []
        for index, check in enumerate(raw_quality_checks):
            if not isinstance(check, dict):
                return ActionResult(False, f"quality check {index} must be an object")
            if any(key in check for key in ("passed", "ok", "result")):
                return ActionResult(
                    False,
                    f"quality check {index} cannot provide its own completion claim",
                )
            kind = str(check.get("type") or "").strip().lower()
            if kind not in supported_quality_types:
                return ActionResult(
                    False,
                    f"quality check {index} type must be one of: {', '.join(sorted(supported_quality_types))}",
                )
            quality_checks.append({**check, "type": kind})



        raw_protected = payload.get("protected_objects", [])
        if raw_protected is None:
            raw_protected = []
        if not isinstance(raw_protected, list) or len(raw_protected) > 100:
            return ActionResult(
                False,
                "protected_objects must be a list with at most 100 selectors",
            )
        protected_objects: list[dict[str, Any]] = []
        protected_keys: set[str] = set()
        for index, item in enumerate(raw_protected):
            if isinstance(item, str):
                item = {"object_name": item}
            if not isinstance(item, dict):
                return ActionResult(
                    False,
                    f"protected object {index} must be a string or object",
                )
            object_name = str(item.get("object_name") or "").strip()
            object_id = str(item.get("ordax_object_id") or "").strip()
            if bool(object_name) == bool(object_id):
                return ActionResult(
                    False,
                    f"protected object {index} must provide exactly one of object_name or ordax_object_id",
                )
            key = f"name:{object_name}" if object_name else f"id:{object_id}"
            if key in protected_keys:
                return ActionResult(False, f"duplicate protected object: {key}")
            protected_keys.add(key)
            selector = (
                {"object_name": object_name}
                if object_name
                else {"ordax_object_id": object_id}
            )
            selector["evaluated"] = bool(item.get("evaluated", True))
            protected_objects.append(selector)

        if protected_objects and bool(payload.get("reset_scene", False)):
            return ActionResult(
                False,
                "protected_objects cannot be used with reset_scene=true",
            )


        raw_multiview = payload.get("multiview", False)
        if raw_multiview not in (None, False, True) and not isinstance(raw_multiview, dict):
            return ActionResult(
                False,
                "multiview must be false, true, or an options object",
            )
        multiview_options: dict[str, Any] | None = None
        if raw_multiview is True:
            multiview_options = {}
        elif isinstance(raw_multiview, dict):
            multiview_options = dict(raw_multiview)

        save_target = None
        raw_save_target = payload.get("save_target_path")
        if raw_save_target:
            save_target = project.path(str(raw_save_target), must_exist=False)
            if save_target.suffix.lower() != ".blend":
                return ActionResult(False, "save_target_path must be a .blend file")

        raw_extra_artifacts = payload.get("collect_artifacts", [])
        if raw_extra_artifacts is None:
            raw_extra_artifacts = []
        if not isinstance(raw_extra_artifacts, list) or len(raw_extra_artifacts) > 24:
            return ActionResult(False, "collect_artifacts must be a list with at most 24 entries")

        extra_artifacts: list[tuple[Path, str]] = []
        allowed_artifact_suffixes = {
            ".png", ".jpg", ".jpeg", ".json", ".glb", ".gltf", ".fbx", ".blend"
        }
        for item in raw_extra_artifacts:
            if isinstance(item, str):
                raw_path = item
                kind = "blender-generated-artifact"
            elif isinstance(item, dict):
                raw_path = str(item.get("path") or "").strip()
                kind = str(item.get("kind") or "blender-generated-artifact").strip()
            else:
                return ActionResult(
                    False,
                    "collect_artifacts entries must be paths or {path, kind} objects",
                )
            if not raw_path:
                return ActionResult(False, "collect_artifacts contains an empty path")
            artifact_path = project.path(raw_path, must_exist=False)
            if artifact_path.suffix.lower() not in allowed_artifact_suffixes:
                return ActionResult(
                    False,
                    f"unsupported collected artifact type: {artifact_path.suffix}",
                )
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", kind):
                return ActionResult(False, "collect_artifacts kind contains unsupported characters")
            extra_artifacts.append((artifact_path, kind))

        live = BlenderLiveBridge(self.config, project)
        phases: dict[str, Any] = {}
        rollback_on_failure = bool(payload.get("rollback_on_failure", True))
        timeout = float(payload.get("timeout_seconds", 300))

        checkpoint = live.request(
            "checkpoint_create",
            {"label": str(payload.get("label") or script.stem)},
            timeout_seconds=min(timeout, 120),
        )
        phases["checkpoint"] = {
            "ok": checkpoint.ok,
            "summary": checkpoint.summary,
            "data": checkpoint.data,
        }
        if not checkpoint.ok:
            return ActionResult(
                False,
                "Blender generation pass could not create a checkpoint",
                {"phases": phases},
            )

        checkpoint_data = checkpoint.data.get("checkpoint") or {}
        checkpoint_id = str(checkpoint_data.get("id") or "").strip()

        if bool(payload.get("reset_scene", False)):
            reset = live.request(
                "scene_reset",
                timeout_seconds=min(timeout, 30),
            )
            phases["scene_reset"] = {
                "ok": reset.ok,
                "summary": reset.summary,
                "data": reset.data,
            }
            if not reset.ok:
                return ActionResult(
                    False,
                    "Blender generation pass could not reset the scene",
                    {
                        "checkpoint_id": checkpoint_id,
                        "phases": phases,
                    },
                )

        def fail(summary: str, failed: ActionResult | None = None) -> ActionResult:
            if failed is not None:
                phases["failure"] = {
                    "ok": failed.ok,
                    "summary": failed.summary,
                    "data": failed.data,
                }
            if rollback_on_failure and checkpoint_id:
                rollback = live.request(
                    "checkpoint_restore",
                    {
                        "checkpoint_id": checkpoint_id,
                        "discard_unsaved": True,
                    },
                    timeout_seconds=30,
                )
                phases["rollback"] = {
                    "ok": rollback.ok,
                    "summary": rollback.summary,
                    "data": rollback.data,
                }
            return ActionResult(
                False,
                summary,
                {
                    "checkpoint_id": checkpoint_id,
                    "rollback_requested": rollback_on_failure,
                    "phases": phases,
                },
            )


        protected_before: dict[str, Any] = {}
        if protected_objects:
            before_lock = live.request(
                "object_fingerprints",
                {"selectors": protected_objects},
                timeout_seconds=min(timeout, 120),
            )
            phases["protected_before"] = {
                "ok": before_lock.ok,
                "summary": before_lock.summary,
                "data": before_lock.data,
            }
            if not before_lock.ok:
                return fail(
                    "Blender protected-object baseline could not be captured",
                    before_lock,
                )
            for entry in before_lock.data.get("fingerprints", []):
                key = str(entry.get("selector_key") or "")
                if key:
                    protected_before[key] = entry

        generated = live.request(
            "run_script",
            {"script_path": str(script)},
            timeout_seconds=timeout,
        )
        phases["generation"] = {
            "ok": generated.ok,
            "summary": generated.summary,
            "data": generated.data,
        }
        if not generated.ok:
            return fail("Blender generation script failed; pass rejected")


        if protected_objects:
            after_lock = live.request(
                "object_fingerprints",
                {"selectors": protected_objects},
                timeout_seconds=min(timeout, 120),
            )
            phases["protected_after"] = {
                "ok": after_lock.ok,
                "summary": after_lock.summary,
                "data": after_lock.data,
            }
            if not after_lock.ok:
                return fail(
                    "A protected Blender object is missing or cannot be fingerprinted",
                    after_lock,
                )

            protected_after = {
                str(entry.get("selector_key") or ""): entry
                for entry in after_lock.data.get("fingerprints", [])
                if str(entry.get("selector_key") or "")
            }
            changed = []
            for key, before_entry in protected_before.items():
                after_entry = protected_after.get(key)
                if after_entry is None:
                    changed.append({
                        "selector_key": key,
                        "reason": "missing_after_generation",
                    })
                    continue
                if before_entry.get("combined_sha256") != after_entry.get("combined_sha256"):
                    changed.append({
                        "selector_key": key,
                        "reason": "fingerprint_changed",
                        "before": {
                            "object_name": before_entry.get("object_name"),
                            "transform_sha256": before_entry.get("transform_sha256"),
                            "geometry_sha256": before_entry.get("geometry_sha256"),
                            "combined_sha256": before_entry.get("combined_sha256"),
                        },
                        "after": {
                            "object_name": after_entry.get("object_name"),
                            "transform_sha256": after_entry.get("transform_sha256"),
                            "geometry_sha256": after_entry.get("geometry_sha256"),
                            "combined_sha256": after_entry.get("combined_sha256"),
                        },
                    })

            phases["protected_objects"] = {
                "ok": not changed,
                "protected_count": len(protected_before),
                "changed_count": len(changed),
                "changed": changed,
            }
            if changed:
                return fail(
                    "Blender generation modified protected approved objects; pass rejected",
                    ActionResult(
                        False,
                        "protected object fingerprint changed",
                        {"changed": changed},
                    ),
                )

        snapshot = live.request(
            "scene_snapshot",
            {"max_objects": int(payload.get("max_objects", 300))},
            timeout_seconds=min(timeout, 60),
        )
        phases["snapshot"] = {
            "ok": snapshot.ok,
            "summary": snapshot.summary,
            "data": snapshot.data,
        }
        if not snapshot.ok:
            return fail("Blender rich snapshot failed; pass rejected")

        if normalized_pairs:
            audit = live.request(
                "contact_audit",
                {"pairs": normalized_pairs},
                timeout_seconds=min(timeout, 120),
            )
            phases["contact_audit"] = {
                "ok": audit.ok,
                "summary": audit.summary,
                "data": audit.data,
            }
            if not audit.ok:
                return fail(
                    "Blender contact audit failed; pass rejected and rollback requested",
                )


        if quality_checks:
            quality = live.request(
                "quality_gate",
                {"checks": quality_checks},
                timeout_seconds=min(timeout, 120),
            )
            phases["quality_gate"] = {
                "ok": quality.ok,
                "summary": quality.summary,
                "data": quality.data,
            }
            if not quality.ok:
                return fail(
                    "Blender deterministic quality gate failed; pass rejected",
                    quality,
                )


        if multiview_options is not None:
            multiview_payload = {
                **multiview_options,
                "project": project.slug,
                "timeout_seconds": min(timeout, 240),
            }
            multiview = self.blender_live_multiview_capture(multiview_payload)
            phases["multiview"] = {
                "ok": multiview.ok,
                "summary": multiview.summary,
                "data": multiview.data,
            }
            if not multiview.ok and bool(
                multiview_options.get("required", True)
            ):
                return fail(
                    "Blender deterministic multiview capture failed; pass rejected",
                    multiview,
                )

        artifact = None
        if bool(payload.get("capture", True)):
            output = self._capture_output(payload, "blender-generation-pass.png")
            capture = live.request(
                "capture_viewport",
                {"output_path": str(output)},
                timeout_seconds=min(timeout, 120),
            )
            phases["capture"] = {
                "ok": capture.ok,
                "summary": capture.summary,
                "data": capture.data,
            }
            if not capture.ok or not output.is_file() or output.stat().st_size == 0:
                if bool(payload.get("capture_required", True)):
                    return fail("Blender viewport capture failed; pass rejected")
            else:
                artifact = str(output)
                self._record_capture(payload, output)

        if save_target is not None:
            saved = live.request(
                "save",
                {"target_path": str(save_target)},
                timeout_seconds=min(timeout, 120),
            )
            phases["save"] = {
                "ok": saved.ok,
                "summary": saved.summary,
                "data": saved.data,
            }
            if not saved.ok:
                return fail("Blender final save failed; pass rejected")

        collected_artifacts = []
        missing_artifacts = []
        for artifact_path, kind in extra_artifacts:
            if artifact_path.is_file() and artifact_path.stat().st_size > 0:
                collected_artifacts.append({
                    "path": str(artifact_path),
                    "kind": kind,
                    "size_bytes": artifact_path.stat().st_size,
                })
            else:
                missing_artifacts.append(str(artifact_path))

        if missing_artifacts and bool(payload.get("collect_artifacts_required", True)):
            return fail(
                "Blender declared artifacts are missing; pass rejected",
                ActionResult(
                    False,
                    "missing declared Blender artifacts",
                    {"missing_artifacts": missing_artifacts},
                ),
            )

        return ActionResult(
            True,
            "Blender generation pass accepted",
            {
                "checkpoint_id": checkpoint_id,
                "script_path": str(script),
                "artifact": artifact,
                "artifacts": collected_artifacts,
                "missing_artifacts": missing_artifacts,
                "save_target_path": str(save_target) if save_target else None,
                "phases": phases,
            },
        )

    def blender_live_result(self, payload: dict[str, Any]) -> ActionResult:
        command_id = str(payload.get("command_id") or "").strip()
        if not command_id:
            return ActionResult(False, "command_id is required")
        return self._blender_live(payload).result(command_id)

    def blender_live_run_script(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw_script = payload.get("script_path")
        if not raw_script:
            return ActionResult(False, "script_path is required")

        script = project.path(str(raw_script))
        allowed_root = project.path(
            project.blender.get("scripts_dir", "automation/blender"),
            must_exist=False,
        ).resolve()
        try:
            script.relative_to(allowed_root)
        except ValueError:
            return ActionResult(
                False,
                f"Blender live script must be inside {allowed_root}",
            )
        if script.suffix.lower() != ".py":
            return ActionResult(False, "Blender live script must be a .py file")

        return BlenderLiveBridge(self.config, project).request(
            "run_script",
            {"script_path": str(script)},
            timeout_seconds=float(payload.get("timeout_seconds", 300)),
        )

    def blender_live_capture(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        live = BlenderLiveBridge(self.config, project)
        output = self._capture_output(payload, "blender-live.png")
        result = live.request(
            "capture_viewport",
            {"output_path": str(output)},
            timeout_seconds=float(payload.get("timeout_seconds", 120)),
        )
        if not result.ok:
            return result

        if output.is_file():
            result.data["artifact"] = str(output)
            result.data["sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()

            snapshot_path = output.with_suffix(".json")
            snapshot = result.data.get("snapshot")
            if isinstance(snapshot, dict):
                snapshot_path.write_text(
                    json.dumps(snapshot, indent=2),
                    encoding="utf-8",
                )
                result.data["snapshot_path"] = str(snapshot_path)

            self._record_capture(payload, output)

        return result


    def blender_live_multiview_capture(self, payload: dict[str, Any]) -> ActionResult:
        views = payload.get(
            "views",
            ["front", "back", "left", "right", "top", "three_quarter"],
        )
        supported = {
            "front",
            "back",
            "left",
            "right",
            "top",
            "bottom",
            "three_quarter",
            "three_quarter_back",
        }
        if (
            not isinstance(views, list)
            or not views
            or len(views) > len(supported)
        ):
            return ActionResult(False, "views must be a non-empty bounded list")
        normalized_views: list[str] = []
        for raw in views:
            view = str(raw or "").strip().lower()
            if view not in supported:
                return ActionResult(
                    False,
                    f"unsupported multiview view: {view}",
                    {"supported_views": sorted(supported)},
                )
            if view in normalized_views:
                return ActionResult(False, "multiview views must be unique")
            normalized_views.append(view)

        object_names = payload.get("object_names")
        if object_names is not None and (
            not isinstance(object_names, list)
            or not object_names
            or len(object_names) > 200
            or not all(isinstance(name, str) and name.strip() for name in object_names)
        ):
            return ActionResult(
                False,
                "object_names must be a non-empty list of at most 200 object names",
            )

        try:
            width = int(payload.get("width", 768))
            height = int(payload.get("height", 768))
            margin = float(payload.get("margin", 1.15))
        except (TypeError, ValueError):
            return ActionResult(False, "width, height and margin must be numeric")
        if width < 128 or width > 4096 or height < 128 or height > 4096:
            return ActionResult(
                False,
                "multiview resolution must be between 128 and 4096",
            )
        if margin < 1.0 or margin > 3.0:
            return ActionResult(False, "multiview margin must be between 1.0 and 3.0")

        project = self._project(payload)
        live = BlenderLiveBridge(self.config, project)
        anchor = self._capture_output(payload, "multiview.json")
        request: dict[str, Any] = {
            "output_dir": str(anchor.parent),
            "views": normalized_views,
            "width": width,
            "height": height,
            "margin": margin,
        }
        if object_names is not None:
            request["object_names"] = [name.strip() for name in object_names]

        result = live.request(
            "multiview_capture",
            request,
            timeout_seconds=float(payload.get("timeout_seconds", 240)),
        )
        if not result.ok:
            return result

        primary = result.data.get("primary_artifact")
        if primary:
            primary_path = Path(str(primary)).resolve()
            manifest_path = primary_path.with_suffix(".json")
            manifest_path.write_text(
                json.dumps(result.data, indent=2),
                encoding="utf-8",
            )
            result.data["primary_snapshot_path"] = str(manifest_path)
            self._record_capture(payload, primary_path)

        return result

    def blender_live_save(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        raw_target = payload.get("target_path")
        data: dict[str, Any] = {}
        if raw_target:
            target = project.path(str(raw_target), must_exist=False)
            if target.suffix.lower() != ".blend":
                return ActionResult(False, "target_path must be a .blend file")
            data["target_path"] = str(target)

        return BlenderLiveBridge(self.config, project).request(
            "save",
            data,
            timeout_seconds=float(payload.get("timeout_seconds", 120)),
        )

    def blender_live_stop(self, payload: dict[str, Any]) -> ActionResult:
        return self._blender_live(payload).request(
            "quit",
            timeout_seconds=float(payload.get("timeout_seconds", 30)),
        )


    def blender_multiview_compare(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        artifact_root = (
            self.config.state_dir / "artifacts" / project.slug
        ).resolve()

        def resolve_manifest(value: Any, field: str) -> Path:
            raw = str(value or "").strip()
            if not raw:
                raise ValueError(f"{field} is required")
            candidate = Path(raw).expanduser()
            path = (
                candidate
                if candidate.is_absolute()
                else artifact_root / candidate
            ).resolve()
            if not path.is_relative_to(artifact_root):
                raise ValueError(f"{field} must be inside the project artifact root")
            if path.suffix.lower() != ".json" or not path.is_file():
                raise FileNotFoundError(path)
            return path

        try:
            baseline_path = resolve_manifest(
                payload.get("baseline_manifest_path"),
                "baseline_manifest_path",
            )
            candidate_path = resolve_manifest(
                payload.get("candidate_manifest_path"),
                "candidate_manifest_path",
            )
        except (ValueError, FileNotFoundError) as error:
            return ActionResult(False, f"{type(error).__name__}: {error}")

        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
            candidate = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            return ActionResult(False, f"invalid multiview manifest: {error}")

        def manifest_views(data: Any, label: str) -> dict[str, dict[str, Any]]:
            if not isinstance(data, dict):
                raise ValueError(f"{label} manifest must contain an object")
            raw_views = data.get("views")
            if not isinstance(raw_views, list) or not raw_views:
                raise ValueError(f"{label} manifest contains no views")
            result: dict[str, dict[str, Any]] = {}
            for index, entry in enumerate(raw_views):
                if not isinstance(entry, dict):
                    raise ValueError(f"{label} view {index} must be an object")
                view = str(entry.get("view") or "").strip()
                artifact = str(entry.get("artifact") or "").strip()
                if not view or not artifact:
                    raise ValueError(
                        f"{label} view {index} needs view and artifact"
                    )
                if view in result:
                    raise ValueError(f"{label} manifest duplicates view: {view}")
                result[view] = entry
            return result

        try:
            baseline_views = manifest_views(baseline, "baseline")
            candidate_views = manifest_views(candidate, "candidate")
        except ValueError as error:
            return ActionResult(False, str(error))

        baseline_names = set(baseline_views)
        candidate_names = set(candidate_views)
        if baseline_names != candidate_names and bool(
            payload.get("require_same_views", True)
        ):
            return ActionResult(
                False,
                "multiview manifests do not contain the same view set",
                {
                    "baseline_only": sorted(baseline_names - candidate_names),
                    "candidate_only": sorted(candidate_names - baseline_names),
                },
            )
        common_views = sorted(baseline_names & candidate_names)
        if not common_views:
            return ActionResult(False, "multiview manifests have no common views")

        try:
            max_mae_raw = payload.get("max_mae")
            max_changed_raw = payload.get("max_changed_ratio")
            max_mae = float(max_mae_raw) if max_mae_raw is not None else None
            max_changed = (
                float(max_changed_raw) if max_changed_raw is not None else None
            )
        except (TypeError, ValueError):
            return ActionResult(
                False,
                "max_mae and max_changed_ratio must be numbers",
            )
        for field, value in (
            ("max_mae", max_mae),
            ("max_changed_ratio", max_changed),
        ):
            if value is not None and (value < 0.0 or value > 1.0):
                return ActionResult(False, f"{field} must be between 0 and 1")

        try:
            from PIL import Image, ImageChops, ImageStat
        except ImportError:
            return ActionResult(False, "Pillow is required for multiview comparison")

        comparison_root = self._capture_output(
            payload,
            "multiview-comparison.json",
        ).parent

        def resolve_artifact(entry: dict[str, Any], label: str, view: str) -> Path:
            raw = str(entry.get("artifact") or "").strip()
            path = Path(raw).expanduser().resolve()
            if not path.is_relative_to(artifact_root):
                raise ValueError(
                    f"{label} artifact for {view} escaped project artifact root"
                )
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg"} or not path.is_file():
                raise FileNotFoundError(path)
            return path

        comparisons = []
        failed_views = []
        write_diffs = bool(payload.get("write_diff_images", True))
        require_same_resolution = bool(payload.get("require_same_resolution", True))

        try:
            for view in common_views:
                baseline_image_path = resolve_artifact(
                    baseline_views[view],
                    "baseline",
                    view,
                )
                candidate_image_path = resolve_artifact(
                    candidate_views[view],
                    "candidate",
                    view,
                )
                with (
                    Image.open(baseline_image_path) as baseline_image_raw,
                    Image.open(candidate_image_path) as candidate_image_raw,
                ):
                    baseline_image = baseline_image_raw.convert("RGB")
                    candidate_image = candidate_image_raw.convert("RGB")
                    if baseline_image.size != candidate_image.size:
                        if require_same_resolution:
                            return ActionResult(
                                False,
                                f"multiview resolution differs for {view}",
                                {
                                    "view": view,
                                    "baseline_size": list(baseline_image.size),
                                    "candidate_size": list(candidate_image.size),
                                },
                            )
                        candidate_image = candidate_image.resize(
                            baseline_image.size,
                            Image.Resampling.LANCZOS,
                        )

                    difference = ImageChops.difference(
                        baseline_image,
                        candidate_image,
                    )
                    stats = ImageStat.Stat(difference)
                    channel_mean = [float(value) / 255.0 for value in stats.mean]
                    channel_rms = [float(value) / 255.0 for value in stats.rms]
                    mae = sum(channel_mean) / len(channel_mean)
                    rms = sum(channel_rms) / len(channel_rms)

                    gray = difference.convert("L")
                    histogram = gray.histogram()
                    total_pixels = baseline_image.size[0] * baseline_image.size[1]
                    unchanged = int(histogram[0]) if histogram else 0
                    changed_ratio = (
                        (total_pixels - unchanged) / total_pixels
                        if total_pixels
                        else 0.0
                    )

                    view_passed = True
                    if max_mae is not None and mae > max_mae:
                        view_passed = False
                    if max_changed is not None and changed_ratio > max_changed:
                        view_passed = False

                    diff_path = None
                    if write_diffs:
                        diff_path = comparison_root / f"{view}-diff.png"
                        difference.save(diff_path, format="PNG")

                    record = {
                        "view": view,
                        "passed": view_passed,
                        "mae": round(mae, 8),
                        "rms": round(rms, 8),
                        "changed_pixel_ratio": round(changed_ratio, 8),
                        "baseline_artifact": str(baseline_image_path),
                        "candidate_artifact": str(candidate_image_path),
                        "diff_artifact": str(diff_path) if diff_path else None,
                        "resolution": list(baseline_image.size),
                    }
                    comparisons.append(record)
                    if not view_passed:
                        failed_views.append(view)
        except (OSError, ValueError, FileNotFoundError) as error:
            return ActionResult(False, f"{type(error).__name__}: {error}")

        def vector3(data: Any, field: str) -> list[float] | None:
            raw = data.get("bounds", {}).get(field) if isinstance(data, dict) else None
            if (
                isinstance(raw, list)
                and len(raw) == 3
                and all(isinstance(value, (int, float)) for value in raw)
            ):
                return [float(value) for value in raw]
            return None

        baseline_dimensions = vector3(baseline, "dimensions")
        candidate_dimensions = vector3(candidate, "dimensions")
        baseline_center = vector3(baseline, "center")
        candidate_center = vector3(candidate, "center")
        dimension_error = None
        center_error = None
        if baseline_dimensions and candidate_dimensions:
            dimension_error = [
                round(abs(candidate_dimensions[i] - baseline_dimensions[i]), 8)
                for i in range(3)
            ]
        if baseline_center and candidate_center:
            center_error = [
                round(abs(candidate_center[i] - baseline_center[i]), 8)
                for i in range(3)
            ]

        thresholds_declared = max_mae is not None or max_changed is not None
        comparison_passed = not failed_views if thresholds_declared else None
        report = {
            "baseline_manifest": str(baseline_path),
            "candidate_manifest": str(candidate_path),
            "views": comparisons,
            "view_count": len(comparisons),
            "thresholds": {
                "max_mae": max_mae,
                "max_changed_ratio": max_changed,
            },
            "comparison_passed": comparison_passed,
            "failed_views": failed_views,
            "bounds": {
                "baseline_dimensions": baseline_dimensions,
                "candidate_dimensions": candidate_dimensions,
                "absolute_dimension_error": dimension_error,
                "baseline_center": baseline_center,
                "candidate_center": candidate_center,
                "absolute_center_error": center_error,
            },
        }
        report_path = comparison_root / "multiview-comparison.json"
        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        report["report"] = str(report_path)

        if thresholds_declared and failed_views:
            return ActionResult(
                False,
                "Multiview comparison exceeded declared thresholds",
                report,
            )
        return ActionResult(
            True,
            "Multiview comparison complete",
            report,
        )

    def blender_asset_search(self, payload: dict[str, Any]) -> ActionResult:
        provider = str(payload.get("provider") or "polyhaven").strip().lower()
        if provider != "polyhaven":
            return ActionResult(False, "supported asset provider: polyhaven")
        try:
            report = search_polyhaven(
                query=str(payload.get("query") or ""),
                asset_type=str(payload.get("asset_type") or "all"),
                categories=(
                    str(payload.get("categories")).strip()
                    if payload.get("categories") is not None
                    else None
                ),
                limit=int(payload.get("limit", 20)),
                timeout_seconds=float(payload.get("timeout_seconds", 30)),
            )
        except Exception as error:
            return ActionResult(False, f"Poly Haven search failed: {type(error).__name__}: {error}")
        return ActionResult(True, "Poly Haven asset search ready", report)

    def blender_asset_manifest(self, payload: dict[str, Any]) -> ActionResult:
        provider = str(payload.get("provider") or "polyhaven").strip().lower()
        if provider != "polyhaven":
            return ActionResult(False, "supported asset provider: polyhaven")
        asset_id = str(payload.get("asset_id") or "").strip()
        if not asset_id:
            return ActionResult(False, "asset_id is required")
        try:
            report = polyhaven_file_manifest(
                asset_id,
                timeout_seconds=float(payload.get("timeout_seconds", 30)),
            )
        except Exception as error:
            return ActionResult(False, f"Poly Haven manifest failed: {type(error).__name__}: {error}")
        return ActionResult(True, "Poly Haven file manifest ready", report)

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

        command = [str(blender), "--background", "--factory-startup", "--disable-autoexec"]
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
