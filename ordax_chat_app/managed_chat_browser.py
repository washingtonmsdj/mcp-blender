"""Managed Chromium host for the ORDAX Browser Companion.

The ORDAX normal-chat surface needs an extension-capable browser that is stable
and isolated from the user's primary browser. Branded Google Chrome may ignore
command-line extension loading, so ORDAX can install a private Chrome for Testing
runtime into its own state directory. The user's normal Chrome profile is never
modified.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from ordax_dev_agent.browser_capture import find_chromium

from .auth import resolve_chat_app_state_dir


CHATGPT_URL = "https://chatgpt.com/"
CFT_METADATA_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/"
    "last-known-good-versions-with-downloads.json"
)
CFT_DOWNLOAD_PREFIX = "https://storage.googleapis.com/chrome-for-testing-public/"


class ManagedChatBrowser:
    def __init__(
        self,
        *,
        extension_dir: str | Path,
        state_dir: str | Path | None = None,
        browser_path: str | Path | None = None,
    ):
        self.extension_dir = Path(extension_dir).expanduser().resolve()
        self.state_dir = (
            Path(state_dir).expanduser().resolve()
            if state_dir
            else resolve_chat_app_state_dir() / "chat-browser"
        )
        self.profile_dir = self.state_dir / "profile"
        self.browser_dir = self.state_dir / "browser"
        self.browser_metadata_path = self.browser_dir / "browser.json"
        self.browser_path = (
            Path(browser_path).expanduser().resolve()
            if browser_path
            else None
        )
        self._process: subprocess.Popen | None = None
        self._lock = threading.RLock()

    def _private_browser(self) -> Path | None:
        candidates = [
            self.browser_dir / "chrome-win64" / "chrome.exe",
            self.browser_dir / "chrome" / "chrome.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None

    @staticmethod
    def _edge_candidates() -> list[Path]:
        if os.name != "nt":
            return []
        values = [
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("ProgramFiles"),
            os.environ.get("LOCALAPPDATA"),
        ]
        candidates: list[Path] = []
        for value in values:
            if not value:
                continue
            base = Path(value)
            if base.name.lower() == "local":
                candidates.append(base / "Microsoft" / "Edge" / "Application" / "msedge.exe")
            else:
                candidates.append(base / "Microsoft" / "Edge" / "Application" / "msedge.exe")
        return candidates

    def _browser(self) -> Path:
        if self.browser_path is not None:
            if not self.browser_path.is_file():
                raise RuntimeError(f"Configured browser was not found: {self.browser_path}")
            return self.browser_path

        private = self._private_browser()
        if private is not None:
            return private

        for candidate in self._edge_candidates():
            if candidate.is_file():
                return candidate.resolve()

        detected = find_chromium()
        if detected is None or not Path(detected).is_file():
            raise RuntimeError(
                "No extension-capable browser is available. Install the ORDAX managed browser."
            )
        detected_path = Path(detected).resolve()
        if (
            os.name == "nt"
            and detected_path.name.lower() == "chrome.exe"
            and "google" in str(detected_path).lower()
        ):
            raise RuntimeError(
                "Google Chrome installed on this computer blocks ORDAX unpacked-extension "
                "startup. Install the ORDAX managed browser."
            )
        return detected_path

    def _browser_metadata(self) -> dict[str, Any] | None:
        try:
            payload = json.loads(self.browser_metadata_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _validate_download_url(url: str) -> str:
        value = str(url or "").strip()
        if not value.startswith(CFT_DOWNLOAD_PREFIX):
            raise RuntimeError("Unexpected Chrome for Testing download origin")
        if not value.endswith(".zip"):
            raise RuntimeError("Chrome for Testing download must be a ZIP archive")
        return value

    @staticmethod
    def _verify_windows_signature(executable: Path) -> None:
        if os.name != "nt":
            return
        env = dict(os.environ)
        env["ORDAX_CFT_EXE"] = str(executable)
        command = (
            "$s=Get-AuthenticodeSignature -FilePath $env:ORDAX_CFT_EXE;"
            "$subject=if($s.SignerCertificate){$s.SignerCertificate.Subject}else{''};"
            "Write-Output ($s.Status.ToString()+'|'+$subject)"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            shell=False,
            check=False,
        )
        output = (result.stdout or "").strip()
        if result.returncode != 0 or not output.startswith("Valid|"):
            raise RuntimeError(
                "Chrome for Testing executable failed Windows signature validation"
            )
        if "Google" not in output:
            raise RuntimeError(
                "Chrome for Testing executable is not signed by Google"
            )

    def install_browser(self) -> dict[str, Any]:
        if os.name != "nt":
            raise RuntimeError("Managed Chrome for Testing install currently supports Windows")

        request = urllib.request.Request(
            CFT_METADATA_URL,
            headers={"User-Agent": "ORDAX-Dev"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)

        stable = payload.get("channels", {}).get("Stable", {})
        version = str(stable.get("version") or "").strip()
        downloads = stable.get("downloads", {}).get("chrome", [])
        candidate = next(
            (
                item
                for item in downloads
                if isinstance(item, dict) and item.get("platform") == "win64"
            ),
            None,
        )
        if not version or not candidate:
            raise RuntimeError("Chrome for Testing Stable win64 metadata is unavailable")
        download_url = self._validate_download_url(candidate.get("url"))

        self.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(self.state_dir)) as temp_dir:
            temp_root = Path(temp_dir)
            archive = temp_root / "chrome-for-testing.zip"
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "ORDAX-Dev"},
            )
            with urllib.request.urlopen(req, timeout=180) as response, archive.open("wb") as handle:
                shutil.copyfileobj(response, handle)

            extract_dir = temp_root / "extract"
            extract_dir.mkdir()
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extract_dir)

            executable = extract_dir / "chrome-win64" / "chrome.exe"
            if not executable.is_file():
                raise RuntimeError("Chrome for Testing archive does not contain chrome.exe")
            self._verify_windows_signature(executable)

            target_root = self.browser_dir / "chrome-win64"
            self.browser_dir.mkdir(parents=True, exist_ok=True)
            if target_root.exists():
                shutil.rmtree(target_root)
            shutil.move(str(executable.parent), str(target_root))

        metadata = {
            "schema": "ordax.managed-browser/1",
            "version": version,
            "platform": "win64",
            "source": download_url,
        }
        self.browser_metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            **self.status(),
            "installed_version": version,
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            running = bool(process is not None and process.poll() is None)

        browser = None
        browser_error = None
        try:
            browser = str(self._browser())
        except RuntimeError as error:
            browser_error = str(error)

        private = self._private_browser()
        return {
            "running": running,
            "pid": process.pid if running and process is not None else None,
            "browser": browser,
            "browser_error": browser_error,
            "managed_runtime_installed": private is not None,
            "managed_runtime": self._browser_metadata(),
            "profile_dir": str(self.profile_dir),
            "extension_dir": str(self.extension_dir),
            "extension_available": (self.extension_dir / "manifest.json").is_file(),
            "chat_url": CHATGPT_URL,
        }

    @staticmethod
    def _safe_initial_url(initial_url: str | None) -> str:
        value = str(initial_url or CHATGPT_URL).strip()
        if value == CHATGPT_URL:
            return value
        if value.startswith("http://127.0.0.1:8775/bootstrap?code="):
            code = value.split("=", 1)[1]
            if code.isdigit() and len(code) == 8:
                return value
        raise ValueError("unsupported managed ChatGPT browser initial URL")

    def start(self, *, initial_url: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self.status()
            if not (self.extension_dir / "manifest.json").is_file():
                raise RuntimeError(
                    f"ORDAX Browser Companion extension is missing: {self.extension_dir}"
                )
            browser = self._browser()
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            flags = 0
            if os.name == "nt":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP
            target_url = self._safe_initial_url(initial_url)
            args = [
                str(browser),
                f"--user-data-dir={self.profile_dir}",
                f"--disable-extensions-except={self.extension_dir}",
                f"--load-extension={self.extension_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                f"--app={target_url}",
            ]
            self._process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                creationflags=flags,
            )
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            self._process = None
        if process is not None and process.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        shell=False,
                        timeout=10,
                        check=False,
                    )
                else:
                    process.terminate()
                    process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        return self.status()
