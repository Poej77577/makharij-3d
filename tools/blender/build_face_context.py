"""Original CC0 artist head/face targets around the new oral unit.

No rejected composed head, Boolean cavity, compressed oral bag or primitive face.
This is an external surface context. It must never be capped as cranial tissue.
"""
import argparse
from collections import Counter
import hashlib
import heapq
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/anatomy'))
from mesh_sources import makehuman_head_data, makehuman_eye_data, uv_islands, apply_target
from nasal_ports import makehuman_nasal_cap_faces, find_nasal_boundary_ports

p = argparse.ArgumentParser()
p.add_argument('--out', default='artifacts/method-evidence/face-context')
p.add_argument('--oral-folder', default='artifacts/method-evidence/oral-sculpt')
p.add_argument('--closed-nostrils', action='store_true', help='Research only: retain original blind nostril caps')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
OUT = ROOT/a.out
OUT.mkdir(parents=True, exist_ok=True)
spec_path = ROOT/'data/anatomy/face-context.json'
spec = json.loads(spec_path.read_text())
oral = ROOT/a.oral_folder
oral_manifest = json.loads((oral/'oral-manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(oral/'oral-unit.blend'), use_scripts=False, load_ui=False)
scene = bpy.context.scene
scene.frame_set(1)


def native(v):
    x, y, z = v
    return (-z, -x, y)


def canonical_delta(raw):
    return np.column_stack([raw[:, 2]*.1, raw[:, 1]*.1, -raw[:, 0]*.1])


def new_collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


SOURCE = new_collection('FACE_SOURCE')
DELIVERY = new_collection('FACE_DELIVERY')
head = makehuman_head_data(0)
helper = head['fittingReferences']['helper-upper-teeth']
mid = helper[np.abs(helper[:, 2]) < .003]
edge = mid[mid[:, 1] < mid[:, 1].min()+.001]
anchor = edge[edge[:, 0].argmax()].copy()
anchor[2] = 0
points = head['canonicalPoints']-anchor
body = head['groups']['body']
oral_islands = []
for island in uv_islands(head, body):
    ids = sorted({v for face in island for v in head['faces'][face]})
    q = points[ids]
    if len(island) == 398 and q[:, 0].min() > -.11 and q[:, 1].max() < .08:
        oral_islands.append(island)
assert len(oral_islands) == 1, 'Source oral-pocket identity changed'
pocket_faces = set(oral_islands[0])
pocket_ids = {v for face in pocket_faces for v in head['faces'][face]}
external_ids = {v for face in body if face not in pocket_faces for v in head['faces'][face]}
rim_ids = sorted(pocket_ids & external_ids)
assert len(rim_ids) == 38
rim = points[rim_ids]
cap_faces, nasal_cap_record = (set(), {'enabled': False}) if a.closed_nostrils else makehuman_nasal_cap_faces(
    head, points, hashlib.sha256((ROOT/'assets/source/makehuman/makehuman/data/3dobjs/base.obj').read_bytes()).hexdigest())
selected_faces = [face for face in body if face not in pocket_faces and face not in cap_faces and
                  min(points[v, 1] for v in head['faces'][face]) >= spec['neckCropY_m']]
used = sorted({v for face in selected_faces for v in head['faces'][face]})
index = {v: i for i, v in enumerate(used)}
edge_use = Counter()
neighbors = {v: set() for v in used}
for face in selected_faces:
    ids = head['faces'][face]
    for i, first in enumerate(ids):
        second = ids[(i+1)%len(ids)]
        edge_use[tuple(sorted((first, second)))] += 1
        neighbors[first].add(second)
        neighbors[second].add(first)
neck_rim = {v for edge, count in edge_use.items() if count == 1 for v in edge if points[v, 1] < -.070}
for old in neck_rim:
    points[old, 1] = spec['neckCropY_m']
base = bpy.data.meshes.new('Original head topology and source vertex IDs')
base.from_pydata([native(points[v]) for v in used], [],
                 [[index[v] for v in head['faces'][face]] for face in selected_faces])
base.update()
source_id = base.attributes.new('source_vertex_id', 'INT', 'POINT')
for attribute, old in zip(source_id.data, used):
    attribute.value = old
uv = base.uv_layers.new(name='Original MakeHuman UV')
for polygon, old in zip(base.polygons, selected_faces):
    for loop, old_uv in zip(polygon.loop_indices, head['face_uv'][old]):
        uv.data[loop].uv = head['uv'][old_uv]
for face in base.polygons:
    face.use_smooth = True

# A smooth vermilion pigment field follows the *original* lip rim. It is not a
# second lip object, and introduces no geometry or texture-registration claim.
colors = base.color_attributes.new(name='Pigment', type='FLOAT_COLOR', domain='POINT')
skin = np.array(spec['skinLinearColor'])
lip = np.array(spec['lipLinearColor'])
distances = {v: float('inf') for v in used}
queue = []
for old in rim_ids:
    distances[old] = 0
    heapq.heappush(queue, (0, old))
while queue:
    distance, old = heapq.heappop(queue)
    if distance > distances[old] or distance > .015:
        continue
    for other in neighbors[old]:
        new_distance = distance+float(np.linalg.norm(points[old]-points[other]))
        if new_distance < distances[other]:
            distances[other] = new_distance
            heapq.heappush(queue, (new_distance, other))
for attr, old in zip(colors.data, used):
    point = points[old]
    d = distances[old]
    lateral = max(.5, 1-abs(point[2])/.045)
    radius = (.010 if point[1] < float(rim[:, 1].mean()) else .008)*lateral
    t = max(0, min(1, 1-max(0, d-.0015)/(radius-.0015)))
    t = t*t*(3-2*t)
    attr.color = (*((1-t)*skin+t*lip), 1)
mat = bpy.data.materials.new('Original face surface / authored vermilion pigment')
mat.use_nodes = True
bs = mat.node_tree.nodes.get('Principled BSDF')
bs.inputs['Roughness'].default_value = .53
color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
color.layer_name = 'Pigment'
mat.node_tree.links.new(color.outputs['Color'], bs.inputs['Base Color'])
base.materials.append(mat)
source = bpy.data.objects.new('SOURCE_HEAD', base)
SOURCE.objects.link(source)
source['source'] = 'Original MakeHuman CC0 body/expression data; no atlas composite head'
source['context_only'] = True
source['oral_pocket_removed_from_delivery'] = True
source['source_vertex_ids'] = 'source_vertex_id point attribute on this unsubdivided source'
source.shape_key_add(name='Basis')
controls = {'JAW_OPEN': ('mouth-open', spec['mouthOpenTargetWeight']),
            'LIP_PRESS': ('mouth-compression', spec['lipPressTargetWeight']),
            'LIP_ROUND': ('mouth-pursing', spec['lipRoundTargetWeight']),
            'LIP_PROTRUDE': ('mouth-protusion', spec['lipProtrudeTargetWeight'])}
target_files = []
for name, (target_name, weight) in controls.items():
    raw = np.zeros_like(head['neutralRawPoints'])
    for family in ['african', 'asian', 'caucasian']:
        target = ROOT/'assets/source/makehuman/makehuman/data/targets/expression/units'/family/(target_name+'.target')
        apply_target(raw, target, weight/3)
        target_files.append({'path': str(target.relative_to(ROOT)),
                             'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'weight': weight/3})
    delta = canonical_delta(raw)
    for old in neck_rim:
        delta[old] = 0
    key = source.shape_key_add(name=name)
    for v, old in zip(key.data, used):
        v.co = native(points[old]+delta[old])

# Preserve the source oral pocket in the native file as a hidden reference only.
ids = sorted(pocket_ids)
remap = {old: i for i, old in enumerate(ids)}
mesh = bpy.data.meshes.new('Original oral pocket reference, not a teaching organ')
mesh.from_pydata([native(points[v]) for v in ids], [], [[remap[v] for v in head['faces'][face]] for face in sorted(pocket_faces)])
reference = bpy.data.objects.new('ORIGINAL_ORAL_POCKET_REFERENCE', mesh)
SOURCE.objects.link(reference)
reference.hide_render = True
reference.hide_set(True)
reference['role'] = 'Unmodified generic source oral pocket, not acquired speech anatomy'

modifier = source.modifiers.new('Fixed face refinement, baked identically for every source target', 'SUBSURF')
modifier.levels = modifier.render_levels = 1
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
mesh = bpy.data.meshes.new_from_object(source.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
if mesh.attributes.get('source_vertex_id'):
    mesh.attributes.remove(mesh.attributes['source_vertex_id'])
external = bpy.data.objects.new('HEAD_EXTERNAL', mesh)
DELIVERY.objects.link(external)
external['context_only'] = True
external['not_closed_cranial_tissue'] = True
external.shape_key_add(name='Basis')
nasal_ports = find_nasal_boundary_ports(
    [(-v.co.y, v.co.z, -v.co.x) for v in external.data.vertices],
    [list(face.vertices) for face in external.data.polygons])
if not a.closed_nostrils:
    assert len(nasal_ports) == 2, 'Nostril opening failed after source subdivision'
motion = {}
for name in controls:
    source.data.shape_keys.key_blocks[name].value = 1
    source.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    evaluated = source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    posed = evaluated.to_mesh()
    assert len(posed.vertices) == len(external.data.vertices), 'Subdivision changed topology by pose'
    key = external.shape_key_add(name=name)
    maximum = 0
    moved = 0
    for v, original, target in zip(posed.vertices, external.data.vertices, key.data):
        target.co = v.co
        distance = (v.co-original.co).length
        maximum = max(maximum, distance)
        moved += distance > 1e-7
    evaluated.to_mesh_clear()
    motion[name] = {'movedVertices': moved, 'maximumDisplacement_m': maximum}
    source.data.shape_keys.key_blocks[name].value = 0
source.hide_render = True
source.hide_set(True)

eye = makehuman_eye_data(head)
mesh = bpy.data.meshes.new('Original bound CC0 eyes')
mesh.from_pydata([native(v-anchor) for v in eye['canonicalPoints']], [], eye['faces'])
layer = mesh.uv_layers.new(name='Original eye UV')
for polygon, ids in zip(mesh.polygons, eye['face_uv']):
    polygon.use_smooth = True
    for loop, old_uv in zip(polygon.loop_indices, ids):
        layer.data[loop].uv = eye['uv'][old_uv]
eye_material = bpy.data.materials.new('Original CC0 brown eye texture')
eye_material.use_nodes = True
eye_material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .3
image_node = eye_material.node_tree.nodes.new('ShaderNodeTexImage')
eye_image = ROOT/'assets/source/makehuman/makehuman/data/eyes/materials/brown_eye.png'
image_node.image = bpy.data.images.load(str(eye_image))
image_node.image.pack()
eye_material.node_tree.links.new(image_node.outputs['Color'], eye_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
eye_material.node_tree.links.new(image_node.outputs['Alpha'], eye_material.node_tree.nodes['Principled BSDF'].inputs['Alpha'])
eye_material.use_backface_culling = True
mesh.materials.append(eye_material)
eyes = bpy.data.objects.new('FACE_EYES', mesh)
DELIVERY.objects.link(eyes)
# One native controller owns the oral unit and facial skin together. The
# original face target already moves chin/skin; never rotate that skin again.
master = bpy.data.objects.new('SPEECH_CONTROLS', None)
scene.collection.objects.link(master)
all_controls = ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT', 'JAW_OPEN',
                'VELUM_RAISE', 'LIP_PRESS', 'LIP_ROUND', 'LIP_PROTRUDE']
for name in all_controls:
    master[name] = 0.0
    master.id_properties_ui(name).update(min=0, max=1)
for ob in [external, *bpy.data.collections['LOW'].objects]:
    keys = ob.data.shape_keys
    if not keys:
        continue
    if keys.animation_data:
        keys.animation_data.action = None
    for name in all_controls:
        key = keys.key_blocks.get(name)
        if key is None:
            continue
        driver = key.driver_add('value').driver
        driver.expression = 'state'
        variable = driver.variables.new()
        variable.name = 'state'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id = master
        variable.targets[0].data_path = '["'+name+'"]'
for index, name in enumerate(all_controls):
    for frame in range(1, 386, 12):
        master[name] = 0.0
        master.keyframe_insert(data_path='["'+name+'"]', frame=frame)
    for offset, value in [(0, 0), (12, .5), (24, 1), (36, .5), (48, 0)]:
        master[name] = float(value)
        master.keyframe_insert(data_path='["'+name+'"]', frame=1+48*index+offset)
for curve in master.animation_data.action.fcurves:
    for key in curve.keyframe_points:
        key.interpolation = 'LINEAR'
scene.frame_end = 385
scene.frame_set(1)
bpy.context.view_layer.update()
blend = OUT/'face-context.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in DELIVERY.objects:
    ob.hide_set(False)
    ob.select_set(True)
glb = OUT/'face-context.glb'
export_options = {}
prop = bpy.ops.export_scene.gltf.get_rna_type().properties['export_animation_mode']
if 'SCENE' in {item.identifier for item in prop.enum_items}:
    export_options['export_animation_mode'] = 'SCENE'
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
                         export_extras=True, export_morph=True, export_animations=True,
                         export_yup=True, export_force_sampling=True, export_frame_range=True,
                         **export_options)
record = {'status': 'external-context-experimental', 'productionSelected': False,
          'visualReview': 'pending', 'expertAcceptance': 'pending',
          'fullInternalHeadComplete': False, 'clinicalAccuracyClaim': False,
          'parts': ['HEAD_EXTERNAL', 'FACE_EYES'], 'contextSurfaceOnly': True,
          'nativeControlMaster': 'SPEECH_CONTROLS', 'controls': all_controls,
          'jawSkinDoubleRotation': False,
          'excludeFromTissueSectionCaps': ['HEAD_EXTERNAL', 'FACE_EYES'],
          'sourceRepository': 'https://github.com/makehumancommunity/makehuman',
          'sourceCommit': 'a8bc2d54ff0ac92e78ff71431b1023eda42bf482', 'originalAssetLicense': 'CC0-1.0',
          'oralSourceGlbSha256': oral_manifest['glbSha256'],
          'sourceToCanonicalTranslation_m': (-anchor).tolist(),
          'gltfToProject': [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
          'sourceVertexMapping': 'SOURCE_HEAD/source_vertex_id in native master, before subdivision',
          'originalOralPocket': {'faces': len(pocket_faces), 'delivery': False, 'changedShape': False},
          'nostrilOpening': nasal_cap_record, 'nasalPorts': nasal_ports,
          'originalLipRimVertices': rim_ids, 'headVertices': len(external.data.vertices),
          'neckCrop': {'planeY_m': spec['neckCropY_m'], 'flattenedBoundaryVertices': len(neck_rim), 'capAsTissue': False},
          'targetFiles': target_files, 'motion': motion,
          'specSha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
          'blendSha256': hashlib.sha256(blend.read_bytes()).hexdigest(),
          'glbSha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
          'limitations': ['External face context, not complete internal head anatomy',
                          'Helper-anchor authoring fit, not clinical registration',
                          'Lip/dental contact and Arabic phoneme calibration pending',
                          'Generic source oral pocket excluded rather than presented as anatomy']}
(OUT/'face-manifest.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'headVertices': len(external.data.vertices), 'motion': motion, 'output': str(OUT)}, indent=2))
