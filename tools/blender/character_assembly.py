"""Reproducible mixed-source character assembly, with diagnostic views.

Translation fits are authoring references, not clinical registration. Original
source files and the preserved legacy study are never overwritten.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/anatomy'))
from mesh_sources import makehuman_head_data, makehuman_eye_data, uv_islands, file_sha
from surface_fits import fit_oral_lining, fit_throat_context, THROAT_FIT

parser = argparse.ArgumentParser()
parser.add_argument('--build-only', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
OUT.mkdir(parents=True, exist_ok=True)
fit_path = ROOT / 'assets/calibration/character-fit.json'
fit = json.loads(fit_path.read_text())
oral_path = ROOT / 'assets/anatomy/rest-meshes.json'
vkh_path = ROOT / 'artifacts/milestone-evidence/M1/vkh-upper-airway/source-meshes.json'
assert file_sha(oral_path) == fit['legacyRestSha256'], 'Recalibrate changed oral source'
oral = json.loads(oral_path.read_text())['parts']
vkh = json.loads(vkh_path.read_text())['parts']
trans = {name: np.array(value['matrix'])[:3, 3] for name, value in fit['transforms'].items()}
bpy.ops.wm.read_factory_settings(use_empty=True)
objects, records, closed = {}, {}, set()

def material(name, rgb, rough=.5, organic=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*rgb, 1)
    bs.inputs['Roughness'].default_value = rough
    if organic:
        bs.inputs['Subsurface Weight'].default_value = .06
        bs.inputs['Subsurface Radius'].default_value = (.0008, .0004, .00025)
        noise = mat.node_tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 850
        bump = mat.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .13
        bump.inputs['Distance'].default_value = .00009
        mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return mat

skin_mat = material('Authored skin pigment', (.43, .255, .17), .56, True)
oral_mat = material('Authored mucosal tissue', (.42, .105, .09), .45, True)
lip_mat = material('Authored vermilion pigment', (.40, .115, .095), .48, True)
tooth_mat = material('Ivory dental crowns', (.72, .68, .54), .3)
gum_mat = material('Authored gingival display margins', (.46, .14, .125), .47, True)
tongue_mat = material('Tongue tissue', (.46, .16, .14), .48, True)
muscle_mat = material('Suprahyoid tissue', (.38, .135, .105), .55, True)
cartilage_mat = material('Laryngeal cartilage', (.55, .62, .52), .6)
bone_mat = material('Hyoid bone', (.73, .64, .43), .53)

def create(name, points, faces, mat, source, uvs=None, face_uvs=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    mesh.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if uvs and face_uvs:
        layer = mesh.uv_layers.new(name='Source UV')
        for poly, ids in zip(mesh.polygons, face_uvs):
            for loop, i in zip(poly.loop_indices, ids):
                if i >= 0:
                    layer.data[loop].uv = uvs[i]
    ob['sourceKind'] = source
    ob['anatomyStatus'] = 'M2 working assembly; independent review pending'
    objects[name] = ob
    records[name] = {'sourceKind': source}
    return ob

head = makehuman_head_data(fit['headPose']['mouthOpenAuthoringWeight'])
body_faces = head['groups']['body']
islands = uv_islands(head, body_faces)
# Identify the original oral-bag UV island by topology and its spatial extent.
oral_islands = []
for fs in islands:
    q = head['canonicalPoints'][sorted({i for f in fs for i in head['faces'][f]})]
    if len(fs) == 398 and q[:, 1].max() < .09 and q[:, 0].min() > .04:
        oral_islands.append(fs)
assert len(oral_islands) == 1, 'Review changed source oral topology'
oral_faces = set(oral_islands[0])
oral_ids = {i for f in oral_faces for i in head['faces'][f]}
external_ids = {i for f in body_faces if f not in oral_faces for i in head['faces'][f]}
rim_ids = sorted(oral_ids & external_ids)
source_points = head['canonicalPoints'].copy()
fitted_points, lining_fit = fit_oral_lining(source_points, head['faces'], oral_faces, rim_ids)
skin = create('HEAD_SKIN', fitted_points, [head['faces'][f] for f in body_faces], skin_mat,
              'CC0 artist-authored continuous head, lips and oral mucosa', head['uv'], [head['face_uv'][f] for f in body_faces])
skin.data.materials.append(oral_mat)
skin.data.materials.append(lip_mat)
rim = source_points[rim_ids]
for poly, source_face in zip(skin.data.polygons, body_faces):
    if source_face in oral_faces:
        poly.material_index = 1
    else:
        center = np.array(poly.center)
        distance = min(np.linalg.norm(source_points[i] - rim, axis=1).min() for i in poly.vertices)
        if distance < .003 and .005 < center[1] < .05:
            poly.material_index = 2
attribute = skin.data.attributes.new('sourceVertexId', 'INT', 'POINT')
for i, item in enumerate(attribute.data):
    item.value = i
bm = bmesh.new()
bm.from_mesh(skin.data)
# Neck context includes the source thyroid/cricoid. Open crop is explicit.
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-8,
                      plane_co=(0, -.135, 0), plane_no=(0, -1, 0), clear_outer=True, clear_inner=False)
loose = [v for v in bm.verts if not v.link_faces]
if loose:
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
bm.to_mesh(skin.data)
bm.free()
sub = skin.modifiers.new('Continuous source smoothing', 'SUBSURF')
sub.levels = sub.render_levels = 1
records['HEAD_SKIN'].update({'neckContextCropY_m': -.135, 'closedVolume': False, 'oralMucosaFit': lining_fit, 'sourceRimVertexIds': rim_ids})

eyes = makehuman_eye_data(head)
eye_mat = material('Original CC0 eye texture', (1, 1, 1), .32)
tex = eye_mat.node_tree.nodes.new('ShaderNodeTexImage')
tex.image = bpy.data.images.load(str(ROOT / 'assets/source/makehuman/makehuman/data/eyes/materials/brown_eye.png'))
bs = eye_mat.node_tree.nodes.get('Principled BSDF')
eye_mat.node_tree.links.new(tex.outputs['Color'], bs.inputs['Base Color'])
eye_mat.node_tree.links.new(tex.outputs['Alpha'], bs.inputs['Alpha'])
create('EYES', eyes['canonicalPoints'], eyes['faces'], eye_mat,
       'CC0 original eyes fitted by original MHCLO bindings', eyes['uv'], eyes['face_uv'])

for name, mat in [('TONGUE', tongue_mat), ('UPPER_TEETH', tooth_mat), ('LOWER_TEETH', tooth_mat),
                  ('GINGIVA_UPPER', gum_mat), ('GINGIVA_LOWER', gum_mat), ('HARD_PALATE', oral_mat), ('SOFT_PALATE', oral_mat)]:
    part = oral[name]
    p = np.array(part['positions']).reshape(-1, 3) + trans['badin_oral']
    create(name, p, np.array(part['indices']).reshape(-1, 3), mat,
           'Prepared research oral source, translation-only character placement' if not name.startswith('GINGIVA') else 'Cast-derived authored display margin; anatomical segmentation not claimed')
    if name in ['TONGUE', 'SOFT_PALATE']:
        closed.add(name)

for source_name, name, mat in [('Pharynx', 'PHARYNX', oral_mat), ('Suprahyoid_muscles_L', 'MOUTH_FLOOR_LEFT', muscle_mat),
                               ('Suprahyoid_muscles_R', 'MOUTH_FLOOR_RIGHT', muscle_mat), ('Hyoid', 'HYOID', bone_mat),
                               ('Thyroid', 'THYROID', cartilage_mat), ('Cricoid', 'CRICOID', cartilage_mat)]:
    part = vkh[source_name]
    p = fit_throat_context(np.array(part['positions']).reshape(-1, 3) + trans['vkh_context'])
    faces = np.array(part['indices']).reshape(-1, 3) if 'indices' in part else part['faces']
    create(name, p, faces, mat, part['sourceKind'] + '; documented translation-only character placement')
    if 'sourceCells' in part or name in ['HYOID', 'THYROID', 'CRICOID']:
        closed.add(name)
    records[name]['surfaceFit'] = THROAT_FIT

# Reconstruct the actual hollow wall against the newly fitted palate, pharynx
# and head. The preserved legacy nasal meshes are not translated into place.
sys.path.insert(0, str(ROOT / 'scripts/anatomy'))
from nasal_lining import build_nasal_lining, SUGGESTED_COLORS
nasal_materials = {name: material(name + ' authored mucosa', tuple(v * .7 for v in rgb[:3]), .52, True) for name, rgb in SUGGESTED_COLORS.items()}
hp = np.array([v.co for v in skin.data.vertices])
nasal = build_nasal_lining(hard_palate=objects['HARD_PALATE'], pharynx=objects['PHARYNX'],
                          face_bounds={'min': hp.min(0).tolist(), 'max': hp.max(0).tolist()},
                          create=lambda name, p, f: create(name, p, f, nasal_materials[name], 'Authored unmeasured hollow nasal reconstruction; not acquired donor geometry'),
                          include_airspace=True, conform_floor=True)
for name in nasal['objects']:
    closed.add(name)
    records[name]['reconstruction'] = 'Palatal roof and source pharyngeal surface anchors; complete limits in nasal-reconstruction.json'
(OUT / 'nasal-reconstruction.json').write_text(json.dumps(nasal['metadata'], indent=2) + '\n')
(OUT / 'nasal-airspace-helper.json').write_text(json.dumps(nasal['airspace'], separators=(',', ':')) + '\n')
subprocess.run([str(ROOT / '.venv-qa/bin/python'), str(ROOT / 'tools/qa/check_negative_spaces.py')], check=True)

# The original complete body is a closed tissue boundary with an oral pocket.
# Close only its explicit neck-context crop, then form actual 3-D negative
# spaces. A section cap can subsequently be computed from this real volume.
bpy.ops.object.select_all(action='DESELECT')
skin.select_set(True)
bpy.context.view_layer.objects.active = skin
bpy.ops.object.modifier_apply(modifier=sub.name)
# Keep continuous source mucosa clear of the placed palatal guide. Raising an
# interior roof is permitted here; lowering it through dental crowns is not.
palate = objects['HARD_PALATE'].data
tree = BVHTree.FromPolygons([v.co for v in palate.vertices], [list(p.vertices) for p in palate.polygons], all_triangles=True)
roof_candidates = {v for poly in skin.data.polygons if poly.material_index == 1 for v in poly.vertices}
roof_deltas = []
for i in roof_candidates:
    vertex = skin.data.vertices[i]
    if vertex.co.y <= .038 or vertex.normal.y >= -.25:
        continue
    hit, normal, face, distance = tree.ray_cast(Vector((vertex.co.x, .12, vertex.co.z)), Vector((0, -1, 0)), .12)
    if hit is not None:
        target_y = max(vertex.co.y, hit.y + .0012)
        roof_deltas.append(abs(vertex.co.y - target_y))
        vertex.co.y = target_y
skin.data.update()
records['HEAD_SKIN']['palatalRoofGuard'] = {'source': 'Actual vertically intersected placed palatal triangles',
                                             'minimumAuthoredClearance_m': .0012, 'verticesChecked': len(roof_deltas),
                                             'maximumCorrection_m': max(roof_deltas, default=0), 'clinicalMeasurement': False}
bm = bmesh.new()
bm.from_mesh(skin.data)
neck_edges = [e for e in bm.edges if e.is_boundary]
assert neck_edges and all(abs(v.co.y + .135) < 1e-6 for e in neck_edges for v in e.verts), 'Unexpected open head surface before cavity work'
fills = bmesh.ops.holes_fill(bm, edges=neck_edges, sides=0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(skin.data)
bm.free()
topology_stages = []
def record_head_topology(stage):
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    bad = [e for e in bm.edges if not e.is_manifold]
    topology_stages.append({'stage': stage, 'nonmanifoldEdges': len(bad),
                            'sample': [{'points': [list(v.co) for v in e.verts], 'faces': len(e.link_faces)} for e in bad[:15]]})
    bm.free()
record_head_topology('neck crop closed before negative spaces')
cutters = [('nasal', nasal['airspace'])]
research_airway_path = OUT / 'research-airspace-helper.json'
lower_airway_path = OUT / 'lower-airway-helper.json'
cutters.extend([('research upper pharyngeal', json.loads(research_airway_path.read_text())),
                ('authored lower airway', json.loads(lower_airway_path.read_text()))])
volume_checks = []
def signed_volume(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    volume = bm.calc_volume(signed=True)
    bm.free()
    return volume
for label, part in cutters:
    mesh = bpy.data.meshes.new('Temporary ' + label + ' negative space')
    mesh.from_pydata(np.array(part['positions']).reshape(-1, 3), [], np.array(part['indices']).reshape(-1, 3))
    mesh.update()
    mesh.materials.append(oral_mat)
    helper = bpy.data.objects.new(mesh.name, mesh)
    scene_collection = bpy.context.collection
    scene_collection.objects.link(helper)
    before_volume = signed_volume(skin.data)
    cutter_volume = signed_volume(mesh)
    assert before_volume > .002 and cutter_volume > 0, 'Invalid head or negative-space volume'
    modifier = skin.modifiers.new('Actual ' + label + ' cavity', 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.solver = 'EXACT'
    modifier.double_threshold = 1e-8
    modifier.object = helper
    if hasattr(modifier, 'material_mode'):
        modifier.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = skin
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    after_volume = signed_volume(skin.data)
    tolerance = 1e-8
    delta = before_volume - after_volume
    assert -tolerance <= delta <= cutter_volume + tolerance, 'Boolean violates subtraction-volume bounds; do not publish the damaged head'
    volume_checks.append({'stage': label, 'before_m3': before_volume, 'after_m3': after_volume,
                          'negativeSpace_m3': cutter_volume, 'removed_m3': delta, 'tolerance_m3': tolerance})
    bpy.data.objects.remove(helper, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    record_head_topology(label + ' negative space applied')
(OUT / 'head-volume-topology.json').write_text(json.dumps(topology_stages, indent=2) + '\n')
(OUT / 'head-volume-bounds.json').write_text(json.dumps(volume_checks, indent=2) + '\n')
# Blender's Boolean ngons can tessellate into coincident opposite triangle
# pairs. They are zero-volume fins, not tissue. Remove only exact opposite
# pairs, retain all other triangles and copy their UV/material correspondence.
old_mesh = skin.data
old_mesh.calc_loop_triangles()
triangles = list(old_mesh.loop_triangles)
by_vertices = defaultdict(list)
for i, triangle in enumerate(triangles):
    by_vertices[tuple(sorted(triangle.vertices))].append(i)
remove = set()
for ids in by_vertices.values():
    if len(ids) > 1:
        assert len(ids) == 2, 'Unexpected multiple coincident Boolean faces'
        a, b = (triangles[i] for i in ids)
        av, bv = tuple(a.vertices), tuple(b.vertices)
        same_direction = bv in [av, av[1:] + av[:1], av[2:] + av[:2]]
        assert not same_direction, 'Same-direction Boolean duplicate is not a removable zero-volume fin'
        remove.update(ids)
kept = [triangle for i, triangle in enumerate(triangles) if i not in remove]
used = sorted({v for triangle in kept for v in triangle.vertices})
remap = {old: new for new, old in enumerate(used)}
mesh = bpy.data.meshes.new('Continuous head with actual oral and nasal-pharyngeal voids')
mesh.from_pydata([old_mesh.vertices[i].co for i in used], [], [[remap[i] for i in t.vertices] for t in kept])
mesh.update()
for mat in old_mesh.materials:
    mesh.materials.append(mat)
for polygon, triangle in zip(mesh.polygons, kept):
    polygon.material_index = triangle.material_index
    polygon.use_smooth = old_mesh.polygons[triangle.polygon_index].use_smooth
for source_uv in old_mesh.uv_layers:
    target_uv = mesh.uv_layers.new(name=source_uv.name)
    for polygon, triangle in zip(mesh.polygons, kept):
        for loop, source_loop in zip(polygon.loop_indices, triangle.loops):
            target_uv.data[loop].uv = source_uv.data[source_loop].uv
skin.data = mesh
bpy.data.meshes.remove(old_mesh)
repair_volume_before = signed_volume(skin.data)
bm = bmesh.new()
bm.from_mesh(skin.data)
vertices_before = len(bm.verts)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-7)
bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
# Preserve Boolean winding, including inward-facing boundaries of enclosed
# cavities. Global normal recalculation can incorrectly invert those shells.
vertices_after = len(bm.verts)
bm.to_mesh(skin.data)
bm.free()
repair_volume_after = signed_volume(skin.data)
assert abs(repair_volume_after - repair_volume_before) < 1e-8, f'Numerical cleanup changed tissue volume materially: {repair_volume_before} -> {repair_volume_after}'
record_head_topology('explicit triangle mesh after opposite zero-volume fin removal')
records['HEAD_SKIN']['booleanTessellationRepair'] = {'removedOppositeCoincidentTrianglePairs': len(remove) // 2,
                                                   'method': 'Exact shared vertex triples with opposite normals only; all other triangles and UV/material correspondence retained',
                                                   'volumeChangeFromRemovedPairs_m3': 0,
                                                   'numericalMergeTolerance_m': 1e-7, 'numericalVerticesMerged': vertices_before - vertices_after,
                                                   'numericalVolumeChange_m3': repair_volume_after - repair_volume_before}
(OUT / 'head-volume-topology.json').write_text(json.dumps(topology_stages, indent=2) + '\n')
closed.add('HEAD_SKIN')
records['HEAD_SKIN'].update({'closedVolume': True, 'contextCap': 'Only the documented neck crop is closed; not a new anatomical structure',
                             'cavities': [label for label, _ in cutters], 'retopology': 'Boolean interior cavity edits require deformation review; original source topology retained upstream'})

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene['status'] = 'M2 working reconstruction, not accepted teaching anatomy'
scene['registration'] = 'Mixed independent sources; authoring fit is not patient registration'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'character-assembly.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in objects.values():
    ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / 'character-assembly.glb'), export_format='GLB', use_selection=True,
                          export_yup=False, export_apply=True, export_extras=True, export_animations=False)
# Evaluated geometry for independent checks; no render cuts enter these files.
dep = bpy.context.evaluated_depsgraph_get()
parts = {}
for name, ob in objects.items():
    evaluated = ob.evaluated_get(dep)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    p = np.array([ob.matrix_world @ v.co for v in mesh.vertices])
    triangles = [list(t.vertices) for t in mesh.loop_triangles]
    parts[name] = {'positions': p.ravel().tolist(), 'indices': np.array(triangles).ravel().tolist(), 'source': records[name], 'closedTissueVolumeClaimed': name in closed}
    evaluated.to_mesh_clear()
(OUT / 'evaluated-meshes.json').write_text(json.dumps({'parts': parts, 'frame': fit['frame'], 'status': scene['status']}, separators=(',', ':')))
manifest = {'status': scene['status'], 'isAcceptedAnatomy': False, 'frame': fit['frame'],
            'glbSha256': file_sha(OUT / 'character-assembly.glb'), 'blendSha256': file_sha(OUT / 'character-assembly.blend'),
            'inputs': {str(path.relative_to(ROOT)): file_sha(path) for path in [fit_path, oral_path, vkh_path, research_airway_path, lower_airway_path,
                       Path(__file__), ROOT / 'tools/anatomy/mesh_sources.py', ROOT / 'tools/anatomy/surface_fits.py', ROOT / 'scripts/anatomy/nasal_lining.py',
                       ROOT / 'assets/source/makehuman/manifest.json', ROOT / 'assets/source/vkh-upper-airway/manifest.json']},
            'parts': records, 'review': {'geometry': 'pending', 'externalVisual': 'pending', 'anatomyExpert': 'pending', 'tajwidExpert': 'pending'},
            'unfinished': ['tongue-root/floor and pharyngeal attachment continuity', 'nasal vestibule/choana fit and septal coverage', 'gingival continuity', 'laryngeal inlet/epiglottis coverage review', 'deformation retopology and visual gate review'],
            'laterMilestones': ['new independent rig', 'new articulation calibration'],
            'cutaway': 'Computed sections of actual closed tissue volumes, including the head after 3-D cavity subtraction; the explicit neck-context crop is an artificial boundary.'}
(OUT / 'assembly.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

print('CHARACTER_ASSEMBLY', OUT)
