from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentJob:
    id: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    project_slug: str | None = None
    lease_token: str | None = None


@dataclass(slots=True)
class ActionResult:
    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
