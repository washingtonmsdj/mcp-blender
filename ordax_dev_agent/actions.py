from __future__ import annotations

import subprocess
import threading
import re
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable

from .config import AgentConfig
from .models import ActionResult
from .projects import load_projects, Project
from .observations import ObservationActions
from .references import ReferenceActions
from .blender_actions import BlenderActions
from .unity_actions import UnityActions
from .agent_actions import AgentActions
from .artifact_actions import ArtifactActions
from .git_actions import GitActions
from .project_text_actions import ProjectTextActions
from .execution_lock import ExecutionLock


Action = Callable[[dict[str, Any]], ActionResult]


class ActionRegistry(
    ObservationActions,
    ReferenceActions,
    BlenderActions,
    UnityActions,
    AgentActions,
    ArtifactActions,
    GitActions,
    ProjectTextActions,
):
    """Strict allow-list. No arbitrary remote shell command is accepted."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.projects = load_projects(config)
        self.on_observation = None
        self._execution_lock = threading.Lock()
        self._actions: dict[str, Action] = {
            "projects.list": self.projects_list,
            "project.observe": self.project_observe,
            "project.references": self.project_references,
            "project.reference_images": self.project_reference_images,
            "project.text_read": self.project_text_read,
            "project.text_write": self.project_text_write,
            "project.text_patch": self.project_text_patch,
            "observation.capture": self.observation_capture,
            "blender.inspect": self.blender_inspect,
            "blender.benchmark": self.blender_benchmark,
            "blender.render_preview": self.blender_render_preview,
            "blender.live_start": self.blender_live_start,
            "blender.live_status": self.blender_live_status,
            "blender.live_inspect": self.blender_live_inspect,
            "blender.live_scene_snapshot": self.blender_live_scene_snapshot,
            "blender.live_scene_reset": self.blender_live_scene_reset,
            "blender.live_object_inspect": self.blender_live_object_inspect,
            "blender.live_object_fingerprints": self.blender_live_object_fingerprints,
            "blender.live_contact_audit": self.blender_live_contact_audit,
            "blender.live_quality_gate": self.blender_live_quality_gate,
            "blender.live_modeling_schema": self.blender_live_modeling_schema,
            "blender.live_modeling_plan": self.blender_live_modeling_plan,
            "blender.live_object_transform": self.blender_live_object_transform,
            "blender.live_create_primitive": self.blender_live_create_primitive,
            "blender.live_add_modifier": self.blender_live_add_modifier,
            "blender.live_object_metadata": self.blender_live_object_metadata,
            "blender.live_api_schema": self.blender_live_api_schema,
            "blender.live_api_lookup": self.blender_live_api_lookup,
            "blender.live_node_schema": self.blender_live_node_schema,
            "blender.live_export": self.blender_live_export,
            "blender.export_headless": self.blender_export_headless,
            "blender.live_checkpoint_create": self.blender_live_checkpoint_create,
            "blender.live_checkpoint_list": self.blender_live_checkpoint_list,
            "blender.live_checkpoint_restore": self.blender_live_checkpoint_restore,
            "blender.live_trajectory": self.blender_live_trajectory,
            "blender.live_generation_pass": self.blender_live_generation_pass,
            "blender.live_result": self.blender_live_result,
            "blender.live_run_script": self.blender_live_run_script,
            "blender.live_capture": self.blender_live_capture,
            "blender.live_multiview_capture": self.blender_live_multiview_capture,
            "blender.live_save": self.blender_live_save,
            "blender.live_stop": self.blender_live_stop,
            "blender.asset_search": self.blender_asset_search,
            "blender.asset_manifest": self.blender_asset_manifest,
            "blender.multiview_compare": self.blender_multiview_compare,
            "blender.reference_review": self.blender_reference_review,
            "blender.reference_generation_pass": self.blender_reference_generation_pass,
            "blender.reference_decision": self.blender_reference_decision,
            "unity.install_companion": self.unity_install_companion,
            "unity.project_profile": self.unity_project_profile,
            "unity.capabilities": self.unity_capabilities,
            "unity.skill_catalog": self.unity_skill_catalog,
            "unity.cli_status": self.unity_cli_status,
            "unity.pipeline_install": self.unity_pipeline_install,
            "unity.pipeline_catalog": self.unity_pipeline_catalog,
            "unity.pipeline_command": self.unity_pipeline_command,
            "unity.asset_inventory": self.unity_asset_inventory,
            "unity.asset_import": self.unity_asset_import,
            "unity.scene_open": self.unity_scene_open,
            "unity.scene_summary": self.unity_scene_summary,
            "unity.physics_audit": self.unity_physics_audit,
            "unity.spatial_audit": self.unity_spatial_audit,
            "unity.benchmark_islands_generate": self.unity_benchmark_islands_generate,
            "agent.status": self.agent_status,
            "agent.resilience_status": self.agent_resilience_status,
            "agent.resilience_repair": self.agent_resilience_repair,
            "agent.update": self.agent_update,
            "agent.self_test": self.agent_self_test,
            "artifact.preview": self.artifact_preview,
            "git.status": self.git_status,
            "git.diff": self.git_diff,
            "git.sync": self.git_sync,
            "unity.editor_status": self.unity_editor_status,
            "unity.editor_diagnostics": self.unity_editor_diagnostics,
            "unity.editor_start": self.unity_editor_start,
            "unity.editor_terminate_stuck": self.unity_editor_terminate_stuck,
            "unity.hub_install_editor": self.unity_hub_install_editor,
            "unity.recover_resume": self.unity_recover_resume,
            "unity.refresh_editor": self.unity_refresh_editor,
            "unity.play_start": self.unity_play_start,
            "unity.play_stop": self.unity_play_stop,
            "unity.stop_play": self.unity_play_stop,
            "unity.compile": self.unity_compile,
            "unity.validate": self.unity_validate,
            "unity.capture": self.unity_capture,
            "unity.run_method": self.unity_run_method,
            "blender.version": self.blender_version,
            "blender.run_python": self.blender_run_python,
        }
        self._app_prefixes = {"unity", "blender"}
        available = {entry.name: entry for entry in entry_points(group="ordax_dev_agent.adapters")}
        for name in config.adapters:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in {"agent", "artifact", "git", "project", "projects", "observation", "unity", "blender"}:
                raise ValueError(f"invalid or reserved adapter name: {name}")
            if name not in available:
                raise ValueError(f"configured adapter is not installed: {name}")
            # Local installed plugin, explicitly enabled by workstation settings.
            handlers = available[name].load()(config)
            for operation, handler in handlers.items():
                if not re.fullmatch(r"[a-z][a-z0-9_]*", operation) or not callable(handler):
                    raise ValueError(f"invalid action in adapter {name}: {operation}")
                self._actions[f"{name}.{operation}"] = (
                    lambda payload, fn=handler: fn(self._project(payload), payload))
            self._app_prefixes.add(name)

    @property
    def names(self) -> list[str]:
        return sorted(self._actions)

    def execute(self, action: str, payload: dict[str, Any]) -> ActionResult:
        handler = self._actions.get(action)
        if handler is None:
            return ActionResult(False, f"action not allowed: {action}")
        payload = payload or {}
        if action in ("agent.status", "projects.list"):
            return handler(payload)
        # A busy application must not receive a second editor/render operation.
        if not self._execution_lock.acquire(blocking=False):
            return ActionResult(False, "Agent is busy; retry after the current action", {"retryable": True})
        process_lock = ExecutionLock(self.config.state_dir)
        try:
            if not process_lock.acquire():
                return ActionResult(False, "Another agent/MCP action is running", {"retryable": True})
            if action.split('.')[0] in self._app_prefixes and action != "blender.version":
                project = self._project(payload)
                if action.split('.')[0] not in project.apps:
                    raise ValueError(f"application not enabled for project {project.slug}")
            result = handler(payload)
            return result
        except (ValueError, FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
            return ActionResult(False, f"{type(error).__name__}: {error}")
        finally:
            process_lock.release()
            self._execution_lock.release()

    def _project_path(self, payload: dict[str, Any]) -> Path:
        return self._project(payload).root

    def _project(self, payload: dict[str, Any]) -> Project:
        slug = payload.get("project") or self.config.default_project
        if slug not in self.projects:
            raise ValueError(f"project not registered: {slug}")
        project = self.projects[slug]
        if not project.root.is_dir():
            raise FileNotFoundError(f"Project directory not found: {project.root}")
        return project
