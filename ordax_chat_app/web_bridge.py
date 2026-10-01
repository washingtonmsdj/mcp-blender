"""ORDAX Web Bridge: managed OpenAI Secure MCP Tunnel for regular ChatGPT."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from typing import Any, Callable

from .auth.local_state import (
    _atomic_write,
    _identity,
    _windows_protect,
    _windows_unprotect,
    resolve_chat_app_state_dir,
)

TUNNELS_URL = "https://platform.openai.com/settings/organization/tunnels"
API_KEYS_URL = "https://platform.openai.com/settings/organization/api-keys"
CHATGPT_URL = "https://chatgpt.com/"
RELEASE_API = "https://api.github.com/repos/openai/tunnel-client/releases/latest"


class WebBridgeCredentialStore:
    """Stores the tunnel runtime key encrypted with DPAPI on Windows."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        protect: Callable[[bytes], bytes] | None = None,
        unprotect: Callable[[bytes], bytes] | None = None,
    ):
        self.path = (
            Path(path).expanduser().resolve()
            if path
            else resolve_chat_app_state_dir() / "web-bridge.dat"
        )
        if protect is None or unprotect is None:
            if os.name == "nt":
                protect = _windows_protect
                unprotect = _windows_unprotect
            else:
                protect = _identity
                unprotect = _identity
        self._protect = protect
        self._unprotect = unprotect

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "tunnel_id": None, "api_key": None, "profile": "ordax-dev", "initialized": False, "enabled": False}
        payload = json.loads(self._unprotect(self.path.read_bytes()).decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("unsupported ORDAX Web Bridge credential format")
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        _atomic_write(self.path, self._protect(encoded), mode=0o600)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _platform_asset_fragment() -> str:
    system = platform.system().lower()
    if system == "darwin":
        os_name = "darwin"
    elif system == "windows":
        os_name = "windows"
    elif system == "linux":
        os_name = "linux"
    else:
        raise RuntimeError(f"unsupported tunnel-client platform: {system}")

    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64", "x64"}:
        arch = "amd64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        raise RuntimeError(f"unsupported tunnel-client architecture: {machine}")
    return f"-{os_name}-{arch}.zip"


class WebBridgeManager:
    def __init__(
        self,
        *,
        state_dir: str | Path | None = None,
        credentials: WebBridgeCredentialStore | None = None,
    ):
        self.state_dir = (
            Path(state_dir).expanduser().resolve()
            if state_dir
            else resolve_chat_app_state_dir()
        )
        self.credentials = credentials or WebBridgeCredentialStore(self.state_dir / "web-bridge.dat")
        self.bin_dir = self.state_dir / "web-bridge" / "bin"
        self.runtime_path = self.state_dir / "web-bridge-runtime.json"
        self.daemon_state_path = self.state_dir / "web-bridge-daemon.json"
        self._process: subprocess.Popen | None = None

    @staticmethod
    def _pid_running(pid: int) -> bool:
        if pid <= 0:
            return False
        if os.name == "nt":
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    shell=False,
                )
                return result.returncode == 0 and f'"{pid}"' in (result.stdout or "")
            except (OSError, subprocess.TimeoutExpired):
                return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    @staticmethod
    def _commandline(pid: int) -> str:
        if pid <= 0:
            return ""
        if os.name == "nt":
            script = (
                "$ErrorActionPreference='SilentlyContinue';"
                f"(Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\").CommandLine"
            )
            try:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", script],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False,
                )
                return (result.stdout or "").strip()
            except (OSError, subprocess.TimeoutExpired):
                return ""
        try:
            return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
        except OSError:
            return ""

    def _load_runtime(self) -> dict[str, Any]:
        if not self.runtime_path.is_file():
            return {}
        try:
            payload = json.loads(self.runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_runtime(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        _atomic_write(self.runtime_path, encoded, mode=0o600)

    def _runtime_owned(self, runtime: dict[str, Any], config: dict[str, Any]) -> bool:
        try:
            pid = int(runtime.get("pid") or 0)
        except (TypeError, ValueError):
            return False
        if not self._pid_running(pid):
            return False
        commandline = self._commandline(pid)
        profile = str(config.get("profile") or "ordax-dev")
        binary = self.binary()
        binary_name = binary.name.lower() if binary else "tunnel-client"
        return (
            binary_name in commandline.lower()
            and "run" in commandline
            and profile in commandline
        )

    def _configured(self) -> dict[str, Any]:
        return self.credentials.load()

    def configure(self, tunnel_id: str, api_key: str) -> dict[str, Any]:
        tunnel_id = str(tunnel_id or "").strip()
        api_key = str(api_key or "").strip()
        if not tunnel_id.startswith("tunnel_") or len(tunnel_id) < 16:
            raise ValueError("Tunnel ID inválido; esperado tunnel_...")
        if not api_key:
            raise ValueError("Runtime API key is required")
        previous = self._configured()
        initialized = bool(previous.get("initialized")) and previous.get("tunnel_id") == tunnel_id
        payload = {
            "version": 1,
            "tunnel_id": tunnel_id,
            "api_key": api_key,
            "profile": "ordax-dev",
            "initialized": initialized,
            "enabled": bool(previous.get("enabled", False)) if previous.get("tunnel_id") == tunnel_id else False,
        }
        self.credentials.save(payload)
        return self.status()

    def set_enabled(self, enabled: bool) -> dict[str, Any]:
        config = self._configured()
        if enabled and not (config.get("tunnel_id") and config.get("api_key")):
            raise RuntimeError("ORDAX Web Bridge is not configured")
        config["enabled"] = bool(enabled)
        self.credentials.save(config)
        return self.status()

    def disconnect(self) -> dict[str, Any]:
        self.stop()
        self.credentials.clear()
        return self.status()

    def _binary_candidates(self) -> list[Path]:
        names = ["tunnel-client.exe", "tunnel-client"] if os.name == "nt" else ["tunnel-client"]
        candidates: list[Path] = []
        override = os.environ.get("ORDAX_TUNNEL_CLIENT")
        if override:
            candidates.append(Path(override).expanduser())
        for name in names:
            candidates.append(self.bin_dir / name)
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))
        return candidates

    def binary(self) -> Path | None:
        for candidate in self._binary_candidates():
            if candidate.is_file():
                return candidate.resolve()
        return None

    def install_client(self) -> dict[str, Any]:
        request = urllib.request.Request(
            RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "ORDAX-Dev"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.load(response)

        fragment = _platform_asset_fragment()
        assets = release.get("assets") if isinstance(release, dict) else None
        if not isinstance(assets, list):
            raise RuntimeError("invalid tunnel-client release metadata")
        candidates = [
            item for item in assets
            if isinstance(item, dict)
            and str(item.get("name") or "").startswith("tunnel-client-v")
            and str(item.get("name") or "").endswith(fragment)
            and "runtime-cloudflared" not in str(item.get("name") or "")
        ]
        if len(candidates) != 1:
            raise RuntimeError(f"could not resolve official tunnel-client asset for {fragment}")
        asset = candidates[0]
        download_url = str(asset.get("browser_download_url") or "")
        digest = str(asset.get("digest") or "")
        if not download_url.startswith("https://github.com/openai/tunnel-client/"):
            raise RuntimeError("unexpected tunnel-client download origin")
        if not digest.startswith("sha256:"):
            raise RuntimeError("tunnel-client release is missing SHA-256 digest")

        self.bin_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(self.state_dir)) as temp_dir:
            archive = Path(temp_dir) / str(asset["name"])
            req = urllib.request.Request(download_url, headers={"User-Agent": "ORDAX-Dev"})
            with urllib.request.urlopen(req, timeout=120) as response, archive.open("wb") as handle:
                shutil.copyfileobj(response, handle)

            actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            expected = digest.split(":", 1)[1].lower()
            if actual.lower() != expected:
                raise RuntimeError("tunnel-client SHA-256 verification failed")

            with zipfile.ZipFile(archive) as bundle:
                executable_names = {"tunnel-client.exe", "tunnel-client"}
                members = [name for name in bundle.namelist() if Path(name).name in executable_names]
                if len(members) != 1:
                    raise RuntimeError("tunnel-client executable not found in official archive")
                target_name = "tunnel-client.exe" if os.name == "nt" else "tunnel-client"
                target = self.bin_dir / target_name
                temp_target = target.with_suffix(target.suffix + ".tmp")
                with bundle.open(members[0]) as source, temp_target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
                if os.name != "nt":
                    temp_target.chmod(0o700)
                os.replace(temp_target, target)

        return {
            **self.status(),
            "installed_version": str(release.get("tag_name") or ""),
        }

    def _env(self, config: dict[str, Any]) -> dict[str, str]:
        env = dict(os.environ)
        env["CONTROL_PLANE_API_KEY"] = str(config.get("api_key") or "")
        root = str(self._product_root())
        env.setdefault("ORDAX_PACKAGED_ROOT", root)
        env.setdefault("ORDAX_AGENT_REPO_PATH", root)
        env.setdefault("ORDAX_BRIDGE_PATH", root)
        return env

    @staticmethod
    def _python_command() -> str:
        executable = Path(sys.executable)
        if os.name == "nt" and executable.name.lower() == "pythonw.exe":
            console = executable.with_name("python.exe")
            if console.is_file():
                executable = console
        return f'"{executable}" -m ordax_chat_app.tunnel_mcp_server'

    def _run_checked(self, args: list[str], *, config: dict[str, Any], timeout: int = 60) -> str:
        binary = self.binary()
        if binary is None:
            raise RuntimeError("tunnel-client is not installed")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run(
            [str(binary), *args],
            env=self._env(config),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            creationflags=flags,
            check=False,
        )
        if result.returncode != 0:
            output = (result.stdout or "")[-4000:]
            raise RuntimeError(f"tunnel-client failed ({result.returncode}): {output}")
        return (result.stdout or "")[-4000:]

    def initialize(self) -> dict[str, Any]:
        config = self._configured()
        tunnel_id = str(config.get("tunnel_id") or "")
        if not tunnel_id or not config.get("api_key"):
            raise RuntimeError("ORDAX Web Bridge is not configured")
        if self.binary() is None:
            self.install_client()
        if not config.get("initialized"):
            self._run_checked(
                [
                    "init",
                    "--sample",
                    "sample_mcp_stdio_local",
                    "--profile",
                    str(config.get("profile") or "ordax-dev"),
                    "--tunnel-id",
                    tunnel_id,
                    "--mcp-command",
                    self._python_command(),
                ],
                config=config,
                timeout=60,
            )
            config["initialized"] = True
            self.credentials.save(config)
        self._run_checked(
            ["doctor", "--profile", str(config.get("profile") or "ordax-dev"), "--explain"],
            config=config,
            timeout=60,
        )
        return self.status()

    def start(self, *, persist_enabled: bool = True) -> dict[str, Any]:
        config = self._configured()
        if persist_enabled and not bool(config.get("enabled", False)):
            config["enabled"] = True
            self.credentials.save(config)
        self.initialize()
        current = self.status()
        if current.get("running"):
            return current
        binary = self.binary()
        if binary is None:
            raise RuntimeError("tunnel-client is not installed")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        if os.name == "nt":
            flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        self._process = subprocess.Popen(
            [str(binary), "run", "--profile", str(config.get("profile") or "ordax-dev")],
            env=self._env(config),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            start_new_session=os.name != "nt",
        )
        self._write_runtime({
            "schema_version": 1,
            "pid": self._process.pid,
            "profile": str(config.get("profile") or "ordax-dev"),
            "binary": str(binary),
            "started_at_unix": time.time(),
        })
        return self.status()

    def stop(self, *, persist_disabled: bool = True) -> dict[str, Any]:
        config = self._configured()
        if persist_disabled and bool(config.get("enabled", False)):
            config["enabled"] = False
            self.credentials.save(config)
        runtime = self._load_runtime()
        process = self._process
        pid = int(runtime.get("pid") or 0) if runtime else 0

        if process is not None and process.poll() is None:
            try:
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait(timeout=5)
        elif pid > 0 and self._runtime_owned(runtime, config):
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=15,
                        shell=False,
                    )
                else:
                    os.kill(pid, signal.SIGTERM)
            except (OSError, subprocess.TimeoutExpired):
                pass

        self._process = None
        try:
            self.runtime_path.unlink()
        except FileNotFoundError:
            pass
        return self.status()

    def _daemon_status(self) -> dict[str, Any]:
        if not self.daemon_state_path.is_file():
            return {"state": "not-running", "heartbeat_fresh": False}
        try:
            payload = json.loads(self.daemon_state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"state": "invalid", "heartbeat_fresh": False}
        if not isinstance(payload, dict):
            return {"state": "invalid", "heartbeat_fresh": False}
        try:
            heartbeat = float(payload.get("heartbeat_unix") or 0)
        except (TypeError, ValueError):
            heartbeat = 0.0
        age = max(0.0, time.time() - heartbeat) if heartbeat > 0 else None
        return {
            "state": str(payload.get("state") or "unknown"),
            "heartbeat_fresh": age is not None and age <= 20.0,
            "heartbeat_age_seconds": round(age, 1) if age is not None else None,
            "failures": int(payload.get("failures") or 0),
            "last_error": payload.get("last_error"),
        }

    def status(self) -> dict[str, Any]:
        config = self._configured()
        runtime = self._load_runtime()
        process = self._process
        in_process = bool(process is not None and process.poll() is None)
        persisted = bool(runtime and self._runtime_owned(runtime, config))
        running = in_process or persisted
        pid = process.pid if in_process else (int(runtime.get("pid") or 0) if persisted else None)
        if runtime and not persisted and not in_process:
            try:
                self.runtime_path.unlink()
            except FileNotFoundError:
                pass
        return {
            "configured": bool(config.get("tunnel_id") and config.get("api_key")),
            "enabled": bool(config.get("enabled", False)),
            "tunnel_id": config.get("tunnel_id"),
            "profile": config.get("profile") or "ordax-dev",
            "initialized": bool(config.get("initialized")),
            "client_installed": self.binary() is not None,
            "client_path": str(self.binary()) if self.binary() else None,
            "running": running,
            "pid": pid,
            "started_at_unix": runtime.get("started_at_unix") if persisted else None,
            "chatgpt_url": CHATGPT_URL,
            "tunnels_url": TUNNELS_URL,
            "api_keys_url": API_KEYS_URL,
            "daemon": self._daemon_status(),
        }

    @staticmethod
    def _product_root() -> Path:
        packaged = os.environ.get("ORDAX_PACKAGED_ROOT")
        if packaged:
            root = Path(packaged).expanduser().resolve()
            if root.is_dir():
                return root
        return Path(__file__).resolve().parents[1]

    @classmethod
    def _startup_script(cls) -> Path:
        return cls._product_root() / "scripts" / "windows" / "ordax-chat-web-bridge-install.ps1"

    @classmethod
    def _run_startup_script(cls, *arguments: str) -> dict[str, Any]:
        if os.name != "nt":
            raise RuntimeError("Web Bridge startup task is only supported on Windows")
        script = cls._startup_script()
        if not script.is_file():
            raise RuntimeError(f"Web Bridge startup installer is missing: {script}")
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-RepoRoot",
            str(cls._product_root()),
            *arguments,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        if result.returncode != 0:
            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()[-4000:]
            raise RuntimeError(f"Web Bridge startup task failed ({result.returncode}): {output}")
        lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("Web Bridge startup task returned no status")
        try:
            payload = json.loads(lines[-1])
        except json.JSONDecodeError as error:
            raise RuntimeError("Web Bridge startup task returned invalid status") from error
        return payload if isinstance(payload, dict) else {"value": payload}

    @classmethod
    def startup_status(cls) -> dict[str, Any]:
        if os.name != "nt":
            return {
                "supported": False,
                "installed": False,
                "state": "Unsupported",
                "task_name": "ORDAX Dev Web Bridge",
            }
        payload = cls._run_startup_script("-Status")
        payload["supported"] = True
        return payload

    @classmethod
    def install_startup(cls, *, start_now: bool = True) -> dict[str, Any]:
        arguments = ["-StartNow"] if start_now else []
        return cls._run_startup_script(*arguments)

    @classmethod
    def uninstall_startup(cls) -> dict[str, Any]:
        return cls._run_startup_script("-Uninstall")

    @staticmethod
    def open_tunnels_page() -> bool:
        return bool(webbrowser.open(TUNNELS_URL, new=2))

    @staticmethod
    def open_api_keys_page() -> bool:
        return bool(webbrowser.open(API_KEYS_URL, new=2))
