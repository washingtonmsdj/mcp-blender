"""Lifecycle controller for the ORDAX 24x7 autonomy supervisor."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from typing import Any

from .autonomy import AutonomySupervisor
from .autonomy_preferences import AutonomyPreferencesStore
from .runtime import OrdaxChatRuntime


@dataclass
class AutonomyServiceState:
    running: bool = False
    model: str | None = None
    project_slugs: tuple[str, ...] = ()
    started_at_unix: float | None = None
    cycles: int = 0
    completed_runs: int = 0
    last_activity_at_unix: float | None = None
    last_error: str | None = None


class AutonomyService:
    """Runs the project-safe supervisor and persists the explicit 24x7 opt-in."""

    def __init__(
        self,
        runtime: OrdaxChatRuntime,
        *,
        preferences: AutonomyPreferencesStore | None = None,
    ):
        self.runtime = runtime
        self.preferences = preferences or AutonomyPreferencesStore()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = AutonomyServiceState()

    def status(self) -> dict[str, Any]:
        with self._lock:
            state = asdict(self._state)
            state["thread_alive"] = bool(self._thread and self._thread.is_alive())
        try:
            persisted = self.preferences.load()
            state["persisted_enabled"] = bool(persisted.get("enabled"))
            state["persisted_model"] = persisted.get("model")
            state["persisted_project_slugs"] = tuple(persisted.get("project_slugs", []))
        except Exception as error:
            state["persisted_enabled"] = False
            state["preferences_error"] = f"{type(error).__name__}: {error}"
        return state

    def start(
        self,
        *,
        model: str,
        project_slugs: list[str] | tuple[str, ...] | set[str],
        context_window_tokens: int = 128000,
        idle_sleep_seconds: float = 5.0,
        persist: bool = True,
    ) -> dict[str, Any]:
        model = model.strip()
        if not model:
            raise ValueError("model is required")
        normalized_projects = tuple(sorted({str(item).strip() for item in project_slugs if str(item).strip()}))
        if not normalized_projects:
            raise ValueError("at least one project must be enabled for autonomy")
        if idle_sleep_seconds < 0.5 or idle_sleep_seconds > 300:
            raise ValueError("idle_sleep_seconds must be between 0.5 and 300")
        if context_window_tokens < 4096:
            raise ValueError("context_window_tokens must be at least 4096")

        if persist:
            self.preferences.save(
                enabled=True,
                model=model,
                project_slugs=normalized_projects,
                context_window_tokens=int(context_window_tokens),
                idle_sleep_seconds=float(idle_sleep_seconds),
            )

        with self._lock:
            if self._thread and self._thread.is_alive():
                if self._state.model != model or self._state.project_slugs != normalized_projects:
                    raise RuntimeError(
                        "autonomy is already running with a different model or project scope"
                    )
                return self.status()
            self._stop = threading.Event()
            self._state = AutonomyServiceState(
                running=True,
                model=model,
                project_slugs=normalized_projects,
                started_at_unix=time.time(),
            )
            self._thread = threading.Thread(
                target=self._run,
                kwargs={
                    "model": model,
                    "project_slugs": set(normalized_projects),
                    "context_window_tokens": int(context_window_tokens),
                    "idle_sleep_seconds": float(idle_sleep_seconds),
                },
                name="ordax-autonomy-supervisor",
                daemon=True,
            )
            self._thread.start()
        return self.status()

    def stop(
        self,
        *,
        timeout_seconds: float = 10.0,
        disable_persisted: bool = True,
    ) -> dict[str, Any]:
        if disable_persisted:
            self.preferences.disable()
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(0.1, timeout_seconds))
        with self._lock:
            self._state.running = bool(thread and thread.is_alive())
        return self.status()

    def resume_persisted(self) -> dict[str, Any]:
        config = self.preferences.load()
        if not config.get("enabled"):
            return self.status()

        account_status = self.runtime.account_status()
        if not account_status.get("connected"):
            with self._lock:
                self._state.last_error = "ChatGPT account is disconnected; autonomy resume deferred"
            return self.status()

        available = {str(item["slug"]) for item in self.runtime.projects()}
        requested = tuple(
            slug for slug in config.get("project_slugs", [])
            if slug in available
        )
        if not requested:
            with self._lock:
                self._state.last_error = "No persisted autonomy projects are currently available"
            return self.status()

        model = str(config.get("model") or "").strip()
        if not model:
            with self._lock:
                self._state.last_error = "Persisted autonomy model is missing"
            return self.status()

        return self.start(
            model=model,
            project_slugs=requested,
            context_window_tokens=int(config.get("context_window_tokens", 128000)),
            idle_sleep_seconds=float(config.get("idle_sleep_seconds", 5.0)),
            persist=False,
        )

    def _run(
        self,
        *,
        model: str,
        project_slugs: set[str],
        context_window_tokens: int,
        idle_sleep_seconds: float,
    ) -> None:
        supervisor = AutonomySupervisor(
            self.runtime,
            model=model,
            context_window_tokens=context_window_tokens,
            project_slugs=project_slugs,
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
