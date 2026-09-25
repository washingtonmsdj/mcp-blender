"""Verified generated-asset handoff into a registered Unity project.

The handoff refuses unverified provider output, reuses the existing atomic Unity
asset copier, and requires an Editor refresh before reporting the engine import
as confirmed. A failed Editor refresh never rewrites or deletes the canonical
source artifact, so the operation can be retried idempotently.
"""
from __future__ import annotations

from typing import Any

from .generated_asset_actions import _verification
from .models import ActionResult
from .unity_assets import asset_inventory, import_project_asset


_SUPPORTED_ENGINE_MODELS = frozenset({".fbx", ".obj", ".glb", ".gltf"})
_DEFAULT_DESTINATION_ROOT = "Assets/OrdaX/Generated"


def _wait_seconds(value: Any) -> float:
    if value is None:
        return 120.0
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("wait_seconds must be a number")
    result = float(value)
    if result < 5.0 or result > 600.0:
        raise ValueError("wait_seconds must be between 5 and 600")
    return result


def _unity_asset_path(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("asset_path must be a string")
    result = value.strip().replace("\\", "/")
    if not result.startswith("Assets/") or result.startswith("Assets/../"):
        raise ValueError("asset_path must stay inside Assets/")
    if "/../" in result or result.endswith("/.."):
        raise ValueError("asset_path must stay inside Assets/")
    suffix = "." + result.rsplit(".", 1)[-1].lower() if "." in result.rsplit("/", 1)[-1] else ""
    if suffix not in _SUPPORTED_ENGINE_MODELS and suffix != ".blend":
        raise ValueError("asset_path must be FBX, OBJ, Blend, GLB, or glTF")
    return result


class GameAssetUnityActions:
    """Move immutable generated evidence into Unity with an active import gate."""

    def game_assets_unity_import_generated(self, payload: dict[str, Any]) -> ActionResult:
        supported = {
            "project",
            "artifact_path",
            "manifest_path",
            "destination_path",
            "overwrite",
            "refresh",
            "wait_seconds",
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")

        project = self._project(payload)
        try:
            if "unity" not in project.apps:
                raise ValueError(f"Unity is not enabled for project {project.slug}")

            artifact = project.path(str(payload.get("artifact_path") or ""))
            if not artifact.is_file():
                raise ValueError("artifact_path must be a file")
            if artifact.suffix.lower() not in _SUPPORTED_ENGINE_MODELS:
                raise ValueError("artifact_path must be FBX, OBJ, GLB, or glTF")

            manifest_raw = payload.get("manifest_path")
            manifest = (
                project.path(str(manifest_raw))
                if manifest_raw is not None
                else artifact.with_name(artifact.name + ".ordax.json")
            )
            verification = _verification(project, artifact, manifest)

            destination_raw = payload.get("destination_path")
            if destination_raw is None:
                destination_raw = f"{_DEFAULT_DESTINATION_ROOT}/{artifact.name}"
            destination_asset_path = _unity_asset_path(str(destination_raw))
            destination = project.path(destination_asset_path, must_exist=False)
            overwrite = bool(payload.get("overwrite", False))
            copy_report = import_project_asset(
                project.root,
                source_path=artifact,
                destination_path=destination,
                overwrite=overwrite,
            )

            refresh_requested = bool(payload.get("refresh", True))
            refresh_report: dict[str, Any] | None = None
            if refresh_requested:
                wait = _wait_seconds(payload.get("wait_seconds"))
                refresh_result = self.unity_refresh_editor(
                    {
                        "project": project.slug,
                        "force": True,
                        "wait_seconds": wait,
                    }
                )
                refresh_report = {
                    "ok": refresh_result.ok,
                    "summary": refresh_result.summary,
                    "data": refresh_result.data,
                }
                if not refresh_result.ok:
                    return ActionResult(
                        False,
                        "generated asset copied into Unity Assets but Editor import refresh was not confirmed",
                        {
                            "integrity": verification,
                            "copy": copy_report,
                            "unity_refresh": refresh_report,
                            "retryable": True,
                            "source_preserved": True,
                        },
                    )

            inventory = asset_inventory(
                project.root,
                terms=[destination.name],
                max_results=100,
            )
            asset_path = copy_report["asset_path"]
            visible = any(
                isinstance(item, dict) and item.get("path") == asset_path
                for item in inventory.get("matches", [])
            )
            if not visible:
                return ActionResult(
                    False,
                    "Unity asset copy completed but the destination was not visible in the project inventory",
                    {
                        "integrity": verification,
                        "copy": copy_report,
                        "unity_refresh": refresh_report,
                        "inventory": inventory,
                    },
                )
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))

        return ActionResult(
            True,
            "generated asset imported into Unity project",
            {
                "integrity": verification,
                "copy": copy_report,
                "unity_refresh": refresh_report,
                "asset_path": asset_path,
                "engine": "unity",
                "source_preserved": True,
                "import_confirmed": refresh_requested,
            },
        )

    def game_assets_unity_model_audit(self, payload: dict[str, Any]) -> ActionResult:
        supported = {"project", "asset_path", "timeout_seconds"}
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")

        project = self._project(payload)
        try:
            if "unity" not in project.apps:
                raise ValueError(f"Unity is not enabled for project {project.slug}")
            asset_path = _unity_asset_path(payload.get("asset_path"))
            physical = project.path(asset_path)
            if not physical.is_file():
                raise ValueError("asset_path must exist inside the Unity project")
            timeout = payload.get("timeout_seconds", 180)
            if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 5 or timeout > 600:
                raise ValueError("timeout_seconds must be an integer between 5 and 600")
            editor = self._editor({"project": project.slug})
            response = editor.request(
                "asset_model_audit",
                {"assetPath": asset_path},
                timeout_seconds=float(timeout),
            )
            if response is None:
                return ActionResult(
                    False,
                    "Unity companion is not ready for model import audit",
                    {"asset_path": asset_path, "retryable": True},
                )
            if not response.ok:
                return response
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))

        return ActionResult(
            True,
            "Unity model import audit passed",
            {
                "asset_path": asset_path,
                "engine": "unity",
                "audit": response.data,
            },
        )
