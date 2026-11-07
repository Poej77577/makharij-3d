"""Rebuild anatomical surfaces from the selected coherent atlas, not primitives.

Tongue curvature/median sulcus and velar tissue thickness are authored here.
The original extracted source remains unchanged. Every repair is recorded.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--out', default=str(ROOT / 'artifacts/milestone-evidence/M2/realistic-rebuild'))
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = Path(args.out).resolve()
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT / 'assets/source/z-anatomy'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'head-neck-reference.blend'), use_scripts=False, load_ui=False)
source_manifest = json.loads((SOURCE / 'extraction.json').read_text())
records = source_manifest['parts'].copy()
construction = json.loads((SOURCE / 'construction-surfaces.json').read_text())['parts']
objects = {ob.name: ob for ob in bpy.context.scene.objects if ob.type == 'MESH'}
edits = {}

def activate(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def volume(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    value = bm.calc_volume(signed=True)
    bm.free()
    return value

def apply(ob, modifier):
    activate(ob)
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def regularize_tissue(ob, voxel, budget):
    prior = volume(ob.data)
    modifier = ob.modifiers.new('Resolve actual tissue offset folds', 'REMESH')
    modifier.mode = 'VOXEL'; modifier.voxel_size = voxel; modifier.adaptivity = .15
    modifier.use_smooth_shade = True; modifier.use_remove_disconnected = False
    apply(ob, modifier)
    ob.data.calc_loop_triangles()
    modifier = ob.modifiers.new('Bounded reconstructed tissue surface', 'DECIMATE')
    modifier.ratio = min(1, budget / len(ob.data.loop_triangles))
    apply(ob, modifier)
    modifier = ob.modifiers.new('Remove subvoxel surface pinches', 'SMOOTH')
    modifier.factor = .30; modifier.iterations = 3
    apply(ob, modifier)
    after = volume(ob.data)
    assert .90 < after / prior < 1.10, 'Tissue repair changed anatomical volume materially: ' + ob.name
    return {'voxelSize_m': voxel, 'maximumTriangles': budget, 'beforeVolume_m3': prior, 'afterVolume_m3': after,
        'subvoxelSmoothing': {'factor': .30, 'iterations': 3}}

def opposite_fin_repair(ob):
    old = ob.data
    old.calc_loop_triangles()
    points = np.array([v.co for v in old.vertices])
    # Source Cricoid has exact opposite zero-volume fins on the mirror seam.
    unique, inverse = np.unique(np.round(points, 9), axis=0, return_inverse=True)
    faces = np.array([[inverse[i] for i in t.vertices] for t in old.loop_triangles])
    groups = defaultdict(list)
    for i, face in enumerate(faces):
        groups[tuple(sorted(face))].append(i)
    remove = set()
    for ids in groups.values():
        if len(ids) == 2:
            a, b = (tuple(faces[i]) for i in ids)
            if b not in [a, a[1:] + a[:1], a[2:] + a[:2]]:
                remove.update(ids)
    keep = [face.tolist() for i, face in enumerate(faces) if i not in remove]
    mesh = bpy.data.meshes.new(old.name + ' repaired mirror seam')
    mesh.from_pydata(unique, [], keep)
    mesh.update()
    for mat in old.materials:
        mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    ob.data = mesh
    edits[ob.name] = {'removedExactOppositeTrianglePairs': len(remove) // 2, 'coordinateWeldPrecision_m': 1e-9}

opposite_fin_repair(objects['ATLAS_CRICOID_CARTILAGE'])

# Replace the thin source velar shell with a genuine curved tissue volume.
velum = objects['ATLAS_SOFT_PALATE']
surface = construction['Soft palate']
mesh = bpy.data.meshes.new('Velar control surface from original atlas')
mesh.from_pydata(np.array(surface['positions']).reshape(-1, 3), [], surface['faces'])
mesh.update()
for mat in velum.data.materials:
    mesh.materials.append(mat)
velum.data = mesh
modifier = velum.modifiers.new('Authored velar tissue thickness', 'SOLIDIFY')
modifier.thickness = .0035
modifier.offset = 0
modifier.use_rim = True
apply(velum, modifier)
edits[velum.name] = {'method': 'Original curved atlas velar surface, full source mirror, new tissue thickness',
                      'sourceThickness_m': .0005, 'authoredThickness_m': .0035, 'clinicalMeasurement': False}
edits[velum.name]['foldRepair'] = regularize_tissue(velum, .00020, 9000)

# Smooth the coarse source tongue as a volume, retaining its anatomical frame.
tongue = objects['ATLAS_TONGUE']
before = volume(tongue.data)
q = np.array([v.co for v in tongue.data.vertices])
center = q.mean(0)
modifier = tongue.modifiers.new('Anatomical tongue surface refinement', 'SUBSURF')
modifier.levels = modifier.render_levels = 2
apply(tongue, modifier)
factor = (before / volume(tongue.data)) ** (1 / 3)
for v in tongue.data.vertices:
    v.co = center + (np.array(v.co) - center) * factor
tongue.data.update()
positions = np.array([v.co for v in tongue.data.vertices])
lo, hi = positions.min(0), positions.max(0)
groove_count = 0
for v in tongue.data.vertices:
    x, y, z = v.co
    along = (x - lo[0]) / (hi[0] - lo[0])
    # Smooth, shallow median sulcus on the dorsum, not on the root/floor.
    dorsal = max(0, min(1, (v.normal.y - .2) / .6))
    height = max(0, min(1, (y - (lo[1] + .55 * (hi[1] - lo[1]))) / .008))
    envelope = np.sin(np.pi * np.clip((along - .18) / .78, 0, 1)) ** 2
    depth = .00065 * np.exp(-(z / .0015) ** 2) * envelope * dorsal * height
    if depth > 1e-8:
        v.co.y -= depth
        groove_count += 1
after_sculpt = volume(tongue.data)
mass_factor = (before / after_sculpt) ** (1 / 3)
for v in tongue.data.vertices:
    v.co = center + (np.array(v.co) - center) * mass_factor
tongue.data.update()
edits[tongue.name] = {'method': 'Source anatomical surface subdivision, gentle dorsal median sulcus, volume preservation',
                       'sourceVertices': len(q), 'refinedVertices': len(tongue.data.vertices),
                       'sourceVolume_m3': before, 'finalVolume_m3': volume(tongue.data),
                       'maximumSulcusDepth_m': .00065, 'sulcusVertices': groove_count,
                       'clinicalMeasurement': False, 'unintendedDentalContacts': 'independent check required'}

# Make a continuous tongue/root envelope from actual atlas tongue muscles.
# The genioglossus/hyoglossus remain as nested anatomical regions for section
# inspection; they are not independent floating substitutes for the tongue.
root_names = ['ATLAS_GENIOGLOSSUS_MUSCLE_L', 'ATLAS_GENIOGLOSSUS_MUSCLE_R',
              'ATLAS_HYOGLOSSUS_MUSCLE_L', 'ATLAS_HYOGLOSSUS_MUSCLE_R']
root_parts = [tongue] + [objects[name] for name in root_names]
vertices, faces = [], []
source_volume_sum = 0
for part in root_parts:
    offset = len(vertices)
    vertices.extend([list(v.co) for v in part.data.vertices])
    faces.extend([[offset + i for i in poly.vertices] for poly in part.data.polygons])
    source_volume_sum += volume(part.data)
mesh = bpy.data.meshes.new('Whole anatomical tongue and connected root envelope')
mesh.from_pydata(vertices, [], faces)
mesh.update()
for mat in tongue.data.materials:
    mesh.materials.append(mat)
tongue.data = mesh
modifier = tongue.modifiers.new('Union of actual tongue-root tissues', 'REMESH')
modifier.mode = 'VOXEL'
modifier.voxel_size = .00020
modifier.adaptivity = .15
modifier.use_smooth_shade = True
modifier.use_remove_disconnected = False
apply(tongue, modifier)
union_volume = volume(tongue.data)
assert .98 * before < union_volume < 1.02 * source_volume_sum, 'Tongue-root union lost or invented tissue volume'
for v in tongue.data.vertices:
    v.co += v.normal * .00018
tongue.data.update()
fascial_repair = regularize_tissue(tongue, .00020, 30000)
edits[tongue.name]['rootReconstruction'] = {'sourceParts': root_names, 'method': 'Fine volumetric union of the actual anatomical tongue/root muscle surfaces',
                                            'voxelSize_m': .00020, 'authoredFascialCover_m': .00018,
                                            'unionVolume_m3': union_volume, 'sourceComponentVolumeSum_m3': source_volume_sum,
                                            'finalVolumeWithRoot_m3': volume(tongue.data), 'fascialFoldRepair': fascial_repair}
for name in root_names:
    objects[name]['anatomicalRegionOf'] = 'ATLAS_TONGUE'
    records[name]['anatomicalRegionOf'] = 'ATLAS_TONGUE'

# A physically scaled, region-limited mucosal surface appearance. This is
# authored tissue detail, not a scanned papilla map or an anatomical claim.
tongue_mat = tongue.data.materials[0].copy()
tongue_mat.name = 'Rebuilt tongue mucosa with dorsal microstructure'
tongue.data.materials.clear(); tongue.data.materials.append(tongue_mat)
nodes, links = tongue_mat.node_tree.nodes, tongue_mat.node_tree.links
bs = nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value = (.36, .10, .085, 1)
bs.inputs['Roughness'].default_value = .42
bs.inputs['Subsurface Weight'].default_value = .07
bs.inputs['Subsurface Radius'].default_value = (.0007, .0003, .0002)
bs.inputs['Coat Weight'].default_value = .10
geometry = nodes.new('ShaderNodeNewGeometry')
origin = nodes.new('ShaderNodeVectorMath'); origin.operation = 'SUBTRACT'; origin.name = 'Anatomical texture origin'
links.new(geometry.outputs['Position'], origin.inputs[0])
separate = nodes.new('ShaderNodeSeparateXYZ'); links.new(origin.outputs['Vector'], separate.inputs[0])
normal = nodes.new('ShaderNodeVectorMath'); normal.operation = 'DOT_PRODUCT'; normal.inputs[1].default_value = (0, 1, 0)
links.new(geometry.outputs['Normal'], normal.inputs[0])
mask = nodes.new('ShaderNodeMapRange'); mask.inputs['From Min'].default_value = .1; mask.inputs['From Max'].default_value = .8; mask.clamp = True
links.new(normal.outputs['Value'], mask.inputs['Value'])
height_mask = nodes.new('ShaderNodeMapRange'); height_mask.inputs['From Min'].default_value = -.005; height_mask.inputs['From Max'].default_value = .005; height_mask.clamp = True
links.new(separate.outputs['Y'], height_mask.inputs['Value'])
mix_mask = nodes.new('ShaderNodeMath'); mix_mask.operation = 'MULTIPLY'; links.new(mask.outputs['Result'], mix_mask.inputs[0]); links.new(height_mask.outputs['Result'], mix_mask.inputs[1])
papilla = nodes.new('ShaderNodeTexVoronoi'); papilla.inputs['Scale'].default_value = 3200
links.new(origin.outputs['Vector'], papilla.inputs['Vector'])
height = nodes.new('ShaderNodeMath'); height.operation = 'MULTIPLY'; links.new(papilla.outputs['Distance'], height.inputs[0]); links.new(mix_mask.outputs[0], height.inputs[1])
bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .28; bump.inputs['Distance'].default_value = .00012
links.new(height.outputs[0], bump.inputs['Height']); links.new(bump.outputs['Normal'], bs.inputs['Normal'])
edits[tongue.name]['surfaceAppearance'] = {'method': 'Authored dorsal microstructure and wet mucosal shading, not scanned histology', 'nominalFeatureScale_m': 1 / 3200}

# These original source meshes contain mirror/scan nonmanifold intersections.
# A fine volumetric reconstruction fuses their tissue, preserving actual voids.
for name, voxel in [('ATLAS_MUCOSA_OF_NASAL_CAVITY', .00015), ('ATLAS_MANDIBLE', .00030), ('ATLAS_ETHMOID_BONE', .00015)]:
    ob = objects[name]
    original_mesh = ob.data.copy()
    prior = volume(ob.data)
    modifier = ob.modifiers.new('Anatomical source tissue reconstruction', 'REMESH')
    modifier.mode = 'VOXEL'
    modifier.voxel_size = voxel
    modifier.adaptivity = .12
    modifier.use_smooth_shade = True
    modifier.use_remove_disconnected = False
    apply(ob, modifier)
    current = volume(ob.data)
    if not (current > 0 and .50 < current / prior < 1.50):
        if name == 'ATLAS_ETHMOID_BONE':
            # Preserve the actual open skeletal reference rather than accepting
            # a voxel operation that fills its fine nasal cells. It remains an
            # uncapped context surface, with no closed-volume claim.
            failed_mesh = ob.data
            ob.data = original_mesh
            bpy.data.meshes.remove(failed_mesh)
            edits[name] = {'voxelReconstructionAccepted': False, 'originalOpenContextRetained': True,
                           'reason': 'Fine nasal-cell volume would be changed materially',
                           'beforeSignedVolume_m3': prior, 'rejectedSignedVolume_m3': current,
                           'closedTissueVolumeClaimed': False}
            continue
        raise AssertionError(f'{name}: volume was lost or filled during reconstruction: {prior} -> {current}')
    edits[name] = {'method': 'Fine voxel reconstruction of original source tissue; cavity preservation requires independent check',
                    'voxelSize_m': voxel, 'beforeVolume_m3': prior, 'afterVolume_m3': current,
                    'vertices': len(ob.data.vertices), 'clinicalMeasurement': False}
    bpy.data.meshes.remove(original_mesh)

# Rebuild a genuinely hollow proximal tracheal wall from the source exterior.
# The original atlas supplies an outer organ surface, not a complete lumen.
trachea = objects['ATLAS_TRACHEA']
full = np.array([v.co for v in trachea.data.vertices])
centers = []
for lo_y, hi_y in zip(np.linspace(full[:, 1].min(), full[:, 1].max(), 33)[:-1], np.linspace(full[:, 1].min(), full[:, 1].max(), 33)[1:]):
    band = full[(full[:, 1] >= lo_y) & (full[:, 1] <= hi_y)]
    if len(band) >= 3:
        centers.append([band[:, 1].mean(), (band[:, 0].min() + band[:, 0].max()) / 2, (band[:, 2].min() + band[:, 2].max()) / 2])
centers = np.array(centers)
center_x = np.polyfit(centers[:, 0], centers[:, 1], 2)
center_z = np.polyfit(centers[:, 0], centers[:, 2], 2)
def inner_airway(points):
    inner = points.copy()
    for axis, coefficients in [(0, center_x), (2, center_z)]:
        center = np.polyval(coefficients, points[:, 1])
        inner[:, axis] = center + (points[:, axis] - center) * .84
    return inner
inner = inner_airway(full).tolist()
inner_faces = [list(poly.vertices) for poly in trachea.data.polygons]
(OUT / 'reconstructed-lumens.json').write_text(json.dumps({'Trachea': {'positions': np.array(inner).ravel().tolist(), 'faces': inner_faces,
    'role': 'Source-shaped full inner airway reference; positive tissue is cropped separately'}}, separators=(',', ':')) + '\n')
bm = bmesh.new()
bm.from_mesh(trachea.data)
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-8,
                      plane_co=(0, -.152, 0), plane_no=(0, -1, 0), clear_outer=True)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(trachea.data)
bm.free()
trachea.data.update()
outer = np.array([v.co for v in trachea.data.vertices])
outer_faces = [list(poly.vertices) for poly in trachea.data.polygons]
from collections import Counter
incidence = Counter(tuple(sorted((a, b))) for face in outer_faces for a, b in zip(face, face[1:] + face[:1]))
boundary = [(a, b) for face in outer_faces for a, b in zip(face, face[1:] + face[:1]) if incidence[tuple(sorted((a, b)))] == 1]
n = len(outer)
faces = outer_faces + [[i + n for i in face[::-1]] for face in outer_faces] + [[b, a, a + n, b + n] for a, b in boundary]
mesh = bpy.data.meshes.new('Source-shaped trachea with open annular airway ports')
mesh.from_pydata(np.vstack([outer, inner_airway(outer)]).tolist(), [], faces); mesh.update()
for material in trachea.data.materials: mesh.materials.append(material)
trachea.data = mesh
assert volume(mesh) > 0
edits[trachea.name] = {'authoredInnerRadialScale': .84, 'inferiorContextCropY_m': -.152,
    'airPortFilled': False, 'centerlineFit': {'x': center_x.tolist(), 'z': center_z.tolist()},
    'method': 'Source-shaped inner/outer walls, preserved longitudinal coordinates and true annular rims; no normal-offset rim fold', 'clinicalMeasurement': False}

# Real source turbinate bones need a visible mucosal envelope. Retain the bone
# as a nested anatomical region so its actual section stays visible inside the
# authored tissue cover; do not show bare nasal bones as finished living mucosa.
for side in ['L', 'R']:
    bone_name = 'ATLAS_INFERIOR_NASAL_CONCHA_BONE_' + side
    bone = objects[bone_name]
    name = 'ATLAS_INFERIOR_CONCHA_MUCOSA_' + side
    mesh = bone.data.copy()
    mesh.name = 'Mucosal envelope from actual inferior concha ' + side
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    for vertex in mesh.vertices:
        vertex.co += vertex.normal * .00065
    mesh.update()
    material = objects['ATLAS_MUCOSA_OF_NASAL_CAVITY'].data.materials[0]
    mesh.materials.clear(); mesh.materials.append(material)
    modifier = ob.modifiers.new('Source-shaped turbinate tissue reconstruction', 'REMESH')
    modifier.mode = 'VOXEL'; modifier.voxel_size = .00015; modifier.adaptivity = .20
    modifier.use_smooth_shade = True; modifier.use_remove_disconnected = False
    apply(ob, modifier)
    ob.data.calc_loop_triangles()
    modifier = ob.modifiers.new('Preserve organic turbinate curvature', 'DECIMATE')
    modifier.ratio = min(1, 8000 / len(ob.data.loop_triangles))
    apply(ob, modifier)
    assert volume(ob.data) > volume(bone.data), 'Mucosal cover lost the source bone envelope'
    bvh = BVHTree.FromPolygons([v.co for v in bone.data.vertices], [list(p.vertices) for p in bone.data.polygons])
    maximum = max(bvh.find_nearest(v.co)[3] for v in ob.data.vertices)
    assert maximum < .0012, 'Turbinate cover changed the source shape materially'
    objects[name] = ob
    records[name] = {'sourceObjectName': 'Authored mucosal envelope of ' + records[bone_name]['sourceObjectName'],
        'sourceKind': 'Adaptation of actual source turbinate geometry', 'materialClass': 'mucosa', 'derivedFrom': bone_name}
    edits[name] = {'method': 'Normal-offset tissue envelope of the actual source turbinate, with nested original bone',
        'authoredCover_m': .00065, 'maximumDistanceToOriginalBone_m': maximum, 'voxelSize_m': .00015, 'clinicalMeasurement': False}

for ob in objects.values():
    for polygon in ob.data.polygons:
        polygon.use_smooth = True
    ob['sourceLicense'] = 'CC-BY-SA-4.0; see assets/source/z-anatomy/NOTICE.md'
    ob['rebuildStatus'] = 'New anatomical reconstruction after rejected study; visual/structural review pending'
    if ob.name == 'ATLAS_EPIGLOTTIS':
        mat = bpy.data.materials.new('Epiglottic mucosal appearance')
        mat.use_nodes = True
        bs = mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (.42, .16, .13, 1)
        bs.inputs['Roughness'].default_value = .42
        ob.data.materials.clear()
        ob.data.materials.append(mat)

# Preserve the repaired source tissue while reducing redundant voxel triangles.
# Volume and exact delivered sections are independently rechecked after export.
for name, budget in [('ATLAS_MUCOSA_OF_NASAL_CAVITY', 60000), ('ATLAS_MANDIBLE', 18000), ('ATLAS_TONGUE', 30000)]:
    ob = objects[name]
    ob.data.calc_loop_triangles()
    count = len(ob.data.loop_triangles)
    prior = volume(ob.data)
    modifier = ob.modifiers.new('Controlled anatomical surface reduction', 'DECIMATE')
    modifier.ratio = min(1, budget / count)
    apply(ob, modifier)
    if name == 'ATLAS_MUCOSA_OF_NASAL_CAVITY':
        modifier = ob.modifiers.new('Resolve reduced mucosal surface pinch', 'SMOOTH')
        modifier.factor = .30; modifier.iterations = 3
        apply(ob, modifier)
    after = volume(ob.data)
    assert abs(after - prior) / prior < .02, 'Surface reduction materially changed tissue volume: ' + name
    edits[name]['surfaceReduction'] = {'beforeTriangles': count, 'targetTriangles': budget, 'beforeVolume_m3': prior, 'afterVolume_m3': after,
        'subvoxelSmoothingAfterReduction': name == 'ATLAS_MUCOSA_OF_NASAL_CAVITY'}

scene = bpy.context.scene
scene['status'] = 'Rebuilt internal geometry, not the rejected mixed-source model; acceptance pending'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'atlas-study.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'internal-rest.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(OUT / 'atlas-study.glb'), export_format='GLB', use_selection=True,
                          export_yup=False, export_apply=True, export_extras=True, export_animations=False)
parts = {}
for name, ob in objects.items():
    ob.data.calc_loop_triangles()
    parts[name] = {'positions': [c for v in ob.data.vertices for c in v.co], 'indices': [i for t in ob.data.loop_triangles for i in t.vertices],
                   'source': records[name]}
(OUT / 'atlas-meshes.json').write_text(json.dumps({'parts': parts}, separators=(',', ':')) + '\n')
record = {**source_manifest, 'parts': records, 'sourceSurfaceShapeModified': True, 'originalExtractedSourceUnchanged': True,
          'sourceSnapshot': 'assets/source/z-anatomy/manifest.json', 'reconstructionEdits': edits,
          'glbSha256': hashlib.sha256((OUT / 'atlas-study.glb').read_bytes()).hexdigest(),
          'blendSha256': hashlib.sha256((OUT / 'atlas-study.blend').read_bytes()).hexdigest(),
          'isAcceptedAnatomy': False, 'status': scene['status']}
(OUT / 'atlas-study.manifest.json').write_text(json.dumps(record, indent=2) + '\n')
(OUT / 'internal-rest.manifest.json').write_text(json.dumps({**record, 'blendSha256': hashlib.sha256((OUT / 'internal-rest.blend').read_bytes()).hexdigest()}, indent=2) + '\n')
print('REFINED_ANATOMY', json.dumps({'tongue': edits[tongue.name], 'folder': str(OUT)}, indent=2))
