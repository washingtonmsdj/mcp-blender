"""Agentic chat loop for ORDAX Dev."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ordax_core import OrchestratorStore

from .providers import ChatTurnResult, ModelProvider
from .toolset import DevelopmentToolset


@dataclass(frozen=True)
class AgentChatResult:
    text: str
    items: list[dict[str, Any]]
    tool_calls: int
    model_rounds: int
    response_ids: list[str] = field(default_factory=list)
    rollover_recommended: bool = False


class AgentChatEngine:
    """Runs model → local tools → model until the turn is complete."""

    def __init__(
        self,
        provider: ModelProvider,
        toolset: DevelopmentToolset,
        *,
        orchestrator: OrchestratorStore | None = None,
        session_id: str | None = None,
        max_tool_rounds: int = 24,
    ):
        self.provider = provider
        self.toolset = toolset
        self.orchestrator = orchestrator
        self.session_id = session_id
        self.max_tool_rounds = max_tool_rounds

    @staticmethod
    def _usage_tokens(usage: dict[str, Any]) -> tuple[int, int]:
        def integer(*keys: str) -> int:
            for key in keys:
                value = usage.get(key)
                if isinstance(value, int) and value >= 0:
                    return value
            return 0
        return integer("input_tokens", "input_tokens_total"), integer("output_tokens", "output_tokens_total")

    def _record_usage(self, result: ChatTurnResult) -> bool:
        if self.orchestrator is None or self.session_id is None:
            return False
        input_tokens, output_tokens = self._usage_tokens(result.usage)
        state = self.orchestrator.record_usage(
            self.session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return bool(state.get("should_rollover"))

    def run_turn(
        self,
        *,
        model: str,
        user_text: str,
        prior_items: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> AgentChatResult:
        user_text = user_text.strip()
        if not user_text:
            raise ValueError("user_text is required")

        items: list[dict[str, Any]] = [dict(item) for item in (prior_items or [])]
        items.append({"role": "user", "content": user_text})
        tool_calls = 0
        rounds = 0
        response_ids: list[str] = []
        rollover = False
        final_text = ""

        while True:
            rounds += 1
            result = self.provider.run_turn(
                model=model,
                input_items=items,
                instructions=instructions,
                tools=self.toolset.definitions,
                on_delta=on_delta,
            )
            rollover = self._record_usage(result) or rollover
            if result.response_id:
                response_ids.append(result.response_id)

            output_items = [dict(item) for item in result.output_items]
            items.extend(output_items)
            function_calls = [
                item for item in output_items
                if item.get("type") == "function_call"
            ]
            if not function_calls:
                final_text = result.text
                break

            if rounds > self.max_tool_rounds:
                raise RuntimeError(
                    f"agent exceeded {self.max_tool_rounds} tool rounds in one user turn"
                )

            for call in function_calls:
                call_id = str(call.get("call_id") or "")
                name = str(call.get("name") or "")
                arguments = str(call.get("arguments") or "{}")
                if not call_id or not name:
                    raise RuntimeError("model returned an invalid function_call item")
                output = self.toolset.execute(name, arguments)
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": output,
                    }
                )
                tool_calls += 1

        return AgentChatResult(
            text=final_text,
            items=items,
            tool_calls=tool_calls,
            model_rounds=rounds,
            response_ids=response_ids,
            rollover_recommended=rollover,
        )
