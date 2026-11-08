"""Actual external-face/dental SURFACE checks. The head is intentionally OPEN.

No contains(), signed-solid-distance, tissue-volume or penetration-depth claims.
Both actual GLBs are evaluated in one frame with one shared jaw state; the face
receives its baked skin morph, and only the oral jaw pivot rotates rigid teeth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import fcl
import numpy as np
import trimesh

from oral_contacts import collision_object, mesh_from, bounded_rows, dental_labels

ROOT = Path(__file__).resolve().parents[2]
CASES = [('rest', {})]
for key in ['JAW_OPEN', 'LIP_PRESS', 'LIP_ROUND', 'LIP_PROTRUDE']:
    for value in [.5, 1]:
        CASES.append((key+'_'+str(value), {key: value}))
CASES.append(('combined_jaw_lips', {'JAW_OPEN': .5, 'LIP_PRESS': .5, 'LIP_ROUND': .5, 'LIP_PROTRUDE': .5}))

EXPORTER = r'''
import bpy, json, sys
from pathlib import Path
import numpy as np
config = json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=config['oral'])
oral_objects = {name: bpy.data.objects[name] for name in ['UPPER_DENTITION', 'LOWER_DENTITION']}
jaw = bpy.data.objects[config['oralManifest']['jawBinding']['node']]
bpy.ops.import_scene.gltf(filepath=config['face'])
head = bpy.data.objects.get('HEAD_EXTERNAL')
if head is None:
    raise RuntimeError('HEAD_EXTERNAL did not arrive from actual face GLB')
required_face_controls = {'JAW_OPEN', 'LIP_PRESS', 'LIP_ROUND', 'LIP_PROTRUDE'}
actual_face_controls = set(key.name for key in head.data.shape_keys.key_blocks) if head.data.shape_keys else set()
if not required_face_controls <= actual_face_controls:
    raise RuntimeError('Actual face GLB lacks required morph controls: '+str(required_face_controls-actual_face_controls))
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH' and ob.data.shape_keys:
        ob.data.shape_keys.animation_data_clear()
jaw.animation_data_clear()
jaw.rotation_mode = 'XYZ'
metadata = []
reference_points = {}
for index, (label, values) in enumerate(config['cases']):
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or not ob.data.shape_keys:
            continue
        for key in ob.data.shape_keys.key_blocks[1:]:
            pair = config['oralManifest']['correctives'].get(key.name)
            key.value = values.get(pair[0], 0)*values.get(pair[1], 0) if pair else values.get(key.name, 0)
        ob.data.shape_keys.update_tag()
    # Exactly one rigid dental rotation; the face's JAW_OPEN skin key above
    # already owns skin motion and is not parented/rotated around this pivot.
    jaw.rotation_euler.x = values.get('JAW_OPEN', 0)*config['oralManifest']['jawBinding']['angle_radians']
    bpy.context.view_layer.update()
    arrays = {}
    movement = {}
    for name, original in {'HEAD_EXTERNAL': head, **oral_objects}.items():
        ob = original.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = ob.to_mesh()
        mesh.calc_loop_triangles()
        native = [ob.matrix_world@vertex.co for vertex in mesh.vertices]
        arrays[name+'_vertices'] = np.array([(-v.y, v.z, -v.x) for v in native], dtype=np.float64)
        if index == 0:
            reference_points[name] = arrays[name+'_vertices'].copy()
        movement[name] = float(np.linalg.norm(arrays[name+'_vertices']-reference_points[name], axis=1).max())
        arrays[name+'_faces'] = np.array([tri.vertices for tri in mesh.loop_triangles], dtype=np.int32)
        ob.to_mesh_clear()
    filename = str(Path(config['cache'])/('pose-%02d.npz'%index))
    np.savez_compressed(filename, **arrays)
    if values and movement['HEAD_EXTERNAL'] < 1e-7:
        raise RuntimeError('Requested face pose produced no actual surface movement: '+label)
    if values.get('JAW_OPEN', 0) > 0 and movement['LOWER_DENTITION'] < 1e-7:
        raise RuntimeError('Shared jaw state did not move lower dental surface')
    if values.get('JAW_OPEN', 0) == 0 and movement['LOWER_DENTITION'] > 1e-7:
        raise RuntimeError('Lip control unexpectedly moved rigid lower dentition')
    if movement['UPPER_DENTITION'] > 1e-7:
        raise RuntimeError('Upper dental surface unexpectedly moved')
    metadata.append({'case': label, 'controls': values, 'file': filename, 'maximumDisplacementFromRest_m': movement})
Path(config['cache'], 'poses.json').write_text(json.dumps(metadata, indent=2)+'\n')
'''


def open_surface_self_test():
    plane = trimesh.Trimesh([[0, -2, -2], [0, 2, -2], [0, 2, 2], [0, -2, 2]], [[0, 1, 2], [0, 2, 3]], process=False)
    separated = trimesh.creation.box(extents=[2., 2., 2.])
    separated.apply_translation([2, 0, 0])
    p, c = collision_object(plane), collision_object(separated)
    result = fcl.CollisionResult()
    fcl.collide(p, c, fcl.CollisionRequest(enable_contact=True), result)
    distance = fcl.distance(p, c, fcl.DistanceRequest(), fcl.DistanceResult())
    assert not result.is_collision and abs(distance-1) < 1e-10
    crossing = trimesh.creation.box(extents=[2., 2., 2.])
    crossing.apply_translation([.5, 0, 0])
    result = fcl.CollisionResult()
    fcl.collide(p, collision_object(crossing), fcl.CollisionRequest(num_max_contacts=32, enable_contact=True), result)
    assert result.is_collision and len(result.contacts) > 0
    return {'passed': True, 'fixture': 'Known open two-triangle plane and triangulated box surfaces',
            'separatedDistance_m': float(distance), 'crossingDetected': True,
            'insideOrVolumeTestsRun': False, 'penetrationDepthClaimed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--face-folder', type=Path, default=ROOT/'artifacts/method-evidence/face-context')
    parser.add_argument('--oral-folder', type=Path, default=ROOT/'artifacts/method-evidence/oral-sculpt')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--contact-limit', type=int, default=4000)
    parser.add_argument('--gate', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(open_surface_self_test(), indent=2))
        return
    face_folder, oral_folder = args.face_folder.resolve(), args.oral_folder.resolve()
    face_path, oral_path = face_folder/'face-context.glb', oral_folder/'oral-unit.glb'
    face_manifest = json.loads((face_folder/'face-manifest.json').read_text())
    oral_manifest = json.loads((oral_folder/'oral-manifest.json').read_text())
    face_hash, oral_hash = [hashlib.sha256(p.read_bytes()).hexdigest() for p in [face_path, oral_path]]
    assert face_hash == face_manifest['glbSha256'], 'Face build not yet consistent with manifest'
    assert oral_hash == oral_manifest['glbSha256'], 'Oral identity differs from manifest'
    assert face_manifest['oralSourceGlbSha256'] == oral_hash, 'Face authoring source pairs with another oral GLB'
    assert face_manifest['contextSurfaceOnly'] is True, 'Open context-surface contract changed'
    for manifest in [face_manifest, oral_manifest]:
        assert manifest['gltfToProject'] == [[0, 0, 1], [0, 1, 0], [-1, 0, 0]], 'Unsupported common frame'
    if args.contact_limit < 1:
        raise ValueError('Contact budget must be positive')
    pair_id = face_hash[:16]+'-'+oral_hash[:12]
    case_hash = hashlib.sha256(json.dumps([CASES, oral_manifest['correctives'], oral_manifest['jawBinding'], EXPORTER], sort_keys=True).encode()).hexdigest()[:12]
    cache = Path('/workspace/research/face-contact-review')/pair_id/case_hash
    cache.mkdir(exist_ok=True, parents=True)
    for source, name, digest in [(face_path, 'face.glb', face_hash), (oral_path, 'oral.glb', oral_hash)]:
        frozen = cache/name
        if not frozen.exists():
            shutil.copyfile(source, frozen)
        assert hashlib.sha256(frozen.read_bytes()).hexdigest() == digest
    out = args.out or face_folder/'contact-review'
    previous = out/'face-contacts.json'
    if previous.exists():
        old = json.loads(previous.read_text())
        if old.get('faceAssetSha256') != face_hash or old.get('oralAssetSha256') != oral_hash:
            out = out/pair_id
    out.mkdir(exist_ok=True, parents=True)
    config = cache/'export.json'
    config.write_text(json.dumps({'face': str(cache/'face.glb'), 'oral': str(cache/'oral.glb'),
                                 'oralManifest': oral_manifest, 'cases': CASES, 'cache': str(cache)}, indent=2))
    exporter = cache/'export_face_poses.py'
    exporter.write_text(EXPORTER)
    if not (cache/'poses.json').exists():
        with (cache/'blender-export.log').open('w') as log:
            subprocess.run(['blender', '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                            '--python-exit-code', '1', '--python', str(exporter), '--', str(config)],
                           stdout=log, stderr=subprocess.STDOUT, check=True, cwd=ROOT)
    poses = json.loads((cache/'poses.json').read_text())
    source = json.loads((ROOT/'assets/source/z-anatomy/reference-meshes.json').read_text())['parts']
    rest = np.load(poses[0]['file'])
    labels, assignments = {}, {}
    for arch in ['UPPER_DENTITION', 'LOWER_DENTITION']:
        labels[arch], assignments[arch] = dental_labels(mesh_from(rest, arch), arch, source)
    records = []
    for pose in poses:
        data = np.load(pose['file'])
        head = mesh_from(data, 'HEAD_EXTERNAL')
        head_object = collision_object(head)
        for arch in ['UPPER_DENTITION', 'LOWER_DENTITION']:
            teeth = mesh_from(data, arch)
            teeth_object = collision_object(teeth)
            result = fcl.CollisionResult()
            fcl.collide(head_object, teeth_object, fcl.CollisionRequest(num_max_contacts=args.contact_limit, enable_contact=True), result)
            distance_result = fcl.DistanceResult()
            minimum = fcl.distance(head_object, teeth_object, fcl.DistanceRequest(enable_nearest_points=True), distance_result)
            contacts = result.contacts
            points = np.array([contact.pos for contact in contacts])
            triangle_ids = np.unique([contact.b2 for contact in contacts if 0 <= contact.b2 < len(teeth.faces)]).astype(np.int64)
            nearest = np.array(distance_result.nearest_points) if minimum >= 0 and not result.is_collision else np.empty((0, 3))
            nearest_tooth = None
            if nearest.shape == (2, 3) and np.isfinite(nearest).all():
                _, _, tri = teeth.nearest.on_surface(nearest[1:2])
                nearest_tooth = str(labels[arch][int(tri[0])])
            row = {'case': pose['case'], 'controls': pose['controls'], 'pair': ['HEAD_EXTERNAL', arch],
                   'maximumDisplacementFromRest_m': pose['maximumDisplacementFromRest_m'],
                   'surfaceCrossing': bool(result.is_collision), 'triangleContactCount': len(contacts),
                   'contactLimitHit': len(contacts) >= args.contact_limit,
                   'minimumSurfaceDistance_m': float(minimum) if minimum >= 0 else None,
                   'crossingTeeth': sorted(set(str(labels[arch][i]) for i in triangle_ids)),
                   'crossingBounds_m': [points.min(0).tolist(), points.max(0).tolist()] if len(points) else None,
                   'crossingWitnesses_m': bounded_rows(points, 24).tolist() if len(points) else [],
                   'closestSurfacePoints_m': nearest.tolist() if nearest.shape == (2, 3) and np.isfinite(nearest).all() else None,
                   'closestTooth': nearest_tooth,
                   'headSurfaceIntentionallyOpen': True, 'insideOrVolumeTestsRun': False,
                   'penetrationDepthClaimed': False}
            records.append(row)
            temp = out/'progress.json.tmp'
            temp.write_text(json.dumps({'faceAssetSha256': face_hash, 'oralAssetSha256': oral_hash,
                                        'complete': False, 'records': records}, indent=2)+'\n')
            temp.replace(out/'progress.json')
            print(json.dumps({'case': pose['case'], 'arch': arch, 'crossing': row['surfaceCrossing'],
                              'contacts': len(contacts), 'distance_mm': None if minimum < 0 else minimum*1000}), flush=True)
    passed = all(not row['surfaceCrossing'] and not row['contactLimitHit'] for row in records)
    report = {'faceAssetSha256': face_hash, 'oralAssetSha256': oral_hash, 'cases': len(poses),
              'pairsChecked': len(records), 'frame': '+X anterior, +Y superior, +Z subject right; metres',
              'sharedJawState': 'One JAW_OPEN state; oral rigid pivot once, separate baked face-skin morph once',
              'headSurfaceIntentionallyOpen': True, 'insideOrVolumeTestsRun': False,
              'penetrationDepthClaimed': False, 'contactLimit': args.contact_limit,
              'toothComponentAssignments': assignments, 'records': records,
              'poseMotion': [{key: value for key, value in pose.items() if key != 'file'} for pose in poses],
              'selectedHeadDentalSurfacePass': passed, 'anatomyAccepted': False,
              'poseExporterSha256': hashlib.sha256(exporter.read_bytes()).hexdigest(),
              'scope': 'Selected external-head/dental surface intersections and nearest distances only. No head containment, tissue volume, exact penetration depth, self-intersection audit, all control combinations, tongue/skin or phonetic acceptance.',
              'sourceProvenance': {'head': face_manifest['sourceRepository'], 'headLicense': face_manifest['originalAssetLicense'],
                                   'dental': oral_manifest['attribution']}}
    temporary = out/'face-contacts.json.tmp'
    temporary.write_text(json.dumps(report, indent=2)+'\n')
    temporary.replace(out/'face-contacts.json')
    (out/'progress.json').write_text(json.dumps({'faceAssetSha256': face_hash, 'oralAssetSha256': oral_hash,
                                               'complete': True, 'report': 'face-contacts.json'}, indent=2)+'\n')
    print(json.dumps({'report': str((out/'face-contacts.json').resolve()), 'selectedHeadDentalSurfacePass': passed,
                      'faceAssetSha256': face_hash, 'oralAssetSha256': oral_hash, 'pairs': len(records)}), flush=True)
    if args.gate and not passed:
        raise SystemExit('Selected head/dental surface gate needs review')


if __name__ == '__main__':
    main()
