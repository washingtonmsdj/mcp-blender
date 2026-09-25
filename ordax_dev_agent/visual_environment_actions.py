"""Typed visual-environment actions shared by Blender and realtime engines."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

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
        return ActionResult(True, "visual environment schema", environment_schema())

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
        supported = {"project", "environment", "output_path", "overwrite"}
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
            if output.exists() and not bool(payload.get("overwrite", False)):
                raise ValueError("environment manifest already exists; set overwrite=true explicitly")
            _write_json_atomic(output, environment)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))
        return ActionResult(
            True,
            "visual environment manifest written",
            {
                "schema": ENVIRONMENT_SCHEMA,
                "output_path": str(output),
                "environment": environment,
            },
        )
