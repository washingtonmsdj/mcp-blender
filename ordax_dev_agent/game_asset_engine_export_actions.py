"""Canonical Blender-to-engine export derivatives with content provenance."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ActionResult


ENGINE_EXPORT_SCHEMA = "ordax.engine-export/1"

_ENGINE_HANDOFF_CONTRACTS: dict[str, dict[str, Any]] = {
    "unity": {
        "formats": {"fbx"},
        "next_gate": "game_assets.unity_import_engine_export",
        "engine_validation_available": True,
    },
    "unreal": {
        "formats": {"fbx"},
        "next_gate": "unreal_engine_import_validation",
        "engine_validation_available": False,
    },
    "godot": {
        "formats": {"glb", "gltf"},
        "next_gate": "godot_engine_import_runtime_validation",
        "engine_validation_available": False,
    },
    "web": {
        "formats": {"glb", "gltf"},
        "next_gate": "web_runtime_load_visual_performance_validation",
        "engine_validation_available": False,
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _relative(project, path: Path) -> str:
    try:
        return path.relative_to(project.root).as_posix()
    except ValueError as error:
        raise ValueError("path must stay inside the registered project") from error


def _manifest_path(artifact: Path) -> Path:
    return artifact.with_name(artifact.name + ".ordax.json")


def verify_engine_export(project, artifact: Path, manifest: Path) -> dict[str, Any]:
    if not artifact.is_file():
        raise ValueError("engine export artifact does not exist")
    if not manifest.is_file():
        raise ValueError("engine export provenance manifest is required")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError("engine export provenance manifest is not valid JSON") from error
    if not isinstance(data, dict) or data.get("schema") != ENGINE_EXPORT_SCHEMA:
        raise ValueError(f"engine export manifest must use {ENGINE_EXPORT_SCHEMA}")
    if data.get("project") != project.slug:
        raise ValueError("engine export manifest belongs to a different project")
    artifact_record = data.get("artifact")
    source_record = data.get("source")
    if not isinstance(artifact_record, dict) or not isinstance(source_record, dict):
        raise ValueError("engine export manifest is missing source/artifact records")
    requested = _relative(project, artifact)
    if artifact_record.get("path") != requested:
        raise ValueError("engine export manifest does not match requested artifact")
    expected_bytes = artifact_record.get("bytes")
    expected_hash = artifact_record.get("sha256")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int):
        raise ValueError("engine export manifest byte size is invalid")
    if artifact.stat().st_size != expected_bytes:
        raise ValueError("engine export artifact byte size no longer matches provenance")
    actual_hash = _sha256(artifact)
    if not isinstance(expected_hash, str) or actual_hash != expected_hash:
        raise ValueError("engine export artifact SHA-256 no longer matches provenance")
    source_path = source_record.get("path")
    source_hash = source_record.get("sha256")
    if not isinstance(source_path, str) or not source_path:
        raise ValueError("engine export manifest source path is invalid")
    if not isinstance(source_hash, str) or len(source_hash) != 64:
        raise ValueError("engine export manifest source SHA-256 is invalid")
    source = project.path(source_path, must_exist=False)
    source_current_matches = source.is_file() and _sha256(source) == source_hash
    return {
        "schema": ENGINE_EXPORT_SCHEMA,
        "engine": data.get("engine"),
        "artifact_path": str(artifact),
        "manifest_path": str(manifest),
        "sha256": actual_hash,
        "bytes": expected_bytes,
        "source_path": str(source),
        "source_sha256": source_hash,
        "source_current_matches": source_current_matches,
        "profile": data.get("profile"),
        "created_at": data.get("created_at"),
    }


class GameAssetEngineExportActions:
    def game_assets_blender_export_verified(self, payload: dict[str, Any]) -> ActionResult:
        supported = {
            "project",
            "blend_file",
            "engine",
            "output_path",
            "timeout_seconds",
            "overwrite",
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        project = self._project(payload)
        manifest_temp: Path | None = None
        try:
            blend_file = project.path(str(payload.get("blend_file") or ""))
            if blend_file.suffix.lower() != ".blend":
                raise ValueError("blend_file must be a .blend file")
            output = project.path(str(payload.get("output_path") or ""), must_exist=False)
            if not output.suffix:
                raise ValueError("output_path must include an engine export extension")
            if output == blend_file:
                raise ValueError("output_path must be different from blend_file")
            manifest = _manifest_path(output)
            overwrite = bool(payload.get("overwrite", False))
            if (output.exists() or manifest.exists()) and not overwrite:
                raise ValueError("engine export already exists; set overwrite=true explicitly")

            output.parent.mkdir(parents=True, exist_ok=True)
            source_before = _sha256(blend_file)
            source_bytes = blend_file.stat().st_size
            temporary = output.with_name(
                f".{output.stem}.ordax-{uuid.uuid4().hex}.tmp{output.suffix}"
            )
            temporary.unlink(missing_ok=True)
            export_payload = {
                "project": project.slug,
                "blend_file": _relative(project, blend_file),
                "engine": payload.get("engine"),
                "output_path": _relative(project, temporary),
            }
            if payload.get("timeout_seconds") is not None:
                export_payload["timeout_seconds"] = payload["timeout_seconds"]
            try:
                exported = self.game_assets_blender_export(export_payload)
                if not exported.ok:
                    return exported
                if not temporary.is_file():
                    return ActionResult(False, "verified engine export produced no temporary artifact")
                source_after = _sha256(blend_file)
                if source_after != source_before:
                    return ActionResult(False, "source blend changed during engine export; refusing derivative")
                artifact_hash = _sha256(temporary)
                artifact_bytes = temporary.stat().st_size
                manifest_data = {
                    "schema": ENGINE_EXPORT_SCHEMA,
                    "project": project.slug,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "engine": str(payload.get("engine") or "").strip().lower(),
                    "source": {
                        "path": _relative(project, blend_file),
                        "bytes": source_bytes,
                        "sha256": source_before,
                    },
                    "artifact": {
                        "path": _relative(project, output),
                        "format": output.suffix.lower().lstrip("."),
                        "bytes": artifact_bytes,
                        "sha256": artifact_hash,
                    },
                    "profile": exported.data.get("profile"),
                    "export_report": exported.data.get("report"),
                }
                manifest_temp = manifest.with_name(manifest.name + f".ordax-{uuid.uuid4().hex}.tmp")
                manifest_temp.write_text(
                    json.dumps(manifest_data, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                temporary.replace(output)
                manifest_temp.replace(manifest)
                manifest_temp = None
            finally:
                temporary.unlink(missing_ok=True)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))
        finally:
            if manifest_temp is not None:
                manifest_temp.unlink(missing_ok=True)

        return ActionResult(
            True,
            "verified Blender engine export completed",
            {
                "engine": manifest_data["engine"],
                "output_path": str(output),
                "manifest_path": str(manifest),
                "sha256": artifact_hash,
                "bytes": artifact_bytes,
                "source_sha256": source_before,
                "profile": manifest_data.get("profile"),
                "schema": ENGINE_EXPORT_SCHEMA,
            },
        )

    def game_assets_engine_export_verify(self, payload: dict[str, Any]) -> ActionResult:
        supported = {"project", "artifact_path", "manifest_path"}
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        project = self._project(payload)
        try:
            artifact = project.path(str(payload.get("artifact_path") or ""))
            raw_manifest = payload.get("manifest_path")
            manifest = (
                project.path(str(raw_manifest))
                if raw_manifest is not None
                else _manifest_path(artifact)
            )
            verified = verify_engine_export(project, artifact, manifest)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))
        return ActionResult(True, "engine export integrity verified", verified)

    def game_assets_engine_handoff_audit(self, payload: dict[str, Any]) -> ActionResult:
        supported = {
            "project",
            "artifact_path",
            "manifest_path",
            "require_current_source",
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        project = self._project(payload)
        try:
            artifact = project.path(str(payload.get("artifact_path") or ""))
            raw_manifest = payload.get("manifest_path")
            manifest = (
                project.path(str(raw_manifest))
                if raw_manifest is not None
                else _manifest_path(artifact)
            )
            verification = verify_engine_export(project, artifact, manifest)
            engine = str(verification.get("engine") or "").strip().lower()
            contract = _ENGINE_HANDOFF_CONTRACTS.get(engine)
            if contract is None:
                raise ValueError("engine export provenance targets an unsupported engine")
            artifact_format = artifact.suffix.lower().lstrip(".")
            if artifact_format not in contract["formats"]:
                allowed = ", ".join(sorted(contract["formats"]))
                raise ValueError(
                    f"{engine} handoff requires one of [{allowed}], got {artifact_format or 'no extension'}"
                )
            profile = verification.get("profile")
            if not isinstance(profile, dict):
                raise ValueError("engine export provenance is missing an export profile")
            profile_format = str(profile.get("format") or "").strip().lower()
            if profile_format != artifact_format:
                raise ValueError("engine export profile format does not match artifact extension")
            require_current_source = bool(payload.get("require_current_source", False))
            source_current = bool(verification.get("source_current_matches"))
            if require_current_source and not source_current:
                raise ValueError(
                    "source blend no longer matches the export provenance; create a fresh derivative"
                )
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))

        return ActionResult(
            True,
            f"{engine} engine handoff is provenance-valid and ready for import validation",
            {
                "engine": engine,
                "artifact_path": str(artifact),
                "manifest_path": str(manifest),
                "artifact_format": artifact_format,
                "sha256": verification["sha256"],
                "source_current_matches": source_current,
                "ready_for_engine_import": True,
                "validated_in_engine": False,
                "engine_validation_available": contract["engine_validation_available"],
                "next_gate": contract["next_gate"],
                "profile": profile,
                "contract": {
                    "accepted_formats": sorted(contract["formats"]),
                    "export_integrity_verified": True,
                    "profile_matches_artifact": True,
                    "source_freshness_required": require_current_source,
                },
            },
        )
