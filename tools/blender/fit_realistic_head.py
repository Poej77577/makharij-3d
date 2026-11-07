"""Fit the rebuilt coherent atlas to continuous CC0 skin and real 3-D cavities.

All atlas structures receive the same translation. No independent throat shear
or substitute organ primitives are used. Original sources remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/anatomy'))
from mesh_sources import makehuman_head_data, makehuman_eye_data, uv_islands

p = argparse.ArgumentParser()
p.add_argument('--folder', default=str(ROOT / 'artifacts/milestone-evidence/M2/realistic-rebuild'))
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = Path(args.folder).resolve()
old_manifest = json.loads((OUT / 'internal-rest.manifest.json').read_text())
assert hashlib.sha256((OUT / 'internal-rest.blend').read_bytes()).hexdigest() == old_manifest['blendSha256'], 'Stale native anatomy source'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'internal-rest.blend'), use_scripts=False, load_ui=False)
objects = {ob.name: ob for ob in bpy.context.scene.objects if ob.type == 'MESH'}
records = old_manifest['parts'].copy()
head = makehuman_head_data(.12)
helper = head['fittingReferences']['helper-upper-teeth']
mid = helper[abs(helper[:, 2]) < .003]
edge = mid[mid[:, 1] < mid[:, 1].min() + .001]
translation = edge[edge[:, 0].argmax()].copy()
translation[2] = 0
for ob in objects.values():
    for vertex in ob.data.vertices:
        vertex.co += Vector(translation)
    ob.data.update()
for material in bpy.data.materials:
    if material.use_nodes and 'Anatomical texture origin' in material.node_tree.nodes:
        material.node_tree.nodes['Anatomical texture origin'].inputs[1].default_value = tuple(translation)

def mat(name, rgb, rough=.5):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    node = material.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*rgb, 1)
    node.inputs['Roughness'].default_value = rough
    return material

skin_mat = mat('Continuous skin', (.43, .27, .19), .53)
mucosa_mat = mat('Continuous perioral mucosa', (.43, .13, .11), .42)
lip_mat = mat('Vermilion pigment', (.36, .10, .085), .43)

def create(name, points, faces, material, uv=None, face_uv=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if uv and face_uv:
        layer = mesh.uv_layers.new(name='Source UV')
        for polygon, ids in zip(mesh.polygons, face_uv):
            for loop, index in zip(polygon.loop_indices, ids):
                if index >= 0:
                    layer.data[loop].uv = uv[index]
    return ob

body = head['groups']['body']
islands = uv_islands(head, body)
oral_candidates = []
for faces in islands:
    q = head['canonicalPoints'][sorted({i for fi in faces for i in head['faces'][fi]})]
    if len(faces) == 398 and q[:, 0].min() > .04 and q[:, 1].max() < .09:
        oral_candidates.append(faces)
assert len(oral_candidates) == 1
oral_faces = set(oral_candidates[0])
oral_ids = {i for fi in oral_faces for i in head['faces'][fi]}
external_ids = {i for fi in body if fi not in oral_faces for i in head['faces'][fi]}
rim = head['canonicalPoints'][sorted(oral_ids & external_ids)]
vestibule_limit = .1383
assert rim[:, 0].min() > vestibule_limit, 'Do not move the visible lip rim'
for i in oral_ids - external_ids:
    x, y, z = head['canonicalPoints'][i]
    if x < vestibule_limit:
        blend = min(1, (vestibule_limit - x) / .006)
        head['canonicalPoints'][i, 0] = vestibule_limit - (vestibule_limit - x) * .05
        head['canonicalPoints'][i, 1] = y + blend * .40 * (.0316 - y)
# This keeps the original connected lip vestibule and replaces the unrelated
# deep MakeHuman oral bag with the actual atlas-guided oral context below.
skin = create('HEAD_SKIN', head['canonicalPoints'], [head['faces'][fi] for fi in body], skin_mat,
              head['uv'], [head['face_uv'][fi] for fi in body])
skin.data.materials.append(mucosa_mat)
skin.data.materials.append(lip_mat)
for poly, fi in zip(skin.data.polygons, body):
    if fi in oral_faces:
        poly.material_index = 1
    elif any(np.linalg.norm(head['canonicalPoints'][i] - rim, axis=1).min() < .003 for i in poly.vertices):
        poly.material_index = 2
bm = bmesh.new()
bm.from_mesh(skin.data)
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-8,
                      plane_co=(0, -.120, 0), plane_no=(0, -1, 0), clear_outer=True)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(skin.data)
bm.free()
bpy.ops.object.select_all(action='DESELECT')
skin.select_set(True)
bpy.context.view_layer.objects.active = skin
sub = skin.modifiers.new('Original continuous skin refinement', 'SUBSURF')
sub.levels = sub.render_levels = 1
bpy.ops.object.modifier_apply(modifier=sub.name)
bm = bmesh.new()
bm.from_mesh(skin.data)
boundaries = [e for e in bm.edges if e.is_boundary]
assert all(abs(v.co.y + .120) < 1e-6 for e in boundaries for v in e.verts), 'Unexpected skin opening'
bmesh.ops.holes_fill(bm, edges=boundaries, sides=0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(skin.data)
bm.free()

eye = makehuman_eye_data(head)
eye_mat = mat('Original CC0 eyes', (1, 1, 1), .3)
texture = eye_mat.node_tree.nodes.new('ShaderNodeTexImage')
texture.image = bpy.data.images.load(str(ROOT / 'assets/source/makehuman/makehuman/data/eyes/materials/brown_eye.png'))
texture.image.pack()
bs = eye_mat.node_tree.nodes.get('Principled BSDF')
eye_mat.node_tree.links.new(texture.outputs['Color'], bs.inputs['Base Color'])
eye_mat.node_tree.links.new(texture.outputs['Alpha'], bs.inputs['Alpha'])
eyes = create('EYES', eye['canonicalPoints'], eye['faces'], eye_mat, eye['uv'], eye['face_uv'])

# Negative spaces come from the original atlas mucosal surfaces themselves.
# Caps close only temporary air-space helpers; they never become visible organs.
construction = json.loads((ROOT / 'assets/source/z-anatomy/construction-surfaces.json').read_text())['parts']
spaces = []
# The context void follows actual tongue/gingiva/velar points. These organs
# remain visible positive tissues inside it. It is not a substitute organ.
oral_points = [list(v.co) for name in ['ATLAS_TONGUE', 'ATLAS_GINGIVA', 'ATLAS_SOFT_PALATE'] for v in objects[name].data.vertices]
bm = bmesh.new()
for co in oral_points:
    bm.verts.new(co)
hull = bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
unused = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=unused, context='VERTS')
bmesh.ops.triangulate(bm, faces=list(bm.faces))
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
mesh = bpy.data.meshes.new('Source oral context envelope')
bm.to_mesh(mesh); bm.free(); mesh.update(); mesh.calc_loop_triangles()
spaces.append({'name': 'Oral context envelope', 'positions': [c for v in mesh.vertices for c in v.co],
    'indices': [i for tri in mesh.loop_triangles for i in tri.vertices],
    'role': 'Negative context envelope of actual tongue, gingiva and velum; positive organs remain unchanged',
    'clinicalMeasurement': False})
bpy.data.meshes.remove(mesh)
# Bridge the original source pharyngeal surface openings as one coherent
# negative context corridor. Actual pharyngeal walls, tongue and epiglottis
# remain positive anatomy defining its visible boundaries.
pharynx_points = [co for source_name in ['Nasopharynx', 'Oropharynx', 'Laryngopharynx']
    for co in np.array(construction[source_name]['positions']).reshape(-1, 3) + translation]
bm = bmesh.new()
for co in pharynx_points:
    bm.verts.new(co)
bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
front_limit = min(v.co.x for v in objects['ATLAS_TONGUE'].data.vertices) + .012
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-9,
    plane_co=(front_limit, 0, 0), plane_no=(1, 0, 0), clear_outer=True)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
bmesh.ops.triangulate(bm, faces=list(bm.faces)); bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
mesh = bpy.data.meshes.new('Source pharyngeal context corridor'); bm.to_mesh(mesh); bm.free(); mesh.update(); mesh.calc_loop_triangles()
spaces.append({'name': 'Connected source pharyngeal context', 'positions': [c for v in mesh.vertices for c in v.co],
    'indices': [i for tri in mesh.loop_triangles for i in tri.vertices], 'anteriorReferenceX_m': front_limit,
    'role': 'Negative corridor from actual source pharyngeal points; positive walls and tongue define visible tissue', 'clinicalMeasurement': False})
bpy.data.meshes.remove(mesh)
subprocess.run([str(ROOT / '.venv-qa/bin/python'), str(ROOT / 'tools/anatomy/prepare_nasal_envelope.py'), '--folder', str(OUT)], check=True)
nasal_spaces = json.loads((OUT / 'source-nasal-envelope.json').read_text())['spaces']
for space in nasal_spaces:
    points = np.array(space['positions']).reshape(-1, 3) + translation
    spaces.append({**space, 'positions': points.ravel().tolist(), 'role': 'Source-guided negative macro space; actual nasal tissues retained'})
construction.update(json.loads((OUT / 'reconstructed-lumens.json').read_text()))
for source_name in ['Nasopharynx', 'Oropharynx', 'Laryngopharynx', 'Trachea']:
    sides = [0]
    for side in sides:
        data = construction[source_name]
        points = np.array(data['positions']).reshape(-1, 3)
        mesh = bpy.data.meshes.new(source_name + ' actual airspace')
        mesh.from_pydata(points, [], data['faces'])
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if source_name == 'Trachea':
            # The source narrows into a distant cut endpoint. Retain only the
            # proximal airway, extended below the delivered neck boundary.
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-9,
                                  plane_co=(0, -.155, 0), plane_no=(0, -1, 0), clear_outer=True)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        if side:
            # Exclude the source's overlapping median mirror sheet. The source
            # septal cartilage/mucosa remain real tissues separating the sides.
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-9,
                                  plane_co=(0, 0, side * .00035), plane_no=(0, 0, -side), clear_outer=True)
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        assert all(e.is_manifold for e in bm.edges), f'Unclosed source airspace: {source_name}/{side}'
        if bm.calc_volume(signed=True) < 0:
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        for v in bm.verts:
            v.co += Vector(translation)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        repair = None
        if source_name in ['Oropharynx', 'Trachea']:
            # Its folded anterior boundary creates intersecting closure slivers.
            # Reconstruct only this negative helper's volume at 0.40 mm; retain
            # the actual original positive pharyngeal wall without reshaping it.
            ob = bpy.data.objects.new('Temporary source airspace repair', mesh)
            bpy.context.collection.objects.link(ob)
            bpy.context.view_layer.objects.active = ob
            bm = bmesh.new(); bm.from_mesh(mesh); before_volume = bm.calc_volume(signed=True); bm.free()
            modifier = ob.modifiers.new('Folded airspace closure repair', 'REMESH')
            modifier.mode = 'VOXEL'; modifier.voxel_size = .00040; modifier.adaptivity = .18
            modifier.use_remove_disconnected = False
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            mesh = ob.data
            mesh.calc_loop_triangles()
            reduce = ob.modifiers.new('Bounded helper surface reduction', 'DECIMATE')
            reduce.ratio = min(1, 8000 / len(mesh.loop_triangles))
            bpy.ops.object.modifier_apply(modifier=reduce.name)
            smooth = ob.modifiers.new('Resolve subvoxel closure pinches', 'SMOOTH')
            smooth.factor = .35; smooth.iterations = 3
            bpy.ops.object.modifier_apply(modifier=smooth.name)
            mesh = ob.data
            bm = bmesh.new(); bm.from_mesh(mesh)
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
            bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-7)
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(mesh); bm.free(); mesh.update()
            bm = bmesh.new(); bm.from_mesh(mesh); after_volume = bm.calc_volume(signed=True); bm.free()
            assert .80 < after_volume / before_volume < 1.25, 'Airspace reconstruction changed source volume materially'
            repair = {'voxelSize_m': .00040, 'maximumHelperTriangles': 8000, 'subvoxelSmoothing': {'factor': .35, 'iterations': 3}, 'beforeSignedVolume_m3': before_volume, 'afterVolume_m3': after_volume}
            bpy.data.objects.remove(ob, do_unlink=True)
        mesh.calc_loop_triangles()
        spaces.append({'name': source_name + (' right' if side == 1 else ' left' if side == -1 else ''),
                       'positions': [c for v in mesh.vertices for c in v.co],
                       'indices': [i for t in mesh.loop_triangles for i in t.vertices],
                       'role': 'Source-surface negative space, not visible anatomy', 'closureRepair': repair})
        bpy.data.meshes.remove(mesh)
(OUT / 'atlas-airspaces.json').write_text(json.dumps({'spaces': spaces}, separators=(',', ':')) + '\n')
subprocess.run([str(ROOT / '.venv-qa/bin/python'), str(ROOT / 'tools/qa/check_atlas_airspaces.py'), '--folder', str(OUT)], check=True)

# Transfer the original skin with per-corner UVs to the robust volume engine.
old = skin.data
old.calc_loop_triangles()
properties, faces, material_ids = [], [], []
uv = old.uv_layers.active
for tri in old.loop_triangles:
    face = []
    for vertex, loop in zip(tri.vertices, tri.loops):
        face.append(len(properties))
        properties.append([*old.vertices[vertex].co, *uv.data[loop].uv])
    faces.append(face)
    material_ids.append(tri.material_index)
(OUT / 'head-before-cavities.json').write_text(json.dumps({'properties': properties, 'faces': faces, 'materialIds': material_ids}, separators=(',', ':')) + '\n')
subprocess.run([str(ROOT / '.venv-qa/bin/python'), str(ROOT / 'tools/anatomy/robust_head_boolean.py'), '--folder', str(OUT)], check=True)
result = json.loads((OUT / 'head-boolean-result.json').read_text())
props = np.array(result['properties'])
# Preserve the volume engine's property seams; UV topology is checked separately
# from positional topology by the independent delivered-GLB evaluator.
mesh = bpy.data.meshes.new('Continuous anatomical head with actual atlas cavities')
mesh.from_pydata(props[:, :3].tolist(), [], result['faces'])
mesh.update()
for material in old.materials:
    mesh.materials.append(material)
layer = mesh.uv_layers.new(name='Source skin and cavity UV')
for polygon, material_id in zip(mesh.polygons, result['materialIds']):
    polygon.material_index = material_id
    polygon.use_smooth = True
    for vertex, loop in zip(polygon.vertices, polygon.loop_indices):
        layer.data[loop].uv = props[vertex, 3:5]
skin.data = mesh
bpy.data.meshes.remove(old)
operations = result['operations']
objects.update(HEAD_SKIN=skin, EYES=eyes)
records['HEAD_SKIN'] = {'sourceObjectName': 'MakeHuman continuous adult head and fitted oral vestibule', 'sourceKind': 'CC0 source head, authored rigid dental fit and source-based cavities', 'materialClass': 'skin', 'neckContextCropY_m': -.120,
    'oralVestibuleFit': {'visibleRimUnchanged': True, 'posteriorLimitX_m': vestibule_limit, 'posteriorDepthScale': .05, 'heightScale': .60, 'sourceAtlasReplacesDeepBag': True}}
records['EYES'] = {'sourceObjectName': 'MakeHuman eyes fitted using original MHCLO', 'sourceKind': 'CC0 eyes/texture', 'materialClass': 'eyes'}
for ob in [skin, eyes]:
    ob['sourceLicense'] = 'CC0-1.0; original MakeHuman asset notices retained'
scene = bpy.context.scene
scene['status'] = 'Rebuilt coherent anatomy and fitted continuous head; visual/structural acceptance pending'
scene['modelDataLicense'] = 'CC-BY-SA-4.0 for adapted atlas model data; CC0 head/eyes components'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'atlas-study.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in objects.values():
    ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / 'atlas-study.glb'), export_format='GLB', use_selection=True,
                          export_yup=False, export_apply=True, export_extras=True, export_animations=False)
parts = {}
for name, ob in objects.items():
    ob.data.calc_loop_triangles()
    parts[name] = {'positions': [c for v in ob.data.vertices for c in v.co], 'indices': [i for tri in ob.data.loop_triangles for i in tri.vertices], 'source': records[name]}
(OUT / 'atlas-meshes.json').write_text(json.dumps({'parts': parts}, separators=(',', ':')) + '\n')
record = {**old_manifest, 'parts': records, 'atlasPlacement': {'translation_m': translation.tolist(), 'uniformScale': 1,
            'relativeInternalPlacementPreserved': True, 'clinicalRegistration': False},
          'headSource': 'Original CC0 MakeHuman asset snapshot, mouth authoring weight0.12; no program code copied',
          'headCavityOperations': operations, 'headBooleanVerification': result['verification'],
          'glbSha256': hashlib.sha256((OUT / 'atlas-study.glb').read_bytes()).hexdigest(),
          'blendSha256': hashlib.sha256((OUT / 'atlas-study.blend').read_bytes()).hexdigest(), 'status': scene['status']}
(OUT / 'atlas-study.manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print('FITTED_REALISTIC_HEAD', json.dumps({'parts': len(parts), 'translation_m': translation.tolist(), 'airspaces': len(spaces)}))
