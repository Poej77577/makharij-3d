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
cases += [('combined', {'JAW_OPEN': .75, 'TIP_ELEVATE': .7, 'DORSUM_ELEVATE': .2, 'VELUM_RAISE': .5}),
          ('jaw_velum', {'JAW_OPEN': .5, 'VELUM_RAISE': 1}),
          ('dorsum_velum', {'DORSUM_ELEVATE': 1, 'VELUM_RAISE': 1}),
          ('root_velum', {'ROOT_RETRACT': 1, 'VELUM_RAISE': 1}), ('return', {})]
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


def sampled_inside_closed_surface(bvh, point):
    """Three deterministic parity rays, only used for verified closed gum."""
    if bvh.find_nearest(point)[3] <= 2e-6:
        return True
    votes = 0
    for direction in [Vector((1, .371, .173)), Vector((-.293, .511, 1)), Vector((.421, -1, .257))]:
        direction.normalize()
        origin = point.copy()
        hits = 0
        for _ in range(128):
            hit, _, _, _ = bvh.ray_cast(origin, direction, 1.)
            if hit is None:
                break
            hits += 1
            origin = hit+direction*1e-7
        else:
            raise RuntimeError('Unresolved interface classification ray; did not reach free space')
        votes += hits % 2
    return votes >= 2


bpy.ops.wm.open_mainfile(filepath=str(folder/'oral-unit.blend'), use_scripts=False, load_ui=False)
objects = {name: bpy.data.objects[name] for name in manifest['parts']}
topology = {}
for name in ['TONGUE', 'ORAL_FLOOR', 'LINGUAL_FRENULUM', 'PALATE', 'UPPER_GINGIVA', 'LOWER_GINGIVA']:
    bm = bmesh.new()
    bm.from_mesh(objects[name].data)
    topology[name] = {'boundaryEdges': sum(e.is_boundary for e in bm.edges),
                      'nonmanifoldEdges': sum(not e.is_manifold for e in bm.edges)}
    bm.free()
    if any(topology[name].values()):
        failures.append(name+': authored tissue is not closed/manifold')
source, seam, additional_attachments = {}, [], []
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
    attachment = {'case': label}
    web = manifest.get('frenulumAttachment')
    if web:
        floor_snapshot = source[label]['ORAL_FLOOR']
        floor_bvh = BVHTree.FromPolygons(floor_snapshot['points'], floor_snapshot['polygons'])
        web_points = source[label]['LINGUAL_FRENULUM']['points']
        top = max(bvh.find_nearest(web_points[i])[3] for i in web['tongueVertices'])
        bottom = max(floor_bvh.find_nearest(web_points[i])[3] for i in web['floorVertices'])
        attachment.update(frenulumTongueMaximumSurfaceDistance_m=top, frenulumFloorMaximumSurfaceDistance_m=bottom)
        if top > .0003 or bottom > .0003:
            failures.append(label+': sampled frenulum attachment exceeds 0.3 mm')
    roof = manifest.get('oralRoofAuthoring', {}).get('posteriorSoftPalate')
    if roof:
        grid = roof['deformationGrid']
        ids = [offset+j for offset in [0, grid['verticesPerLayer']] for j in range(grid['transverseSegments']+1)]
        palate = source[label]['PALATE']['points']
        rest = source['rest']['PALATE']['points']
        drift = max((palate[i]-rest[i]).length for i in ids)
        upper = source[label]['UPPER_GINGIVA']
        gum_bvh = BVHTree.FromPolygons(upper['points'], upper['polygons'])
        samples = [palate[i] for i in ids]
        samples += [(palate[j]+palate[grid['verticesPerLayer']+j])*.5 for j in range(grid['transverseSegments']+1)]
        proximity = max(gum_bvh.find_nearest(p)[3] for p in samples)
        if any(topology['UPPER_GINGIVA'].values()):
            raise RuntimeError('Cannot classify interface samples against an open upper gingival surface')
        outside = [p for p in samples if not sampled_inside_closed_surface(gum_bvh, p)]
        attachment.update(velumAnteriorPinnedMaximumDrift_m=drift,
                          palatalMucosalInterfaceMaximumSurfaceDistance_m=proximity,
                          palatalMucosalInterfaceSamples=len(samples),
                          palatalMucosalInterfaceSampledOutsideCount=len(outside),
                          palatalMucosalInterfaceMaximumOutsideDistance_m=max((gum_bvh.find_nearest(p)[3] for p in outside), default=0))
        if drift > 2e-6 or outside:
            failures.append(label+': posterior palate attachment moved or sampled points left the closed source mucosa')
    additional_attachments.append(attachment)
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
          'additionalAttachmentSamples': additional_attachments,
          'attachmentScope': 'Unsigned nearest distances of sampled interfaces; intentional overlap is not welded continuity',
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
