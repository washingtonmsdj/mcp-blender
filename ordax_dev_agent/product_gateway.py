from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

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
class ProductGrant:
    """Explicit caller-supplied authorization for the Product Gateway.

    Identity/grant persistence intentionally lives outside this module. Until the
    Control Plane supplies a grant, there is no implicit/default authorization.
    """

    actions: frozenset[str]
    projects: frozenset[str] = frozenset()


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
        # Local execution details contain absolute workstation paths.
        data.pop("command", None)
    elif action == "artifact.preview":
        data.pop("path", None)

    return ActionResult(result.ok, result.summary, data)


class ProductActionGateway:
    """Fail-closed read-only Product MCP/OrdaX Web action facade.

    This is not a network server. It is the shared execution contract that a
    future authenticated Product MCP or Web endpoint can call after resolving
    identity and grants in the Control Plane.
    """

    def __init__(self, executor: ActionExecutor):
        self.executor = executor

    def catalog(self) -> list[dict[str, Any]]:
        available = set(self.executor.names)
        return [
            entry
            for entry in product_action_catalog()
            if PRODUCT_READ_ONLY_ACTIONS[entry["name"]].local_action in available
        ]

    def execute(
        self,
        action: str,
        payload: dict[str, Any] | None,
        *,
        grant: ProductGrant,
    ) -> ActionResult:
        spec = PRODUCT_READ_ONLY_ACTIONS.get(action)
        if spec is None:
            return ActionResult(False, f"product action is not exposed: {action}")

        if action not in grant.actions:
            return ActionResult(
                False,
                f"product action is not granted: {action}",
                {"error_code": "grant_required"},
            )

        body = dict(payload or {})
        unsupported = sorted(set(body) - spec.allowed_fields)
        if unsupported:
            return ActionResult(
                False,
                "unsupported field(s): " + ", ".join(unsupported),
                {"error_code": "invalid_product_action_payload"},
            )

        if spec.project_required:
            project = body.get("project")
            if not isinstance(project, str) or not project:
                return ActionResult(
                    False,
                    "project is required",
                    {"error_code": "project_required"},
                )
            if project not in grant.projects:
                return ActionResult(
                    False,
                    f"project is not granted: {project}",
                    {"error_code": "project_grant_required"},
                )
        elif "project" in body:
            return ActionResult(
                False,
                "project is not accepted for this global action",
                {"error_code": "invalid_product_action_payload"},
            )

        if spec.local_action not in set(self.executor.names):
            return ActionResult(
                False,
                f"local action is unavailable: {spec.local_action}",
                {"error_code": "local_action_unavailable"},
            )

        result = self.executor.execute(spec.local_action, body)
        return _sanitize_product_result(action, result)
