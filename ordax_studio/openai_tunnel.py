from __future__ import annotations

import base64
import ctypes
import getpass
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from ctypes import wintypes
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

TUNNEL_CLIENT_VERSION = "v0.0.15"
TUNNEL_CLIENT_ARCHIVE = f"tunnel-client-{TUNNEL_CLIENT_VERSION}-windows-amd64.zip"
TUNNEL_CLIENT_URL = (
    f"https://github.com/openai/tunnel-client/releases/download/{TUNNEL_CLIENT_VERSION}/"
    f"{TUNNEL_CLIENT_ARCHIVE}"
)
TUNNEL_CLIENT_SHA256 = "3b53133a1e24d43f63088d843860cb1701a4c3ed6390de2e19f69089e43bddc1"
PROFILE_NAME = "ordax-studio"
TASK_NAME = "ORDAX OpenAI MCP Tunnel"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


class OpenAITunnelError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _require_windows() -> None:
    if os.name != "nt":
        raise OpenAITunnelError("OpenAI Secure MCP Tunnel integration is supported on Windows only")


def _dpapi_protect(value: str) -> str:
    _require_windows()
    raw = value.encode("utf-8")
    buffer = ctypes.create_string_buffer(raw)
    source = _DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(source),
        "ORDAX OpenAI MCP Tunnel",
        None,
        None,
        None,
        0x1,
        ctypes.byref(target),
    ):
        raise ctypes.WinError()
    try:
        protected = ctypes.string_at(target.pbData, target.cbData)
        return base64.b64encode(protected).decode("ascii")
    finally:
        kernel32.LocalFree(target.pbData)


def _dpapi_unprotect(value: str) -> str:
    _require_windows()
    raw = base64.b64decode(value.encode("ascii"), validate=True)
    buffer = ctypes.create_string_buffer(raw)
    source = _DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        0x1,
        ctypes.byref(target),
    ):
        raise ctypes.WinError()
    try:
        plain = ctypes.string_at(target.pbData, target.cbData)
        return plain.decode("utf-8")
    finally:
        kernel32.LocalFree(target.pbData)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            target = (destination / entry.filename).resolve()
            if not target.is_relative_to(destination):
                raise OpenAITunnelError(f"Unsafe tunnel-client archive entry: {entry.filename}")
        bundle.extractall(destination)


def _pid_running(pid: int | None) -> bool:
    if not pid or pid <= 0 or os.name != "nt":
        return False
    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return False
    ctypes.windll.kernel32.CloseHandle(handle)
    return True


class OpenAITunnelManager:
    def __init__(self, state_dir: Path | None = None, managed_repo: Path | None = None):
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        self.state_dir = (state_dir or local / "OrdaX" / "OpenAI").resolve()
        self.managed_repo = (managed_repo or local / "OrdaX" / "DevAgent" / "src").resolve()
        self.runtime_dir = self.state_dir / "runtime" / TUNNEL_CLIENT_VERSION
        self.profiles_dir = self.state_dir / "profiles"
        self.config_path = self.state_dir / "connection.json"
        self.secret_path = self.state_dir / "runtime-api-key.dpapi"
        self.status_path = self.state_dir / "runtime-status.json"
        self.log_path = self.state_dir / "tunnel.log"
        self.task_xml_path = self.state_dir / "scheduled-task.xml"

    @property
    def mcp_executable(self) -> Path:
        return self.managed_repo / ".venv" / "Scripts" / "ordax-studio-mcp.exe"

    @property
    def pythonw_executable(self) -> Path:
        return self.managed_repo / ".venv" / "Scripts" / "pythonw.exe"

    def _read_config(self) -> dict[str, Any]:
        if not self.config_path.is_file():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_config(self, data: dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temp = self.config_path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.config_path)

    def _read_runtime_status(self) -> dict[str, Any]:
        if not self.status_path.is_file():
            return {}
        try:
            data = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def tunnel_client(self) -> Path | None:
        if not self.runtime_dir.is_dir():
            return None
        matches = sorted(self.runtime_dir.rglob("tunnel-client.exe"))
        return matches[0] if matches else None

    def ensure_tunnel_client(self) -> Path:
        _require_windows()
        current = self.tunnel_client()
        manifest = self.runtime_dir / ".ordax-release.json"
        if current and manifest.is_file():
            try:
                metadata = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
            if metadata.get("sha256") == TUNNEL_CLIENT_SHA256:
                return current

        self.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ordax-openai-") as raw_temp:
            temp = Path(raw_temp)
            archive = temp / TUNNEL_CLIENT_ARCHIVE
            request = urllib.request.Request(TUNNEL_CLIENT_URL, headers={"User-Agent": "ORDAX-Studio/0.3"})
            size = 0
            with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_ARCHIVE_BYTES:
                        raise OpenAITunnelError("Official tunnel-client archive exceeded the expected size budget")
                    output.write(chunk)
            actual = _sha256_file(archive)
            if actual != TUNNEL_CLIENT_SHA256:
                raise OpenAITunnelError(
                    f"Official tunnel-client SHA-256 mismatch: expected {TUNNEL_CLIENT_SHA256}, got {actual}"
                )
            extracted = temp / "extracted"
            extracted.mkdir()
            _safe_extract(archive, extracted)
            candidates = list(extracted.rglob("tunnel-client.exe"))
            if len(candidates) != 1:
                raise OpenAITunnelError(f"Expected exactly one tunnel-client.exe, found {len(candidates)}")
            if self.runtime_dir.exists():
                shutil.rmtree(self.runtime_dir)
            self.runtime_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(extracted, self.runtime_dir)
            (self.runtime_dir / ".ordax-release.json").write_text(
                json.dumps(
                    {
                        "version": TUNNEL_CLIENT_VERSION,
                        "archive": TUNNEL_CLIENT_ARCHIVE,
                        "sha256": TUNNEL_CLIENT_SHA256,
                        "source": TUNNEL_CLIENT_URL,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        installed = self.tunnel_client()
        if not installed:
            raise OpenAITunnelError("tunnel-client installation completed without an executable")
        return installed

    def _run_client(self, *args: str, api_key: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
        client = self.ensure_tunnel_client()
        env = dict(os.environ)
        env["CONTROL_PLANE_API_KEY"] = api_key
        result = subprocess.run(
            [str(client), *args],
            cwd=str(self.state_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "tunnel-client failed").strip()
            raise OpenAITunnelError(detail[-2000:])
        return result

    def setup(self, tunnel_id: str, runtime_api_key: str) -> dict[str, Any]:
        _require_windows()
        tunnel_id = tunnel_id.strip()
        runtime_api_key = runtime_api_key.strip()
        if not tunnel_id.startswith("tunnel_") or len(tunnel_id) < 20 or len(tunnel_id) > 200:
            raise OpenAITunnelError("Tunnel ID inválido")
        if len(runtime_api_key) < 16:
            raise OpenAITunnelError("Runtime API key inválida")
        if not self.mcp_executable.is_file():
            raise OpenAITunnelError(f"ORDAX Studio MCP gerenciado não encontrado: {self.mcp_executable}")
        if not self.pythonw_executable.is_file():
            raise OpenAITunnelError(f"Pythonw gerenciado não encontrado: {self.pythonw_executable}")

        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        client = self.ensure_tunnel_client()
        self._run_client(
            "init",
            "--sample",
            "sample_mcp_stdio_local",
            "--profile",
            PROFILE_NAME,
            "--profile-dir",
            str(self.profiles_dir),
            "--force",
            "--tunnel-id",
            tunnel_id,
            "--mcp-command",
            str(self.mcp_executable),
            "--health-listen-addr",
            "127.0.0.1:0",
            api_key=runtime_api_key,
        )
        doctor = self._run_client(
            "doctor",
            "--profile",
            PROFILE_NAME,
            "--profile-dir",
            str(self.profiles_dir),
            "--explain",
            api_key=runtime_api_key,
            timeout=90.0,
        )
        self.secret_path.write_text(_dpapi_protect(runtime_api_key), encoding="ascii")
        self._write_config(
            {
                "version": 1,
                "profile": PROFILE_NAME,
                "tunnel_id": tunnel_id,
                "client_version": TUNNEL_CLIENT_VERSION,
                "client": str(client),
                "mcp_command": str(self.mcp_executable),
                "configured_at": time.time(),
                "doctor_ok": True,
                "doctor_summary": (doctor.stdout or "doctor ok").strip()[-2000:],
            }
        )
        self.install_task()
        self.start_task()
        return self.status()

    def load_runtime_api_key(self) -> str:
        if not self.secret_path.is_file():
            raise OpenAITunnelError("OpenAI runtime API key is not configured")
        return _dpapi_unprotect(self.secret_path.read_text(encoding="ascii").strip())

    def _task_xml(self) -> bytes:
        _require_windows()
        domain = os.environ.get("USERDOMAIN", "").strip()
        username = os.environ.get("USERNAME", getpass.getuser()).strip()
        user_id = f"{domain}\\{username}" if domain else username
        ns = "http://schemas.microsoft.com/windows/2004/02/mit/task"
        ET.register_namespace("", ns)
        q = lambda tag: f"{{{ns}}}{tag}"
        task = ET.Element(q("Task"), {"version": "1.4"})
        registration = ET.SubElement(task, q("RegistrationInfo"))
        ET.SubElement(registration, q("Description")).text = "Persistent ORDAX Studio bridge to OpenAI Secure MCP Tunnel"
        triggers = ET.SubElement(task, q("Triggers"))
        logon = ET.SubElement(triggers, q("LogonTrigger"))
        ET.SubElement(logon, q("Enabled")).text = "true"
        ET.SubElement(logon, q("UserId")).text = user_id
        principals = ET.SubElement(task, q("Principals"))
        principal = ET.SubElement(principals, q("Principal"), {"id": "Author"})
        ET.SubElement(principal, q("UserId")).text = user_id
        ET.SubElement(principal, q("LogonType")).text = "InteractiveToken"
        ET.SubElement(principal, q("RunLevel")).text = "LeastPrivilege"
        settings = ET.SubElement(task, q("Settings"))
        ET.SubElement(settings, q("MultipleInstancesPolicy")).text = "IgnoreNew"
        ET.SubElement(settings, q("DisallowStartIfOnBatteries")).text = "false"
        ET.SubElement(settings, q("StopIfGoingOnBatteries")).text = "false"
        ET.SubElement(settings, q("StartWhenAvailable")).text = "true"
        ET.SubElement(settings, q("ExecutionTimeLimit")).text = "PT0S"
        restart = ET.SubElement(settings, q("RestartOnFailure"))
        ET.SubElement(restart, q("Interval")).text = "PT1M"
        ET.SubElement(restart, q("Count")).text = "999"
        actions = ET.SubElement(task, q("Actions"), {"Context": "Author"})
        execute = ET.SubElement(actions, q("Exec"))
        ET.SubElement(execute, q("Command")).text = str(self.pythonw_executable)
        ET.SubElement(execute, q("Arguments")).text = "-m ordax_studio.openai_tunnel_runner"
        ET.SubElement(execute, q("WorkingDirectory")).text = str(self.managed_repo)
        return ET.tostring(task, encoding="utf-16", xml_declaration=True)

    def install_task(self) -> None:
        _require_windows()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.task_xml_path.write_bytes(self._task_xml())
        result = subprocess.run(
            ["schtasks.exe", "/Create", "/TN", TASK_NAME, "/XML", str(self.task_xml_path), "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise OpenAITunnelError((result.stderr or result.stdout or "Failed to install tunnel task").strip())

    def start_task(self) -> None:
        _require_windows()
        result = subprocess.run(
            ["schtasks.exe", "/Run", "/TN", TASK_NAME],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise OpenAITunnelError((result.stderr or result.stdout or "Failed to start tunnel task").strip())

    def task_installed(self) -> bool:
        if os.name != "nt":
            return False
        result = subprocess.run(
            ["schtasks.exe", "/Query", "/TN", TASK_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    def status(self) -> dict[str, Any]:
        config = self._read_config()
        runtime = self._read_runtime_status()
        pid = runtime.get("pid") if isinstance(runtime.get("pid"), int) else None
        return {
            "configured": bool(config.get("tunnel_id") and self.secret_path.is_file()),
            "tunnel_id": config.get("tunnel_id"),
            "profile": config.get("profile", PROFILE_NAME),
            "client_version": config.get("client_version", TUNNEL_CLIENT_VERSION),
            "client_installed": self.tunnel_client() is not None,
            "task_installed": self.task_installed(),
            "runtime_pid": pid,
            "runtime_running": _pid_running(pid),
            "last_started_at": runtime.get("started_at"),
            "last_exit_code": runtime.get("exit_code"),
            "doctor_ok": bool(config.get("doctor_ok")),
            "log_path": str(self.log_path),
        }
