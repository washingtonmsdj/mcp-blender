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
            return {"version": 1, "tunnel_id": None, "api_key": None, "profile": "ordax-dev", "initialized": False}
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
        self._process: subprocess.Popen | None = None

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
        }
        self.credentials.save(payload)
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

    def start(self) -> dict[str, Any]:
        config = self._configured()
        self.initialize()
        if self._process is not None and self._process.poll() is None:
            return self.status()
        binary = self.binary()
        if binary is None:
            raise RuntimeError("tunnel-client is not installed")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self._process = subprocess.Popen(
            [str(binary), "run", "--profile", str(config.get("profile") or "ordax-dev")],
            env=self._env(config),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        return self.status()

    def stop(self) -> dict[str, Any]:
        process = self._process
        if process is not None and process.poll() is None:
            try:
                process.send_signal(signal.SIGTERM)
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait(timeout=5)
        self._process = None
        return self.status()

    def status(self) -> dict[str, Any]:
        config = self._configured()
        process = self._process
        running = bool(process is not None and process.poll() is None)
        return {
            "configured": bool(config.get("tunnel_id") and config.get("api_key")),
            "tunnel_id": config.get("tunnel_id"),
            "profile": config.get("profile") or "ordax-dev",
            "initialized": bool(config.get("initialized")),
            "client_installed": self.binary() is not None,
            "client_path": str(self.binary()) if self.binary() else None,
            "running": running,
            "pid": process.pid if running else None,
            "chatgpt_url": CHATGPT_URL,
            "tunnels_url": TUNNELS_URL,
            "api_keys_url": API_KEYS_URL,
        }

    @staticmethod
    def open_tunnels_page() -> bool:
        return bool(webbrowser.open(TUNNELS_URL, new=2))

    @staticmethod
    def open_api_keys_page() -> bool:
        return bool(webbrowser.open(API_KEYS_URL, new=2))
