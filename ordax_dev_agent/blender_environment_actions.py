"""Typed Blender visual-environment materialization actions."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from mcp_blender_unity.config import find_blender

from .models import ActionResult
from .process_runner import run_command as _run
from .visual_environment import normalize_environment


class BlenderEnvironmentActions:
    def blender_environment_apply(self, payload: dict[str, Any]) -> ActionResult:
        supported = {
            "project",
            "blend_file",
            "output_path",
            "environment",
            "report_path",
            "timeout_seconds",
            "overwrite",
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")

        blender = find_blender()
        if blender is None:
            return ActionResult(False, "Blender executable not found")

        project = self._project(payload)
        manifest_temp: Path | None = None
        try:
            blend_file = project.path(str(payload.get("blend_file") or ""))
            if blend_file.suffix.lower() != ".blend":
                raise ValueError("blend_file must be a .blend file")

            output_raw = payload.get("output_path") or "ordax/environment-applied.blend"
            if not isinstance(output_raw, str) or not output_raw.strip():
                raise ValueError("output_path must be a non-empty project-relative path")
            output = project.path(output_raw.strip(), must_exist=False)
            if output.suffix.lower() != ".blend":
                raise ValueError("output_path must be a .blend file")
            if output == blend_file:
                raise ValueError("output_path must differ from blend_file")
            if output.exists() and not bool(payload.get("overwrite", False)):
                raise ValueError("output blend already exists; set overwrite=true explicitly")

            report_raw = payload.get("report_path") or output.with_suffix(".environment.json").relative_to(project.root).as_posix()
            if not isinstance(report_raw, str) or not report_raw.strip():
                raise ValueError("report_path must be a non-empty project-relative path")
            report = project.path(report_raw.strip(), must_exist=False)
            if report.suffix.lower() != ".json":
                raise ValueError("report_path must be a .json file")
            if report.exists() and not bool(payload.get("overwrite", False)):
                raise ValueError("environment report already exists; set overwrite=true explicitly")

            environment = normalize_environment(payload.get("environment") or {})
            staging = project.root / ".ordax" / "environment"
            staging.mkdir(parents=True, exist_ok=True)
            manifest_temp = staging / f"environment-{uuid.uuid4().hex}.json"
            manifest_temp.write_text(
                json.dumps(environment, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            report.parent.mkdir(parents=True, exist_ok=True)

            script = Path(__file__).resolve().parent / "assets" / "blender_visual_environment.py"
            if not script.is_file():
                raise ValueError("Blender visual-environment script is missing")
            timeout_raw = payload.get("timeout_seconds", 300)
            if isinstance(timeout_raw, bool) or not isinstance(timeout_raw, (int, float)):
                raise ValueError("timeout_seconds must be numeric")
            timeout = int(timeout_raw)
            if timeout < 30 or timeout > 1800:
                raise ValueError("timeout_seconds must be between 30 and 1800")

            result = _run(
                [
                    str(blender),
                    "--background",
                    str(blend_file),
                    "--python",
                    str(script),
                    "--",
                    "--environment",
                    str(manifest_temp),
                    "--output",
                    str(output),
                    "--report",
                    str(report),
                ],
                cwd=project.root,
                timeout=timeout,
            )
            if not result.ok:
                return ActionResult(False, "Blender environment application failed", result.data)
            if not output.is_file():
                return ActionResult(False, "Blender environment application produced no output blend")
            if not report.is_file():
                return ActionResult(False, "Blender environment application produced no report")
            report_data = json.loads(report.read_text(encoding="utf-8"))
            if not isinstance(report_data, dict) or not report_data.get("ok"):
                raise ValueError("Blender environment report is invalid")
        except (ValueError, OSError, FileNotFoundError, json.JSONDecodeError) as error:
            return ActionResult(False, str(error))
        finally:
            if manifest_temp is not None:
                manifest_temp.unlink(missing_ok=True)

        return ActionResult(
            True,
            "Blender visual environment materialized",
            {
                "output_path": str(output),
                "report_path": str(report),
                "environment": environment,
                "blender_report": report_data,
            },
        )
