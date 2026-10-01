"""Headless ORDAX autonomy supervisor for 24x7 project work."""
from __future__ import annotations

import signal
import threading
import time
from typing import Any

from .autonomy_service import AutonomyService
from .runtime import OrdaxChatRuntime


class AutonomyDaemon:
    """Keeps persisted autonomy active independently from the desktop window."""

    def __init__(
        self,
        runtime: OrdaxChatRuntime | None = None,
        service: AutonomyService | None = None,
    ):
        self.runtime = runtime or OrdaxChatRuntime()
        self.service = service or AutonomyService(self.runtime)

    def sync_once(self) -> dict[str, Any]:
        config = self.service.preferences.load()
        status = self.service.status()

        if not config.get("enabled"):
            if status.get("running"):
                return self.service.stop(
                    timeout_seconds=10.0,
                    disable_persisted=False,
                )
            return status

        expected_model = str(config.get("model") or "")
        expected_projects = tuple(sorted(config.get("project_slugs") or []))
        if status.get("running"):
            current_projects = tuple(sorted(status.get("project_slugs") or ()))
            if status.get("model") == expected_model and current_projects == expected_projects:
                return status
            self.service.stop(
                timeout_seconds=10.0,
                disable_persisted=False,
            )

        # This also retries a previously-contended cross-process lock. Only one
        # desktop/daemon process can own the supervisor at any given time.
        return self.service.resume_persisted()

    def run_forever(
        self,
        *,
        stop_event: threading.Event,
        poll_seconds: float = 5.0,
    ) -> None:
        if poll_seconds < 0.5 or poll_seconds > 300:
            raise ValueError("poll_seconds must be between 0.5 and 300")
        while not stop_event.is_set():
            try:
                self.sync_once()
            except Exception:
                # AutonomyService preserves detailed execution errors. The daemon
                # stays alive so account reauth/project remount can recover later.
                pass
            stop_event.wait(poll_seconds)
        self.service.stop(
            timeout_seconds=10.0,
            disable_persisted=False,
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

    daemon = AutonomyDaemon()
    try:
        daemon.run_forever(stop_event=stop)
    except KeyboardInterrupt:
        stop.set()
        daemon.service.stop(timeout_seconds=10.0, disable_persisted=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
