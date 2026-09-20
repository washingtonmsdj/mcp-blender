"""Unity-specific typed actions composed into the central ActionRegistry.

The mixin owns Unity CLI/editor/play/capture behavior but does not register any
remote action by itself. The central ActionRegistry remains the allow-list.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcp_blender_unity.config import find_unity

from .models import ActionResult
from .process_runner import run_command as _run
from .unity_assets import (
    asset_inventory as unity_asset_inventory,
    import_project_asset as unity_import_project_asset,
)
from .unity_cli import (
    cli_status as unity_cli_status,
    install_pipeline as unity_install_pipeline,
    pipeline_catalog as unity_pipeline_catalog,
    pipeline_command as unity_pipeline_command,
)
from .unity_editor_bridge import UnityEditorBridge
from .unity_knowledge import (
    capability_report as unity_capability_report,
    project_profile as unity_project_profile,
    skill_catalog as unity_skill_catalog,
)


def _unity_editor_log_candidates(project: Path) -> list[Path]:
    project_log = project.resolve() / "Logs" / "Editor.log"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        global_log = base / "Unity" / "Editor" / "Editor.log"
    elif sys.platform == "darwin":
        global_log = Path.home() / "Library" / "Logs" / "Unity" / "Editor.log"
    else:
        global_log = Path.home() / ".config" / "unity3d" / "Editor.log"
    return [project_log, global_log]


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


class UnityActions:
    def _editor(self, payload: dict[str, Any]) -> UnityEditorBridge:
        project = self._project(payload)
        source = project.unity.get("companion_source")
        if source:
            source = project.path(source, must_exist=False)
        elif project.unity.get("profile") == "hordax":
            source = project.path(
                "Assets/HORDAX/Editor/OrdaXEditorAgent.cs",
                must_exist=False,
            )
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

    def unity_asset_import(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        source_raw = str(payload.get("source_path") or "").strip()
        destination_raw = str(payload.get("destination_path") or "").strip()
        if not source_raw or not destination_raw:
            return ActionResult(False, "source_path and destination_path are required")

        try:
            source = project.path(source_raw)
            destination = project.path(destination_raw, must_exist=False)
            assets_root = (project.root / "Assets").resolve()
            destination.resolve().relative_to(assets_root)
        except (ValueError, FileNotFoundError) as error:
            return ActionResult(False, str(error))

        try:
            report = unity_import_project_asset(
                project.root,
                source_path=source,
                destination_path=destination,
                overwrite=bool(payload.get("overwrite", False)),
            )
        except (ValueError, FileNotFoundError, FileExistsError, OSError) as error:
            return ActionResult(False, f"{type(error).__name__}: {error}")

        return ActionResult(
            True,
            "Unity project asset imported" if report.get("imported") else "Unity project asset already current",
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

    def unity_spatial_audit(self, payload: dict[str, Any]) -> ActionResult:
        return self._unity_live_inspection(
            payload,
            "spatial_audit",
            "Unity spatial audit completed",
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
        # Status is intentionally observational. A read-only health probe must
        # never touch project files, wait for Unity imports, focus the Editor, or
        # mutate Editor state. Use unity.refresh_editor for active recovery.
        editor = self._editor(payload)
        status = editor.status()
        ready = bool(status.get("presence_fresh"))
        return ActionResult(
            ready,
            "Unity Editor companion ready" if ready else "Unity Editor companion not ready",
            status,
        )

    def unity_editor_diagnostics(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        editor = self._editor(payload)
        process_ids = _unity_process_ids_for_project(project.root)

        log_candidates = _unity_editor_log_candidates(project.root)
        log_path = next((path for path in log_candidates if path.is_file()), log_candidates[-1])

        max_lines = max(20, min(int(payload.get("max_lines", 160)), 500))
        max_chars = max(4096, min(int(payload.get("max_chars", 60000)), 200000))
        tail = ""
        log_size = None
        log_mtime = None
        if log_path.is_file():
            try:
                log_size = log_path.stat().st_size
                log_mtime = log_path.stat().st_mtime
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                tail = "\n".join(lines[-max_lines:])
                if len(tail) > max_chars:
                    tail = tail[-max_chars:]
            except OSError as error:
                tail = f"<could not read Unity Editor.log: {error}>"

        status = editor.status()
        data = {
            **status,
            "unity_process_ids": process_ids,
            "editor_log_path": str(log_path),
            "editor_log_candidates": [str(path) for path in log_candidates],
            "editor_log_source": "project" if log_path == log_candidates[0] else "global",
            "editor_log_exists": log_path.is_file(),
            "editor_log_size_bytes": log_size,
            "editor_log_mtime": log_mtime,
            "editor_log_tail": tail,
        }
        return ActionResult(
            True,
            "Unity Editor diagnostics ready",
            data,
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


