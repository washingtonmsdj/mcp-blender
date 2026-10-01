"""Composition root for the ORDAX Dev embedded chat runtime."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from ordax_core import OrchestratorStore
from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig

from .agent_engine import AgentChatEngine, AgentChatResult
from .auth import OpenAISignInClient
from .conversations import ConversationStore
from .providers import ModelProvider, OpenAIChatGPTPlanProvider
from .project_context import ProjectContextLoader
from .toolset import DevelopmentToolset


COMPACTION_PROMPT = """Create a compact continuation checkpoint for another session of the same development agent.
Preserve only durable information needed to continue accurately: current objective, completed work, key technical decisions,
important files, commands/tests and results, blockers, unresolved risks, and the exact next action. Do not add new work.
Return concise plain text suitable for injecting into a fresh model context."""


@dataclass(frozen=True)
class RuntimeChatResult:
    thread_id: str
    text: str
    tool_calls: int
    model_rounds: int
    session_rotated: bool
    session_id: str
    compaction_error: str | None = None


class OrdaxChatRuntime:
    def __init__(
        self,
        *,
        agent: ActionRegistry | None = None,
        sign_in: OpenAISignInClient | None = None,
        conversations: ConversationStore | None = None,
        provider_factory: Callable[[], ModelProvider] | None = None,
    ):
        self.agent = agent or ActionRegistry(AgentConfig.from_env())
        memory = self.agent._memory_store_instance()
        self.orchestrator = OrchestratorStore(memory.db_path)
        self.conversations = conversations or ConversationStore(memory.db_path)
        self.sign_in = sign_in or OpenAISignInClient()
        self.provider_factory = provider_factory
        self.project_context = ProjectContextLoader()

    def account_status(self) -> dict[str, Any]:
        selected = self.sign_in.account_store.selected()
        return {
            "connected": bool(selected and selected.access_token and selected.refresh_token),
            "account": None if selected is None else {
                "key": selected.key,
                "email": selected.email,
                "name": selected.name,
                "client_id": selected.client_id,
                "scopes": selected.scopes,
                "expires_at_unix": selected.expires_at_unix,
            },
        }

    def connect_chatgpt(self) -> dict[str, Any]:
        account = self.sign_in.sign_in_interactive()
        return {
            "key": account.key,
            "email": account.email,
            "name": account.name,
            "scopes": account.scopes,
        }

    def models(self) -> list[dict[str, Any]]:
        provider = self._provider()
        return [
            {"id": model.id, "display_name": model.display_name}
            for model in provider.list_models()
        ]

    def projects(self) -> list[dict[str, Any]]:
        return [project.public() for project in self.agent.projects.values() if project.root.is_dir()]

    def _provider(self) -> ModelProvider:
        if self.provider_factory is not None:
            return self.provider_factory()
        return OpenAIChatGPTPlanProvider(lambda: self.sign_in.access_token())

    def _coordinator(self, project_slug: str) -> dict[str, Any]:
        status = self.orchestrator.status(project_slug)
        for agent in status["agents"]:
            if agent["parent_agent_id"] is None and agent["role"] == "chat coordinator":
                return agent
        return self.orchestrator.create_agent(project_slug, "Prime", "chat coordinator")

    def new_thread(
        self,
        *,
        project: str,
        model: str,
        context_window_tokens: int = 128000,
    ) -> dict[str, Any]:
        selected = self.agent.select_available_project(project)
        coordinator = self._coordinator(selected)
        session = self.orchestrator.start_session(
            coordinator["id"],
            goal_id=None,
            provider="openai-chatgpt-plan",
            model=model,
            context_window_tokens=context_window_tokens,
            rollover_ratio=0.80,
        )
        return self.conversations.create_thread(
            project_slug=selected,
            agent_id=coordinator["id"],
            session_id=session["id"],
            provider="openai-chatgpt-plan",
            model=model,
        )

    def threads(self, project: str | None = None) -> list[dict[str, Any]]:
        return self.conversations.list_threads(project)

    def messages(self, thread_id: str) -> list[dict[str, Any]]:
        return self.conversations.messages(thread_id)

    def send_message(
        self,
        thread_id: str,
        text: str,
        *,
        on_delta: Callable[[str], None] | None = None,
    ) -> RuntimeChatResult:
        thread = self.conversations.thread(thread_id)
        prior = self.conversations.items(thread_id)
        provider = self._provider()
        engine = AgentChatEngine(
            provider,
            DevelopmentToolset(self.agent, project=thread["project_slug"]),
            orchestrator=self.orchestrator,
            session_id=thread["session_id"],
        )
        result = engine.run_turn(
            model=thread["model"],
            user_text=text,
            prior_items=prior,
            instructions=self._instructions(thread["project_slug"]),
            on_delta=on_delta,
        )

        new_items = result.items[len(prior):]
        self.conversations.append_items(thread_id, new_items)
        self.conversations.append_message(thread_id, "user", text)
        if result.text:
            self.conversations.append_message(thread_id, "assistant", result.text)
        if thread["title"] == "New chat":
            title = " ".join(text.strip().split())[:80]
            if title:
                self.conversations.set_title(thread_id, title)

        rotated = False
        compaction_error = None
        session_id = thread["session_id"]
        if result.rollover_recommended:
            try:
                session_id = self._compact_and_rotate(
                    thread_id=thread_id,
                    thread=thread,
                    provider=provider,
                    items=result.items,
                )
                rotated = True
            except Exception as error:
                compaction_error = f"{type(error).__name__}: {error}"

        return RuntimeChatResult(
            thread_id=thread_id,
            text=result.text,
            tool_calls=result.tool_calls,
            model_rounds=result.model_rounds,
            session_rotated=rotated,
            session_id=session_id,
            compaction_error=compaction_error,
        )

    def _compact_and_rotate(
        self,
        *,
        thread_id: str,
        thread: dict[str, Any],
        provider: ModelProvider,
        items: list[dict[str, Any]],
    ) -> str:
        compact_input = [dict(item) for item in items]
        compact_input.append({"role": "user", "content": COMPACTION_PROMPT})
        compact = provider.run_turn(
            model=thread["model"],
            input_items=compact_input,
            instructions="You are the ORDAX session handoff writer. Do not call tools.",
            tools=None,
        )
        if not compact.text.strip():
            raise RuntimeError("model returned an empty continuation checkpoint")

        usage = compact.usage or {}
        self.orchestrator.record_usage(
            thread["session_id"],
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
        )
        project = self.agent._project({"project": thread["project_slug"]})
        rotated = self.orchestrator.rotate_session(
            thread["session_id"],
            summary=compact.text.strip(),
            next_action="Continue the same development objective from the checkpoint.",
            completed=[],
            blockers=[],
            changed_paths=[],
            git_state=self.agent._memory_store_instance().git_state(project.root),
        )
        successor = rotated["session"]
        checkpoint = rotated["checkpoint"]
        seed = {
            "role": "user",
            "content": (
                "[ORDAX CONTINUATION CHECKPOINT]\n"
                + checkpoint["summary"]
                + "\n\nNext action: "
                + checkpoint["next_action"]
            ),
        }
        self.conversations.replace_items(thread_id, [seed])
        self.conversations.update_session(thread_id, successor["id"])
        return successor["id"]

    def _instructions(self, project_slug: str) -> str:
        project = self.agent._project({"project": project_slug})
        context = self.project_context.load(project.root)
        base = (
            "You are the development agent inside ORDAX Dev. Work directly on the selected project using the supplied tools. "
            "Inspect before editing, preserve existing architecture, fix root causes, run relevant tests/builds, and verify your changes. "
            "Never pretend a tool ran. The project scope is enforced by ORDAX and must not be bypassed. "
            f"Selected project: {project_slug}."
        )
        extra = context.instructions_block()
        return base if not extra else base + "\n\n" + extra
