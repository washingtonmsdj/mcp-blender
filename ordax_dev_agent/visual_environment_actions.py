"""Typed visual-environment actions shared by Blender and realtime engines."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .blender_environment_actions import BlenderEnvironmentActions
from .models import ActionResult
from .visual_environment import (
    ENVIRONMENT_SCHEMA,
    environment_preset,
    environment_schema,
    normalize_environment,
)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.ordax-{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


class VisualEnvironmentActions:
    def visual_environment_schema(self, payload: dict[str, Any]) -> ActionResult:
        unsupported = set(payload) - {"project"}
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        schema = environment_schema()
        schema["materialization"] = {
            "blender": {
                "action": "visual.environment_write",
                "optional_field": "blender",
                "output": "derived .blend with Nishita sky, Sun light and Ocean modifier",
            },
            "threejs": {
                "action": "game_assets.threejs_prepare_viewer",
                "environment_schema": ENVIRONMENT_SCHEMA,
            },
        }
        return ActionResult(True, "visual environment schema", schema)

    def visual_environment_preset(self, payload: dict[str, Any]) -> ActionResult:
        unsupported = set(payload) - {"project", "preset"}
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        try:
            preset = environment_preset(str(payload.get("preset") or ""))
        except ValueError as error:
            return ActionResult(False, str(error))
        return ActionResult(True, "visual environment preset", preset)

    def visual_environment_write(self, payload: dict[str, Any]) -> ActionResult:
        supported = {"project", "environment", "output_path", "overwrite", "blender"}
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        project = self._project(payload)
        try:
            environment = normalize_environment(payload.get("environment") or {})
            output_raw = payload.get("output_path") or "ordax/environment.json"
            if not isinstance(output_raw, str) or not output_raw.strip():
                raise ValueError("output_path must be a non-empty project-relative path")
            output = project.path(output_raw.strip(), must_exist=False)
            if output.suffix.lower() != ".json":
                raise ValueError("output_path must be a .json file")
            overwrite = bool(payload.get("overwrite", False))
            if output.exists() and not overwrite:
                raise ValueError("environment manifest already exists; set overwrite=true explicitly")
            _write_json_atomic(output, environment)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))

        blender_result: ActionResult | None = None
        raw_blender = payload.get("blender")
        if raw_blender is not None:
            if not isinstance(raw_blender, dict):
                return ActionResult(False, "blender must be an object")
            allowed_blender = {
                "blend_file",
                "output_path",
                "report_path",
                "timeout_seconds",
                "overwrite",
            }
            unsupported_blender = sorted(set(raw_blender) - allowed_blender)
            if unsupported_blender:
                return ActionResult(
                    False,
                    "unsupported blender field(s): " + ", ".join(unsupported_blender),
                )
            blender_payload = {
                "project": project.slug,
                "environment": environment,
                **raw_blender,
            }
            blender_payload.setdefault("overwrite", overwrite)
            blender_result = BlenderEnvironmentActions.blender_environment_apply(
                self, blender_payload
            )
            if not blender_result.ok:
                return ActionResult(
                    False,
                    "environment manifest written but Blender materialization failed: "
                    + blender_result.summary,
                    {
                        "schema": ENVIRONMENT_SCHEMA,
                        "output_path": str(output),
                        "environment": environment,
                        "blender": blender_result.data,
                    },
                )

        data: dict[str, Any] = {
            "schema": ENVIRONMENT_SCHEMA,
            "output_path": str(output),
            "environment": environment,
        }
        if blender_result is not None:
            data["blender"] = blender_result.data
        return ActionResult(
            True,
            (
                "visual environment manifest written and materialized in Blender"
                if blender_result is not None
                else "visual environment manifest written"
            ),
            data,
        )
