from __future__ import annotations

from .config import AgentConfig


def build_control_plane(config: AgentConfig):
    """Select one supported device-scoped remote transport."""

    protocol = str(config.control_plane_protocol or "development-v2").strip().lower()
    if protocol == "development-v2":
        from .development_control_plane import DevelopmentControlPlane

        return DevelopmentControlPlane(config)
    if protocol == "cloudflare-v3":
        from .cloudflare_control_plane import CloudflareControlPlane

        return CloudflareControlPlane(config)
    raise ValueError(f"Unsupported control-plane protocol: {protocol}")
