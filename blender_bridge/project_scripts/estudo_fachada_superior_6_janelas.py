"""MIRROR EXECUTAVEL. Fonte: projeto-salvador-elevador-lacerda, branch chatgpt/blender-collab.
Nao editar aqui como fonte canonica.
"""
import bpy
import math
from mathutils import Vector, Matrix

COLLECTION_NAME = "07 CHATGPT | estudo fachada superior 6 janelas"
scene = bpy.context.scene
required = [
    "OFICIAL | Entrada superior | fachada esquerda",
    "OFICIAL | Entrada superior | lintel",
    "OFICIAL | Entrada superior | fachada direita",
    "OFICIAL | Entrada superior | cobertura",
]
for name in required:
    assert bpy.data.objects.get(name), f"Objeto oficial ausente: {name}"
old = bpy.data.collections.get(COLLECTION_NAME)
if old:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for parent in list(bpy.data.collections):
        if old.name in parent.children:
            parent.children.unlink(old)
    bpy.data.collections.remove(old)
study = bpy.data.collections.new(COLLECTION_NAME)
scene.collection.children.link(study)
study["status"] = "estudo visual incremental; nao levantamento"
study["referencia_fachada"] = "3 colunas x 2 niveis de janelas grandes na entrada superior"
study["nao_destrutivo"] = True
base = bpy.data.objects["OFICIAL | Entrada superior | lintel"]
theta = base.rotation_euler.z
ex = Vector((math.cos(theta), math.sin(theta), 0.0))
ey = Vector((-math.sin(theta), math.cos(theta), 0.0))
ez = Vector((0.0, 0.0, 1.0))
origin = Vector((base.location.x, base.location.y, 0.0))
U_FACE = 0.405

def material(name, rgba, roughness=0.55, metallic=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.roughness = roughness
    m.metallic = metallic
    return m

ivory = material("CHATGPT | fachada marfim", (0.78, 0.72, 0.61, 1.0), 0.72)
glass = material("CHATGPT | vidro azul cinza", (0.10, 0.18, 0.22, 1.0), 0.28)
shadow = material("CHATGPT | rebaixo escuro", (0.055, 0.060, 0.065, 1.0), 0.45)
metal = material("CHATGPT | metal escuro", (0.18, 0.18, 0.17, 1.0), 0.40, 0.20)

def world(u, v, z):
    return origin + ex * u + ey * v + Vector((0.0, 0.0, z))

def box(name, u, v, z, du, dv, dz, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=world(u, v, z))
    obj = bpy.context.object
    obj.name = "CHATGPT | " + name
    obj.rotation_euler.z = theta
    obj.dimensions = (du, dv, dz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    study.objects.link(obj)
    obj.data.materials.append(mat)
    obj["status_dimensao"] = "aproximacao visual; validar por fotografia/levantamento"
    if bevel:
        mod = obj.modifiers.new("Bevel leve", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj

def facade_text(name, body, u, v, z, size, mat):
    bpy.ops.object.text_add(location=world(u, v, z))
    obj = bpy.context.object
    obj.name = "CHATGPT | " + name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.018
    obj.data.bevel_depth = 0.006
    obj.rotation_euler = Matrix((ey, ez, ex)).transposed().to_euler()
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    study.objects.link(obj)
    obj.data.materials.append(mat)
    obj["status_dimensao"] = "aproximacao visual"
    return obj

bay_centers = (-3.2, 0.0, 3.2)
window_width = 2.18
window_height = 2.20
row_centers = (45.05, 49.35)
for row, z in enumerate(row_centers, start=1):
    for col, v in enumerate(bay_centers, start=1):
        box(f"janela rebaixo {row}-{col}", U_FACE - 0.020, v, z, 0.10, window_width + 0.16, window_height + 0.16, shadow, 0.02)
        box(f"janela vidro {row}-{col}", U_FACE + 0.035, v, z, 0.055, window_width, window_height, glass, 0.015)
        for dv in (-window_width / 6.0, window_width / 6.0):
            box(f"caixilho vertical {row}-{col}-{dv:+.2f}", U_FACE + 0.072, v + dv, z, 0.025, 0.055, window_height - 0.10, ivory)
        for dz in (-window_height / 6.0, window_height / 6.0):
            box(f"caixilho horizontal {row}-{col}-{dz:+.2f}", U_FACE + 0.072, v, z + dz, 0.025, window_width - 0.10, 0.050, ivory)
for col, v in enumerate(bay_centers, start=1):
    box(f"painel decorativo fundo {col}", U_FACE + 0.020, v, 47.18, 0.065, 2.02, 1.18, ivory, 0.035)
    box(f"painel decorativo rebaixo {col}", U_FACE + 0.064, v, 47.18, 0.030, 1.58, 0.78, shadow, 0.02)
    box(f"painel decorativo miolo {col}", U_FACE + 0.086, v, 47.18, 0.018, 1.38, 0.60, ivory, 0.015)
for col, v in enumerate(bay_centers, start=1):
    box(f"painel inferior {col}", U_FACE + 0.060, v, 43.95, 0.030, 1.62, 0.28, ivory, 0.02)
for idx, v in enumerate((-4.72, -1.60, 1.60, 4.72), start=1):
    box(f"pilastra frontal {idx}", U_FACE + 0.085, v, 47.85, 0.05, 0.22, 7.55, ivory, 0.01)
box("coroamento base", U_FACE + 0.020, 0.0, 52.18, 0.07, 9.55, 0.34, ivory, 0.02)
box("coroamento central", U_FACE + 0.040, 0.0, 52.48, 0.06, 4.30, 0.48, ivory, 0.025)
box("placa LACERDA", U_FACE + 0.075, 0.0, 51.35, 0.05, 4.35, 0.62, ivory, 0.02)
facade_text("texto LACERDA", "LACERDA", U_FACE + 0.115, 0.0, 51.35, 0.52, metal)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.36, depth=0.07, location=world(U_FACE + 0.12, 0.0, 52.46))
emblem = bpy.context.object
emblem.name = "CHATGPT | emblema circular superior"
emblem.rotation_mode = "QUATERNION"
emblem.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(ex)
for collection in list(emblem.users_collection):
    collection.objects.unlink(emblem)
study.objects.link(emblem)
emblem.data.materials.append(metal)
emblem["status_dimensao"] = "aproximacao visual"
bpy.ops.object.select_all(action="DESELECT")
for obj in study.objects:
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
if study.objects:
    bpy.context.view_layer.objects.active = study.objects[0]
print("ESTUDO_FACHADA_SUPERIOR_OK", "janelas=6", "objetos=", len(study.objects), "theta=", round(theta, 6), "largura_oficial=9.6m")
