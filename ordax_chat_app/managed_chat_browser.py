"""Managed Chromium host for the ORDAX Browser Companion.

This is deliberately not a browser-automation channel. It launches a dedicated,
persistent Chromium profile with the unpacked ORDAX Browser Companion extension
and ChatGPT Web. The Companion remains the only bridge between the page and ORDAX.
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Any

from ordax_dev_agent.browser_capture import find_chromium

from .auth import resolve_chat_app_state_dir


CHATGPT_URL = "https://chatgpt.com/"


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
        self.browser_path = (
            Path(browser_path).expanduser().resolve()
            if browser_path
            else None
        )
        self._process: subprocess.Popen | None = None
        self._lock = threading.RLock()

    def _browser(self) -> Path:
        browser = self.browser_path or find_chromium()
        if browser is None or not Path(browser).is_file():
            raise RuntimeError("Chrome or Edge was not found")
        return Path(browser).resolve()

    def status(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            running = bool(process is not None and process.poll() is None)
        browser = None
        try:
            browser = str(self._browser())
        except RuntimeError:
            pass
        return {
            "running": running,
            "pid": process.pid if running and process is not None else None,
            "browser": browser,
            "profile_dir": str(self.profile_dir),
            "extension_dir": str(self.extension_dir),
            "extension_available": self.extension_dir.is_dir(),
            "chat_url": CHATGPT_URL,
        }

    def start(self) -> dict[str, Any]:
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
            args = [
                str(browser),
                f"--user-data-dir={self.profile_dir}",
                f"--disable-extensions-except={self.extension_dir}",
                f"--load-extension={self.extension_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                f"--app={CHATGPT_URL}",
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
