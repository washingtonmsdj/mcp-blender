from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import threading
import re
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable

from .config import AgentConfig
from .models import ActionResult
from .blender_live_bridge import BlenderLiveBridge
from .projects import load_projects, Project
from .observations import ObservationActions
from .references import ReferenceActions
from .blender_actions import BlenderActions
from .unity_actions import UnityActions
from .process_runner import run_command as _run
from .execution_lock import ExecutionLock


Action = Callable[[dict[str, Any]], ActionResult]


class ActionRegistry(ObservationActions, ReferenceActions, BlenderActions, UnityActions):
    """Strict allow-list. No arbitrary remote shell command is accepted."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.projects = load_projects(config)
        self.on_observation = None
        self._execution_lock = threading.Lock()
        self._actions: dict[str, Action] = {
            "projects.list": self.projects_list,
            "project.observe": self.project_observe,
            "project.references": self.project_references,
            "project.reference_images": self.project_reference_images,
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
            "blender.export_headless": self.blender_export_headless,
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
            "blender.reference_review": self.blender_reference_review,
            "blender.reference_generation_pass": self.blender_reference_generation_pass,
            "blender.reference_decision": self.blender_reference_decision,
            "unity.install_companion": self.unity_install_companion,
            "unity.project_profile": self.unity_project_profile,
            "unity.capabilities": self.unity_capabilities,
            "unity.skill_catalog": self.unity_skill_catalog,
            "unity.cli_status": self.unity_cli_status,
            "unity.pipeline_install": self.unity_pipeline_install,
            "unity.pipeline_catalog": self.unity_pipeline_catalog,
            "unity.pipeline_command": self.unity_pipeline_command,
            "unity.asset_inventory": self.unity_asset_inventory,
            "unity.asset_import": self.unity_asset_import,
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
            "unity.editor_diagnostics": self.unity_editor_diagnostics,
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

        branch = "main"
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
