"""Original section-authored tongue study. NOT an accepted anatomical asset.

No atlas tongue, Boolean, remeshing, texture or random surface displacement.
All section dimensions are inferred authoring choices, not patient measurements.
Blender Z-up / -Y anterior; project conversion is explicit in the manifest.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--out', default='artifacts/method-evidence/tongue-pilot')
p.add_argument('--revision', choices=['baseline', 'rounded-sections'], default='baseline')
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
OUT = (ROOT / args.out).resolve()
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.fps = 24

# x anterior, dorsal height, ventral height, transverse half width (all mm).
# Explicit sagittal/transverse design: a broad descending root, dorsal arch,
# thinning free blade and rounded tip. These are inferred, not traced MRI data.
SECTIONS_MM = [
    [-79, -28, -28, 0],
    [-77, -16, -35, 8],
    [-72, -4, -40, 15],
    [-65, 5, -39, 19],
    [-56, 11, -34, 20],
    [-46, 13, -26, 19],
    [-36, 11, -19, 18],
    [-25, 6, -13, 16],
    [-16, 1, -9, 13],
    [-10, -3, -7, 8],
    [-7, -5, -5, 0],
]


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def smooth(v):
    v = clamp(v)
    return v * v * (3 - 2 * v)


def profile(x, col):
    """Monotone cubic Hermite interpolation; prevents cap overshoot."""
    xs = [v[0] * .001 for v in SECTIONS_MM]
    ys = [v[col] * .001 for v in SECTIONS_MM]
    ds = [(ys[i+1]-ys[i])/(xs[i+1]-xs[i]) for i in range(len(xs)-1)]
    slopes = [ds[0]] + [0 if ds[i-1]*ds[i] <= 0 else
                         2/(1/ds[i-1]+1/ds[i]) for i in range(1, len(ds))] + [ds[-1]]
    i = next((i for i in range(len(xs)-1) if x <= xs[i+1]), len(xs)-2)
    h = xs[i+1] - xs[i]
    t = clamp((x-xs[i])/h)
    return ((2*t**3-3*t*t+1)*ys[i] + (t**3-2*t*t+t)*h*slopes[i] +
            (-2*t**3+3*t*t)*ys[i+1] + (t**3-t*t)*h*slopes[i+1])


def native(v):
    x, y, z = v
    return (-z, -x, y)


def canonical(v):
    return Vector((-v.y, v.z, -v.x))


def mesh_object(name, verts, faces, collection):
    mesh = bpy.data.meshes.new(name + '_quad_surface')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    ob = bpy.data.objects.new(name, mesh)
    collection.objects.link(ob)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mat = bpy.data.materials.get('Untextured review clay')
    if mat is None:
        mat = bpy.data.materials.new('Untextured review clay')
        mat.diffuse_color = (.44, .44, .44, 1)
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.44, .44, .44, 1)
        mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .8
    mesh.materials.append(mat)
    return ob


low = bpy.data.collections.new('LOW')
scene.collection.children.link(low)
context = bpy.data.collections.new('REFERENCE_CONTEXT_NOT_DELIVERY')
scene.collection.children.link(context)

N, K = 72, 64
vertices = [native((-.079, -.028, 0))]
for i in range(1, N):
    # Cosine stations provide dense rounded tip/root loops without clipping.
    x = -.079 + .072 * (1 - math.cos(math.pi*i/N)) / 2
    top, bottom, width = (profile(x, col) for col in (1, 2, 3))
    mid = bottom + (top-bottom) * .47
    for j in range(K):
        angle = 2*math.pi*j/K
        s, c = math.sin(angle), math.cos(angle)
        if args.revision == 'rounded-sections':
            # One bounded shape correction: elliptical caps have vertical
            # tangency instead of conical zero-thickness apexes. The radial
            # transition has no fractional-cosine shoulder. No microdetail.
            if x >= -.016:
                q = math.sqrt(max(0, 1-((x+.016)/.009)**2))
                top, bottom, width = -.004+.005*q, -.004-.005*q, .014*q
            elif x <= -.072:
                q = math.sqrt(max(0, 1-((x+.072)/.007)**2))
                top, bottom, width = -.022+.018*q, -.022-.018*q, .016*q
            mid = (top+bottom)/2
            z = width * math.copysign(abs(s)**.86, s)
        else:
            z = width*s
        if c >= 0:
            exponent = 1 if args.revision == 'rounded-sections' else .62
            y = mid + (top-mid)*c**exponent
            # Geometric median sulcus and terminal V; submillimetre, no noise.
            dorsal_mask = c**4
            median = .00065 * math.exp(-(z/.0027)**2) * math.exp(-((x+.036)/.022)**4)
            terminal_x = -.060 + .52*abs(z)
            terminal = (0 if args.revision == 'rounded-sections' else
                        .0006 * math.exp(-((x-terminal_x)/.0014)**2))
            y -= (median+terminal)*dorsal_mask
        else:
            # Broad inferior muscular body blending into a thinner free blade.
            exponent = 1 if args.revision == 'rounded-sections' else .88
            y = mid - (mid-bottom)*(-c)**exponent
        vertices.append(native((x, y, z)))
tip = len(vertices)
vertices.append(native((-.007, -.004 if args.revision == 'rounded-sections' else -.005, 0)))
if args.revision == 'rounded-sections':
    vertices[0] = native((-.079, -.022, 0))
faces = []
for j in range(K):
    faces.append((0, 1+j, 1+(j+1)%K))
for i in range(N-2):
    a, b = 1+i*K, 1+(i+1)*K
    for j in range(K):
        q = (j+1)%K
        faces.append((a+j, b+j, b+q, a+q))
last = 1+(N-2)*K
for j in range(K):
    faces.append((last+j, tip, last+(j+1)%K))
tongue = mesh_object('PILOT_TONGUE', vertices, faces, low)
bpy.context.view_layer.objects.active = tongue
tongue.select_set(True)
subd = tongue.modifiers.new('One fixed authoring subdivision before morphs', 'SUBSURF')
subd.levels = subd.render_levels = 1
bpy.ops.object.modifier_apply(modifier=subd.name)
tongue['asset_status'] = 'experimental; anatomical and user review pending'
tongue['source'] = 'Original section-authored study; inferred dimensions'
tongue['not_a_speech_pose'] = True
rest = [canonical(v.co) for v in tongue.data.vertices]
tongue.shape_key_add(name='Basis')


def morph(point, control):
    x, y, z = point
    # Inferior-posterior attachment remains fixed in all controls.
    anchor_free = smooth((y+.035)/.014)
    if control == 'TIP_ELEVATE':
        w = smooth((x+.039)/.026) * anchor_free
        a = .78*w
        px, py = -.032, -.012
        dx, dy = x-px, y-py
        return (px+dx*math.cos(a)-dy*math.sin(a), py+dx*math.sin(a)+dy*math.cos(a), z*(1-.025*w))
    if control == 'DORSUM_ELEVATE':
        w = math.exp(-((x+.043)/.018)**4) * anchor_free
        dorsal = .35+.65*smooth((y+.020)/.025)
        return (x, y+.008*w*dorsal, z*(1-.035*w))
    w = math.exp(-((x+.063)/.015)**4) * anchor_free
    return (x-.005*w, y-.0015*w, z*(1+.035*w))


controls = ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT']
motion = {}
for name in controls:
    key = tongue.shape_key_add(name=name)
    distances, anchored = [], []
    for i, v in enumerate(rest):
        moved = Vector(morph(v, name))
        key.data[i].co = native(moved)
        d = (moved-v).length
        distances.append(d)
        if v.y <= -.035:
            anchored.append(d)
    motion[name] = {'movedVertices': sum(d > 1e-7 for d in distances),
                    'maxDisplacement_m': max(distances),
                    'inferiorAnchorMaxDisplacement_m': max(anchored, default=0)}

# Single diagnostic timeline; these are isolated controls, not Arabic letters.
keys = tongue.data.shape_keys
for name in controls:
    key = keys.key_blocks[name]
    for frame in range(1, 146, 12):
        key.value = 0
        key.keyframe_insert('value', frame=frame)
for index, name in enumerate(controls):
    key = keys.key_blocks[name]
    start = 1+48*index
    for offset, value in [(0, 0), (12, .5), (24, 1), (36, .5), (48, 0)]:
        key.value = value
        key.keyframe_insert('value', frame=start+offset)
keys.animation_data.action.name = 'DIAGNOSTIC_THREE_CONTROLS_NOT_SPEECH'
for fc in keys.animation_data.action.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
scene.frame_end = 145
scene.frame_set(1)

# Read-only atlas dentition/gingiva as a scale/context comparator. This is NOT
# a new atlas reconstruction; no atlas tongue/velum/head enters this pilot.
source = ROOT/'assets/source/z-anatomy/reference-meshes.json'
source_data = json.loads(source.read_text())
context_names = []
for name, part in source_data['parts'].items():
    if name != 'ATLAS_GINGIVA' and not name.startswith(('ATLAS_LOWER_', 'ATLAS_UPPER_')):
        continue
    pts = part['positions']
    verts = [native(pts[i:i+3]) for i in range(0, len(pts), 3)]
    ids = part['indices']
    ob = mesh_object('REFERENCE_'+name, verts, [ids[i:i+3] for i in range(0, len(ids), 3)], context)
    ob['license'] = 'CC BY-SA 4.0; BodyParts3D / Z-Anatomy, see source NOTICE'
    ob['reference_only'] = True
    context_names.append(ob.name)

# Inferred mucosal floor and hard-palate vault are open review surfaces. Their
# edges/attachments are unresolved; they are never exported as accepted organs.
for is_floor in (True, False):
    verts, quads = [], []
    ni, nj = 40, 40
    for i in range(ni+1):
        u = i/ni
        x = -.075+.068*u
        w = .014+.008*math.sin(math.pi*u)**.6
        for j in range(nj+1):
            s = 2*j/nj-1
            z = w*s
            if is_floor:
                y = -.034+.015*u+.010*s*s
                y += .003*math.exp(-((x+.05)/.013)**2)*(1-s*s)
            else:
                y = .014+.014*(1-s*s)*math.sin(math.pi*(.14+.72*u))
            verts.append(native((x, y, z)))
    for i in range(ni):
        for j in range(nj):
            a = i*(nj+1)+j
            quads.append((a, a+1, a+nj+2, a+nj+1))
    ob = mesh_object('INFERRED_FLOOR_GUIDE' if is_floor else 'INFERRED_PALATE_GUIDE', verts, quads, context)
    ob['reference_only'] = True
    ob['limitations'] = 'Inferred open guide; not a completed anatomical tissue volume'
    context_names.append(ob.name)

context.hide_render = True
context.hide_viewport = False
scene['review_status'] = 'unreviewed pilot; not the production model'
scene['project_to_blender'] = '(-z, -x, y); metres'
blend = OUT/'tongue-pilot.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
bpy.ops.object.select_all(action='DESELECT')
tongue.select_set(True)
bpy.context.view_layer.objects.active = tongue
glb = OUT/'tongue-pilot.glb'
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
                         export_extras=True, export_animations=True, export_morph=True,
                         export_morph_normal=True, export_yup=True,
                         export_force_sampling=True, export_frame_range=True)
manifest = {'status': 'experimental-unreviewed', 'productionSelected': False,
            'revision': args.revision,
            'anatomicalAcceptance': 'pending', 'clinicalAccuracyClaim': False,
            'shapeMethod': 'Explicit inferred sagittal/transverse sections; continuous quad cage, fixed subdivision before morphs',
            'sourceImage': 'User sagittal illustration; not redistributed; not scale calibrated',
            'sections_mm': SECTIONS_MM, 'inferred': ['all dimensions', 'transverse surfaces', 'floor/palate guides', 'control amplitudes'],
            'projectToBlender': [[0, 0, -1], [-1, 0, 0], [0, 1, 0]],
            'gltfToProject': [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
            'geometry': {'vertices': len(tongue.data.vertices), 'polygons': len(tongue.data.polygons),
                         'shapeKeys': controls, 'topologyChangesAfterMorphs': False},
            'motion': motion, 'referenceContext': context_names,
            'contextExported': False, 'contextSourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'contextAttribution': 'BodyParts3D, Kousaku Okubo, DBCLS; Z-Anatomy, Gauthier Kervyn; CC BY-SA 4.0; see assets/source/z-anatomy/NOTICE.md',
            'limitations': ['No papillae or final materials', 'No complete oral-floor attachment or muscle anatomy',
                            'No volume conservation or contact constraint', 'Not calibrated Arabic articulations',
                            'Clay review and independent critique required before any promotion'],
            'blendSha256': hashlib.sha256(blend.read_bytes()).hexdigest(),
            'glbSha256': hashlib.sha256(glb.read_bytes()).hexdigest()}
(OUT/'pilot-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({'blend': str(blend), 'glb': str(glb), 'motion': motion}, indent=2))
