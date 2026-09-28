"""MCP stdio front end for a client running on the workstation.

Remote jobs continue to use the paired cloud queue; this does not publish a public server.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent, TextContent

from .actions import ActionRegistry
from .config import AgentConfig

mcp = FastMCP("ordax-projects")
_registry: ActionRegistry | None = None


def registry() -> ActionRegistry:
    global _registry
    if _registry is None:
        _registry = ActionRegistry(AgentConfig.from_env())
    return _registry


@mcp.tool()
def projects_list() -> dict:
    """Discover connected projects, app profiles and permitted Git branches before executing."""
    return registry().projects_list({}).data


@mcp.tool()
def agent_capabilities() -> dict:
    """Discover action names and registered projects. Observe before changing or retrying."""
    return registry().agent_status({}).data


@mcp.tool()
def action_execute(action: str, project: str, arguments: dict | None = None) -> dict:
    """Execute a registered action on one project. Returns ok, summary and structured evidence.

Examples: project.observe {app:unity}, blender.inspect {blend_file:scene.blend},
blender.render_preview {blend_file:scene.blend,width:1280,height:720},
observation.capture {app:unity,frames:3,interval_seconds:1},
project.references {asset:wooden-boat},
blender.reference_review {asset:wooden-boat,reference_ids:[front],object_names:[Hull]},
blender.reference_generation_pass {asset:wooden-boat,reference_ids:[front],object_names:[Hull],script_path:automation/blender/refine.py},
git.sync {branch:main}, unity.install_companion {} (adds an Editor script).
Use artifact_image for managed reference/model PNG/JPEG evidence returned by actions.
"""
    payload = {**(arguments or {}), "project": project}
    result = registry().execute(action, payload)
    return {"ok": result.ok, "summary": result.summary, "data": result.data}


def _artifact_image_contents(
    agent: ActionRegistry,
    project: str,
    artifact_path: str,
    *,
    metadata: dict | None = None,
) -> list[TextContent | ImageContent]:
    selected = agent._project({"project": project})
    root = (agent.config.state_dir / "artifacts" / selected.slug).resolve()
    path = Path(artifact_path).resolve()
    if not path.is_relative_to(root) or path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise ValueError("Image must be an artifact belonging to the selected project")
    if not path.is_file():
        raise FileNotFoundError(f"Image artifact not found: {path}")
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Image exceeds 10 MiB; request a lower resolution")

    details = {"project": project, "artifact": str(path), **(metadata or {})}
    mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return [
        TextContent(type="text", text=json.dumps(details)),
        ImageContent(
            type="image",
            mimeType=mime_type,
            data=base64.b64encode(path.read_bytes()).decode("ascii"),
        ),
    ]


@mcp.tool()
def artifact_image(project: str, artifact_path: str) -> list[TextContent | ImageContent]:
    """Return actual PNG/JPEG pixels to the model, not just a local file path (max 10 MiB)."""
    return _artifact_image_contents(registry(), project, artifact_path)


@mcp.tool()
def blender_live_view(
    project: str,
    timeout_seconds: float = 120.0,
) -> list[TextContent | ImageContent]:
    """Capture the visible Blender viewport and return its pixels in the same MCP call."""
    timeout = max(5.0, min(float(timeout_seconds), 300.0))
    agent = registry()
    result = agent.execute(
        "blender.live_capture",
        {"project": project, "timeout_seconds": timeout},
    )
    if not result.ok:
        raise RuntimeError(result.summary)

    artifact = result.data.get("artifact")
    if not isinstance(artifact, str) or not artifact.strip():
        raise RuntimeError("Blender live capture completed without an image artifact")
    return _artifact_image_contents(
        agent,
        project,
        artifact,
        metadata={
            "summary": result.summary,
            "sha256": result.data.get("sha256"),
            "snapshot_path": result.data.get("snapshot_path"),
            "transport": result.data.get("transport"),
        },
    )

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
