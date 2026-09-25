"""Engine handoff readiness gates for verified Blender export derivatives.

This module deliberately does not claim an engine import succeeded.  It verifies
that the immutable export derivative still matches its provenance, that the
engine/format/profile contract is coherent, and returns the next engine-side
validation gate that must still run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .game_asset_engine_export_actions import verify_engine_export
from .models import ActionResult


_ENGINE_CONTRACTS: dict[str, dict[str, Any]] = {
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


def _artifact_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if not suffix:
        raise ValueError("engine export artifact has no file extension")
    return suffix


class GameAssetEngineHandoffActions:
    """Validate a verified export before it crosses into an engine/toolchain."""

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
                else artifact.with_name(artifact.name + ".ordax.json")
            )
            verification = verify_engine_export(project, artifact, manifest)
            engine = str(verification.get("engine") or "").strip().lower()
            contract = _ENGINE_CONTRACTS.get(engine)
            if contract is None:
                raise ValueError("engine export provenance targets an unsupported engine")

            artifact_format = _artifact_format(artifact)
            if artifact_format not in contract["formats"]:
                allowed = ", ".join(sorted(contract["formats"]))
                raise ValueError(
                    f"{engine} handoff requires one of [{allowed}], got {artifact_format}"
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
