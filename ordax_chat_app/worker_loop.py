"""Crash-safe worker loop for persistent ORDAX agent work items."""
from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Event
from typing import Callable

from ordax_core import OrchestratorStore


@dataclass(frozen=True)
class WorkOutcome:
    ok: bool
    result: str = ""
    error: str = ""
    retryable: bool = True
    retry_delay_seconds: float = 30.0


class WorkerLoop:
    """Claims one leased work item at a time and never calls the handler when idle."""

    def __init__(
        self,
        store: OrchestratorStore,
        *,
        agent_id: str,
        runner_id: str,
        handler: Callable[[dict], WorkOutcome],
        lease_seconds: int = 300,
    ):
        self.store = store
        self.agent_id = agent_id
        self.runner_id = runner_id
        self.handler = handler
        self.lease_seconds = lease_seconds

    def run_once(self) -> dict:
        work = self.store.claim_next_work(
            self.agent_id,
            self.runner_id,
            lease_seconds=self.lease_seconds,
        )
        if work is None:
            return {"state": "idle", "agent_id": self.agent_id}

        try:
            outcome = self.handler(work)
            if not isinstance(outcome, WorkOutcome):
                raise TypeError("worker handler must return WorkOutcome")
        except Exception as error:
            failed = self.store.fail_work(
                work["id"],
                self.runner_id,
                error=f"{type(error).__name__}: {error}",
                retryable=True,
                retry_delay_seconds=30,
            )
            return {"state": failed["state"], "work": failed, "handler_exception": True}

        if outcome.ok:
            completed = self.store.complete_work(
                work["id"],
                self.runner_id,
                result=outcome.result,
            )
            return {"state": "done", "work": completed}

        failed = self.store.fail_work(
            work["id"],
            self.runner_id,
            error=outcome.error or "worker reported failure",
            retryable=outcome.retryable,
            retry_delay_seconds=outcome.retry_delay_seconds,
        )
        return {"state": failed["state"], "work": failed}

    def run_forever(
        self,
        *,
        stop_event: Event,
        idle_sleep_seconds: float = 2.0,
    ) -> None:
        if idle_sleep_seconds < 0.1:
            raise ValueError("idle_sleep_seconds must be at least 0.1")
        while not stop_event.is_set():
            result = self.run_once()
            if result["state"] == "idle":
                stop_event.wait(idle_sleep_seconds)
