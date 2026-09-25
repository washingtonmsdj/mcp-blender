"""Semantic production gates backed by Unity Editor evidence."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
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
_ADVANCED_REQUIREMENT_FIELDS = frozenset(
    {
        "include_advanced_telemetry",
        "require_avatar",
        "require_valid_avatar",
        "require_humanoid_avatar",
        "require_root_motion",
        "require_human_motion",
        "require_skinned_renderer",
        "require_all_lod_levels_have_renderers",
        "min_humanoid_mapped_bones",
        "min_root_motion_clips",
        "min_human_motion_clips",
        "min_lod_levels",
        "min_lod_renderers",
        "min_skinned_renderers",
    }
)
_ADVANCED_PROTOCOL = "ordax-game-assets-v1"


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


def _require_flag(value: Any, field: str) -> bool:
    parsed = _optional_bool(value, field)
    return bool(parsed)


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


def _timeout_seconds(value: Any) -> float:
    if value is None:
        return 180.0
    if isinstance(value, bool) or not isinstance(value, int) or value < 5 or value > 600:
        raise ValueError("timeout_seconds must be an integer between 5 and 600")
    return float(value)


def _fresh(path: Path, max_age_seconds: float = 8.0) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
        return 0 <= age <= max_age_seconds
    except OSError:
        return False


class GameAssetUnitySemanticActions:
    """Require explicit production semantics from evidence reported by Unity itself."""

    def _install_game_asset_companion(self, project) -> tuple[Path, bool]:
        source = Path(__file__).parent / "assets" / "OrdaXGameAssetAgent.cs"
        if not source.is_file():
            raise FileNotFoundError("packaged Unity game asset companion is missing")
        target = project.path(
            "Assets/OrdaX/Editor/OrdaXGameAssetAgent.cs", must_exist=False
        )
        content = source.read_bytes()
        before = target.read_bytes() if target.is_file() else None
        if before is not None and before != content:
            try:
                existing = before.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise ValueError(
                    "existing Unity game asset companion is not valid UTF-8; refusing overwrite"
                ) from error
            markers = (
                "class OrdaXGameAssetAgent",
                "ordax-game-assets-v1",
                "namespace OrdaX.EditorTools",
            )
            if not all(marker in existing for marker in markers):
                raise ValueError(
                    "existing Unity game asset companion is not OrdaX-managed; refusing overwrite"
                )
        target.parent.mkdir(parents=True, exist_ok=True)
        changed = before != content
        if changed:
            temporary = target.with_name(target.name + f".ordax-{uuid.uuid4().hex}.tmp")
            try:
                temporary.write_bytes(content)
                if temporary.read_bytes() != content:
                    raise OSError("temporary Unity game asset companion verification failed")
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return target, changed

    def _advanced_unity_audit(
        self,
        *,
        project,
        asset_path: str,
        timeout_seconds: float,
    ) -> ActionResult:
        try:
            companion, changed = self._install_game_asset_companion(project)
        except (ValueError, OSError, FileNotFoundError) as error:
            return ActionResult(False, str(error))

        root = project.root / "Library" / "OrdaXAgent" / "game-assets"
        presence = root / "presence.json"
        if changed or not _fresh(presence):
            refreshed = self.unity_refresh_editor(
                {
                    "project": project.slug,
                    "force": True,
                    "wait_seconds": min(120.0, timeout_seconds),
                }
            )
            if not refreshed.ok:
                return ActionResult(
                    False,
                    "Unity game asset companion was installed but Editor refresh was not confirmed",
                    {
                        "retryable": True,
                        "companion_path": str(companion),
                        "refresh": refreshed.data,
                    },
                )
            deadline = time.monotonic() + min(timeout_seconds, 120.0)
            while time.monotonic() < deadline and not _fresh(presence):
                time.sleep(0.25)
        if not _fresh(presence):
            return ActionResult(
                False,
                "Unity game asset telemetry companion did not become ready",
                {
                    "retryable": True,
                    "companion_path": str(companion),
                    "presence_path": str(presence),
                },
            )

        inbox = root / "inbox"
        responses = root / "responses"
        inbox.mkdir(parents=True, exist_ok=True)
        responses.mkdir(parents=True, exist_ok=True)
        command_id = uuid.uuid4().hex
        command_path = inbox / f"{command_id}.json"
        temp_path = inbox / f"{command_id}.tmp"
        response_path = responses / f"{command_id}.json"
        temp_path.write_text(
            json.dumps(
                {
                    "id": command_id,
                    "action": "asset_character_audit",
                    "assetPath": asset_path,
                }
            ),
            encoding="utf-8",
        )
        temp_path.replace(command_path)

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if response_path.is_file():
                try:
                    response = json.loads(response_path.read_text(encoding="utf-8-sig"))
                except (OSError, json.JSONDecodeError) as error:
                    return ActionResult(False, f"Unity game asset telemetry response is invalid: {error}")
                finally:
                    response_path.unlink(missing_ok=True)
                if not isinstance(response, dict):
                    return ActionResult(False, "Unity game asset telemetry response must be an object")
                if response.get("protocol") != _ADVANCED_PROTOCOL:
                    return ActionResult(
                        False,
                        "Unity game asset telemetry companion protocol is incompatible",
                        {"retryable": True, "response": response},
                    )
                if not bool(response.get("ok")):
                    return ActionResult(
                        False,
                        str(response.get("summary") or "Unity game asset telemetry failed"),
                        response,
                    )
                return ActionResult(
                    True,
                    "Unity advanced game asset telemetry completed",
                    {
                        "transport": "unity-game-asset-companion",
                        **response,
                    },
                )
            time.sleep(0.2)

        command_path.unlink(missing_ok=True)
        return ActionResult(
            False,
            "Unity game asset telemetry timed out; inspect Editor state before retrying",
            {
                "retryable": True,
                "outcome_unknown": True,
                "command_id": command_id,
            },
        )

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
            *_ADVANCED_REQUIREMENT_FIELDS,
        }
        unsupported = set(payload) - supported
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")

        try:
            timeout = _timeout_seconds(payload.get("timeout_seconds"))
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
            advanced_minimums = {
                "humanoidMappedBoneCount": _non_negative_int(
                    payload.get("min_humanoid_mapped_bones"), "min_humanoid_mapped_bones"
                ),
                "motionCurveClipCount": _non_negative_int(
                    payload.get("min_root_motion_clips"), "min_root_motion_clips"
                ),
                "humanMotionClipCount": _non_negative_int(
                    payload.get("min_human_motion_clips"), "min_human_motion_clips"
                ),
                "lodLevelCount": _non_negative_int(payload.get("min_lod_levels"), "min_lod_levels"),
                "lodRendererCount": _non_negative_int(
                    payload.get("min_lod_renderers"), "min_lod_renderers"
                ),
                "skinnedMeshRendererCount": _non_negative_int(
                    payload.get("min_skinned_renderers"), "min_skinned_renderers"
                ),
            }
            advanced_flags = {
                "require_avatar": _require_flag(payload.get("require_avatar"), "require_avatar"),
                "require_valid_avatar": _require_flag(
                    payload.get("require_valid_avatar"), "require_valid_avatar"
                ),
                "require_humanoid_avatar": _require_flag(
                    payload.get("require_humanoid_avatar"), "require_humanoid_avatar"
                ),
                "require_root_motion": _require_flag(
                    payload.get("require_root_motion"), "require_root_motion"
                ),
                "require_human_motion": _require_flag(
                    payload.get("require_human_motion"), "require_human_motion"
                ),
                "require_skinned_renderer": _require_flag(
                    payload.get("require_skinned_renderer"), "require_skinned_renderer"
                ),
                "require_all_lod_levels_have_renderers": _require_flag(
                    payload.get("require_all_lod_levels_have_renderers"),
                    "require_all_lod_levels_have_renderers",
                ),
            }
            include_advanced = _require_flag(
                payload.get("include_advanced_telemetry"), "include_advanced_telemetry"
            )
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

        advanced_requested = include_advanced or any(advanced_flags.values()) or any(
            value is not None for value in advanced_minimums.values()
        )
        advanced: dict[str, Any] | None = None
        if advanced_requested:
            project = self._project(payload)
            asset_path = str(audited.data.get("asset_path") or payload.get("asset_path") or "")
            advanced_result = self._advanced_unity_audit(
                project=project,
                asset_path=asset_path,
                timeout_seconds=timeout,
            )
            if not advanced_result.ok:
                return advanced_result
            advanced = advanced_result.data

            valid_avatar_count = max(
                int(advanced.get("validAvatarCount") or 0),
                int(advanced.get("animatorWithAvatarCount") or 0),
            )
            human_avatar_count = max(
                int(advanced.get("humanAvatarCount") or 0),
                int(advanced.get("humanAnimatorCount") or 0),
            )
            if advanced_flags["require_avatar"] and (
                int(advanced.get("avatarCount") or 0) <= 0
                and int(advanced.get("animatorWithAvatarCount") or 0) <= 0
            ):
                failures.append("Unity model has no Avatar evidence")
            if advanced_flags["require_valid_avatar"] and valid_avatar_count <= 0:
                failures.append("Unity model has no valid Mecanim Avatar")
            if advanced_flags["require_humanoid_avatar"] and human_avatar_count <= 0:
                failures.append("Unity model has no valid humanoid Avatar")
            if advanced_flags["require_root_motion"] and int(
                advanced.get("motionCurveClipCount") or 0
            ) <= 0:
                failures.append("no AnimationClip reports root-motion curves")
            if advanced_flags["require_human_motion"] and int(
                advanced.get("humanMotionClipCount") or 0
            ) <= 0:
                failures.append("no AnimationClip reports humanoid motion")
            if advanced_flags["require_skinned_renderer"] and int(
                advanced.get("skinnedMeshRendererCount") or 0
            ) <= 0:
                failures.append("model has no SkinnedMeshRenderer")
            if advanced_flags["require_all_lod_levels_have_renderers"] and int(
                advanced.get("lodEmptyLevelCount") or 0
            ) > 0:
                failures.append(
                    f"{int(advanced.get('lodEmptyLevelCount') or 0)} LOD level(s) have no renderer assignment"
                )
            for field, minimum in advanced_minimums.items():
                if minimum is None:
                    continue
                actual = int(advanced.get(field) or 0)
                if actual < minimum:
                    failures.append(f"{field} is {actual}, minimum required is {minimum}")

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
                "advanced_audit": advanced,
                "requirements": {
                    "expected_animation_type": expected_animation_type,
                    "require_animation_import": require_animation_import,
                    "minimums": {key: value for key, value in minimums.items() if value is not None},
                    "max_lod_groups": max_lod_groups,
                    "advanced_flags": advanced_flags,
                    "advanced_minimums": {
                        key: value for key, value in advanced_minimums.items() if value is not None
                    },
                },
                "limitations": (
                    [
                        "advanced_avatar_root_motion_lod_telemetry_not_requested",
                    ]
                    if not advanced_requested
                    else [
                        "root_motion_curve_presence_does_not_define_gameplay_root_motion_policy",
                    ]
                ),
            },
        )
