"""Small CPU-only study of real head sources; no source/master modification.

MakeHuman eyes use their original MHCLO reference bindings. Helpers are never
displayed as anatomy. A cutaway is diagnostic, not a completed internal head.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--candidate', choices=['makehuman', 'badin'], required=True)
parser.add_argument('--pose', choices=['rest', 'mouth-open'], default='rest')
parser.add_argument('--views', default='front,side,three-quarter')
parser.add_argument('--resolution', type=int, default=512)
parser.add_argument('--samples', type=int, default=8)
opts = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = ROOT / 'artifacts/milestone-evidence/M1' / opts.candidate / opts.pose
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
provenance = {}

def read_bytes(path):
    data = path.read_bytes()
    provenance[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return data

def obj_data(path, group_filter=None):
    vertices, uvs, faces, face_uvs = [], [], [], []
    group = ''
    for line in read_bytes(path).decode().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'v':
            vertices.append(list(map(float, t[1:4])))
        elif t[0] == 'vt':
            uvs.append(list(map(float, t[1:3])))
        elif t[0] == 'g':
            group = ' '.join(t[1:])
        elif t[0] == 'f' and (group_filter is None or group == group_filter):
            fields = [v.split('/') for v in t[1:]]
            faces.append([int(v[0]) - 1 for v in fields])
            face_uvs.append([int(v[1]) - 1 if len(v) > 1 and v[1] else -1 for v in fields])
    return np.asarray(vertices), faces, uvs, face_uvs

def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = .58
    return mat

skin = material('Neutral study skin; artistic color, not acquired texture', (.51, .32, .23))

def create(name, points, faces, uvs=None, face_uvs=None, mat=skin):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    if uvs and face_uvs:
        layer = mesh.uv_layers.new(name='Source UV')
        for poly, indices in zip(mesh.polygons, face_uvs):
            for loop, index in zip(poly.loop_indices, indices):
                if index >= 0:
                    layer.data[loop].uv = uvs[index]
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    mesh.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return ob

def canonical_makehuman(v):
    # Upstream getHeightCm = 10 * native Y height. Rotate +Z anterior to +X.
    return np.column_stack([v[:, 2] * .1, (v[:, 1] - 7) * .1, -v[:, 0] * .1])

source_notes = []
if opts.candidate == 'makehuman':
    base = ROOT / 'assets/source/makehuman/makehuman/data'
    points, faces, uvs, face_uvs = obj_data(base / '3dobjs/base.obj', 'body')
    if opts.pose == 'mouth-open':
        # Neutral equal mix is an authored diagnostic control, not an Arabic sound.
        for family in ['african', 'asian', 'caucasian']:
            path = base / f'targets/expression/units/{family}/mouth-open.target'
            for line in read_bytes(path).decode().splitlines():
                t = line.split()
                if t and not t[0].startswith('#'):
                    points[int(t[0])] += np.array(list(map(float, t[1:4]))) / 3
    head = create('Source continuous body skin — head crop', canonical_makehuman(points), faces, uvs, face_uvs)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    # A documented context crop below the neck. Never capped as invented tissue.
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-8, plane_co=(0, -.11, 0), plane_no=(0, -1, 0), clear_outer=True, clear_inner=False)
    bm.to_mesh(head.data)
    bm.free()
    mod = head.modifiers.new('Source topology smooth preview', 'SUBSURF')
    mod.levels = 1
    mod.render_levels = 1
    eye_path = base / 'eyes/high-poly/high-poly.obj'
    eye_points, eye_faces, eye_uvs, eye_face_uvs = obj_data(eye_path)
    binding = base / 'eyes/high-poly/high-poly.mhclo'
    scales, refs = {}, []
    reading = False
    for line in read_bytes(binding).decode().splitlines():
        t = line.split()
        if not t or t[0].startswith('#'):
            continue
        if t[0] in ['x_scale', 'y_scale', 'z_scale']:
            axis = 'xyz'.index(t[0][0])
            a, b, denominator = int(t[1]), int(t[2]), float(t[3])
            scales[axis] = abs(points[a, axis] - points[b, axis]) / denominator
        elif t[0] == 'verts':
            reading = True
        elif reading and t[0].lstrip('-').isdigit():
            if len(t) != 9:
                raise ValueError('Unsupported MHCLO binding row')
            refs.append(t)
        elif reading:
            reading = False
    assert len(refs) == len(eye_points), (len(refs), len(eye_points))
    fitted = []
    for row in refs:
        indices = list(map(int, row[:3]))
        weights = np.array(list(map(float, row[3:6])))
        offsets = np.array(list(map(float, row[6:9])))
        assert abs(weights.sum() - 1) < 1e-3
        fitted.append(weights @ points[indices] + offsets * np.array([scales[i] for i in range(3)]))
    eyes = material('Original CC0 eye texture', (1, 1, 1))
    texture = base / 'eyes/materials/brown_eye.png'
    read_bytes(texture)
    tex = eyes.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(texture))
    eyes.node_tree.links.new(tex.outputs['Color'], eyes.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    eyes.node_tree.links.new(tex.outputs['Alpha'], eyes.node_tree.nodes.get('Principled BSDF').inputs['Alpha'])
    create('Source eyes fitted by original MHCLO', canonical_makehuman(np.array(fitted)), eye_faces, eye_uvs, eye_face_uvs, eyes)
    source_notes = ['body group only; helper cages excluded', 'source eye MHCLO fitted against full base vertex array', '0.1 m/native unit; right-handed axis rotation; neck context crop', 'one subdivision preview; neutral artistic material', 'not registered to Badin; incomplete internal anatomy']
else:
    if opts.pose != 'rest':
        raise ValueError('No authored mouth-open control claimed for the raw Badin skin')
    source = ROOT / 'assets/source/artiSynth/face/geometry/badinskin.obj'
    points, faces, uvs, face_uvs = obj_data(source)
    points = np.column_stack([.14 - points[:, 0], points[:, 2] - .1, points[:, 1]])
    create('Raw acquired Badin skin', points, faces)
    source_notes = ['published raw meter frame converted by documented research transform', 'unmodified skin geometry; smooth normals only', 'neutral artistic material', 'no independent external-face rig or anatomical approval']

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = opts.samples
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = opts.resolution
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('Neutral study background')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.18, .19, .20, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
objects = [ob for ob in scene.objects if ob.type == 'MESH']
bpy.context.view_layer.update()
corners = [ob.matrix_world @ Vector(c) for ob in objects for c in ob.bound_box]
low = Vector([min(c[i] for c in corners) for i in range(3)])
high = Vector([max(c[i] for c in corners) for i in range(3)])
center = (low + high) / 2
scale = max(high - low) * 1.15
for direction, power in [((1, 1, -1.5), 18), ((1, .2, 1), 10), ((-1, .8, .5), 12)]:
    ld = bpy.data.lights.new('Study softbox', 'AREA')
    ld.energy = power
    ld.size = .45
    ob = bpy.data.objects.new('Study softbox', ld)
    scene.collection.objects.link(ob)
    ob.location = center + Vector(direction) * .45
    ob.rotation_euler = (center - ob.location).to_track_quat('-Z', 'Y').to_euler()
cam = bpy.data.objects.new('Study camera', bpy.data.cameras.new('Study camera'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.type = 'ORTHO'
cam.data.ortho_scale = scale
for view in opts.views.split(','):
    direction = {'front': (1, 0, 0), 'side': (0, 0, -1), 'three-quarter': (1, .08, -1)}[view]
    cam.location = center + Vector(direction).normalized() * scale * 4
    forward = (center - cam.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward)
    cam.rotation_euler = Matrix(((right.x, up.x, -forward.x), (right.y, up.y, -forward.y), (right.z, up.z, -forward.z))).to_euler()
    scene.render.filepath = str(OUT / (view + '.png'))
    bpy.ops.render.render(write_still=True)
    print('STUDY_RENDER', opts.candidate, view, flush=True)
report = {'candidate': opts.candidate, 'pose': opts.pose, 'views': opts.views.split(','), 'sourceSha256': provenance, 'notes': source_notes, 'sourceFilesModified': False, 'anatomyReview': 'pending', 'renderer': {'engine': 'Cycles CPU', 'threads': 2, 'samples': opts.samples, 'resolution': opts.resolution}}
(OUT / 'evidence.json').write_text(json.dumps(report, indent=2) + '\n')
print('CANDIDATE_EVIDENCE', OUT)
