"""Actual multi-organ morph export, attachment and collapse diagnostics.

Does not grant medical, visual, phonetic or general contact acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/method-evidence/oral-sculpt')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder = ROOT/a.folder
manifest = json.loads((folder/'oral-manifest.json').read_text())
for ext in ['blend', 'glb']:
    assert hashlib.sha256((folder/('oral-unit.'+ext)).read_bytes()).hexdigest() == manifest[ext+'Sha256']
cases = [('rest', {})]
for name in ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT', 'JAW_OPEN', 'VELUM_RAISE']:
    for value in [.5, 1]:
        cases.append((name+'_'+str(value), {name: value}))
cases += [('combined', {'JAW_OPEN': .75, 'TIP_ELEVATE': .7, 'DORSUM_ELEVATE': .2, 'VELUM_RAISE': .5}), ('return', {})]
failures = []


def set_state(objects, values, native_drivers):
    for ob in objects.values():
        keys = ob.data.shape_keys
        if not keys:
            continue
        if native_drivers:
            if keys.animation_data:
                keys.animation_data.action = None
        else:
            keys.animation_data_clear()
        for key in keys.key_blocks[1:]:
            if key.name.startswith('JAW_X_'):
                if not native_drivers:
                    left, right = manifest['correctives'][key.name]
                    key.value = values.get(left, 0)*values.get(right, 0)
            else:
                key.value = values.get(key.name, 0)
        keys.update_tag()
    if not native_drivers:
        jaw = bpy.data.objects[manifest['jawBinding']['node']]
        jaw.animation_data_clear()
        jaw.rotation_mode = 'XYZ'
        jaw.rotation_euler.x = values.get('JAW_OPEN', 0)*manifest['jawBinding']['angle_radians']
    bpy.context.view_layer.update()


def snapshot(ob):
    evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = evaluated.to_mesh()
    pts = [evaluated.matrix_world@v.co for v in me.vertices]
    polys = [list(face.vertices) for face in me.polygons]
    me.calc_loop_triangles()
    triangles = np.array([tri.vertices for tri in me.loop_triangles], dtype=np.int32)
    array = np.array(pts, dtype=np.float64)
    signed_volume = float(np.einsum('ij,ij->i', array[triangles[:, 0]],
                                    np.cross(array[triangles[:, 1]], array[triangles[:, 2]])).sum()/6)
    evaluated.to_mesh_clear()
    return {'points': pts, 'polygons': polys, 'volume_m3': signed_volume}


def distance(a, b):
    tree = KDTree(len(b))
    for i, point in enumerate(b):
        tree.insert(point, i)
    tree.balance()
    return max(tree.find(point)[2] for point in a)


bpy.ops.wm.open_mainfile(filepath=str(folder/'oral-unit.blend'), use_scripts=False, load_ui=False)
objects = {name: bpy.data.objects[name] for name in manifest['parts']}
topology = {}
for name in ['TONGUE', 'ORAL_FLOOR', 'LINGUAL_FRENULUM', 'PALATE']:
    bm = bmesh.new()
    bm.from_mesh(objects[name].data)
    topology[name] = {'boundaryEdges': sum(e.is_boundary for e in bm.edges),
                      'nonmanifoldEdges': sum(not e.is_manifold for e in bm.edges)}
    bm.free()
    if any(topology[name].values()):
        failures.append(name+': authored tissue is not closed/manifold')
source, seam = {}, []
for label, values in cases:
    set_state(objects, values, True)
    source[label] = {name: snapshot(ob) for name, ob in objects.items()}
    tongue = source[label]['TONGUE']
    bvh = BVHTree.FromPolygons(tongue['points'], tongue['polygons'])
    inner = source[label]['ORAL_FLOOR']['points'][:128]
    gap = max(bvh.find_nearest(point)[3] for point in inner)
    seam.append({'case': label, 'maximumRootFloorGap_m': gap})
    if gap > .0002:
        failures.append(label+': root/floor gap exceeds 0.2 mm')
    if tongue['volume_m3'] <= 0:
        failures.append(label+': inverted/collapsed tongue volume')
source_shapes = {name: [k.name for k in ob.data.shape_keys.key_blocks][1:] if ob.data.shape_keys else [] for name, ob in objects.items()}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(folder/'oral-unit.glb'))
objects = {name: bpy.data.objects.get(name) for name in manifest['parts']}
if any(ob is None for ob in objects.values()):
    raise RuntimeError('An exported anatomical part did not arrive')
mesh_names = {ob.name for ob in bpy.context.scene.objects if ob.type == 'MESH'}
if mesh_names != set(objects):
    failures.append('Unexpected or missing delivery meshes')
for name, ob in objects.items():
    actual = [k.name for k in ob.data.shape_keys.key_blocks][1:] if ob.data.shape_keys else []
    if actual != source_shapes[name]:
        failures.append(name+': morph names/order changed')
comparisons = []
for label, values in cases:
    set_state(objects, values, False)
    record = {'case': label, 'controls': values, 'partErrors_m': {}}
    for name, ob in objects.items():
        actual = snapshot(ob)['points']
        expected = source[label][name]['points']
        error = max(distance(actual, expected), distance(expected, actual))
        record['partErrors_m'][name] = error
        if error > 2e-6:
            failures.append(label+'/'+name+': GLB geometry deviation exceeds 2 micrometres')
    volume = source[label]['TONGUE']['volume_m3']
    rigid = snapshot(objects['LOWER_DENTITION'])['points']
    original = source['rest']['LOWER_DENTITION']['points']
    rigid_error = abs((rigid[0]-rigid[-1]).length-(original[0]-original[-1]).length)
    record['lowerDentalArchDistanceDrift_m'] = rigid_error
    if rigid_error > 2e-6:
        failures.append(label+': rigid dental arch changed dimensions')
    record['tongueVolumeChangeFraction'] = volume/source['rest']['TONGUE']['volume_m3']-1
    if abs(record['tongueVolumeChangeFraction']) > .05:
        failures.append(label+': severe volume loss/expansion')
    comparisons.append(record)
report = {'scope': 'Closed authored tissues, measured root/floor seam and actual multi-organ GLB morph geometry',
          'clinicalAcceptance': 'not assessed', 'generalDentalContactReview': 'pending',
          'volumeConservingSimulation': False, 'productionSelected': False,
          'blendSha256': manifest['blendSha256'], 'glbSha256': manifest['glbSha256'],
          'topology': topology, 'rootFloorSeam': seam, 'cases': comparisons,
          'correctiveMapping': manifest['correctives'],
          'maximumExportError_m': max(v for row in comparisons for v in row['partErrors_m'].values()),
          'failures': failures, 'technicalPass': not failures}
(folder/'technical-review.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'technicalPass': not failures, 'cases': len(cases),
                  'maxExportError_m': report['maximumExportError_m'],
                  'maxRootFloorGap_m': max(row['maximumRootFloorGap_m'] for row in seam),
                  'failures': failures}, indent=2))
if failures:
    raise RuntimeError('Oral-sculpt technical review failed')
