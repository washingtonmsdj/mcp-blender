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

    def _enqueue_coordinator_followups(self, project_slug: str) -> int:
        """Turn unread worker reports into durable coordinator work.

        Messages are marked read only after the follow-up work item is persisted,
        so a crash cannot silently lose a worker result.
        """
        created = 0
        status = self.runtime.orchestrator.status(project_slug)
        coordinators = [
            agent
            for agent in status["agents"]
            if agent["state"] == "active" and agent.get("parent_agent_id") is None
        ]
        for coordinator in coordinators:
            inbox = self.runtime.orchestrator.inbox(
                str(coordinator["id"]),
                unread_only=True,
                limit=100,
            )
            if not inbox:
                continue
            lines = [
                "Review these worker reports, verify the project state, and decide the next actions. "
                "Delegate follow-up work when useful; otherwise finish the objective."
            ]
            for message in inbox:
                sender = self.runtime.orchestrator.get_agent(str(message["sender_agent_id"]))
                correlation = str(message.get("correlation_id") or "")
                prefix = f"[{sender['name']} / {sender['role']}]"
                if correlation:
                    prefix += f" task={correlation}"
                lines.append(prefix + "\n" + str(message["content"]))
            work = self.runtime.orchestrator.enqueue_work(
                str(coordinator["id"]),
                "Review worker results",
                "\n\n".join(lines),
                priority=90,
                max_attempts=3,
            )
            if not work.get("id"):
                continue
            for message in inbox:
                self.runtime.orchestrator.mark_message_read(
                    str(coordinator["id"]),
                    int(message["id"]),
                )
            created += 1
        return created

    def run_cycle(self) -> list[AutonomousRunResult]:
        results: list[AutonomousRunResult] = []
        selected_projects: list[str] = []
        for project in self.runtime.projects():
            slug = str(project["slug"])
            if self.project_slugs is not None and slug not in self.project_slugs:
                continue
            selected_projects.append(slug)
            # Process coordinator work before workers so a Prime can delegate and
            # the worker can pick up the task in the same cycle.
            status = self.runtime.orchestrator.status(slug)
            agents = sorted(
                status["agents"],
                key=lambda item: (item.get("parent_agent_id") is not None, item["created_at"]),
            )
            for agent in agents:
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

        # Worker results produced during this cycle become durable Prime work for
        # the next cycle. run_forever will immediately continue while activity exists.
        for slug in selected_projects:
            self._enqueue_coordinator_followups(slug)
        return results

    def run_forever(self, *, stop_event: Event, idle_sleep_seconds: float = 5.0) -> None:
        if idle_sleep_seconds < 0.5:
            raise ValueError("idle_sleep_seconds must be at least 0.5")
        while not stop_event.is_set():
            results = self.run_cycle()
            if not results:
                stop_event.wait(idle_sleep_seconds)
