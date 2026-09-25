"""Apply/audit ordax.visual-environment/1 inside an isolated Blender process."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

ENVIRONMENT_SCHEMA = "ordax.visual-environment/1"
SUN_OBJECT = "OrdaX_Environment_Sun"
OCEAN_OBJECT = "OrdaX_Environment_Ocean"
OCEAN_MATERIAL = "OrdaX_Environment_Ocean_Material"


def _args() -> Path:
    raw = sys.argv
    raw = raw[raw.index("--") + 1 :] if "--" in raw else []
    if len(raw) != 1:
        raise RuntimeError("expected exactly one environment request JSON path")
    return Path(raw[0]).resolve()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("environment request must contain a JSON object")
    return payload


def _set_if(target: Any, name: str, value: Any, applied: dict[str, Any]) -> None:
    if hasattr(target, name):
        try:
            setattr(target, name, value)
            applied[name] = value
        except (TypeError, ValueError):
            applied[name] = {"requested": value, "applied": False}


def _input(node: Any, names: tuple[str, ...]):
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            return socket
    return None


def _kelvin_rgb(kelvin: float) -> tuple[float, float, float]:
    """Approximate black-body RGB for viewport/reference lighting."""
    temperature = max(1000.0, min(40000.0, kelvin)) / 100.0
    if temperature <= 66.0:
        red = 255.0
        green = 99.4708025861 * math.log(temperature) - 161.1195681661
        blue = 0.0 if temperature <= 19.0 else 138.5177312231 * math.log(temperature - 10.0) - 305.0447927307
    else:
        red = 329.698727446 * ((temperature - 60.0) ** -0.1332047592)
        green = 288.1221695283 * ((temperature - 60.0) ** -0.0755148492)
        blue = 255.0
    clamp = lambda value: max(0.0, min(255.0, value)) / 255.0
    return clamp(red), clamp(green), clamp(blue)


def _sun_direction(environment: dict[str, Any]) -> Vector:
    elevation = math.radians(float(environment["sun"]["elevation_deg"]))
    azimuth = math.radians(float(environment["sun"]["azimuth_deg"]))
    return Vector(
        (
            math.sin(azimuth) * math.cos(elevation),
            math.cos(azimuth) * math.cos(elevation),
            math.sin(elevation),
        )
    ).normalized()


def _apply_color_management(scene: bpy.types.Scene, environment: dict[str, Any]) -> dict[str, Any]:
    exposure = float(environment["exposure"]["ev100"])
    tone_mapping = str(environment["exposure"]["tone_mapping"])
    result: dict[str, Any] = {"tone_mapping": tone_mapping, "ev100": exposure}
    # Shared EV100 is a semantic exposure target, not Blender's direct exposure unit.
    blender_exposure = max(-10.0, min(10.0, 14.0 - exposure))
    try:
        scene.view_settings.exposure = blender_exposure
        result["blender_exposure"] = blender_exposure
    except (TypeError, ValueError, AttributeError):
        result["blender_exposure"] = None
    if tone_mapping == "agx":
        try:
            scene.view_settings.view_transform = "AgX"
            result["view_transform"] = "AgX"
        except (TypeError, ValueError, AttributeError):
            result["view_transform"] = None
    return result


def _apply_world(scene: bpy.types.Scene, environment: dict[str, Any]) -> dict[str, Any]:
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("OrdaX_Environment_World")
        scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    links.new(sky.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])

    applied: dict[str, Any] = {"sky_type": "NISHITA"}
    sun = environment["sun"]
    sky_values = environment["sky"]
    _set_if(sky, "sun_elevation", math.radians(float(sun["elevation_deg"])), applied)
    _set_if(sky, "sun_rotation", math.radians(float(sun["azimuth_deg"])), applied)
    _set_if(sky, "altitude", 0.0, applied)
    _set_if(sky, "air_density", max(0.1, min(5.0, float(sky_values["rayleigh"]) / 2.4)), applied)
    _set_if(sky, "dust_density", max(0.0, min(10.0, float(sky_values["mie_coefficient"]) / 0.006)), applied)
    _set_if(sky, "ozone_density", 1.0, applied)
    _set_if(sky, "sun_disc", True, applied)
    _set_if(sky, "sun_intensity", max(0.0, min(10.0, float(sun["intensity_lux"]) / 100000.0)), applied)
    background.inputs["Strength"].default_value = max(0.1, min(2.0, 0.9 - (float(sky_values["turbidity"]) - 2.0) * 0.03))
    applied["background_strength"] = float(background.inputs["Strength"].default_value)

    fog_density = float(environment["atmosphere"]["fog_density"])
    if fog_density > 0.0:
        try:
            volume = nodes.new("ShaderNodeVolumePrincipled")
            density = _input(volume, ("Density",))
            anisotropy = _input(volume, ("Anisotropy",))
            if density is not None:
                density.default_value = max(0.0, min(0.05, fog_density * 0.002))
            if anisotropy is not None:
                anisotropy.default_value = 0.2
            links.new(volume.outputs["Volume"], output.inputs["Volume"])
            applied["volume_density"] = float(density.default_value) if density is not None else None
        except RuntimeError:
            applied["volume_density"] = None
    else:
        applied["volume_density"] = 0.0
    return applied


def _apply_sun(scene: bpy.types.Scene, environment: dict[str, Any]) -> dict[str, Any]:
    obj = bpy.data.objects.get(SUN_OBJECT)
    if obj is not None and obj.type != "LIGHT":
        raise RuntimeError(f"{SUN_OBJECT} exists but is not a Light object")
    if obj is None:
        light = bpy.data.lights.new(SUN_OBJECT + "_Data", "SUN")
        obj = bpy.data.objects.new(SUN_OBJECT, light)
        scene.collection.objects.link(obj)
    light = obj.data
    light.type = "SUN"
    direction = _sun_direction(environment)
    obj.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    lux = float(environment["sun"]["intensity_lux"])
    light.energy = max(0.0, min(10.0, lux / 50000.0))
    light.color = _kelvin_rgb(float(environment["sun"]["color_temperature_k"]))
    if hasattr(light, "angle"):
        light.angle = math.radians(0.53)
    obj["ordax_role"] = "environment_sun"
    obj["ordax_environment_schema"] = ENVIRONMENT_SCHEMA
    return {
        "name": obj.name,
        "energy": float(light.energy),
        "color": [round(float(value), 6) for value in light.color],
        "direction": [round(float(value), 6) for value in direction],
    }


def _water_material(environment: dict[str, Any]) -> bpy.types.Material:
    material = bpy.data.materials.get(OCEAN_MATERIAL)
    if material is None:
        material = bpy.data.materials.new(OCEAN_MATERIAL)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    deep = environment["ocean"]["deep_color"]
    bsdf.inputs["Base Color"].default_value = (*[float(value) for value in deep], 1.0)
    roughness = _input(bsdf, ("Roughness",))
    if roughness is not None:
        roughness.default_value = float(environment["ocean"]["roughness"])
    metallic = _input(bsdf, ("Metallic",))
    if metallic is not None:
        metallic.default_value = 0.0
    ior = _input(bsdf, ("IOR",))
    if ior is not None:
        ior.default_value = 1.333
    transmission = _input(bsdf, ("Transmission Weight", "Transmission"))
    if transmission is not None:
        transmission.default_value = 0.65
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def _remove_ocean() -> None:
    obj = bpy.data.objects.get(OCEAN_OBJECT)
    if obj is None:
        return
    mesh = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _apply_ocean(scene: bpy.types.Scene, environment: dict[str, Any]) -> dict[str, Any]:
    ocean = environment["ocean"]
    if not bool(ocean["enabled"]):
        _remove_ocean()
        return {"enabled": False}

    obj = bpy.data.objects.get(OCEAN_OBJECT)
    if obj is not None and obj.type != "MESH":
        raise RuntimeError(f"{OCEAN_OBJECT} exists but is not a Mesh object")
    if obj is None:
        mesh = bpy.data.meshes.new(OCEAN_OBJECT + "_Mesh")
        obj = bpy.data.objects.new(OCEAN_OBJECT, mesh)
        scene.collection.objects.link(obj)
    obj.location.z = float(ocean["sea_level_m"])
    obj["ordax_role"] = "environment_ocean"
    obj["ordax_environment_schema"] = ENVIRONMENT_SCHEMA

    modifier = obj.modifiers.get("OrdaX Ocean")
    if modifier is not None and modifier.type != "OCEAN":
        raise RuntimeError("OrdaX Ocean modifier name is occupied by a non-Ocean modifier")
    if modifier is None:
        modifier = obj.modifiers.new("OrdaX Ocean", "OCEAN")

    applied: dict[str, Any] = {"enabled": True, "object": obj.name, "modifier": modifier.name}
    values = {
        "geometry_mode": "GENERATE",
        "resolution": 10,
        "render_resolution": 14,
        "spatial_size": 750.0,
        "repeat_x": 8,
        "repeat_y": 8,
        "wave_scale": max(0.01, float(ocean["significant_wave_height_m"]) * 0.5),
        "choppiness": float(ocean["choppiness"]),
        "wind_velocity": float(environment["wind"]["speed_mps"]),
        "wave_direction": math.radians(float(ocean["swell_direction_deg"])),
        "wave_alignment": 0.45,
        "damping": 0.5,
        "smallest_wave": max(0.05, min(2.0, float(ocean["significant_wave_height_m"]) * 0.2)),
        "use_foam": float(ocean["foam_amount"]) > 0.001,
        "foam_coverage": float(ocean["foam_amount"]),
    }
    for key, value in values.items():
        _set_if(modifier, key, value, applied)

    material = _water_material(environment)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    applied["material"] = material.name
    applied["reference_extent_m"] = 6000.0
    return applied


def _audit(scene: bpy.types.Scene) -> dict[str, Any]:
    metadata_raw = scene.get("ordax_visual_environment_json")
    metadata: dict[str, Any] | None = None
    if isinstance(metadata_raw, str):
        try:
            parsed = json.loads(metadata_raw)
            metadata = parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            metadata = None

    world = scene.world
    sky_nodes = []
    volume_nodes = []
    if world is not None and world.use_nodes and world.node_tree is not None:
        for node in world.node_tree.nodes:
            if node.bl_idname == "ShaderNodeTexSky":
                sky_nodes.append(node.name)
            if node.bl_idname == "ShaderNodeVolumePrincipled":
                volume_nodes.append(node.name)

    sun = bpy.data.objects.get(SUN_OBJECT)
    ocean = bpy.data.objects.get(OCEAN_OBJECT)
    ocean_modifier = ocean.modifiers.get("OrdaX Ocean") if ocean is not None and ocean.type == "MESH" else None
    return {
        "schema": "ordax.blender-environment-audit/1",
        "environment_schema": scene.get("ordax_visual_environment_schema"),
        "environment_metadata_valid": metadata is not None and metadata.get("schema") == ENVIRONMENT_SCHEMA,
        "environment": metadata,
        "world": {
            "present": world is not None,
            "uses_nodes": bool(world is not None and world.use_nodes),
            "sky_nodes": sky_nodes,
            "volume_nodes": volume_nodes,
        },
        "sun": {
            "present": sun is not None,
            "type": sun.type if sun is not None else None,
            "light_type": sun.data.type if sun is not None and sun.type == "LIGHT" else None,
            "role": sun.get("ordax_role") if sun is not None else None,
        },
        "ocean": {
            "present": ocean is not None,
            "type": ocean.type if ocean is not None else None,
            "modifier_present": ocean_modifier is not None,
            "material": (
                ocean.data.materials[0].name
                if ocean is not None and ocean.type == "MESH" and ocean.data.materials
                else None
            ),
            "role": ocean.get("ordax_role") if ocean is not None else None,
        },
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    request_path = _args()
    request = _load(request_path)
    report_path = Path(str(request.get("report_path") or "")).resolve()
    try:
        operation = request.get("operation")
        if operation not in {"apply", "audit"}:
            raise RuntimeError("operation must be apply or audit")
        scene = bpy.context.scene
        if operation == "apply":
            environment = request.get("environment")
            if not isinstance(environment, dict) or environment.get("schema") != ENVIRONMENT_SCHEMA:
                raise RuntimeError(f"environment must use {ENVIRONMENT_SCHEMA}")
            output_path = Path(str(request.get("output_path") or "")).resolve()
            if output_path.suffix.lower() != ".blend":
                raise RuntimeError("output_path must be a .blend file")
            scene.unit_settings.system = "METRIC"
            scene.unit_settings.scale_length = 1.0
            scene["ordax_visual_environment_schema"] = ENVIRONMENT_SCHEMA
            scene["ordax_visual_environment_json"] = json.dumps(environment, sort_keys=True)
            color_management = _apply_color_management(scene, environment)
            world = _apply_world(scene, environment)
            sun = _apply_sun(scene, environment)
            ocean = _apply_ocean(scene, environment)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False)
            audit = _audit(scene)
            report = {
                "ok": True,
                "schema": "ordax.blender-environment-build/1",
                "operation": "apply",
                "output_blend": str(output_path),
                "bytes": output_path.stat().st_size,
                "blender_version": ".".join(str(value) for value in bpy.app.version),
                "color_management": color_management,
                "world_mapping": world,
                "sun_mapping": sun,
                "ocean_mapping": ocean,
                "audit": audit,
            }
        else:
            audit = _audit(scene)
            report = {
                "ok": bool(
                    audit["environment_metadata_valid"]
                    and audit["world"]["sky_nodes"]
                    and audit["sun"]["present"]
                    and audit["sun"]["light_type"] == "SUN"
                    and (
                        not bool((audit.get("environment") or {}).get("ocean", {}).get("enabled"))
                        or audit["ocean"]["modifier_present"]
                    )
                ),
                "schema": "ordax.blender-environment-audit/1",
                "operation": "audit",
                "blender_version": ".".join(str(value) for value in bpy.app.version),
                "audit": audit,
            }
        _write_report(report_path, report)
        print(json.dumps({"ok": report["ok"], "report": str(report_path)}))
        return 0 if report["ok"] else 3
    except Exception as error:
        failure = {"ok": False, "error_type": type(error).__name__, "error": str(error)}
        try:
            _write_report(report_path, failure)
        except Exception:
            pass
        print(json.dumps(failure), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
