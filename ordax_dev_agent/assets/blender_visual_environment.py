"""Apply an OrdaX visual-environment manifest to a Blender scene headlessly."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def _args() -> argparse.Namespace:
    raw = sys.argv
    raw = raw[raw.index("--") + 1 :] if "--" in raw else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(raw)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("environment manifest must contain an object")
    if value.get("schema") != "ordax.visual-environment/1":
        raise RuntimeError("unsupported visual environment schema")
    return value


def _remove_object(name: str) -> None:
    obj = bpy.data.objects.get(name)
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)


def _sun_direction(environment: dict) -> Vector:
    elevation = math.radians(float(environment["sun"]["elevation_deg"]))
    azimuth = math.radians(float(environment["sun"]["azimuth_deg"]))
    return Vector((math.sin(azimuth) * math.cos(elevation), math.cos(azimuth) * math.cos(elevation), math.sin(elevation))).normalized()


def _apply_world(environment: dict) -> dict:
    world = bpy.data.worlds.get("OrdaX_Environment") or bpy.data.worlds.new("OrdaX_Environment")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.turbidity = float(environment["sky"]["turbidity"])
    sky.sun_elevation = math.radians(float(environment["sun"]["elevation_deg"]))
    sky.sun_rotation = math.radians(float(environment["sun"]["azimuth_deg"]))
    if hasattr(sky, "air_density"):
        sky.air_density = max(0.0, min(10.0, float(environment["sky"]["rayleigh"]) / 2.4))
    if hasattr(sky, "dust_density"):
        sky.dust_density = max(0.0, min(10.0, float(environment["sky"]["mie_coefficient"]) / 0.006))
    if hasattr(sky, "ozone_density"):
        sky.ozone_density = 1.0
    background.inputs["Strength"].default_value = 0.7 + 0.6 * (1.0 - float(environment["sky"]["cloud_coverage"]))
    links.new(sky.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])
    return {"world": world.name, "sky_type": sky.sky_type}


def _apply_sun(environment: dict) -> dict:
    _remove_object("OrdaX_Sun")
    data = bpy.data.lights.new("OrdaX_Sun_Data", type="SUN")
    data.energy = max(0.0, min(12.0, float(environment["sun"]["intensity_lux"]) / 25000.0))
    data.angle = math.radians(0.526)
    obj = bpy.data.objects.new("OrdaX_Sun", data)
    bpy.context.scene.collection.objects.link(obj)
    direction = _sun_direction(environment)
    obj.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    obj["ordax_role"] = "sun"
    obj["ordax_intensity_lux"] = float(environment["sun"]["intensity_lux"])
    obj["ordax_color_temperature_k"] = float(environment["sun"]["color_temperature_k"])
    return {"object": obj.name, "energy": data.energy}


def _principled_input(bsdf, *names: str):
    for name in names:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            return socket
    return None


def _water_material(environment: dict):
    material = bpy.data.materials.get("OrdaX_Ocean_Material") or bpy.data.materials.new("OrdaX_Ocean_Material")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    deep = environment["ocean"]["deep_color"]
    base = _principled_input(bsdf, "Base Color")
    if base is not None:
        base.default_value = (*[float(value) for value in deep], 1.0)
    roughness = _principled_input(bsdf, "Roughness")
    if roughness is not None:
        roughness.default_value = float(environment["ocean"]["roughness"])
    metallic = _principled_input(bsdf, "Metallic")
    if metallic is not None:
        metallic.default_value = 0.0
    transmission = _principled_input(bsdf, "Transmission Weight", "Transmission")
    if transmission is not None:
        transmission.default_value = 0.88
    ior = _principled_input(bsdf, "IOR")
    if ior is not None:
        ior.default_value = 1.333
    coat = _principled_input(bsdf, "Coat Weight", "Clearcoat")
    if coat is not None:
        coat.default_value = 0.22
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def _apply_ocean(environment: dict) -> dict:
    _remove_object("OrdaX_Ocean")
    if not bool(environment["ocean"]["enabled"]):
        return {"enabled": False}
    mesh = bpy.data.meshes.new("OrdaX_Ocean_Mesh")
    obj = bpy.data.objects.new("OrdaX_Ocean", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location.z = float(environment["ocean"]["sea_level_m"])
    obj.data.materials.append(_water_material(environment))
    modifier = obj.modifiers.new("OrdaX_Ocean_Surface", "OCEAN")
    modifier.geometry_mode = "GENERATE"
    modifier.resolution = 12
    modifier.viewport_resolution = 8
    modifier.spatial_size = 180.0
    modifier.wave_scale = max(0.05, float(environment["ocean"]["significant_wave_height_m"]) * 0.75)
    modifier.choppiness = float(environment["ocean"]["choppiness"])
    modifier.wind_velocity = max(0.1, float(environment["wind"]["speed_mps"]))
    modifier.wind_direction = math.radians(float(environment["wind"]["direction_deg"]))
    modifier.wave_scale_min = max(0.01, modifier.wave_scale * 0.08)
    modifier.time = 1.0
    if hasattr(modifier, "use_foam"):
        modifier.use_foam = float(environment["ocean"]["foam_amount"]) > 0.0
    if hasattr(modifier, "foam_coverage"):
        modifier.foam_coverage = float(environment["ocean"]["foam_amount"])
    obj["ordax_role"] = "ocean"
    obj["ordax_wave_height_m"] = float(environment["ocean"]["significant_wave_height_m"])
    obj["ordax_swell_period_s"] = float(environment["ocean"]["swell_period_s"])
    obj["ordax_swell_direction_deg"] = float(environment["ocean"]["swell_direction_deg"])
    return {"enabled": True, "object": obj.name, "modifier": modifier.name, "resolution": modifier.resolution, "viewport_resolution": modifier.viewport_resolution}


def _apply_scene_settings(environment: dict) -> dict:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene["ordax_environment_schema"] = environment["schema"]
    scene["ordax_environment_name"] = environment["name"]
    scene["ordax_environment_json"] = json.dumps(environment, sort_keys=True)
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        pass
    return {"units": "METRIC", "scale_length": 1.0}


def main() -> int:
    args = _args()
    environment_path = Path(args.environment).resolve()
    output = Path(args.output).resolve()
    report_path = Path(args.report).resolve()
    try:
        environment = _load(environment_path)
        scene_info = _apply_scene_settings(environment)
        world_info = _apply_world(environment)
        sun_info = _apply_sun(environment)
        ocean_info = _apply_ocean(environment)
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
        report = {"ok": True, "schema": "ordax.blender-visual-environment/1", "environment_schema": environment["schema"], "environment_name": environment["name"], "output_blend": str(output), "bytes": output.stat().st_size, "blender_version": ".".join(str(value) for value in bpy.app.version), "scene": scene_info, "world": world_info, "sun": sun_info, "ocean": ocean_info}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "report": str(report_path)}))
        return 0
    except Exception as error:
        payload = {"ok": False, "error_type": type(error).__name__, "error": str(error)}
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        print(json.dumps(payload), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
