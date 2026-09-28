from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .models import ActionResult


class ActionExecutor(Protocol):
    @property
    def names(self) -> list[str]: ...

    def execute(self, action: str, payload: dict[str, Any]) -> ActionResult: ...


@dataclass(frozen=True)
class ProductActionSpec:
    name: str
    local_action: str
    allowed_fields: frozenset[str]
    project_required: bool = True


@dataclass(frozen=True)
class ProductRequestContext:
    """Verified caller/device context supplied by the authenticated Control Plane."""

    request_id: str
    subject_id: str
    device_id: str
    space_id: str | None = None


@dataclass(frozen=True)
class ProductGrant:
    """Resolved grant provenance supplied by the Control Plane.

    This object is not a bearer credential and it is never accepted from an
    unauthenticated network request. The gateway validates that its subject and
    optional Space/device scopes match the verified request context.
    """

    grant_id: str
    subject_id: str
    actions: frozenset[str]
    projects: frozenset[str] = frozenset()
    space_id: str | None = None
    device_id: str | None = None
    expires_at_unix: int | None = None


@dataclass(frozen=True)
class ProductAuditEvent:
    occurred_at_unix: int
    request_id: str
    subject_id: str
    grant_id: str | None
    action: str
    project: str | None
    phase: str
    decision: str
    reason: str
    payload_fields: tuple[str, ...]
    result_ok: bool | None = None


class ProductAuditSink(Protocol):
    def record(self, event: ProductAuditEvent) -> None: ...


PRODUCT_READ_ONLY_ACTIONS: dict[str, ProductActionSpec] = {
    "projects.list": ProductActionSpec(
        name="projects.list",
        local_action="projects.list",
        allowed_fields=frozenset(),
        project_required=False,
    ),
    "project.inventory": ProductActionSpec(
        name="project.inventory",
        local_action="project.inventory",
        allowed_fields=frozenset({"project", "max_depth", "max_entries"}),
    ),
    "project.text_read": ProductActionSpec(
        name="project.text_read",
        local_action="project.text_read",
        allowed_fields=frozenset({"project", "path"}),
    ),
    "git.status": ProductActionSpec(
        name="git.status",
        local_action="git.status",
        allowed_fields=frozenset({"project"}),
    ),
    "git.diff": ProductActionSpec(
        name="git.diff",
        local_action="git.diff",
        allowed_fields=frozenset({"project", "paths"}),
    ),
    "artifact.preview": ProductActionSpec(
        name="artifact.preview",
        local_action="artifact.preview",
        allowed_fields=frozenset(
            {
                "project",
                "artifact_name",
                "project_artifact_path",
                "max_bytes",
                "thumbnail",
                "max_width",
                "max_height",
                "quality",
            }
        ),
    ),
}

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,199}$")


def product_action_catalog() -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "effect": "read",
            "project_required": spec.project_required,
            "allowed_fields": sorted(spec.allowed_fields),
        }
        for spec in PRODUCT_READ_ONLY_ACTIONS.values()
    ]


def _sanitize_product_result(action: str, result: ActionResult) -> ActionResult:
    data = dict(result.data) if isinstance(result.data, dict) else {}

    if action == "projects.list":
        projects = data.get("projects")
        if isinstance(projects, list):
            data["projects"] = [
                {
                    key: item[key]
                    for key in ("slug", "apps", "available", "allowed_branches")
                    if isinstance(item, dict) and key in item
                }
                for item in projects
                if isinstance(item, dict)
            ]
    elif action == "project.inventory":
        data.pop("project_root", None)
    elif action in {"git.status", "git.diff"}:
        data.pop("command", None)
    elif action == "artifact.preview":
        data.pop("path", None)

    return ActionResult(result.ok, result.summary, data)


def _valid_id(value: str | None) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


class ProductActionGateway:
    """Fail-closed read-only Product MCP/OrdaX Web action facade.

    The gateway is not a network server. A future Product MCP/Web endpoint must
    authenticate first, resolve a grant in the Control Plane, provide a verified
    request context and persist audit events through the required audit sink.
    """

    def __init__(
        self,
        executor: ActionExecutor,
        audit_sink: ProductAuditSink,
        *,
        clock: Callable[[], float] = time.time,
    ):
        self.executor = executor
        self.audit_sink = audit_sink
        self.clock = clock

    def catalog(self) -> list[dict[str, Any]]:
        available = set(self.executor.names)
        return [
            entry
            for entry in product_action_catalog()
            if PRODUCT_READ_ONLY_ACTIONS[entry["name"]].local_action in available
        ]

    def _event(
        self,
        *,
        context: ProductRequestContext,
        grant: ProductGrant | None,
        action: str,
        body: dict[str, Any],
        phase: str,
        decision: str,
        reason: str,
        result_ok: bool | None = None,
    ) -> ProductAuditEvent:
        project = body.get("project")
        return ProductAuditEvent(
            occurred_at_unix=int(self.clock()),
            request_id=context.request_id,
            subject_id=context.subject_id,
            grant_id=grant.grant_id if grant is not None else None,
            action=action,
            project=project if isinstance(project, str) else None,
            phase=phase,
            decision=decision,
            reason=reason,
            payload_fields=tuple(sorted(body)),
            result_ok=result_ok,
        )

    def _deny(
        self,
        *,
        context: ProductRequestContext,
        grant: ProductGrant | None,
        action: str,
        body: dict[str, Any],
        summary: str,
        error_code: str,
    ) -> ActionResult:
        try:
            self.audit_sink.record(
                self._event(
                    context=context,
                    grant=grant,
                    action=action,
                    body=body,
                    phase="decision",
                    decision="deny",
                    reason=error_code,
                )
            )
        except Exception:
            return ActionResult(
                False,
                "product action denied; audit sink unavailable",
                {"error_code": "audit_unavailable", "original_error_code": error_code},
            )
        return ActionResult(False, summary, {"error_code": error_code})

    def execute(
        self,
        action: str,
        payload: dict[str, Any] | None,
        *,
        context: ProductRequestContext,
        grant: ProductGrant,
    ) -> ActionResult:
        body = dict(payload or {})

        if not (
            _valid_id(context.request_id)
            and _valid_id(context.subject_id)
            and _valid_id(context.device_id)
            and (context.space_id is None or _valid_id(context.space_id))
        ):
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="verified product request context is invalid",
                error_code="invalid_request_context",
            )

        if not (_valid_id(grant.grant_id) and _valid_id(grant.subject_id)):
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="resolved product grant provenance is invalid",
                error_code="invalid_grant_provenance",
            )

        if grant.subject_id != context.subject_id:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="grant subject does not match authenticated subject",
                error_code="grant_subject_mismatch",
            )

        if grant.device_id is not None and grant.device_id != context.device_id:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="grant is scoped to another device",
                error_code="grant_device_mismatch",
            )

        if grant.space_id is not None and grant.space_id != context.space_id:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="grant is scoped to another Space",
                error_code="grant_space_mismatch",
            )

        now = int(self.clock())
        if grant.expires_at_unix is not None and grant.expires_at_unix <= now:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="product grant is expired",
                error_code="grant_expired",
            )

        spec = PRODUCT_READ_ONLY_ACTIONS.get(action)
        if spec is None:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary=f"product action is not exposed: {action}",
                error_code="action_not_exposed",
            )

        if action not in grant.actions:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary=f"product action is not granted: {action}",
                error_code="grant_required",
            )

        unsupported = sorted(set(body) - spec.allowed_fields)
        if unsupported:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="unsupported field(s): " + ", ".join(unsupported),
                error_code="invalid_product_action_payload",
            )

        if spec.project_required:
            project = body.get("project")
            if not isinstance(project, str) or not project:
                return self._deny(
                    context=context,
                    grant=grant,
                    action=action,
                    body=body,
                    summary="project is required",
                    error_code="project_required",
                )
            if project not in grant.projects:
                return self._deny(
                    context=context,
                    grant=grant,
                    action=action,
                    body=body,
                    summary=f"project is not granted: {project}",
                    error_code="project_grant_required",
                )
        elif "project" in body:
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary="project is not accepted for this global action",
                error_code="invalid_product_action_payload",
            )

        if spec.local_action not in set(self.executor.names):
            return self._deny(
                context=context,
                grant=grant,
                action=action,
                body=body,
                summary=f"local action is unavailable: {spec.local_action}",
                error_code="local_action_unavailable",
            )

        try:
            self.audit_sink.record(
                self._event(
                    context=context,
                    grant=grant,
                    action=action,
                    body=body,
                    phase="decision",
                    decision="allow",
                    reason="grant_validated",
                )
            )
        except Exception:
            return ActionResult(
                False,
                "product action refused because audit sink is unavailable",
                {"error_code": "audit_unavailable"},
            )

        result = _sanitize_product_result(
            action,
            self.executor.execute(spec.local_action, body),
        )

        try:
            self.audit_sink.record(
                self._event(
                    context=context,
                    grant=grant,
                    action=action,
                    body=body,
                    phase="result",
                    decision="allow",
                    reason="local_action_completed",
                    result_ok=result.ok,
                )
            )
        except Exception:
            return ActionResult(
                False,
                "product result withheld because audit persistence failed",
                {
                    "error_code": "audit_unavailable",
                    "local_result_ok": bool(result.ok),
                },
            )

        return result
