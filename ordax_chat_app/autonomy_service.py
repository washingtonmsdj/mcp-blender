"""Lifecycle controller for the ORDAX 24x7 autonomy supervisor."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from typing import Any

from .autonomy import AutonomySupervisor
from .runtime import OrdaxChatRuntime


@dataclass
class AutonomyServiceState:
    running: bool = False
    model: str | None = None
    started_at_unix: float | None = None
    cycles: int = 0
    completed_runs: int = 0
    last_activity_at_unix: float | None = None
    last_error: str | None = None


class AutonomyService:
    """Runs the sequential project-safe supervisor on a recoverable daemon thread."""

    def __init__(self, runtime: OrdaxChatRuntime):
        self.runtime = runtime
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = AutonomyServiceState()

    def status(self) -> dict[str, Any]:
        with self._lock:
            state = asdict(self._state)
            state["thread_alive"] = bool(self._thread and self._thread.is_alive())
            return state

    def start(
        self,
        *,
        model: str,
        context_window_tokens: int = 128000,
        idle_sleep_seconds: float = 5.0,
    ) -> dict[str, Any]:
        model = model.strip()
        if not model:
            raise ValueError("model is required")
        if idle_sleep_seconds < 0.5 or idle_sleep_seconds > 300:
            raise ValueError("idle_sleep_seconds must be between 0.5 and 300")
        if context_window_tokens < 4096:
            raise ValueError("context_window_tokens must be at least 4096")

        with self._lock:
            if self._thread and self._thread.is_alive():
                if self._state.model != model:
                    raise RuntimeError(
                        f"autonomy is already running with model {self._state.model}"
                    )
                return self.status()
            self._stop = threading.Event()
            self._state = AutonomyServiceState(
                running=True,
                model=model,
                started_at_unix=time.time(),
            )
            self._thread = threading.Thread(
                target=self._run,
                kwargs={
                    "model": model,
                    "context_window_tokens": int(context_window_tokens),
                    "idle_sleep_seconds": float(idle_sleep_seconds),
                },
                name="ordax-autonomy-supervisor",
                daemon=True,
            )
            self._thread.start()
        return self.status()

    def stop(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(0.1, timeout_seconds))
        with self._lock:
            self._state.running = bool(thread and thread.is_alive())
        return self.status()

    def _run(
        self,
        *,
        model: str,
        context_window_tokens: int,
        idle_sleep_seconds: float,
    ) -> None:
        supervisor = AutonomySupervisor(
            self.runtime,
            model=model,
            context_window_tokens=context_window_tokens,
        )
        while not self._stop.is_set():
            try:
                results = supervisor.run_cycle()
                now = time.time()
                with self._lock:
                    self._state.cycles += 1
                    if results:
                        self._state.completed_runs += len(results)
                        self._state.last_activity_at_unix = now
                    self._state.last_error = None
                if not results:
                    self._stop.wait(idle_sleep_seconds)
            except Exception as error:
                with self._lock:
                    self._state.last_error = f"{type(error).__name__}: {error}"
                self._stop.wait(min(max(idle_sleep_seconds, 1.0), 30.0))
        with self._lock:
            self._state.running = False
