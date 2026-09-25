"""Capability catalog for the OrdaX game-asset ecosystem."""
from __future__ import annotations

import os
from typing import Any

from .aleph_actions import ALEPH_PINNED_REF
from .models import ActionResult


class GameAssetCatalogActions:
    """Expose integrated providers and researched extension points in one place."""

    def game_assets_providers(self, payload: dict[str, Any]) -> ActionResult:
        unsupported = set(payload) - {"project"}
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        providers = {
            "adobe_mixamo": {
                "mode": "validated_manual_handoff",
                "configured": True,
                "capabilities": [
                    "humanoid_auto_rig",
                    "humanoid_animation_library",
                    "fbx_roundtrip",
                ],
                "actions": [
                    "game_assets.mixamo_handoff",
                    "game_assets.blender_import_fbx",
                ],
                "notes": [
                    "Uses Adobe's documented web workflow; no private API or browser scraping.",
                    "Already-rigged uploads use FBX.",
                ],
            },
            "tripo": {
                "mode": "api",
                "configured": bool(os.environ.get("TRIPO_API_KEY")),
                "credential_env": "TRIPO_API_KEY",
                "capabilities": [
                    "text_to_model",
                    "pre_rig_check",
                    "rig",
                    "mixamo_skeleton_spec",
                    "animation_retarget",
                    "smart_lowpoly",
                    "canonical_artifact_download",
                ],
                "actions": [
                    "game_assets.provider_submit",
                    "game_assets.provider_status",
                    "game_assets.provider_download",
                ],
            },
            "meshy": {
                "mode": "api",
                "configured": bool(os.environ.get("MESHY_API_KEY")),
                "credential_env": "MESHY_API_KEY",
                "capabilities": [
                    "text_to_3d",
                    "pbr_refine",
                    "humanoid_rig",
                    "animation",
                    "text_to_motion",
                    "canonical_artifact_download",
                ],
                "actions": [
                    "game_assets.provider_submit",
                    "game_assets.provider_status",
                    "game_assets.provider_download",
                ],
            },
            "hyper3d_rodin": {
                "mode": "api",
                "configured": bool(os.environ.get("RODIN_API_KEY")),
                "credential_env": "RODIN_API_KEY",
                "capabilities": [
                    "text_to_3d",
                    "pbr",
                    "raw_or_quad_mesh",
                    "face_budget",
                    "ta_pose_conditioning",
                    "glb_fbx_obj_stl_usdz",
                    "canonical_artifact_download",
                ],
                "actions": [
                    "game_assets.rodin_submit_text",
                    "game_assets.rodin_status",
                    "game_assets.rodin_download_manifest",
                    "game_assets.provider_download",
                ],
            },
            "comfyui_local": {
                "mode": "local_loopback_workflow",
                "configured": True,
                "endpoint_env": "ORDAX_COMFYUI_URL",
                "default_endpoint": "http://127.0.0.1:8188",
                "capabilities": [
                    "project_versioned_workflows",
                    "3d_node_discovery",
                    "local_gpu_generation",
                    "workflow_history",
                ],
                "actions": [
                    "game_assets.comfyui_status",
                    "game_assets.comfyui_node_info",
                    "game_assets.comfyui_run_workflow",
                    "game_assets.comfyui_history",
                ],
                "security": "loopback-only",
            },
            "alephgeo": {
                "mode": "managed_external_component",
                "configured": True,
                "auto_install_on_first_use": True,
                "upstream": "Belluxx/Aleph",
                "pinned_ref": ALEPH_PINNED_REF,
                "capabilities": [
                    "place_resolution",
                    "satellite_imagery",
                    "streetview_reference_photos",
                    "osm_buildings_and_roads",
                    "terrain_elevation",
                    "resumable_area_capture",
                    "capture_inspection",
                    "blender_terrain_reconstruction",
                    "blender_osm_building_massing",
                    "blender_road_curves",
                    "blender_streetview_reference_cameras",
                ],
                "actions": [
                    "geo.aleph_status",
                    "geo.aleph_ensure",
                    "geo.aleph_update",
                    "geo.aleph_resolve",
                    "geo.aleph_satellite",
                    "geo.aleph_streetview",
                    "geo.aleph_capture",
                    "geo.aleph_capture_resume",
                    "geo.aleph_capture_export",
                    "geo.aleph_capture_inspect",
                    "geo.aleph_blender_stage",
                ],
                "notes": [
                    "Installed into an isolated Device Agent state-directory virtual environment.",
                    "Upstream explicitly warns that it uses undocumented APIs and may break or hit rate limits.",
                    "Captured data is canonical; Blender scenes are reproducible local-metre derivatives.",
                ],
            },
        }
        return ActionResult(True, "game-asset providers inspected", {"providers": providers})

    def game_assets_ecosystem_catalog(self, payload: dict[str, Any]) -> ActionResult:
        unsupported = set(payload) - {"project"}
        if unsupported:
            return ActionResult(False, f"unsupported fields: {', '.join(sorted(unsupported))}")
        catalog = {
            "integrated": {
                "cloud_generation": ["tripo", "meshy", "hyper3d_rodin"],
                "local_generation_host": ["comfyui_local"],
                "world_reference_capture": ["alephgeo"],
                "world_reconstruction": ["alephgeo", "blender"],
                "rig_animation": ["adobe_mixamo", "tripo", "meshy"],
                "dcc": ["blender"],
                "engines": ["unity", "unreal_export", "godot_export", "web_gltf"],
            },
            "canonical_generated_artifacts": {
                "action": "game_assets.provider_download",
                "providers": ["tripo", "meshy", "rodin"],
                "properties": [
                    "provider_status_is_retrieved_server_side",
                    "job_cannot_supply_arbitrary_download_url",
                    "https_only_result_download",
                    "bounded_streaming_download",
                    "atomic_partial_file_replacement",
                    "sha256_content_identity",
                    "sidecar_provenance_manifest",
                    "signed_query_parameters_are_not_persisted",
                    "explicit_overwrite_required",
                ],
                "manifest_schema": "ordax.generated-asset/1",
                "purpose": "turn short-lived provider task results into durable project-local evidence and pipeline inputs",
            },
            "world_generation_pipeline": {
                "reference_source": "alephgeo",
                "inputs": [
                    "satellite_png_or_geotiff",
                    "terrain_geotiff",
                    "osm_buildings_roads_and_pois",
                    "streetview_reference_photos",
                ],
                "implemented_stages": [
                    "inspect_and_validate_capture",
                    "normalize_to_local_metre_coordinates",
                    "construct_blender_terrain_with_uv",
                    "apply_packed_satellite_reference_material",
                    "extrude_osm_building_massing",
                    "construct_width_classed_road_curves",
                    "create_georeferenced_streetview_reference_cameras",
                    "store_geographic_provenance_metadata",
                ],
                "next_stages": [
                    "architectural_facade_detail",
                    "road_intersection_and_lane_semantics",
                    "vegetation_and_poi_instancing",
                    "collision_navmesh_and_runtime_lod",
                    "engine_specific_world_import_validation",
                ],
                "reliability_note": "Aleph uses undocumented upstream data APIs; capture artifacts should be cached and reproducible locally.",
            },
            "local_model_candidates": {
                "trellis_2": {
                    "route": "ComfyUI workflow or isolated local adapter",
                    "strength": "high-fidelity image-to-3D with PBR materials",
                    "constraint": "upstream documents Linux + NVIDIA GPU >=24GB",
                    "integration_state": "candidate_not_bundled",
                },
                "hunyuan3d_2_1": {
                    "route": "ComfyUI workflow or isolated FastAPI adapter",
                    "strength": "image-to-3D, optional texture, GLB/OBJ API",
                    "constraint": "upstream model code/weights carry Tencent Hunyuan non-commercial terms",
                    "integration_state": "candidate_not_bundled",
                },
                "stable_fast_3d": {
                    "route": "ComfyUI workflow",
                    "strength": "fast single-image 3D asset generation",
                    "constraint": "validate model license and target GPU before deployment",
                    "integration_state": "candidate_not_bundled",
                },
            },
            "motion_candidates": {
                "deepmotion": {
                    "strength": "video-to-3D markerless mocap with custom-character retarget",
                    "route": "future API adapter",
                },
                "rokoko": {
                    "strength": "studio recording/calibration command API and FBX/BVH export workflows",
                    "route": "future workstation adapter",
                },
                "cascadeur": {
                    "strength": "animation cleanup/authoring with Python scripting API",
                    "route": "future workstation adapter",
                },
            },
            "optimization_targets": {
                "canonical_web_exchange": "glTF 2.0 / GLB",
                "texture_delivery": "KTX2/BasisU where the target supports KHR_texture_basisu",
                "future_passes": [
                    "meshopt_or_draco_geometry_compression",
                    "ktx2_texture_compression",
                    "lod_generation",
                    "orm_texture_packing",
                    "per_engine_triangle_material_texture_budgets",
                ],
            },
            "quality_gates": [
                "geometry_topology",
                "uv_and_materials",
                "skin_influence_budget",
                "armature_and_actions",
                "origin_scale_axes",
                "visual_multiview_review",
                "engine_import_validation",
            ],
        }
        return ActionResult(True, "game-asset ecosystem catalog", {"catalog": catalog})
