"""Unified project preview actions for ORDAX Studio."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import urllib.request
import subprocess
from pathlib import Path
from typing import Any

from .models import ActionResult

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class PreviewActions:
    def _latest_preview_image(self, project) -> dict[str, Any] | None:
        roots = (
            ("managed", (self.config.state_dir / "artifacts" / project.slug).resolve()),
            ("project", (project.root / "Artifacts").resolve()),
        )
        latest: tuple[int, Path, str, Path] | None = None
        for source, root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                candidate = (stat.st_mtime_ns, path.resolve(), source, root)
                if latest is None or candidate[0] > latest[0]:
                    latest = candidate
        if latest is None:
            return None
        modified_ns, path, source, root = latest
        relative = path.relative_to(root).as_posix()
        return {
            "source": source,
            "path": str(path),
            "relative_path": relative,
            "modified_at_ns": modified_ns,
            "size_bytes": path.stat().st_size,
            "artifact_preview_payload": (
                {"project_artifact_path": relative}
                if source == "project"
                else {"artifact_name": relative}
            ),
        }

    def _preview_mode(self, project) -> str:
        preview = getattr(project, "preview", {}) or {}
        if preview.get("url") or preview.get("entry") or (project.root / "package.json").is_file():
            return "web"
        if "blender" in project.apps:
            return "blender"
        if "unity" in project.apps:
            return "unity"
        if (project.root / "index.html").is_file():
            return "web"
        return "artifact"

    def project_preview_status(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        preview = getattr(project, "preview", {}) or {}
        latest = self._latest_preview_image(project)
        runtime = self._preview_runtime_status(project)
        url = str(runtime.get("url") or preview.get("url") or "").strip()
        entry = str(preview.get("entry") or "").strip()
        if not url and entry:
            entry_path = project.path(entry)
            url = entry_path.as_uri()
        if not url and (project.root / "index.html").is_file():
            url = (project.root / "index.html").resolve().as_uri()
        return ActionResult(True, "project preview status ready", {
            "project": project.slug,
            "mode": self._preview_mode(project),
            "url": url or None,
            "runtime": runtime,
            "latest_image": latest,
            "auto_refresh_seconds": int(preview.get("refresh_seconds", 3) or 3),
        })

    @staticmethod
    def _find_chromium() -> Path | None:
        candidates = [
            shutil.which("chrome"), shutil.which("msedge"),
            str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        for raw in candidates:
            if raw and Path(raw).is_file():
                return Path(raw)
        return None

    def project_preview_capture(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        mode = self._preview_mode(project)
        if mode == "blender":
            return self.blender_live_capture({
                "project": project.slug,
                "timeout_seconds": float(payload.get("timeout_seconds", 90)),
            })
        if mode == "unity":
            return self.unity_capture({
                "project": project.slug,
                "width": int(payload.get("width", 1280)),
                "height": int(payload.get("height", 720)),
                "warmup_frames": int(payload.get("warmup_frames", 1)),
                "timeout_seconds": float(payload.get("timeout_seconds", 120)),
            })
        status = self.project_preview_status({"project": project.slug})
        url = str(status.data.get("url") or "") if status.ok else ""
        if not url:
            return ActionResult(False, "no visual or web preview source is configured")
        browser = self._find_chromium()
        if browser is None:
            return ActionResult(False, "Chrome or Edge executable not found for web preview")
        output = (self.config.state_dir / "artifacts" / project.slug / "web-preview.png").resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        width = max(320, min(int(payload.get("width", 1280)), 2560))
        height = max(240, min(int(payload.get("height", 720)), 1600))
        command = [
            str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--window-size={width},{height}", f"--screenshot={output}", url,
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True,
                                       shell=False, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            return ActionResult(False, f"web preview capture failed: {error}")
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            return ActionResult(False, "web preview capture did not produce an image", {
                "returncode": completed.returncode,
                "stderr": (completed.stderr or "")[-2000:],
            })
        return ActionResult(True, "web preview captured", {
            "artifact": str(output),
            "url": url,
            "browser": str(browser),
            "width": width,
            "height": height,
        })

    def _preview_state_path(self, project) -> Path:
        return self.config.state_dir / "previews" / f"{project.slug}.json"

    @staticmethod
    def _process_running(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, shell=False, timeout=3,
                )
                return result.returncode == 0 and f'"{pid}"' in result.stdout
            except (OSError, subprocess.TimeoutExpired):
                return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _url_ready(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                return 200 <= int(response.status) < 500
        except Exception:
            return False

    def _preview_runtime_status(self, project) -> dict[str, Any]:
        path = self._preview_state_path(project)
        if not path.is_file():
            return {"running": False}
        try:
            state = json.loads(path.read_text(encoding="utf-8-sig"))
            pid = int(state.get("pid") or 0)
        except Exception as error:
            return {"running": False, "error": str(error)}
        running = self._process_running(pid)
        url = str(state.get("url") or "")
        return {
            **state,
            "running": running,
            "url_ready": bool(running and url and self._url_ready(url)),
        }

    def _web_launch_spec(self, project) -> tuple[list[str], str, dict[str, str]] | ActionResult:
        preview = getattr(project, "preview", {}) or {}
        port = int(preview.get("port") or 0)
        package = project.root / "package.json"
        env = os.environ.copy()
        if package.is_file():
            try:
                data = json.loads(package.read_text(encoding="utf-8-sig"))
            except Exception as error:
                return ActionResult(False, f"cannot read package.json: {error}")
            scripts = data.get("scripts") or {}
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            npm = shutil.which("npm") or shutil.which("npm.cmd")
            if not npm or "dev" not in scripts:
                return ActionResult(False, "web preview needs npm and a package.json dev script")
            if "vite" in deps:
                port = port or 5173
                command = [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)]
            elif "next" in deps:
                port = port or 3000
                command = [npm, "run", "dev", "--", "-H", "127.0.0.1", "-p", str(port)]
            else:
                port = port or 3000
                env["HOST"] = "127.0.0.1"
                env["PORT"] = str(port)
                env["BROWSER"] = "none"
                command = [npm, "run", "dev"]
            return command, f"http://127.0.0.1:{port}", env
        if (project.root / "index.html").is_file():
            port = port or 4173
            command = [sys.executable, "-m", "http.server", str(port),
                       "--bind", "127.0.0.1", "--directory", str(project.root)]
            return command, f"http://127.0.0.1:{port}", env
        return ActionResult(False, "no supported web preview runtime was detected")

    def project_preview_start(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        if self._preview_mode(project) != "web":
            return ActionResult(False, "preview runtime start is available only for web projects")
        current = self._preview_runtime_status(project)
        if current.get("running"):
            return ActionResult(True, "web preview runtime already running", current)
        spec = self._web_launch_spec(project)
        if isinstance(spec, ActionResult):
            return spec
        command, url, env = spec
        log = self.config.state_dir / "previews" / f"{project.slug}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if os.name == "nt":
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        try:
            with log.open("a", encoding="utf-8", errors="replace") as handle:
                process = subprocess.Popen(
                    command, cwd=str(project.root), env=env,
                    stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
                    shell=False, creationflags=creationflags,
                )
        except OSError as error:
            return ActionResult(False, f"cannot start web preview runtime: {error}")
        processes = getattr(self, "_preview_processes", None)
        if processes is None:
            processes = {}
            self._preview_processes = processes
        processes[project.slug] = process
        state = {"pid": process.pid, "url": url, "command": command, "log": str(log)}
        self._preview_state_path(project).write_text(json.dumps(state, indent=2), encoding="utf-8")
        deadline = time.monotonic() + max(2.0, min(float(payload.get("wait_seconds", 20)), 45.0))
        while time.monotonic() < deadline:
            if self._url_ready(url):
                state.update({"running": True, "url_ready": True})
                return ActionResult(True, "web preview runtime started", state)
            if process.poll() is not None:
                return ActionResult(False, "web preview runtime exited during startup", state)
            time.sleep(0.25)
        state.update({"running": self._process_running(process.pid), "url_ready": False})
        return ActionResult(state["running"], "web preview runtime started but URL is not ready yet", state)

    def project_preview_stop(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        state = self._preview_runtime_status(project)
        pid = int(state.get("pid") or 0)
        if not state.get("running") or not pid:
            return ActionResult(True, "web preview runtime is already stopped", state)
        try:
            if os.name == "nt":
                completed = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, text=True, shell=False, timeout=10,
                )
                stopped = completed.returncode == 0
            else:
                os.kill(pid, 15)
                stopped = True
        except (OSError, subprocess.TimeoutExpired) as error:
            return ActionResult(False, f"cannot stop web preview runtime: {error}", state)
        if stopped:
            process = getattr(self, "_preview_processes", {}).pop(project.slug, None)
            if process is not None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            try:
                self._preview_state_path(project).unlink(missing_ok=True)
            except OSError:
                pass
            return ActionResult(True, "web preview runtime stopped", {**state, "running": False})
        return ActionResult(False, "web preview runtime stop failed", state)
