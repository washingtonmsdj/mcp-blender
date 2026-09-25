"""Typed visual-environment actions shared by Blender and realtime engines."""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from mcp_blender_unity.config import find_blender
from mcp_blender_unity.process import run_process

from .models import ActionResult
from .visual_environment import (
    ENVIRONMENT_SCHEMA,
    environment_preset,
    environment_schema,
    normalize_environment,
)

MAX_ENVIRONMENT_BYTES = 256 * 1024


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.ordax-{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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

    def _environment_payload(self, project, payload: dict[str, Any]) -> dict[str, Any]:
        inline = payload.get("environment")
        path_raw = payload.get("environment_path")
        if inline is not None and path_raw is not None:
            raise ValueError("provide either environment or environment_path, not both")
        if path_raw is not None:
            if not isinstance(path_raw, str) or not path_raw.strip():
                raise ValueError("environment_path must be a non-empty project-relative path")
            path = project.path(path_raw.strip())
            if path.suffix.lower() != ".json":
                raise ValueError("environment_path must be a .json file")
            if path.stat().st_size > MAX_ENVIRONMENT_BYTES:
                raise ValueError("environment_path exceeds the 256 KiB safety limit")
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError("environment_path must contain valid JSON") from error
            return normalize_environment(loaded)
        return normalize_environment(inline or {})

    def _blender_environment_request(
        self,
        *,
        project,
        blend_file: Path,
        operation: str,
        environment: dict[str, Any] | None,
        output_path: Path | None,
        timeout_seconds: int,
    ) -> tuple[dict[str, Any], dict[str, Any], Path]:
        blender = find_blender()
        if blender is None:
            raise FileNotFoundError("Blender executable not found")
        request_root = self.config.state_dir / "visual-environment" / project.slug / uuid.uuid4().hex
        request_root.mkdir(parents=True, exist_ok=False)
        request_path = request_root / "request.json"
        report_path = request_root / "report.json"
        request: dict[str, Any] = {
            "operation": operation,
            "report_path": str(report_path),
        }
        if environment is not None:
            request["environment"] = environment
        if output_path is not None:
            request["output_path"] = str(output_path)
        request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
        script = Path(__file__).parent / "assets" / "blender_visual_environment.py"
        command = [
            str(blender),
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            str(blend_file),
            "--python-exit-code",
            "1",
            "--python",
            str(script),
            "--",
            str(request_path),
        ]
        process = run_process(command, cwd=project.root, timeout_seconds=timeout_seconds)
        report: dict[str, Any] = {}
        if report_path.is_file():
            try:
                loaded = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    report = loaded
            except (OSError, json.JSONDecodeError):
                report = {}
        return process, report, request_path

    def visual_blender_environment_build(self, payload: dict[str, Any]) -> ActionResult:
        supported = {
            "project",
            "blend_file",
            "environment",
            "environment_path",
            "output_path",
            "overwrite",
            "timeout_seconds",
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        project = self._project(payload)
        temporary: Path | None = None
        try:
            blend_raw = payload.get("blend_file") or project.blender.get("blend_file", "")
            blend_file = project.path(str(blend_raw))
            if blend_file.suffix.lower() != ".blend":
                raise ValueError("blend_file must be a .blend file")
            environment = self._environment_payload(project, payload)
            output_raw = payload.get("output_path")
            if output_raw is None:
                output_raw = f"{blend_file.stem}.environment.blend"
            if not isinstance(output_raw, str) or not output_raw.strip():
                raise ValueError("output_path must be a non-empty project-relative path")
            output = project.path(output_raw.strip(), must_exist=False)
            if output.suffix.lower() != ".blend":
                raise ValueError("output_path must be a .blend file")
            if output == blend_file:
                raise ValueError("output_path must differ from the source blend_file")
            overwrite = bool(payload.get("overwrite", False))
            if output.exists() and not overwrite:
                raise ValueError("environment derivative already exists; set overwrite=true explicitly")
            timeout = payload.get("timeout_seconds", 300)
            if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 1800:
                raise ValueError("timeout_seconds must be an integer between 1 and 1800")

            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(f".{output.stem}.ordax-{uuid.uuid4().hex}.tmp.blend")
            temporary.unlink(missing_ok=True)
            source_hash_before = _sha256(blend_file)
            process, report, request_path = self._blender_environment_request(
                project=project,
                blend_file=blend_file,
                operation="apply",
                environment=environment,
                output_path=temporary,
                timeout_seconds=timeout,
            )
            source_hash_after = _sha256(blend_file)
            source_preserved = source_hash_before == source_hash_after
            temporary_valid = temporary.is_file() and temporary.stat().st_size > 0
            ok = bool(process.get("ok") and report.get("ok") and temporary_valid and source_preserved)
            generated_path = report.get("output_blend")
            if ok:
                temporary.replace(output)
                temporary = None
                report = {
                    **report,
                    "generated_output_blend": generated_path,
                    "output_blend": str(output),
                }
            output_valid = output.is_file() and output.stat().st_size > 0
            ok = bool(ok and output_valid)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return ActionResult(
            ok,
            "Blender visual environment derivative built" if ok else "Blender visual environment build failed",
            {
                "project": project.slug,
                "source_blend": str(blend_file),
                "source_sha256": source_hash_before,
                "source_preserved": source_preserved,
                "output_blend": str(output),
                "output_sha256": _sha256(output) if output_valid else None,
                "environment": environment,
                "report": report,
                "process": process,
                "request_path": str(request_path),
                "transport": "blender-cli-isolated-derivative",
            },
        )

    def visual_blender_environment_audit(self, payload: dict[str, Any]) -> ActionResult:
        supported = {"project", "blend_file", "timeout_seconds"}
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        project = self._project(payload)
        try:
            blend_raw = payload.get("blend_file") or project.blender.get("blend_file", "")
            blend_file = project.path(str(blend_raw))
            if blend_file.suffix.lower() != ".blend":
                raise ValueError("blend_file must be a .blend file")
            timeout = payload.get("timeout_seconds", 180)
            if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 1800:
                raise ValueError("timeout_seconds must be an integer between 1 and 1800")
            source_hash_before = _sha256(blend_file)
            process, report, request_path = self._blender_environment_request(
                project=project,
                blend_file=blend_file,
                operation="audit",
                environment=None,
                output_path=None,
                timeout_seconds=timeout,
            )
            source_hash_after = _sha256(blend_file)
            source_preserved = source_hash_before == source_hash_after
            ok = bool(process.get("ok") and report.get("ok") and source_preserved)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))
        return ActionResult(
            ok,
            "Blender visual environment audit passed" if ok else "Blender visual environment audit failed",
            {
                "project": project.slug,
                "blend_file": str(blend_file),
                "sha256": source_hash_before,
                "source_preserved": source_preserved,
                "report": report,
                "process": process,
                "request_path": str(request_path),
                "transport": "blender-cli-readonly-audit",
            },
        )
