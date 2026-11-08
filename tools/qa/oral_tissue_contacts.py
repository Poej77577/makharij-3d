"""Bounded actual-GLB tongue/palate/gingival surface diagnostics.

The three clearance pairs alone participate in --gate. Floor/frenulum pairs
are reported as attachment interfaces needing review, never accepted as safe
just because attachment is intended. FCL triangle contacts do not measure
penetration depth. Optional finite inside-solid samples are used only for an
opposing mesh that is a closed, consistently wound, positive volume.
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

from oral_contacts import bounded_rows, collision_object, mesh_from, sampled_intrusion

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ('rest', {}),
    ('TIP_ELEVATE_1', {'TIP_ELEVATE': 1}),
    ('DORSUM_ELEVATE_1', {'DORSUM_ELEVATE': 1}),
    ('ROOT_RETRACT_1', {'ROOT_RETRACT': 1}),
    ('JAW_OPEN_0.5', {'JAW_OPEN': .5}),
    ('JAW_OPEN_1', {'JAW_OPEN': 1}),
    ('jaw_tip', {'JAW_OPEN': .65, 'TIP_ELEVATE': .8}),
    ('source_combined', {'JAW_OPEN': .75, 'TIP_ELEVATE': .7,
                         'DORSUM_ELEVATE': .2, 'VELUM_RAISE': .5}),
]
CLEARANCE = ['PALATE', 'UPPER_GINGIVA', 'LOWER_GINGIVA']
ATTACHMENTS = ['ORAL_FLOOR', 'LINGUAL_FRENULUM']
NAMES = ['TONGUE'] + CLEARANCE + ATTACHMENTS

EXPORTER = r'''
import bpy, json, sys
from pathlib import Path
import numpy as np
config = json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=config['asset'])
manifest = config['manifest']
names = config['parts']
for name in names:
    if bpy.data.objects.get(name) is None or bpy.data.objects[name].type != 'MESH':
        raise RuntimeError('Missing actual GLB tissue mesh: '+name)
tongue = bpy.data.objects['TONGUE']
actual_keys = set(k.name for k in tongue.data.shape_keys.key_blocks) if tongue.data.shape_keys else set()
required_keys = {'JAW_OPEN', 'TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT'} | set(manifest['correctives'])
if not required_keys <= actual_keys:
    raise RuntimeError('Actual tongue lacks requested controls/correctives: '+str(required_keys-actual_keys))
known = {'JAW_OPEN'}
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH' and ob.data.shape_keys:
        known.update(k.name for k in ob.data.shape_keys.key_blocks[1:])
        ob.data.shape_keys.animation_data_clear()
for label, values in config['cases']:
    if set(values)-known:
        raise RuntimeError('Unknown actual GLB controls: '+str(set(values)-known))
jaw = bpy.data.objects[manifest['jawBinding']['node']]
jaw.animation_data_clear()
jaw.rotation_mode = 'XYZ'
metadata, reference = [], {}
for index, (label, values) in enumerate(config['cases']):
    for original in bpy.context.scene.objects:
        if original.type != 'MESH' or not original.data.shape_keys:
            continue
        for key in original.data.shape_keys.key_blocks[1:]:
            pair = manifest['correctives'].get(key.name)
            key.value = values.get(pair[0], 0)*values.get(pair[1], 0) if pair else values.get(key.name, 0)
        original.data.shape_keys.update_tag()
    # The imported rigid pivot rotates once. Tongue/floor/frenulum receive
    # their own soft coupling and the explicit jaw x tongue correctives.
    jaw.rotation_euler.x = values.get('JAW_OPEN', 0)*manifest['jawBinding']['angle_radians']
    bpy.context.view_layer.update()
    arrays, movement = {}, {}
    graph = bpy.context.evaluated_depsgraph_get()
    for name in names:
        ob = bpy.data.objects[name].evaluated_get(graph)
        me = ob.to_mesh()
        me.calc_loop_triangles()
        native = [ob.matrix_world@v.co for v in me.vertices]
        points = np.array([(-v.y, v.z, -v.x) for v in native], dtype=np.float64)
        arrays[name+'_vertices'] = points
        arrays[name+'_faces'] = np.array([t.vertices for t in me.loop_triangles], dtype=np.int32)
        if index == 0:
            reference[name] = points.copy()
        movement[name] = float(np.linalg.norm(points-reference[name], axis=1).max())
        ob.to_mesh_clear()
    if values and movement['TONGUE'] < 1e-7:
        raise RuntimeError('Requested tongue/jaw case did not move actual tongue: '+label)
    if values.get('JAW_OPEN', 0) > 0 and movement['LOWER_GINGIVA'] < 1e-7:
        raise RuntimeError('Actual rigid lower gingiva did not follow jaw: '+label)
    if values.get('JAW_OPEN', 0) == 0 and movement['LOWER_GINGIVA'] > 1e-7:
        raise RuntimeError('Non-jaw control unexpectedly moved lower gingiva')
    if movement['UPPER_GINGIVA'] > 1e-7:
        raise RuntimeError('Fixed upper gingiva unexpectedly moved')
    if values.get('VELUM_RAISE', 0) == 0 and movement['PALATE'] > 1e-7:
        raise RuntimeError('Palate moved without its velum control')
    filename = str(Path(config['cache'])/('pose-%02d.npz'%index))
    np.savez_compressed(filename, **arrays)
    metadata.append({'case': label, 'controls': values, 'file': filename,
                     'maximumDisplacementFromRest_m': movement})
Path(config['cache'], 'poses.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(json.dumps({'exportedCases': len(metadata), 'frame': '+X anterior,+Y superior,+Z subject right; m'}))
'''


def topology(mesh):
    return {'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
            'watertight': bool(mesh.is_watertight),
            'windingConsistent': bool(mesh.is_winding_consistent),
            'positiveClosedVolume': bool(mesh.is_volume),
            'volume_m3': float(mesh.volume) if mesh.is_volume else None}


def transverse_contacts(contacts, left, right, tolerance=1e-8):
    """Strict plane-straddling is sufficient evidence of transverse crossing.

    FCL contacts without this evidence remain contact/crossing requiring
    review. They are not silently treated as clear or as pure tangency.
    """
    valid = [c for c in contacts if 0 <= c.b1 < len(left.faces) and 0 <= c.b2 < len(right.faces)]
    if not valid:
        return [], np.empty((0, 3))
    a = left.triangles[np.array([c.b1 for c in valid])]
    b = right.triangles[np.array([c.b2 for c in valid])]
    na = left.face_normals[np.array([c.b1 for c in valid])]
    nb = right.face_normals[np.array([c.b2 for c in valid])]
    da = np.einsum('ijk,ik->ij', a-b[:, :1], nb)
    db = np.einsum('ijk,ik->ij', b-a[:, :1], na)
    strict = (da.min(1) < -tolerance) & (da.max(1) > tolerance) & (db.min(1) < -tolerance) & (db.max(1) > tolerance)
    selected = [c for c, ok in zip(valid, strict) if ok]
    # FCL contact positions are identified as such; they are not asserted to
    # be exact points on both surfaces or measurements of overlap depth.
    points = np.array([c.pos for c in selected], dtype=float).reshape((-1, 3))
    return selected, points


def triangle_intersection_segment(a, b, normal_a, normal_b):
    """Intersect nonparallel triangle plane sections, in double precision.

    This supplies points actually on both triangle surfaces: FCL contact.pos
    can lie on only one triangle for intersecting mesh triangles.
    """
    line = np.cross(normal_a, normal_b)
    length = np.linalg.norm(line)
    if length < 1e-12:
        return None
    line /= length

    def section(triangle, origin, normal):
        signed = (triangle-origin)@normal
        points = []
        for i in range(3):
            j = (i+1) % 3
            if abs(signed[i]) <= 1e-13:
                points.append(triangle[i])
            if signed[i]*signed[j] < 0:
                points.append(triangle[i]+(triangle[j]-triangle[i])*signed[i]/(signed[i]-signed[j]))
        return np.asarray(points).reshape((-1, 3))

    sa, sb = section(a, b[0], normal_b), section(b, a[0], normal_a)
    if len(sa) < 2 or len(sb) < 2:
        return None
    pa, pb = sa@line, sb@line
    low, high = max(pa.min(), pb.min()), min(pa.max(), pb.max())
    if high-low <= 1e-10:
        return None
    return sa[0]+(np.array([low, high])-sa[0]@line)[:, None]*line


def surface_record(left, right, limit):
    objects = collision_object(left), collision_object(right)
    collision = fcl.CollisionResult()
    fcl.collide(*objects, fcl.CollisionRequest(num_max_contacts=limit, enable_contact=True), collision)
    distance = fcl.DistanceResult()
    raw = fcl.distance(*objects, fcl.DistanceRequest(enable_nearest_points=True), distance)
    contacts = collision.contacts
    crossing, transverse_positions = transverse_contacts(contacts, left, right)
    points = np.array([c.pos for c in contacts], dtype=float).reshape((-1, 3))
    nearest = np.array(distance.nearest_points, dtype=float) if raw >= 0 and not collision.is_collision else np.empty((0, 3))
    if nearest.shape == (2, 3) and (not np.isfinite(nearest).all() or abs(np.linalg.norm(nearest[0]-nearest[1])-raw) > 1e-7):
        raise RuntimeError('FCL nearest-point/distance inconsistency')
    intersections = []
    for c in crossing:
        segment = triangle_intersection_segment(left.triangles[c.b1], right.triangles[c.b2],
                                                left.face_normals[c.b1], right.face_normals[c.b2])
        if segment is not None:
            intersections.append((c, segment))
    witnesses = []
    indices = bounded_rows(np.arange(len(intersections)), 12)
    for index in indices:
        c, segment = intersections[index]
        p = segment.mean(0).reshape((1, 3))
        ta, tb = left.triangles[int(c.b1):int(c.b1)+1], right.triangles[int(c.b2):int(c.b2)+1]
        # Trimesh's absolute tolerances can misclassify tiny metre-unit
        # triangles. Numerical mm queries preserve the geometry and return m.
        pa = trimesh.triangles.closest_point(ta*1000, p*1000)[0]/1000
        pb = trimesh.triangles.closest_point(tb*1000, p*1000)[0]/1000
        residual = [float(np.linalg.norm(pa-p[0])), float(np.linalg.norm(pb-p[0]))]
        if max(residual) > 1e-8:
            raise RuntimeError('Computed triangle intersection witness is not on both triangles')
        witnesses.append({'surfaceIntersectionPoint_m': p[0].tolist(),
                          'surfaceIntersectionSegment_m': segment.tolist(),
                          'triangleIndices': [int(c.b1), int(c.b2)],
                          'distanceToEachTriangle_m': residual,
                          'fclContactPosition_m': np.array(c.pos).tolist()})
    intersection_points = np.vstack([segment for _, segment in intersections]) if intersections else np.empty((0, 3))
    return {'surfaceContactOrCrossing': bool(collision.is_collision),
            'confirmedTransverseSurfaceCrossing': bool(intersections),
            'triangleContactCount': len(contacts),
            'strictTransverseTriangleContactCount': len(crossing),
            'properIntersectionSegmentCount': len(intersections),
            'contactLimitHit': len(contacts) >= limit,
            'minimumSurfaceDistance_m': 0.0 if collision.is_collision else float(raw) if raw >= 0 else None,
            'nearestSurfacePoints_m': nearest.tolist() if nearest.shape == (2, 3) else None,
            'negativeFclDistanceNotUsedAsPenetrationDepth': bool(raw < 0),
            'fclContactBounds_m': [points.min(0).tolist(), points.max(0).tolist()] if len(points) else None,
            'strictPlaneStraddlingFclContactBounds_m': [transverse_positions.min(0).tolist(), transverse_positions.max(0).tolist()] if len(transverse_positions) else None,
            'surfaceIntersectionBounds_m': [intersection_points.min(0).tolist(), intersection_points.max(0).tolist()] if len(intersection_points) else None,
            'surfaceIntersectionWitnesses': witnesses}, contacts


def closed_sample_record(surface, solid, contacts, direction, limit):
    if not solid.is_volume:
        return {'run': False, 'reason': 'Opposing mesh is not a positive closed consistently wound volume; no containment test'}
    ids = np.unique([getattr(c, direction) for c in contacts if 0 <= getattr(c, direction) < len(surface.faces)]).astype(int)
    points = np.vstack([bounded_rows(surface.vertices, limit),
                        surface.triangles[ids].reshape((-1, 3)), surface.triangles_center[ids]])
    # Uniform numerical scaling is used only for Trimesh queries, never
    # delivered geometry or the FCL checks. This avoids absolute-tolerance
    # errors on sub-mm triangles when distances are queried in metres.
    numerical_solid = trimesh.Trimesh(solid.vertices*1000, solid.faces, process=False)
    record = sampled_intrusion(points*1000, numerical_solid, limit)
    if record['maximumSampledInteriorDistance_m'] is not None:
        record['maximumSampledInteriorDistance_m'] /= 1000
    if record['worstWitness_m'] is not None:
        record['worstWitness_m'] = (np.array(record['worstWitness_m'])/1000).tolist()
    record.update({'run': True, 'numericalQueryUnits': 'millimetres; all output positions/distances converted to metres',
                   'metric': 'Finite surface samples classified inside a closed opposing solid; nearest surface distance is a sampled lower bound, not exact penetration depth'})
    if record['worstWitness_m'] is not None:
        nearest, distances, faces = numerical_solid.nearest.on_surface(np.array([record['worstWitness_m']])*1000)
        record['opposingSurfaceNearestToWorstWitness_m'] = (nearest[0]/1000).tolist()
        record['opposingTriangleAtWorstWitness'] = int(faces[0])
    return record


def self_test():
    plane = trimesh.Trimesh([[0, -2, -2], [0, 2, -2], [0, 2, 2], [0, -2, 2]], [[0, 1, 2], [0, 2, 3]], process=False)
    box = trimesh.creation.box(extents=[2., 2., 2.])
    crossed, contacts = surface_record(plane, box, 128)
    assert not plane.is_volume and crossed['surfaceContactOrCrossing'] and crossed['confirmedTransverseSurfaceCrossing']
    assert all(max(w['distanceToEachTriangle_m']) < 1e-10 for w in crossed['surfaceIntersectionWitnesses'])
    # Independent sub-mm triangle with a known interior point; mm queries
    # avoid absolute tolerance errors on anatomy-scale metre coordinates.
    small = np.array([[[0, 0, 0], [.0003, 0, 0], [0, .0003, 0]]])
    known_point = np.array([[.0001, .0001, 0]])
    queried = trimesh.triangles.closest_point(small*1000, known_point*1000)/1000
    assert np.max(np.abs(queried-known_point)) < 1e-12
    skipped = closed_sample_record(box, plane, contacts, 'b2', 32)
    assert not skipped['run']
    box.apply_translation([2, 0, 0])
    separated, _ = surface_record(plane, box, 128)
    assert not separated['surfaceContactOrCrossing'] and abs(separated['minimumSurfaceDistance_m']-1) < 1e-10
    return {'passed': True, 'fixture': 'Open plane crosses a box, then separates by 1 metre',
            'openSurfaceContainmentSkipped': True, 'knownSeparation_m': 1.0,
            'strictTransverseDetectionPassed': True, 'subMillimetreTriangleNearestPointPassed': True,
            'anatomyFixture': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT/'artifacts/method-evidence/oral-sculpt')
    parser.add_argument('--asset', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT/'artifacts/method-evidence/oral-sculpt/tissue-contact-review')
    parser.add_argument('--cache', type=Path, default=Path('/workspace/research/oral-tissue-contact-review'))
    parser.add_argument('--contact-limit', type=int, default=4000)
    parser.add_argument('--samples', type=int, default=256)
    parser.add_argument('--gate', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        return
    if not 1 <= args.contact_limit <= 20000 or not 1 <= args.samples <= 2048:
        raise ValueError('Bounded budgets: contacts 1..20000, surface samples 1..2048')
    asset = (args.asset or args.folder/'oral-unit.glb').resolve()
    manifest_path = (args.manifest or args.folder/'oral-manifest.json').resolve()
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    asset_hash = hashlib.sha256(asset.read_bytes()).hexdigest()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if asset_hash != manifest['glbSha256']:
        raise RuntimeError('Actual GLB does not match manifest identity')
    if manifest.get('gltfToProject') != [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]:
        raise RuntimeError('Unsupported canonical coordinate contract')
    config_hash = hashlib.sha256(json.dumps([CASES, NAMES, manifest['correctives'], manifest['jawBinding'], EXPORTER], sort_keys=True).encode()).hexdigest()
    cache = args.cache/asset_hash[:16]/config_hash[:12]
    cache.mkdir(parents=True, exist_ok=True)
    frozen = cache/'input.glb'
    if not frozen.exists():
        shutil.copyfile(asset, frozen)
    if hashlib.sha256(frozen.read_bytes()).hexdigest() != asset_hash:
        raise RuntimeError('Frozen geometry identity differs')
    (cache/'oral-manifest.json').write_bytes(manifest_bytes)
    config = cache/'export.json'
    config.write_text(json.dumps({'asset': str(frozen), 'manifest': manifest, 'parts': NAMES,
                                 'cases': CASES, 'cache': str(cache)}, indent=2)+'\n')
    exporter = cache/'export_poses.py'
    exporter.write_text(EXPORTER)
    if not (cache/'poses.json').exists():
        with (cache/'blender-export.log').open('w') as log:
            subprocess.run(['blender', '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                            '--python-exit-code', '1', '--python', str(exporter), '--', str(config)],
                           check=True, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
    out = args.out.resolve()
    previous = out/'tissue-contacts.json'
    if previous.exists() and json.loads(previous.read_text()).get('assetSha256') != asset_hash:
        out = out/asset_hash[:16]
    out.mkdir(parents=True, exist_ok=True)
    previous = out/'tissue-contacts.json'
    if previous.exists() and json.loads(previous.read_text()).get('assetSha256') != asset_hash:
        raise RuntimeError('Output identity collision; use fresh --out')
    poses = json.loads((cache/'poses.json').read_text())
    if [p['case'] for p in poses] != [c[0] for c in CASES]:
        raise RuntimeError('Incomplete or mismatched evaluated case cache')
    records, pose_topology = [], []
    for pose in poses:
        with np.load(pose['file']) as data:
            meshes = {name: mesh_from(data, name) for name in NAMES}
        statuses = {name: topology(mesh) for name, mesh in meshes.items()}
        pose_topology.append({'case': pose['case'], 'parts': statuses,
                              'maximumDisplacementFromRest_m': pose['maximumDisplacementFromRest_m']})
        for name in CLEARANCE+ATTACHMENTS:
            right = meshes[name]
            row, contacts = surface_record(meshes['TONGUE'], right, args.contact_limit)
            forbidden = name in CLEARANCE
            row.update({'case': pose['case'], 'controls': pose['controls'], 'pair': ['TONGUE', name],
                        'relationship': 'forbidden-clearance-surface-pair' if forbidden else 'basal-or-ventral-attachment-interface-diagnostic',
                        'gateParticipates': forbidden,
                        'intendedAttachmentOverlapAccepted': False,
                        'topology': {'TONGUE': statuses['TONGUE'], name: statuses[name]}})
            if forbidden:
                row['tongueSurfaceInsideOther'] = closed_sample_record(meshes['TONGUE'], right, contacts, 'b1', args.samples)
                row['otherSurfaceInsideTongue'] = closed_sample_record(right, meshes['TONGUE'], contacts, 'b2', args.samples)
            else:
                row['attachmentInterpretation'] = 'Only basal floor and ventral frenulum attachment is intended. Crossing extent remains a review diagnostic; no arbitrary overlap is accepted and no attachment anatomy gate is passed.'
            records.append(row)
            progress = out/'progress.json.tmp'
            progress.write_text(json.dumps({'assetSha256': asset_hash, 'complete': False, 'records': records}, indent=2)+'\n')
            progress.replace(out/'progress.json')
            print(json.dumps({'case': pose['case'], 'pair': name, 'gateParticipates': forbidden,
                              'contactOrCrossing': row['surfaceContactOrCrossing'],
                              'strictTransverse': row['confirmedTransverseSurfaceCrossing'],
                              'triangleContacts': row['triangleContactCount']}), flush=True)
    forbidden_rows = [r for r in records if r['gateParticipates']]
    passed = len(forbidden_rows) == 24 and all(not r['surfaceContactOrCrossing'] and not r['contactLimitHit']
                                             and r['minimumSurfaceDistance_m'] is not None for r in forbidden_rows)
    report = {'assetSha256': asset_hash, 'manifestSha256': manifest_hash,
              'poseConfigurationSha256': config_hash, 'toolSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'helperSha256': hashlib.sha256(Path(__file__).with_name('oral_contacts.py').read_bytes()).hexdigest(),
              'poseExporterSha256': hashlib.sha256(EXPORTER.encode()).hexdigest(),
              'frame': '+X anterior, +Y superior, +Z subject right; metres',
              'evaluatedBy': 'Blender actual GLB importer; explicit morphs and product correctives, evaluated world matrices, one rigid jaw pivot',
              'frozenInput': str(frozen), 'cases': len(poses), 'pairsChecked': len(records),
              'forbiddenPairsChecked': len(forbidden_rows), 'attachmentPairsDiagnosticOnly': len(records)-len(forbidden_rows),
              'selectedForbiddenTissueSurfacePass': passed,
              'forbiddenSurfaceContactPairs': sum(r['surfaceContactOrCrossing'] for r in forbidden_rows),
              'forbiddenConfirmedTransversePairs': sum(r['confirmedTransverseSurfaceCrossing'] for r in forbidden_rows),
              'contactLimit': args.contact_limit, 'maximumFiniteSamplesPerDirection': args.samples,
              'strictPlaneStraddlingTolerance_m': 1e-8,
              'fclContactPositionsAreNotExactIntersectionWitnesses': True,
              'surfaceIntersectionWitnessMethod': 'Intersect two triangle plane sections; verify resulting midpoint is on both triangles. Trimesh nearest-point validation uses numerical mm, output is m.',
              'sampledInteriorDistancesAreNotExactPenetrationDepth': True,
              'topologyByCase': pose_topology, 'records': records,
              'insideTestsOnOpenMeshesRun': False, 'fclPenetrationDepthUsed': False,
              'anatomyAccepted': False, 'expertAcceptance': 'pending',
              'scope': 'Eight fixed poses; tongue versus palate and upper/lower gingiva only contribute to surface gate. Floor/frenulum are attachment-interface diagnostics, not accepted safe overlaps. Finite closed-solid sample distances are sampled lower bounds, not exact penetration depth. No containment on open/non-volume meshes, full control-space coverage, self-intersection audit, phoneme contact, biomechanical or clinical acceptance.',
              'sourceAttribution': manifest['attribution'], 'cacheSourceGeometryRedistributed': False}
    (out/'tissue-contacts.json').write_text(json.dumps(report, indent=2)+'\n')
    (out/'progress.json').write_text(json.dumps({'assetSha256': asset_hash, 'complete': True,
                                               'report': 'tissue-contacts.json'}, indent=2)+'\n')
    print(json.dumps({'report': str(out/'tissue-contacts.json'), 'assetSha256': asset_hash,
                      'cases': len(poses), 'pairsChecked': len(records), 'forbiddenPairsChecked': len(forbidden_rows),
                      'selectedForbiddenTissueSurfacePass': passed}), flush=True)
    if args.gate and not passed:
        raise SystemExit('Selected forbidden tissue surface gate needs review')


if __name__ == '__main__':
    main()
