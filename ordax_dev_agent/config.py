from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentConfig:
    agent_name: str
    supabase_url: str | None
    publishable_key: str | None
    poll_seconds: float
    state_dir: Path
    agent_repo_path: Path
    hordax_path: Path
    bridge_path: Path
    projects: dict | None = None
    default_project: str = "hordax"
    adapters: tuple[str, ...] = ()
    control_plane_protocol: str = "legacy-v1"
    development_device_id: str | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        state_dir = Path(
            os.environ.get(
                "ORDAX_AGENT_STATE_DIR",
                local_app_data / "OrdaX" / "DevAgent",
            )
        )
        state_dir.mkdir(parents=True, exist_ok=True)

        settings_path = state_dir / "agent-settings.json"
        settings: dict = {}
        if settings_path.is_file():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
            except Exception as error:
                raise ValueError(f"Cannot read agent settings: {settings_path}: {error}") from error
        if not isinstance(settings, dict):
            raise ValueError("Agent settings must be a JSON object")
        if not isinstance(settings.get("adapters", []), list):
            raise ValueError("adapters must be a list of locally installed adapter names")

        projects = settings.get("projects")
        default_project = settings.get("default_project", "hordax")
        # When an explicit registry contains exactly one project, an obsolete
        # legacy default must not make otherwise-safe unscoped local status
        # operations point at a nonexistent HORDAX project.
        if (
            isinstance(projects, dict)
            and len(projects) == 1
            and default_project not in projects
        ):
            default_project = next(iter(projects))

        config = cls(
            projects=projects,
            default_project=default_project,
            adapters=tuple(settings.get("adapters", [])),
            control_plane_protocol=os.environ.get(
                "ORDAX_CONTROL_PLANE_PROTOCOL",
                settings.get("control_plane_protocol", "legacy-v1"),
            ),
            development_device_id=os.environ.get(
                "ORDAX_DEVICE_ID",
                settings.get("development_device_id"),
            ),
            agent_name=os.environ.get(
                "ORDAX_AGENT_NAME",
                settings.get("agent_name") or socket.gethostname(),
            ),
            supabase_url=os.environ.get(
                "ORDAX_SUPABASE_URL",
                settings.get("supabase_url"),
            ),
            publishable_key=os.environ.get(
                "ORDAX_SUPABASE_PUBLISHABLE_KEY",
                settings.get("publishable_key"),
            ),
            poll_seconds=min(
                1.0,
                max(
                    0.25,
                    float(
                        os.environ.get(
                            "ORDAX_AGENT_POLL_SECONDS",
                            settings.get("poll_seconds", 1),
                        )
                    ),
                ),
            ),
            state_dir=state_dir,
            agent_repo_path=Path(
                os.environ.get(
                    "ORDAX_AGENT_REPO_PATH",
                    settings.get("agent_repo_path", state_dir / "src"),
                )
            ),
            hordax_path=Path(
                os.environ.get(
                    "ORDAX_HORDAX_PATH",
                    settings.get(
                        "hordax_path",
                        str(Path.home() / "Documents" / "github" / "HORDAX-game"),
                    ),
                )
            ),
            bridge_path=Path(
                os.environ.get(
                    "ORDAX_BRIDGE_PATH",
                    settings.get(
                        "bridge_path",
                        str(Path(__file__).resolve().parents[1]),
                    ),
                )
            ),
        )

        return config

    def public_status(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "poll_seconds": self.poll_seconds,
            "state_dir": str(self.state_dir),
            "agent_repo_path": str(self.agent_repo_path),
            "hordax_path": str(self.hordax_path),
            "bridge_path": str(self.bridge_path),
            "supabase_configured": bool(self.supabase_url and self.publishable_key),
            "control_plane_protocol": self.control_plane_protocol,
            "development_device_id_configured": bool(self.development_device_id),
        }

    def write_public_status(self) -> None:
        target = self.state_dir / "agent-config.json"
        target.write_text(
            json.dumps(self.public_status(), indent=2),
            encoding="utf-8",
        )
