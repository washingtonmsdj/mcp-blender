"""Headless supervisor for the ORDAX Secure MCP Web Bridge."""
from __future__ import annotations

import json
import signal
import threading
import time
from pathlib import Path
from typing import Any

from .auth import resolve_chat_app_state_dir
from .auth.local_state import _atomic_write
from .web_bridge import WebBridgeManager


class WebBridgeDaemon:
    """Keep the configured Secure MCP tunnel alive without invoking any model."""

    def __init__(
        self,
        manager: WebBridgeManager | None = None,
        *,
        state_path: str | Path | None = None,
    ):
        self.manager = manager or WebBridgeManager()
        self.state_path = (
            Path(state_path).expanduser().resolve()
            if state_path
            else resolve_chat_app_state_dir() / "web-bridge-daemon.json"
        )
        self.failures = 0

    def _write_state(
        self,
        *,
        state: str,
        bridge: dict[str, Any],
        error: str | None = None,
        retry_seconds: float | None = None,
    ) -> dict[str, Any]:
        payload = {
            "schema_version": 1,
            "state": state,
            "configured": bool(bridge.get("configured")),
            "running": bool(bridge.get("running")),
            "tunnel_id": bridge.get("tunnel_id"),
            "profile": bridge.get("profile"),
            "pid": bridge.get("pid"),
            "failures": self.failures,
            "last_error": error,
            "retry_seconds": retry_seconds,
            "heartbeat_unix": time.time(),
        }
        _atomic_write(
            self.state_path,
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            mode=0o600,
        )
        return payload

    def sync_once(self) -> dict[str, Any]:
        bridge = self.manager.status()
        if not bridge.get("configured"):
            self.failures = 0
            return self._write_state(state="unconfigured", bridge=bridge)

        if not bridge.get("enabled"):
            self.failures = 0
            if bridge.get("running"):
                bridge = self.manager.stop(persist_disabled=False)
            return self._write_state(state="disabled", bridge=bridge)

        if bridge.get("running"):
            self.failures = 0
            return self._write_state(state="healthy", bridge=bridge)

        try:
            bridge = self.manager.start(persist_enabled=False)
        except Exception as error:
            self.failures += 1
            retry = min(300.0, max(5.0, float(2 ** min(self.failures, 8))))
            return self._write_state(
                state="degraded",
                bridge=self.manager.status(),
                error=f"{type(error).__name__}: {error}",
                retry_seconds=retry,
            )

        self.failures = 0
        return self._write_state(
            state="healthy" if bridge.get("running") else "degraded",
            bridge=bridge,
            error=None if bridge.get("running") else "Web Bridge start returned without a running tunnel",
            retry_seconds=None if bridge.get("running") else 5.0,
        )

    def run_forever(
        self,
        *,
        stop_event: threading.Event,
        poll_seconds: float = 5.0,
    ) -> None:
        if poll_seconds < 1.0 or poll_seconds > 300:
            raise ValueError("poll_seconds must be between 1 and 300")

        while not stop_event.is_set():
            try:
                state = self.sync_once()
                delay = float(state.get("retry_seconds") or poll_seconds)
            except Exception as error:
                self.failures += 1
                delay = min(300.0, max(5.0, float(2 ** min(self.failures, 8))))
                try:
                    bridge = self.manager.status()
                except Exception:
                    bridge = {}
                self._write_state(
                    state="degraded",
                    bridge=bridge,
                    error=f"{type(error).__name__}: {error}",
                    retry_seconds=delay,
                )
            stop_event.wait(delay)

        try:
            bridge = self.manager.stop(persist_disabled=False)
            self._write_state(state="stopped", bridge=bridge)
        except Exception as error:
            try:
                bridge = self.manager.status()
            except Exception:
                bridge = {}
            self._write_state(
                state="stopped",
                bridge=bridge,
                error=f"{type(error).__name__}: {error}",
            )


def main() -> int:
    stop = threading.Event()

    def request_stop(_signum=None, _frame=None):
        stop.set()

    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, request_stop)
            except (ValueError, OSError):
                pass

    daemon = WebBridgeDaemon()
    try:
        daemon.run_forever(stop_event=stop)
    except KeyboardInterrupt:
        stop.set()
        daemon.manager.stop(persist_disabled=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
