"""MIRROR EXECUTAVEL. Fonte: projeto-salvador-elevador-lacerda/chatgpt/blender-collab."""
import bpy
import math
from mathutils import Vector, Matrix
COLLECTION_NAME="08 CHATGPT | estudo acesso superior marquise terreo"
for name in ["OFICIAL | Entrada superior | lintel","OFICIAL | Terminal alto | piso de entrada","OFICIAL | Terminal alto | galeria cobertura"]:
    assert bpy.data.objects.get(name),f"Objeto oficial ausente: {name}"
scene=bpy.context.scene
old=bpy.data.collections.get(COLLECTION_NAME)
if old:
    for obj in list(old.objects): bpy.data.objects.remove(obj,do_unlink=True)
    for parent in list(bpy.data.collections):
        if old.name in parent.children: parent.children.unlink(old)
    bpy.data.collections.remove(old)
study=bpy.data.collections.new(COLLECTION_NAME);scene.collection.children.link(study)
study["status"]="estudo visual incremental; nao levantamento";study["nao_destrutivo"]=True
base=bpy.data.objects["OFICIAL | Entrada superior | lintel"];theta=base.rotation_euler.z
ex=Vector((math.cos(theta),math.sin(theta),0));ey=Vector((-math.sin(theta),math.cos(theta),0));ez=Vector((0,0,1));origin=Vector((base.location.x,base.location.y,0))
def material(name,rgba,roughness=.55,metallic=0):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=rgba;m.roughness=roughness;m.metallic=metallic;return m
ivory=material("CHATGPT | acesso marfim",(.77,.70,.59,1),.74);stone=material("CHATGPT | acesso pedra escura",(.22,.20,.18,1),.82);glass=material("CHATGPT | acesso vidro",(.08,.13,.15,1),.30);metal=material("CHATGPT | acesso metal",(.16,.16,.15,1),.40,.20)
def world(u,v,z): return origin+ex*u+ey*v+Vector((0,0,z))
def box(name,u,v,z,du,dv,dz,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=world(u,v,z));o=bpy.context.object;o.name="CHATGPT | "+name;o.rotation_euler.z=theta;o.dimensions=(du,dv,dz);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection): c.objects.unlink(o)
    study.objects.link(o);o.data.materials.append(mat);o["status_dimensao"]="aproximacao visual; nao levantamento"
    if bevel:
        mod=o.modifiers.new("Bevel leve","BEVEL");mod.width=bevel;mod.segments=3
    return o
def facade_text(name,body,u,v,z,size):
    bpy.ops.object.text_add(location=world(u,v,z));o=bpy.context.object;o.name="CHATGPT | "+name;o.data.body=body;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=size;o.data.extrude=.010;o.data.bevel_depth=.004;o.rotation_euler=Matrix((ey,ez,ex)).transposed().to_euler()
    for c in list(o.users_collection): c.objects.unlink(o)
    study.objects.link(o);o.data.materials.append(metal);return o
CANOPY_Z=43.48
box("volume terreo recuado",-1.15,0,41.63,2.2,20.2,3.25,stone,.06)
box("marquise superior",.10,0,CANOPY_Z,3.10,20.8,.28,ivory,.16)
box("faixa frontal marquise",1.48,0,43.34,.20,20.4,.50,stone,.05)
for idx,v in enumerate((-4.72,-1.60,1.60,4.72),start=1):
    box(f"pilar terreo {idx}",.50,v,41.65,.72,.78,3.30,ivory,.035);box(f"capitel pilar {idx}",.50,v,43.05,.82,.96,.36,ivory,.025)
for name,v,width in [("lateral esquerda",-8.10,2.05),("entrada",-3.15,2.15),("circulacao central",0,2.10),("saida",3.15,2.15),("lateral direita",8.10,2.05)]: box(f"vao {name}",1.24,v,41.58,.08,width,2.72,glass,.018)
for idx,v in enumerate((-9.55,-6.62,6.62,9.55),start=1): box(f"montante lateral terreo {idx}",1.30,v,41.60,.10,.18,2.78,ivory,.015)
facade_text("sinal ENTRADA","ENTRADA",1.40,-3.15,42.85,.28);facade_text("sinal SAIDA","SAIDA",1.40,3.15,42.85,.28)
box("soleira frontal",1.10,0,40.05,1.30,20.0,.10,stone,.02)
bpy.ops.object.select_all(action="DESELECT")
for o in study.objects:o.hide_set(False);o.hide_viewport=False;o.select_set(True)
if study.objects:bpy.context.view_layer.objects.active=study.objects[0]
print("ESTUDO_ACESSO_SUPERIOR_OK","pilares=4","largura_marquise=20.8m","objetos=",len(study.objects),"theta=",round(theta,6))
