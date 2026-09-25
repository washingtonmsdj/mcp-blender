"""Semantic production gates layered on top of Unity's real model-import audit."""
from __future__ import annotations

from typing import Any

from .models import ActionResult


_REQUIRED_AUDIT_FIELDS = frozenset(
    {
        "modelImporterPresent",
        "modelAnimationType",
        "modelImportAnimation",
        "modelMeshCount",
        "modelAnimationClipCount",
        "modelBoneCount",
        "modelBlendShapeCount",
        "modelLodGroupCount",
    }
)


def _non_negative_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _animation_type(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected_animation_type must be a string")
    result = value.strip().lower()
    allowed = {"none", "legacy", "generic", "human", "humanoid"}
    if result not in allowed:
        raise ValueError(
            "expected_animation_type must be one of: none, legacy, generic, human, humanoid"
        )
    return "human" if result == "humanoid" else result


class GameAssetUnitySemanticActions:
    """Require explicit production semantics from evidence already reported by Unity."""

    def game_assets_unity_semantic_audit(self, payload: dict[str, Any]) -> ActionResult:
        supported = {
            "project",
            "asset_path",
            "timeout_seconds",
            "expected_animation_type",
            "require_animation_import",
            "min_meshes",
            "min_bones",
            "min_animation_clips",
            "min_blend_shapes",
            "min_lod_groups",
            "max_lod_groups",
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")

        try:
            expected_animation_type = _animation_type(payload.get("expected_animation_type"))
            require_animation_import = _optional_bool(
                payload.get("require_animation_import"), "require_animation_import"
            )
            minimums = {
                "modelMeshCount": _non_negative_int(payload.get("min_meshes"), "min_meshes"),
                "modelBoneCount": _non_negative_int(payload.get("min_bones"), "min_bones"),
                "modelAnimationClipCount": _non_negative_int(
                    payload.get("min_animation_clips"), "min_animation_clips"
                ),
                "modelBlendShapeCount": _non_negative_int(
                    payload.get("min_blend_shapes"), "min_blend_shapes"
                ),
                "modelLodGroupCount": _non_negative_int(
                    payload.get("min_lod_groups"), "min_lod_groups"
                ),
            }
            max_lod_groups = _non_negative_int(payload.get("max_lod_groups"), "max_lod_groups")
            if (
                minimums["modelLodGroupCount"] is not None
                and max_lod_groups is not None
                and minimums["modelLodGroupCount"] > max_lod_groups
            ):
                raise ValueError("min_lod_groups cannot exceed max_lod_groups")
        except ValueError as error:
            return ActionResult(False, str(error))

        audit_payload = {
            key: payload[key]
            for key in ("project", "asset_path", "timeout_seconds")
            if key in payload
        }
        audited = self.game_assets_unity_model_audit(audit_payload)
        if not audited.ok:
            return audited

        evidence = audited.data.get("audit")
        if not isinstance(evidence, dict):
            return ActionResult(
                False,
                "Unity model audit returned no semantic evidence",
                {"retryable": True, "audit_result": audited.data},
            )
        missing = sorted(_REQUIRED_AUDIT_FIELDS - set(evidence))
        if missing:
            return ActionResult(
                False,
                "Unity companion is too old for semantic asset validation",
                {"missing_fields": missing, "retryable": True, "audit": evidence},
            )

        failures: list[str] = []
        if not bool(evidence.get("modelImporterPresent")):
            failures.append("asset is not backed by a Unity ModelImporter")

        actual_animation_type = str(evidence.get("modelAnimationType") or "").strip().lower()
        if expected_animation_type is not None and actual_animation_type != expected_animation_type:
            failures.append(
                f"animation type is {actual_animation_type or 'missing'}, expected {expected_animation_type}"
            )

        if (
            require_animation_import is not None
            and bool(evidence.get("modelImportAnimation")) != require_animation_import
        ):
            failures.append(
                "animation import is "
                + ("enabled" if bool(evidence.get("modelImportAnimation")) else "disabled")
                + ", expected "
                + ("enabled" if require_animation_import else "disabled")
            )

        for field, minimum in minimums.items():
            if minimum is None:
                continue
            actual = int(evidence.get(field) or 0)
            if actual < minimum:
                failures.append(f"{field} is {actual}, minimum required is {minimum}")

        if max_lod_groups is not None:
            actual_lods = int(evidence.get("modelLodGroupCount") or 0)
            if actual_lods > max_lod_groups:
                failures.append(
                    f"modelLodGroupCount is {actual_lods}, maximum allowed is {max_lod_groups}"
                )

        return ActionResult(
            not failures,
            (
                "Unity semantic asset requirements passed"
                if not failures
                else "Unity asset loaded but semantic requirements failed"
            ),
            {
                "engine": "unity",
                "asset_path": audited.data.get("asset_path"),
                "engine_loaded": True,
                "semantic_requirements_passed": not failures,
                "failures": failures,
                "audit": evidence,
                "requirements": {
                    "expected_animation_type": expected_animation_type,
                    "require_animation_import": require_animation_import,
                    "minimums": {key: value for key, value in minimums.items() if value is not None},
                    "max_lod_groups": max_lod_groups,
                },
                "limitations": [
                    "avatar_mapping_not_yet_reported_by_companion",
                    "root_motion_not_yet_reported_by_companion",
                    "per_lod_renderer_assignment_not_checked_here",
                ],
            },
        )
