from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import ActionResult
from .product_gateway import (
    ProductActionGateway,
    ProductGrant,
    ProductRequestContext,
)


@dataclass(frozen=True)
class ProductMcpToolSpec:
    """Transport-neutral Product MCP tool description.

    The MCP host is responsible for authenticating the Product session and
    resolving a live ProductGrant before calling this facade.
    """

    name: str
    action: str
    description: str


PRODUCT_MCP_TOOLS: tuple[ProductMcpToolSpec, ...] = (
    ProductMcpToolSpec(
        name="projects_list",
        action="projects.list",
        description="List projects visible through the resolved Product grant.",
    ),
    ProductMcpToolSpec(
        name="project_inventory",
        action="project.inventory",
        description="Inspect a bounded project inventory without exposing local roots.",
    ),
    ProductMcpToolSpec(
        name="project_text_read",
        action="project.text_read",
        description="Read a granted project-relative text file.",
    ),
    ProductMcpToolSpec(
        name="repository_catalog",
        action="workspace.repository_catalog",
        description="List canonical ORDAX Studio repositories without exposing local filesystem roots.",
    ),
    ProductMcpToolSpec(
        name="project_health",
        action="agent.project_health",
        description="Read sanitized ORDAX Studio project health, Git, memory and adapter state.",
    ),
    ProductMcpToolSpec(
        name="project_search",
        action="project.search_text",
        description="Search bounded approved text sources in a granted project.",
    ),
    ProductMcpToolSpec(
        name="project_read_batch",
        action="project.text_read_batch",
        description="Read a bounded batch of granted project text files.",
    ),
    ProductMcpToolSpec(
        name="project_preview_status",
        action="project.preview_status",
        description="Read sanitized ORDAX Studio preview/runtime state for a granted project.",
    ),
    ProductMcpToolSpec(
        name="git_status",
        action="git.status",
        description="Read Git working-tree status for a granted project.",
    ),
    ProductMcpToolSpec(
        name="git_diff",
        action="git.diff",
        description="Read a bounded Git diff for a granted project.",
    ),
    ProductMcpToolSpec(
        name="artifacts_list",
        action="artifacts.list",
        description="List bounded metadata for artifacts in a granted project.",
    ),
    ProductMcpToolSpec(
        name="artifact_preview",
        action="artifact.preview",
        description="Read a bounded preview of a granted project artifact.",
    ),
)

_TOOL_BY_NAME = {tool.name: tool for tool in PRODUCT_MCP_TOOLS}


def product_mcp_tool_catalog(gateway: ProductActionGateway) -> list[dict[str, Any]]:
    """Return only Product MCP tools whose gateway actions are locally available."""
    available_actions = {entry["name"] for entry in gateway.catalog()}
    return [
        {
            "name": tool.name,
            "action": tool.action,
            "effect": "read",
            "description": tool.description,
        }
        for tool in PRODUCT_MCP_TOOLS
        if tool.action in available_actions
    ]


class ProductMcpFacade:
    """Read-only MCP-facing facade over ProductActionGateway.

    This is deliberately not an MCP server and performs no authentication,
    network I/O, grant lookup, or credential handling. A future authenticated
    MCP host supplies verified context + resolved grant for every invocation.
    """

    def __init__(self, gateway: ProductActionGateway):
        self.gateway = gateway

    def tools(self) -> list[dict[str, Any]]:
        return product_mcp_tool_catalog(self.gateway)

    def call(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
        *,
        context: ProductRequestContext,
        grant: ProductGrant,
    ) -> ActionResult:
        tool = _TOOL_BY_NAME.get(tool_name)
        if tool is None:
            return ActionResult(
                False,
                f"Product MCP tool is not exposed: {tool_name}",
                {"error_code": "product_mcp_tool_not_exposed"},
            )

        available_actions = {entry["name"] for entry in self.gateway.catalog()}
        if tool.action not in available_actions:
            return ActionResult(
                False,
                f"Product MCP action is unavailable: {tool.action}",
                {"error_code": "product_mcp_action_unavailable"},
            )

        return self.gateway.execute(
            tool.action,
            arguments or {},
            context=context,
            grant=grant,
        )
