"""Provider-neutral chat contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass(frozen=True)
class ChatModel:
    id: str
    display_name: str


@dataclass(frozen=True)
class ChatTurnResult:
    text: str
    response_id: str | None
    usage: dict[str, Any] = field(default_factory=dict)
    raw_completed_event: dict[str, Any] = field(default_factory=dict)


ChatDeltaHandler = Callable[[str], None]


class ModelProvider(Protocol):
    def list_models(self) -> list[ChatModel]: ...

    def run_turn(
        self,
        *,
        model: str,
        input_items: list[dict[str, Any]],
        instructions: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        on_delta: ChatDeltaHandler | None = None,
    ) -> ChatTurnResult: ...
