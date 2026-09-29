from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from mcp_blender_unity.config import find_blender

from .models import ActionResult
from .projects import Project


BOOTSTRAP_VERSION = 1
ADDON_MODULE = "ordax_studio_bridge"
ADDON_SOURCE_FILENAME = "ordax_studio_blender_addon.py"
LEGACY_STARTUP_FILENAME = "ordax_studio_bootstrap.py"
BOOTSTRAP_CONFIG_NAME = "blender-bootstrap.json"
DISCOVERY_MAX_AGE_SECONDS = 4.0
ADOPTION_REQUEST_MAX_AGE_SECONDS = 30.0
LEGACY_BRIDGE_RESPONSE_LIMIT = 1024 * 1024


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def _safe_project_payload(config, project: Project) -> dict[str, str]:
    scripts_root = project.path(
        project.blender.get("scripts_dir", "automation/blender"),
        must_exist=False,
    )
    return {
        "slug": project.slug,
        "root": str(project.root.resolve()),
        "scripts_root": str(scripts_root.resolve()),
        "control_root": str((config.state_dir / "blender-live" / project.slug).resolve()),
        "artifacts_root": str((config.state_dir / "artifacts" / project.slug).resolve()),
    }


def _numeric_blender_versions(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    versions: list[Path] = []
    for entry in base.iterdir():
        if entry.is_dir() and re.fullmatch(r"\d+\.\d+", entry.name):
            versions.append(entry)
    return sorted(versions, key=lambda item: tuple(int(x) for x in item.name.split(".")))


class BlenderAdoptionManager:
    """Discovery/adoption control plane for already-open Blender windows."""

    def __init__(
        self,
        config,
        projects: dict[str, Project],
        *,
        assets_root: Path,
        companion_fingerprint: str | None,
        appdata: Path | None = None,
        enable_addon: bool = True,
    ) -> None:
        self.config = config
        self.projects = projects
        self.assets_root = assets_root.resolve()
        self.companion = (self.assets_root / "blender_live_companion.py").resolve()
        self.bootstrap_source = (self.assets_root / ADDON_SOURCE_FILENAME).resolve()
        self.companion_fingerprint = companion_fingerprint
        self.enable_addon = bool(enable_addon)
        roaming = appdata or Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        self.blender_user_root = roaming / "Blender Foundation" / "Blender"
        self.config_path = (config.state_dir / BOOTSTRAP_CONFIG_NAME).resolve()
        self.discovery_root = (config.state_dir / "blender-discovery").resolve()
        self.adoption_root = (config.state_dir / "blender-adoption").resolve()

    def _eligible_projects(self) -> dict[str, Project]:
        return {
            slug: project
            for slug, project in self.projects.items()
            if "blender" in project.apps and project.root.is_dir()
        }

    def build_config(self) -> dict[str, Any]:
        if not self.companion.is_file():
            raise FileNotFoundError(self.companion)
        if not self.bootstrap_source.is_file():
            raise FileNotFoundError(self.bootstrap_source)
        if not self.companion_fingerprint:
            raise ValueError("Blender companion fingerprint is unavailable")
        projects = {
            slug: _safe_project_payload(self.config, project)
            for slug, project in self._eligible_projects().items()
        }
        return {
            "version": BOOTSTRAP_VERSION,
            "generated_at": time.time(),
            "state_dir": str(self.config.state_dir.resolve()),
            "assets_root": str(self.assets_root),
            "companion_path": str(self.companion),
            "companion_fingerprint": self.companion_fingerprint,
            "projects": projects,
        }

    def sync_config(self) -> Path:
        _write_json_atomic(self.config_path, self.build_config())
        return self.config_path

    def profile_versions(self) -> list[Path]:
        return _numeric_blender_versions(self.blender_user_root)

    def addon_dirs(self) -> list[Path]:
        return [version / "scripts" / "addons" / ADDON_MODULE for version in self.profile_versions()]

    def _enable_installed_addon(self) -> dict[str, Any]:
        if not self.enable_addon:
            return {"enabled": False, "skipped": True, "reason": "disabled for this manager"}
        blender = find_blender()
        if blender is None:
            raise FileNotFoundError("Blender executable not found")
        env = os.environ.copy()
        env["ORDAX_BLENDER_BOOTSTRAP_CONFIG"] = str(self.config_path)
        expression = (
            "import bpy; "
            f"r=bpy.ops.preferences.addon_enable(module='{ADDON_MODULE}'); "
            "bpy.ops.wm.save_userpref(); "
            "print('ORDAX_STUDIO_ADDON_ENABLED='+str(r))"
        )
        command = [str(blender), "--background", "--python-expr", expression]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
                env=env,
            )
        except subprocess.TimeoutExpired as timeout_error:
            probe_expression = (
                "import bpy; "
                f"print('ORDAX_STUDIO_ADDON_PRESENT='+str('{ADDON_MODULE}' in bpy.context.preferences.addons))"
            )
            probe = subprocess.run(
                [str(blender), "--background", "--python-expr", probe_expression],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
                check=False,
                env=env,
            )
            probe_output = probe.stdout[-12000:]
            if probe.returncode == 0 and "ORDAX_STUDIO_ADDON_PRESENT=True" in probe_output:
                return {
                    "enabled": True,
                    "blender": str(blender),
                    "enable_timed_out": True,
                    "timeout_seconds": float(timeout_error.timeout or 60),
                    "probe_output_tail": probe_output[-2000:],
                }
            raise RuntimeError(
                f"Blender addon enable timed out and verification failed: {probe_output[-2000:]}"
            )
        output = completed.stdout[-12000:]
        if completed.returncode != 0 or "ORDAX_STUDIO_ADDON_ENABLED" not in output:
            raise RuntimeError(f"Blender could not enable {ADDON_MODULE}: {output[-2000:]}")
        return {"enabled": True, "blender": str(blender), "output_tail": output[-2000:]}

    def install(self) -> ActionResult:
        try:
            config_path = self.sync_config()
            versions = self.profile_versions()
            if not versions:
                return ActionResult(
                    False,
                    "No Blender user profile versions were found",
                    {"blender_user_root": str(self.blender_user_root), "config": str(config_path)},
                )
            installed: list[str] = []
            removed_legacy: list[str] = []
            for version in versions:
                addon_dir = version / "scripts" / "addons" / ADDON_MODULE
                addon_dir.mkdir(parents=True, exist_ok=True)
                target = (addon_dir / "__init__.py").resolve()
                if not target.is_relative_to(addon_dir.resolve()):
                    raise ValueError("Blender addon target escaped managed addon directory")
                shutil.copyfile(self.bootstrap_source, target)
                installed.append(str(target))
                legacy = version / "scripts" / "startup" / LEGACY_STARTUP_FILENAME
                if legacy.is_file():
                    legacy.unlink()
                    removed_legacy.append(str(legacy))
            enabled = self._enable_installed_addon()
            return ActionResult(
                True,
                "ORDAX Blender adoption addon installed",
                {
                    "config": str(config_path),
                    "installed": installed,
                    "removed_legacy": removed_legacy,
                    "enable": enabled,
                    "restart_required_for_existing_blender": True,
                    "projects": sorted(self._eligible_projects()),
                },
            )
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            return ActionResult(False, f"Blender adoption addon install failed: {error}")

    def instances(self, *, max_age_seconds: float = DISCOVERY_MAX_AGE_SECONDS) -> list[dict[str, Any]]:
        now = time.time()
        found: list[dict[str, Any]] = []
        if not self.discovery_root.is_dir():
            return found
        for path in sorted(self.discovery_root.glob("*.json")):
            try:
                data = _read_json_object(path)
                pid = int(data.get("pid"))
                timestamp = float(data.get("timestamp"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            age = now - timestamp
            if age < 0 or age > max_age_seconds:
                continue
            data = {**data, "pid": pid, "age_seconds": round(age, 3), "discovery_path": str(path)}
            found.append(data)
        return found

    @staticmethod
    def _instance_matches_project(instance: dict[str, Any], project: Project) -> bool:
        raw_file = str(instance.get("file") or "").strip()
        if not raw_file:
            return False
        try:
            current = Path(raw_file).resolve()
        except OSError:
            return False
        return current.is_relative_to(project.root.resolve())

    def matching_instances(self, project: Project) -> list[dict[str, Any]]:
        return [
            item
            for item in self.instances()
            if self._instance_matches_project(item, project)
        ]

    def system_blender_pids(self) -> list[int]:
        """Return Blender process ids even when the ORDAX addon is not active."""
        try:
            if os.name == "nt":
                completed = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq blender.exe", "/FO", "CSV", "/NH"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                    check=False,
                )
                if completed.returncode != 0:
                    return []
                pids: list[int] = []
                for row in csv.reader(io.StringIO(completed.stdout)):
                    if len(row) < 2 or row[0].strip().lower() != "blender.exe":
                        continue
                    try:
                        pid = int(row[1].replace(",", "").strip())
                    except ValueError:
                        continue
                    if pid > 0 and pid not in pids:
                        pids.append(pid)
                return sorted(pids)

            completed = subprocess.run(
                ["pgrep", "-x", "blender"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
            if completed.returncode not in (0, 1):
                return []
            return sorted({int(line.strip()) for line in completed.stdout.splitlines() if line.strip().isdigit()})
        except (OSError, subprocess.TimeoutExpired):
            return []

    @staticmethod
    def _legacy_bridge_port(project: Project) -> int | None:
        raw = project.blender.get("legacy_blendmcp_port")
        if raw is None or raw == "":
            return None
        if isinstance(raw, bool):
            raise ValueError("legacy_blendmcp_port must be an integer port")
        try:
            port = int(raw)
        except (TypeError, ValueError) as error:
            raise ValueError("legacy_blendmcp_port must be an integer port") from error
        if not 1024 <= port <= 65535:
            raise ValueError("legacy_blendmcp_port must be between 1024 and 65535")
        return port

    @staticmethod
    def _legacy_bridge_rpc(port: int, payload: dict[str, Any], *, timeout_seconds: float = 5.0) -> dict[str, Any]:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        with socket.create_connection(("127.0.0.1", int(port)), timeout=max(0.5, min(timeout_seconds, 10.0))) as client:
            client.settimeout(max(0.5, min(timeout_seconds, 10.0)))
            client.sendall(encoded)
            response = client.recv(LEGACY_BRIDGE_RESPONSE_LIMIT + 1)
        if not response:
            raise RuntimeError("legacy BlendMCP bridge closed without a response")
        if len(response) > LEGACY_BRIDGE_RESPONSE_LIMIT:
            raise RuntimeError("legacy BlendMCP response exceeded 1 MiB")
        decoded = json.loads(response.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise RuntimeError("legacy BlendMCP response must be a JSON object")
        return decoded

    def _presence_for_pid(self, project: Project, pid: int) -> dict[str, Any] | None:
        path = (self.config.state_dir / "blender-live" / project.slug / "presence.json").resolve()
        try:
            data = _read_json_object(path)
            age = time.time() - path.stat().st_mtime
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None
        if not 0 <= age <= DISCOVERY_MAX_AGE_SECONDS:
            return None
        if int(data.get("pid", -1)) != int(pid):
            return None
        if data.get("project") != project.slug:
            return None
        if data.get("companion_fingerprint") != self.companion_fingerprint:
            return None
        return data

    def _try_legacy_bridge_adoption(
        self,
        project: Project,
        *,
        requested_pid: int | None,
        wait_seconds: float,
    ) -> ActionResult | None:
        port = self._legacy_bridge_port(project)
        if port is None:
            return None
        pids = self.system_blender_pids()
        if requested_pid is not None:
            if int(requested_pid) not in pids:
                return ActionResult(
                    False,
                    "Requested Blender PID is not running",
                    {"project": project.slug, "pid": int(requested_pid), "legacy_bridge_port": port, "no_match": True},
                )
            selected_pid = int(requested_pid)
        elif len(pids) == 1:
            selected_pid = pids[0]
        elif len(pids) > 1:
            return ActionResult(
                False,
                "Multiple unmanaged Blender windows are running; choose a PID explicitly before legacy migration",
                {"project": project.slug, "blender_pids": pids, "legacy_bridge_port": port, "ambiguous": True},
            )
        else:
            return None

        try:
            probe = self._legacy_bridge_rpc(port, {"type": "get_addon_version", "params": {}}, timeout_seconds=3.0)
            if probe.get("status") != "success":
                raise RuntimeError("legacy bridge probe did not identify a healthy BlendMCP server")
            migrated = self._legacy_bridge_rpc(
                port,
                {
                    "type": "execute_code",
                    "params": {
                        "code": "import ordax_studio_bridge; ordax_studio_bridge.register(); print('ORDAX_ADOPTION_REGISTERED')",
                    },
                },
                timeout_seconds=5.0,
            )
            result = migrated.get("result")
            if migrated.get("status") != "success" or not isinstance(result, dict) or not bool(result.get("executed")):
                raise RuntimeError("legacy bridge refused the ORDAX adoption bootstrap")
        except (OSError, TimeoutError, ValueError, RuntimeError, json.JSONDecodeError) as error:
            return ActionResult(
                False,
                f"Legacy Blender bridge migration failed: {error}",
                {
                    "project": project.slug,
                    "pid": selected_pid,
                    "legacy_bridge_port": port,
                    "legacy_bridge_migration": True,
                    "retryable": True,
                    "no_match": True,
                },
            )

        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 15.0))
        while time.monotonic() < deadline:
            presence = self._presence_for_pid(project, selected_pid)
            if presence is not None:
                return ActionResult(
                    True,
                    "Existing legacy Blender window migrated to ORDAX Studio",
                    {
                        "project": project.slug,
                        "pid": selected_pid,
                        "legacy_bridge_port": port,
                        "legacy_bridge_migration": True,
                        "presence": presence,
                    },
                )
            time.sleep(0.05)
        return ActionResult(
            False,
            "Legacy Blender bridge accepted migration but ORDAX companion did not become ready",
            {
                "project": project.slug,
                "pid": selected_pid,
                "legacy_bridge_port": port,
                "legacy_bridge_migration": True,
                "retryable": True,
                "no_match": True,
            },
        )

    def _request_path(self, pid: int) -> Path:
        return (self.adoption_root / f"{int(pid)}.json").resolve()

    def request_adoption(
        self,
        project: Project,
        *,
        pid: int | None = None,
        wait_seconds: float = 8.0,
    ) -> ActionResult:
        if project.slug not in self._eligible_projects():
            return ActionResult(False, f"Blender is not enabled for project: {project.slug}")
        try:
            self.sync_config()
        except (OSError, ValueError) as error:
            return ActionResult(False, f"Blender bootstrap configuration could not be refreshed: {error}")

        candidates = self.matching_instances(project)
        if pid is not None:
            candidates = [item for item in candidates if int(item.get("pid", -1)) == int(pid)]
        if not candidates:
            try:
                legacy = self._try_legacy_bridge_adoption(
                    project,
                    requested_pid=pid,
                    wait_seconds=wait_seconds,
                )
            except ValueError as error:
                return ActionResult(False, f"Invalid Blender legacy bridge configuration: {error}")
            if legacy is not None:
                return legacy
            return ActionResult(
                False,
                "No adoptable Blender window matches this project",
                {
                    "project": project.slug,
                    "pid": pid,
                    "instances": self.instances(),
                    "retryable": False,
                    "no_match": True,
                },
            )
        if len(candidates) != 1:
            return ActionResult(
                False,
                "Multiple Blender windows match this project; choose a PID explicitly",
                {"project": project.slug, "instances": candidates, "ambiguous": True},
            )

        selected = candidates[0]
        selected_pid = int(selected["pid"])
        request_id = uuid.uuid4().hex
        request_path = self._request_path(selected_pid)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(
            request_path,
            {
                "version": BOOTSTRAP_VERSION,
                "request_id": request_id,
                "created_at": time.time(),
                "project": project.slug,
                "pid": selected_pid,
            },
        )

        presence = (self.config.state_dir / "blender-live" / project.slug / "presence.json").resolve()
        deadline = time.monotonic() + max(0.5, min(float(wait_seconds), 30.0))
        while time.monotonic() < deadline:
            try:
                data = _read_json_object(presence)
                age = time.time() - presence.stat().st_mtime
                if (
                    0 <= age <= DISCOVERY_MAX_AGE_SECONDS
                    and int(data.get("pid", -1)) == selected_pid
                    and data.get("companion_fingerprint") == self.companion_fingerprint
                ):
                    return ActionResult(
                        True,
                        "Existing Blender window adopted by ORDAX Studio",
                        {"project": project.slug, "pid": selected_pid, "request_id": request_id, "presence": data},
                    )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
            time.sleep(0.05)

        return ActionResult(
            False,
            "Blender adoption request timed out",
            {
                "project": project.slug,
                "pid": selected_pid,
                "request_id": request_id,
                "retryable": True,
            },
        )
