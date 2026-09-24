"""Build a Blender environment scene from preprocessed Aleph capture assets."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


def _args() -> argparse.Namespace:
    raw = sys.argv
    raw = raw[raw.index("--") + 1 :] if "--" in raw else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--preprocess", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--no-satellite", action="store_true")
    return parser.parse_args(raw)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path.name} must contain a JSON object")
    return value


def _collection(name: str) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _load_local_obj(path: Path, object_name: str, collection: bpy.types.Collection) -> list[bpy.types.Object]:
    """Load our tiny OBJ subset without axis conversion from Blender's OBJ importer."""
    vertices: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    faces: list[list[int]] = []
    face_uvs: list[list[int | None]] = []
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "v" and len(parts) >= 4:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == "vt" and len(parts) >= 3:
                uvs.append((float(parts[1]), float(parts[2])))
            elif parts[0] == "f" and len(parts) >= 4:
                indices: list[int] = []
                uv_indices: list[int | None] = []
                for token in parts[1:]:
                    values = token.split("/")
                    vertex_index = int(values[0])
                    if vertex_index <= 0:
                        raise RuntimeError("Aleph staging OBJ must use positive vertex indices")
                    indices.append(vertex_index - 1)
                    uv_index: int | None = None
                    if len(values) >= 2 and values[1]:
                        parsed = int(values[1])
                        if parsed <= 0:
                            raise RuntimeError("Aleph staging OBJ must use positive UV indices")
                        uv_index = parsed - 1
                    uv_indices.append(uv_index)
                faces.append(indices)
                face_uvs.append(uv_indices)
    if not vertices or not faces:
        raise RuntimeError(f"Aleph staging mesh {path.name} has no usable geometry")
    if len(vertices) > 5_000_000 or len(faces) > 5_000_000:
        raise RuntimeError(f"Aleph staging mesh {path.name} exceeds the safety geometry limit")

    mesh = bpy.data.meshes.new(f"{object_name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if uvs and any(any(index is not None for index in values) for values in face_uvs):
        layer = mesh.uv_layers.new(name="UVMap")
        for polygon, uv_indices in zip(mesh.polygons, face_uvs):
            for loop_index, uv_index in zip(polygon.loop_indices, uv_indices):
                if uv_index is not None and 0 <= uv_index < len(uvs):
                    layer.data[loop_index].uv = uvs[uv_index]

    obj = bpy.data.objects.new(object_name, mesh)
    collection.objects.link(obj)
    return [obj]


def _satellite_material(image_path: Path) -> bpy.types.Material:
    material = bpy.data.materials.new("Aleph_Satellite")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    texture.interpolation = "Linear"
    image = bpy.data.images.load(str(image_path), check_existing=True)
    try:
        image.pack()
    except RuntimeError:
        pass
    texture.image = image
    links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = 0.82
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def _assign_material(objects: list[bpy.types.Object], material: bpy.types.Material) -> None:
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)


def _create_flat_reference(size_m: list[float], image_path: Path, collection: bpy.types.Collection) -> bpy.types.Object:
    width, height = float(size_m[0]), float(size_m[1])
    mesh = bpy.data.meshes.new("Aleph_SatellitePlane_Mesh")
    verts = [
        (-width / 2, -height / 2, 0.0),
        (width / 2, -height / 2, 0.0),
        (width / 2, height / 2, 0.0),
        (-width / 2, height / 2, 0.0),
    ]
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    values = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for loop, uv in zip(mesh.loops, values):
        uv_layer.data[loop.index].uv = uv
    obj = bpy.data.objects.new("Aleph_SatellitePlane", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(_satellite_material(image_path))
    return obj


def _road_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Aleph_Road")
    material.diffuse_color = (0.12, 0.12, 0.12, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.12, 0.12, 0.12, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.9
    return material


def _building_material() -> bpy.types.Material:
    material = bpy.data.materials.new("Aleph_Building")
    material.diffuse_color = (0.55, 0.53, 0.5, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.55, 0.53, 0.5, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.88
    return material


def _create_roads(path: Path, collection: bpy.types.Collection) -> tuple[list[bpy.types.Object], int]:
    payload = _load_json(path)
    roads = payload.get("roads")
    if not isinstance(roads, list):
        raise RuntimeError("roads.json has no roads list")
    groups: dict[float, list[dict[str, Any]]] = {}
    for road in roads:
        if not isinstance(road, dict):
            continue
        try:
            width = float(road.get("width_m", 3.0))
        except (TypeError, ValueError):
            width = 3.0
        width = round(max(0.5, min(30.0, width)) * 2) / 2
        groups.setdefault(width, []).append(road)
    material = _road_material()
    objects: list[bpy.types.Object] = []
    spline_count = 0
    for width, items in sorted(groups.items()):
        curve = bpy.data.curves.new(f"Aleph_Roads_{width:g}m_Curve", "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 1
        curve.bevel_depth = width / 2.0
        curve.bevel_resolution = 0
        curve.resolution_v = 0
        for road in items:
            raw_points = road.get("points")
            if not isinstance(raw_points, list) or len(raw_points) < 2:
                continue
            points = []
            for point in raw_points:
                if isinstance(point, list) and len(point) == 3:
                    try:
                        xyz = tuple(float(value) for value in point)
                    except (TypeError, ValueError):
                        continue
                    if all(math.isfinite(value) for value in xyz):
                        points.append(xyz)
            if len(points) < 2:
                continue
            spline = curve.splines.new("POLY")
            spline.points.add(len(points) - 1)
            for item, point in zip(spline.points, points):
                item.co = (*point, 1.0)
            spline_count += 1
        if not curve.splines:
            bpy.data.curves.remove(curve)
            continue
        obj = bpy.data.objects.new(f"Aleph_Roads_{width:g}m", curve)
        collection.objects.link(obj)
        obj.data.materials.append(material)
        objects.append(obj)
    return objects, spline_count


def _bounds(objects: list[bpy.types.Object]) -> dict[str, list[float]] | None:
    points: list[Vector] = []
    for obj in objects:
        if obj.type == "MESH" and obj.bound_box:
            points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        return None
    mins = [min(getattr(point, axis) for point in points) for axis in ("x", "y", "z")]
    maxs = [max(getattr(point, axis) for point in points) for axis in ("x", "y", "z")]
    return {"min": [round(v, 5) for v in mins], "max": [round(v, 5) for v in maxs]}


def main() -> int:
    args = _args()
    preprocess_path = Path(args.preprocess).resolve()
    output = Path(args.output).resolve()
    report_path = Path(args.report).resolve()
    try:
        data = _load_json(preprocess_path)
        assets = data.get("assets")
        if not isinstance(assets, dict):
            raise RuntimeError("preprocess report has no assets")

        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        scene = bpy.context.scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1.0

        terrain_collection = _collection("ALEPH_Terrain")
        building_collection = _collection("ALEPH_Buildings")
        road_collection = _collection("ALEPH_Roads")
        reference_collection = _collection("ALEPH_References")
        all_objects: list[bpy.types.Object] = []

        terrain_objects: list[bpy.types.Object] = []
        terrain_info = assets.get("terrain")
        if isinstance(terrain_info, dict) and terrain_info.get("path"):
            terrain_objects = _load_local_obj(Path(terrain_info["path"]), "Aleph_Terrain", terrain_collection)
            all_objects.extend(terrain_objects)

        building_objects: list[bpy.types.Object] = []
        building_info = assets.get("buildings")
        if isinstance(building_info, dict) and building_info.get("path"):
            building_objects = _load_local_obj(Path(building_info["path"]), "Aleph_Buildings", building_collection)
            material = _building_material()
            _assign_material(building_objects, material)
            all_objects.extend(building_objects)

        roads_objects: list[bpy.types.Object] = []
        road_splines = 0
        road_info = assets.get("roads")
        if isinstance(road_info, dict) and road_info.get("path"):
            roads_objects, road_splines = _create_roads(Path(road_info["path"]), road_collection)
            all_objects.extend(roads_objects)

        satellite_info = assets.get("satellite")
        satellite_used = False
        if not args.no_satellite and isinstance(satellite_info, dict) and satellite_info.get("path"):
            image_path = Path(satellite_info["path"])
            if image_path.is_file():
                if terrain_objects:
                    material = _satellite_material(image_path)
                    _assign_material(terrain_objects, material)
                else:
                    flat = _create_flat_reference(data["size_m"], image_path, reference_collection)
                    all_objects.append(flat)
                satellite_used = True

        metadata = bpy.data.objects.new("ALEPH_Metadata", None)
        reference_collection.objects.link(metadata)
        metadata.empty_display_type = "PLAIN_AXES"
        metadata["source_capture"] = str(data.get("capture", ""))
        metadata["aleph_format_version"] = int(data.get("aleph_format_version", 0))
        metadata["bounds_json"] = json.dumps(data.get("bounds"))
        metadata["origin_epsg3857_json"] = json.dumps(data.get("origin_epsg3857"))
        metadata["size_m_json"] = json.dumps(data.get("size_m"))
        if isinstance(terrain_info, dict):
            metadata["terrain_base_elevation_m"] = float(terrain_info.get("base_elevation_m", 0.0))

        scene["ordax_source"] = "Belluxx/Aleph"
        scene["ordax_aleph_capture"] = str(data.get("capture", ""))
        scene["ordax_aleph_bounds"] = json.dumps(data.get("bounds"))

        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)

        report = {
            "ok": True,
            "schema": "ordax.aleph-blender-scene/1",
            "output_blend": str(output),
            "bytes": output.stat().st_size,
            "blender_version": ".".join(str(value) for value in bpy.app.version),
            "objects": len(all_objects) + 1,
            "terrain_objects": len(terrain_objects),
            "building_objects": len(building_objects),
            "road_objects": len(roads_objects),
            "road_splines": road_splines,
            "satellite_material": satellite_used,
            "bounds": _bounds(all_objects),
            "source": data,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "report": str(report_path)}))
        return 0
    except Exception as error:
        payload = {"ok": False, "error_type": type(error).__name__, "error": str(error)}
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass
        print(json.dumps(payload), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
