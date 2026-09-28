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


@mcp.tool()
def blender_live_multiview(
    project: str,
    views: list[str] | None = None,
    object_names: list[str] | None = None,
    width: int = 512,
    height: int = 512,
    mode: str = "material",
    timeout_seconds: float = 240.0,
) -> list[TextContent | ImageContent]:
    """Capture deterministic Blender views and return every image to the MCP client."""
    requested_views = views or ["front", "right", "top", "three_quarter"]
    if not 1 <= len(requested_views) <= 6:
        raise ValueError("views must contain between 1 and 6 entries")
    if not 128 <= int(width) <= 1024 or not 128 <= int(height) <= 1024:
        raise ValueError("direct MCP multiview resolution must be between 128 and 1024")
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"material", "silhouette"}:
        raise ValueError("mode must be material or silhouette")

    timeout = max(15.0, min(float(timeout_seconds), 600.0))
    payload: dict = {
        "project": project,
        "views": requested_views,
        "width": int(width),
        "height": int(height),
        "mode": normalized_mode,
        "timeout_seconds": timeout,
    }
    if object_names is not None:
        payload["object_names"] = object_names

    agent = registry()
    result = agent.execute("blender.live_multiview_capture", payload)
    if not result.ok:
        raise RuntimeError(result.summary)

    artifacts = result.data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise RuntimeError("Blender multiview completed without image artifacts")

    summary = {
        "project": project,
        "summary": result.summary,
        "primary_artifact": result.data.get("primary_artifact"),
        "manifest": result.data.get("manifest"),
        "bounds": result.data.get("bounds"),
        "objects": result.data.get("objects"),
        "resolution": result.data.get("resolution"),
        "projection": result.data.get("projection"),
        "render_engine": result.data.get("render_engine"),
        "mode": result.data.get("mode"),
    }
    contents: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(summary))
    ]
    for item in artifacts:
        if not isinstance(item, dict):
            raise RuntimeError("Blender multiview returned an invalid artifact entry")
        artifact = item.get("artifact")
        if not isinstance(artifact, str) or not artifact.strip():
            raise RuntimeError("Blender multiview artifact path is missing")
        validated = _artifact_image_contents(
            agent,
            project,
            artifact,
            metadata={"view": item.get("view"), "sha256": item.get("sha256")},
        )
        contents.extend(validated)
    return contents
def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
