"""Inspect the actual published upper-airway assembly before character fitting."""
from pathlib import Path
import sys
import json
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/anatomy'))
from mesh_sources import load_obj, load_tetra_boundary, canonical_vkh, file_sha

source = ROOT / 'assets/source/vkh-upper-airway/src/artisynth/models/vkhUpperAirway/geometry'
out = ROOT / 'artifacts/milestone-evidence/M1/vkh-upper-airway'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
parts, objects, closed = {}, {}, set()

def create(name, points, faces, color):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + ' study tissue')
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = .6
    mesh.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    objects[name] = ob
    return ob

for name, color in [
    ('Tongue', (.58, .23, .22)), ('Palatine_aponeurosis', (.7, .37, .37)),
    ('Pharynx', (.58, .35, .3)), ('Suprahyoid_muscles_L', (.64, .31, .27)),
    ('Suprahyoid_muscles_R', (.64, .31, .27)),
]:
    nodes, elements = source / f'fem/{name}.node', source / f'fem/{name}.elem'
    data = load_tetra_boundary(nodes, elements)
    p = canonical_vkh(data['points'])
    create(name, p, data['faces'].tolist(), color)
    parts[name] = {
        'positions': p.ravel().tolist(), 'indices': data['faces'].ravel().tolist(),
        'sourceNodeIds': data['sourceNodeIds'].tolist(),
        'sourceCells': data['cells'], 'skippedDegenerateCells': data['skippedDegenerateCells'],
        'sources': {str(nodes.relative_to(ROOT)): file_sha(nodes), str(elements.relative_to(ROOT)): file_sha(elements)},
        'sourceKind': 'published research FEM boundary',
    }
    closed.add(name)
for name in ['Maxilla', 'Mandible', 'Hyoid', 'Thyroid', 'Cricoid']:
    path = source / f'rigidBodies/{name}.obj'
    data = load_obj(path)
    p = canonical_vkh(data['points'])
    create(name, p, data['faces'], (.79, .73, .57))
    parts[name] = {'positions': p.ravel().tolist(), 'faces': data['faces'], 'sources': {str(path.relative_to(ROOT)): file_sha(path)}, 'sourceKind': 'published research rigid surface; not separately segmented dental crowns'}

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene['studyStatus'] = 'source-assembly inspection; character registration and expert review pending'
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'source-assembly.blend'))
(out / 'source-meshes.json').write_text(json.dumps({'parts': parts, 'frame': {'anterior': '+X', 'superior': '+Y', 'right': '+Z', 'units': 'm'}, 'sourceMapping': '[(nativeY-110), (nativeZ+180), (nativeX+130)] * .001', 'sourceUnits': 'nominal native millimeter model convention, not human measurement', 'status': 'unregistered source assembly, not a validated character model'}, separators=(',', ':')))

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world = bpy.data.worlds.new('Neutral study background')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.18, .19, .20, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
for pos, power in [((.25, .25, -.3), 8), ((.1, .05, .3), 5), ((-.15, .1, -.1), 3)]:
    light = bpy.data.lights.new('Source softbox', 'AREA')
    light.energy = power
    light.size = .3
    ob = bpy.data.objects.new('Source softbox', light)
    bpy.context.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (Vector((.02, -.01, 0)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
camera = bpy.data.objects.new('Study camera', bpy.data.cameras.new('Study camera'))
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .22
center = Vector((.025, -.015, 0))
for view, direction in [('three-quarter', (1, .05, -1)), ('sagittal', (0, 0, -1))]:
    copies = []
    if view == 'sagittal':
        for name, original in objects.items():
            original.hide_render = True
            ob = original.copy()
            ob.data = original.data.copy()
            bpy.context.collection.objects.link(ob)
            ob.hide_render = False
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            result = bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-8, plane_co=(0, 0, 0), plane_no=(0, 0, -1), clear_outer=True, clear_inner=False)
            if name in closed:
                edges = [e for e in result['geom_cut'] if isinstance(e, bmesh.types.BMEdge) and e.is_boundary]
                if edges:
                    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(ob.data)
            bm.free()
            copies.append(ob)
    camera.location = center + Vector(direction).normalized() * .7
    forward = (center - camera.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward)
    camera.rotation_euler = Matrix(((right.x, up.x, -forward.x), (right.y, up.y, -forward.y), (right.z, up.z, -forward.z))).to_euler()
    scene.render.filepath = str(out / (view + '.png'))
    bpy.ops.render.render(write_still=True)
    for ob in copies:
        bpy.data.objects.remove(ob, do_unlink=True)
print('SOURCE_ASSEMBLY_STUDY', out)
