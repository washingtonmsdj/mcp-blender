"""Autonomous 24x7 execution on top of ORDAX work queues and embedded chat."""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from threading import Event
from typing import Any

from .runtime import OrdaxChatRuntime
from .worker_loop import WorkOutcome, WorkerLoop


@dataclass(frozen=True)
class AutonomousRunResult:
    agent_id: str
    state: str
    work_id: str | None = None
    thread_id: str | None = None
    summary: str | None = None


class AutonomousAgentRunner:
    """Executes queued work for one persistent agent using the embedded model/tool loop."""

    def __init__(
        self,
        runtime: OrdaxChatRuntime,
        *,
        agent_id: str,
        model: str,
        context_window_tokens: int = 128000,
        runner_id: str | None = None,
    ):
        self.runtime = runtime
        self.agent_id = agent_id
        self.model = model
        self.context_window_tokens = context_window_tokens
        self.runner_id = runner_id or f"ordax-dev:{os.getpid()}:{uuid.uuid4().hex[:12]}"
        self.last_thread_id: str | None = None

    def _handle(self, work: dict[str, Any]) -> WorkOutcome:
        store = self.runtime.orchestrator
        agent = store.get_agent(self.agent_id)
        if agent["state"] in {"stopped", "waiting"}:
            return WorkOutcome(
                ok=False,
                error=f"agent is {agent['state']}",
                retryable=False,
            )

        session = store.start_session(
            self.agent_id,
            goal_id=work.get("goal_id") or None,
            provider="openai-chatgpt-plan",
            model=self.model,
            context_window_tokens=self.context_window_tokens,
            rollover_ratio=0.80,
        )
        thread = self.runtime.conversations.create_thread(
            project_slug=agent["project_slug"],
            agent_id=self.agent_id,
            session_id=session["id"],
            provider="openai-chatgpt-plan",
            model=self.model,
            title=str(work.get("title") or "Autonomous task"),
        )
        self.last_thread_id = thread["id"]

        instruction = str(work.get("instruction") or "").strip()
        if not instruction:
            return WorkOutcome(ok=False, error="work instruction is empty", retryable=False)

        try:
            result = self.runtime.send_message(thread["id"], instruction)
        except Exception as error:
            return WorkOutcome(
                ok=False,
                error=f"{type(error).__name__}: {error}",
                retryable=True,
                retry_delay_seconds=60,
            )

        summary = result.text.strip() or "Task completed without a textual summary."
        parent_id = agent.get("parent_agent_id")
        if parent_id:
            store.send_message(
                self.agent_id,
                str(parent_id),
                summary,
                kind="result",
                correlation_id=str(work["id"]),
            )
        return WorkOutcome(ok=True, result=summary)

    def run_once(self) -> AutonomousRunResult:
        agent = self.runtime.orchestrator.get_agent(self.agent_id)
        if agent["state"] in {"stopped", "waiting"}:
            return AutonomousRunResult(
                agent_id=self.agent_id,
                state=agent["state"],
                summary=f"agent is {agent['state']}",
            )

        loop = WorkerLoop(
            self.runtime.orchestrator,
            agent_id=self.agent_id,
            runner_id=self.runner_id,
            handler=self._handle,
            lease_seconds=900,
        )
        result = loop.run_once()
        work = result.get("work")
        return AutonomousRunResult(
            agent_id=self.agent_id,
            state=str(result.get("state") or "unknown"),
            work_id=str(work.get("id")) if isinstance(work, dict) and work.get("id") else None,
            thread_id=self.last_thread_id,
            summary=(
                str(work.get("result") or work.get("error") or "")
                if isinstance(work, dict)
                else None
            ),
        )


class AutonomySupervisor:
    """Sequential project-safe scheduler; stays idle without invoking a model."""

    def __init__(
        self,
        runtime: OrdaxChatRuntime,
        *,
        model: str,
        context_window_tokens: int = 128000,
        runner_prefix: str | None = None,
        project_slugs: set[str] | None = None,
    ):
        self.runtime = runtime
        self.model = model
        self.context_window_tokens = context_window_tokens
        self.runner_prefix = runner_prefix or f"ordax-supervisor:{os.getpid()}"
        self.project_slugs = set(project_slugs) if project_slugs is not None else None

    def run_cycle(self) -> list[AutonomousRunResult]:
        results: list[AutonomousRunResult] = []
        for project in self.runtime.projects():
            slug = str(project["slug"])
            if self.project_slugs is not None and slug not in self.project_slugs:
                continue
            status = self.runtime.orchestrator.status(slug)
            for agent in status["agents"]:
                if agent["state"] != "active":
                    continue
                runner = AutonomousAgentRunner(
                    self.runtime,
                    agent_id=str(agent["id"]),
                    model=self.model,
                    context_window_tokens=self.context_window_tokens,
                    runner_id=f"{self.runner_prefix}:{agent['id']}",
                )
                result = runner.run_once()
                if result.state != "idle":
                    results.append(result)
        return results

    def run_forever(self, *, stop_event: Event, idle_sleep_seconds: float = 5.0) -> None:
        if idle_sleep_seconds < 0.5:
            raise ValueError("idle_sleep_seconds must be at least 0.5")
        while not stop_event.is_set():
            results = self.run_cycle()
            if not results:
                stop_event.wait(idle_sleep_seconds)
