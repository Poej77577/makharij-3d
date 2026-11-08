"""Selected actual-GLB tongue/dental contact diagnostics, not anatomy approval.

Run with .venv-qa/bin/python. Blender evaluates imported morphs and the rigid
jaw; FCL checks surface intersections. Intrusion is measured separately as the
nearest-surface distance of finite surface samples classified inside a closed
opposing mesh. It is a sampled lower bound, NOT FCL's mesh penetration_depth or
an exact intersection-volume / global penetration-depth measurement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import fcl
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = [('rest', {})]
for control in ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT', 'JAW_OPEN']:
    for value in [.5, 1]:
        DEFAULT_CASES.append((control+'_'+str(value), {control: value}))
DEFAULT_CASES += [
    ('VELUM_RAISE_1', {'VELUM_RAISE': 1}),
    ('jaw_tip', {'JAW_OPEN': .65, 'TIP_ELEVATE': .8}),
    ('jaw_dorsum', {'JAW_OPEN': .6, 'DORSUM_ELEVATE': 1}),
    ('jaw_root', {'JAW_OPEN': .6, 'ROOT_RETRACT': 1}),
    ('closed_tongue_combination', {'TIP_ELEVATE': .7, 'DORSUM_ELEVATE': .7, 'ROOT_RETRACT': .7}),
    ('all_half', {key: .5 for key in ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT', 'JAW_OPEN', 'VELUM_RAISE']}),
    ('all_max', {key: 1 for key in ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT', 'JAW_OPEN', 'VELUM_RAISE']}),
    ('source_combined', {'JAW_OPEN': .75, 'TIP_ELEVATE': .7, 'DORSUM_ELEVATE': .2, 'VELUM_RAISE': .5}),
    ('return', {}),
]

EXPORTER = r'''
import bpy, json, sys
from pathlib import Path
import numpy as np
from mathutils import Vector
config = json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=config['asset'])
names = ['TONGUE', 'UPPER_DENTITION', 'LOWER_DENTITION']
manifest = config['manifest']
known = {'JAW_OPEN'}
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH' and ob.data.shape_keys:
        known.update(key.name for key in ob.data.shape_keys.key_blocks[1:] if not key.name.startswith('JAW_X_'))
for label, values in config['cases']:
    if set(values)-known:
        raise RuntimeError('Unknown GLB controls in '+label+': '+str(set(values)-known))
for ob in bpy.context.scene.objects:
    if ob.type == 'MESH' and ob.data.shape_keys:
        ob.data.shape_keys.animation_data_clear()
jaw = bpy.data.objects[manifest['jawBinding']['node']]
jaw.animation_data_clear()
jaw.rotation_mode = 'XYZ'
metadata = []
for case_index, (label, values) in enumerate([('__label_rest__', {})]+config['cases']):
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH' or not ob.data.shape_keys:
            continue
        for key in ob.data.shape_keys.key_blocks[1:]:
            pair = manifest['correctives'].get(key.name)
            key.value = values.get(pair[0], 0)*values.get(pair[1], 0) if pair else values.get(key.name, 0)
        ob.data.shape_keys.update_tag()
    jaw.rotation_euler.x = values.get('JAW_OPEN', 0)*manifest['jawBinding']['angle_radians']
    bpy.context.view_layer.update()
    arrays = {}
    for name in names:
        ob = bpy.data.objects[name].evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ob.to_mesh()
        me.calc_loop_triangles()
        native = [ob.matrix_world@v.co for v in me.vertices]
        arrays[name+'_vertices'] = np.array([(-v.y, v.z, -v.x) for v in native], dtype=np.float64)
        arrays[name+'_faces'] = np.array([t.vertices for t in me.loop_triangles], dtype=np.int32)
        ob.to_mesh_clear()
    filename = str(Path(config['cache'])/('pose-%02d.npz'%case_index))
    np.savez_compressed(filename, **arrays)
    if label == '__label_rest__':
        Path(config['cache'], 'rest-file.json').write_text(json.dumps({'file': filename}))
    else:
        metadata.append({'case': label, 'controls': values, 'file': filename})
Path(config['cache'], 'poses.json').write_text(json.dumps(metadata, indent=2)+'\n')
print(json.dumps({'exportedCases': len(metadata), 'frame': '+X anterior, +Y superior, +Z subject right; m'}))
'''


def mesh_from(data, name):
    mesh = trimesh.Trimesh(data[name+'_vertices'], data[name+'_faces'], process=False)
    if not len(mesh.vertices) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all() or mesh.faces.min() < 0 or mesh.faces.max() >= len(mesh.vertices):
        raise ValueError(name+': invalid delivered mesh arrays')
    # UV/normal seams duplicate coincident positions in GLB. Welding only
    # duplicates at 1e-10 m preserves the delivered geometric surface.
    mesh.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
    return mesh


def collision_object(mesh):
    tree = fcl.BVHModel()
    tree.beginModel(len(mesh.vertices), len(mesh.faces))
    tree.addSubModel(np.asarray(mesh.vertices, dtype=np.float64), np.asarray(mesh.faces, dtype=np.int32))
    tree.endModel()
    return fcl.CollisionObject(tree)


def bounded_rows(rows, maximum):
    if len(rows) <= maximum:
        return rows
    return rows[np.linspace(0, len(rows)-1, maximum, dtype=np.int64)]


def sampled_intrusion(surface_points, solid, sample_limit):
    lo, hi = solid.bounds
    candidates = surface_points[np.all(surface_points >= lo, axis=1) & np.all(surface_points <= hi, axis=1)]
    points = bounded_rows(candidates, sample_limit)
    record = {'candidateSurfaceSamples': len(candidates), 'testedSamples': len(points),
              'opposingMeshWatertight': bool(solid.is_watertight),
              'maximumSampledInteriorDistance_m': None, 'worstWitness_m': None}
    if not solid.is_watertight or not len(points):
        return record
    inside = np.zeros(len(points), dtype=bool)
    for start in range(0, len(points), 128):
        inside[start:start+128] = solid.contains(points[start:start+128])
    interior = points[inside]
    record['classifiedInteriorSamples'] = int(inside.sum())
    record['maximumSampledInteriorDistance_m'] = 0.0
    if len(interior):
        distances = []
        for start in range(0, len(interior), 128):
            distances.extend(solid.nearest.on_surface(interior[start:start+128])[1])
        worst = int(np.argmax(distances))
        record['maximumSampledInteriorDistance_m'] = float(distances[worst])
        record['worstWitness_m'] = interior[worst].tolist()
    return record


def dental_labels(mesh, arch, source):
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
    components = sorted(components, key=lambda ids: int(ids.min()))
    prefixes = 'ATLAS_UPPER_' if arch.startswith('UPPER') else 'ATLAS_LOWER_'
    originals = [(name, np.array(part['positions']).reshape(-1, 3)) for name, part in source.items() if name.startswith(prefixes)]
    trees = [(name, cKDTree(points)) for name, points in originals]
    labels = np.full(len(mesh.faces), 'unassigned', dtype=object)
    assignments = []
    for faces in components:
        faces = np.asarray(faces)
        points = mesh.vertices[np.unique(mesh.faces[faces])]
        probes = bounded_rows(points, 256)
        matches = []
        for name, tree in trees:
            distances = tree.query(probes)[0]
            matches.append((float(distances.max()), float(distances.mean()), name))
        maximum, mean, name = min(matches)
        if maximum > 1e-6:
            name = 'unassigned'
        labels[faces] = name
        assignments.append({'tooth': name, 'triangles': len(faces),
                            'sourceVertexMaximumResidual_m': maximum,
                            'sourceVertexMeanResidual_m': mean,
                            'componentLabelSamples': len(probes)})
    return labels, assignments


def diagnostic_plot(record, pose_file, output, cache):
    """Scientific projections of actual mesh samples, not a medical render."""
    os.environ.setdefault('MPLCONFIGDIR', str(cache/'matplotlib-config'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data = np.load(pose_file)
    tongue = mesh_from(data, 'TONGUE')
    teeth = mesh_from(data, record['pair'][1])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, indices, caption in zip(axes, [(0, 2), (0, 1)], ['Dorsal projection', 'Sagittal projection']):
        for mesh, color, label in [(tongue, '#c58181', 'Tongue surface samples'), (teeth, '#59666d', 'Dental surface samples')]:
            points = bounded_rows(np.asarray(mesh.vertices), 6000)*1000
            ax.scatter(points[:, indices[0]], points[:, indices[1]], s=.6, alpha=.17, color=color, label=label)
        points = np.array(record['crossingWitnesses_m'])
        if len(points):
            ax.scatter(points[:, indices[0]]*1000, points[:, indices[1]]*1000, s=18, color='#cc2222', marker='o', label='FCL crossing witnesses')
        witnesses = [r['worstWitness_m'] for r in [record['toothSurfaceInsideTongue'], record['tongueSurfaceInsideTeeth']] if r['worstWitness_m'] is not None]
        if witnesses:
            points = np.array(witnesses)*1000
            ax.scatter(points[:, indices[0]], points[:, indices[1]], s=55, color='#1763c0', marker='x', linewidths=1.5, label='Deepest tested inside samples')
        nearest = record.get('closestSurfacePoints_m')
        if nearest:
            points = np.array(nearest)*1000
            ax.plot(points[:, indices[0]], points[:, indices[1]], 'o-', color='#1763c0', markersize=3, linewidth=1, label='Closest surface pair')
        ax.set_title(caption)
        ax.set_xlabel('+X anterior (mm)')
        ax.set_ylabel('+Z subject right (mm)' if indices[1] == 2 else '+Y superior (mm)')
        ax.set_aspect('equal', adjustable='box')
        ax.grid(alpha=.2)
    depth = max(record['toothSurfaceInsideTongue']['maximumSampledInteriorDistance_m'] or 0,
                record['tongueSurfaceInsideTeeth']['maximumSampledInteriorDistance_m'] or 0)*1000
    fig.suptitle(f"{record['case']} / {record['pair'][1]}: {record['classification']}\nMaximum tested inside-surface distance: {depth:.3f} mm", fontsize=11)
    axes[0].legend(loc='lower left', fontsize=7)
    fig.text(.5, .02, 'Actual evaluated GLB geometry; projections do not show depth occlusion. Finite sample distance is not exact penetration depth.', ha='center', fontsize=7)
    fig.tight_layout(rect=(0, .05, 1, .87))
    fig.savefig(output, dpi=160)
    plt.close(fig)


def analytical_self_test():
    cube = trimesh.creation.box(extents=[2., 2., 2.])
    centre = sampled_intrusion(np.array([[0., 0, 0], [.9, 0, 0], [2., 0, 0]]), cube, 100)
    assert abs(centre['maximumSampledInteriorDistance_m']-1) < 1e-10
    separated = cube.copy()
    separated.apply_translation([3, 0, 0])
    result = fcl.CollisionResult()
    fcl.collide(collision_object(cube), collision_object(separated), fcl.CollisionRequest(enable_contact=True), result)
    gap = fcl.distance(collision_object(cube), collision_object(separated), fcl.DistanceRequest(), fcl.DistanceResult())
    assert not result.is_collision and abs(gap-1) < 1e-10
    overlap_surface = np.array([[.5, 0, 0]])
    overlap = sampled_intrusion(overlap_surface, cube, 100)
    assert abs(overlap['maximumSampledInteriorDistance_m']-.5) < 1e-10
    contained = trimesh.creation.box(extents=[.2, .2, .2])
    containment = sampled_intrusion(contained.vertices, cube, 100)
    assert abs(containment['maximumSampledInteriorDistance_m']-.9) < 1e-10
    return {'passed': True, 'scope': 'Analytical metre-unit boxes; not anatomy',
            'centreToSurfaceDistance_m': 1.0, 'separatedGap_m': 1.0,
            'overlappingBoxSurfaceSampleInsideDistance_m': .5,
            'fullyContainedSmallBoxSurfaceDistance_m': .9}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder', type=Path, default=ROOT/'artifacts/method-evidence/oral-sculpt')
    p.add_argument('--asset', type=Path)
    p.add_argument('--manifest', type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--cache', type=Path, default=Path('/workspace/research/oral-contact-review'))
    p.add_argument('--samples', type=int, default=512)
    p.add_argument('--contact-limit', type=int, default=4000)
    p.add_argument('--cases', type=Path, help='Optional JSON list of [case, control-values]')
    p.add_argument('--case', action='append', help='Run only named case(s)')
    p.add_argument('--gate', action='store_true')
    p.add_argument('--no-plots', action='store_true')
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        print(json.dumps(analytical_self_test(), indent=2))
        return
    folder = a.folder.resolve()
    asset = (a.asset or folder/'oral-unit.glb').resolve()
    manifest = json.loads((a.manifest or folder/'oral-manifest.json').read_text())
    a.out = a.out or folder/'contact-review'
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    if digest != manifest['glbSha256']:
        raise RuntimeError('GLB identity does not match its manifest')
    previous = a.out/'contact-review.json'
    if previous.exists():
        existing_identity = json.loads(previous.read_text()).get('assetSha256')
        if existing_identity != digest:
            # Keep defect evidence when the main asset is replaced/rebaked.
            a.out = a.out/digest[:16]
            nested = a.out/'contact-review.json'
            if nested.exists() and json.loads(nested.read_text()).get('assetSha256') != digest:
                raise RuntimeError('Output identity collision; choose a fresh --out directory')
    cases = json.loads(a.cases.read_text()) if a.cases else DEFAULT_CASES
    if a.case:
        cases = [row for row in cases if row[0] in a.case]
    if not cases or a.samples < 1 or a.contact_limit < 1:
        raise ValueError('No cases or invalid bounded diagnostic budget')
    labels = []
    for label, values in cases:
        if not isinstance(label, str) or label == '__label_rest__' or not isinstance(values, dict) or any(
                not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in values.values()):
            raise ValueError('Cases require unique labels and finite control values in [0, 1]')
        labels.append(label)
    if len(set(labels)) != len(labels):
        raise ValueError('Case labels must be unique')
    if manifest.get('gltfToProject') != [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]:
        raise ValueError('Unsupported GLB-to-project coordinate contract')
    case_digest = hashlib.sha256(json.dumps([cases, manifest['correctives'], manifest['jawBinding'], EXPORTER], sort_keys=True).encode()).hexdigest()[:12]
    cache = a.cache/digest[:16]/case_digest
    cache.mkdir(exist_ok=True, parents=True)
    a.out.mkdir(exist_ok=True, parents=True)
    frozen = cache/'input.glb'
    if not frozen.exists():
        shutil.copyfile(asset, frozen)
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == digest
    config = cache/'export.json'
    config.write_text(json.dumps({'asset': str(frozen), 'manifest': manifest, 'cases': cases, 'cache': str(cache)}, indent=2))
    exporter = cache/'export_poses.py'
    exporter.write_text(EXPORTER)
    if not (cache/'poses.json').exists():
        with (cache/'blender-export.log').open('w') as log:
            subprocess.run(['blender', '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                            '--python-exit-code', '1', '--python', str(exporter), '--', str(config)],
                           check=True, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
    poses = json.loads((cache/'poses.json').read_text())
    source = json.loads((ROOT/'assets/source/z-anatomy/reference-meshes.json').read_text())['parts']
    rest = np.load(json.loads((cache/'rest-file.json').read_text())['file'])
    labels, assignments = {}, {}
    for name in ['UPPER_DENTITION', 'LOWER_DENTITION']:
        labels[name], assignments[name] = dental_labels(mesh_from(rest, name), name, source)
    records = []
    for pose in poses:
        data = np.load(pose['file'])
        tongue = mesh_from(data, 'TONGUE')
        tongue_object = collision_object(tongue)
        for arch in ['UPPER_DENTITION', 'LOWER_DENTITION']:
            teeth = mesh_from(data, arch)
            dental_object = collision_object(teeth)
            result = fcl.CollisionResult()
            fcl.collide(tongue_object, dental_object,
                        fcl.CollisionRequest(num_max_contacts=a.contact_limit, enable_contact=True), result)
            distance_result = fcl.DistanceResult()
            raw_distance = fcl.distance(tongue_object, dental_object,
                                        fcl.DistanceRequest(enable_nearest_points=True), distance_result)
            contacts = result.contacts
            dental_ids = np.unique([c.b2 for c in contacts if 0 <= c.b2 < len(teeth.faces)]).astype(np.int64)
            tongue_ids = np.unique([c.b1 for c in contacts if 0 <= c.b1 < len(tongue.faces)]).astype(np.int64)
            # Include globally distributed vertices as well as crossing-patch
            # vertices/centroids, so the metric is not just an intersection line.
            dental_samples = np.vstack([bounded_rows(teeth.vertices, a.samples),
                                         teeth.triangles[dental_ids].reshape(-1, 3), teeth.triangles_center[dental_ids]])
            tongue_samples = np.vstack([bounded_rows(tongue.vertices, a.samples),
                                         tongue.triangles[tongue_ids].reshape(-1, 3), tongue.triangles_center[tongue_ids]])
            dental_inside = sampled_intrusion(dental_samples, tongue, a.samples)
            tongue_inside = sampled_intrusion(tongue_samples, teeth, a.samples)
            for measurement in [dental_inside, tongue_inside]:
                witness = measurement['worstWitness_m']
                if witness is not None:
                    _, _, nearest_tri = teeth.nearest.on_surface(np.array([witness]))
                    measurement['nearestToothAtWitness'] = str(labels[arch][int(nearest_tri[0])])
            intrusion = max(dental_inside['maximumSampledInteriorDistance_m'] or 0,
                            tongue_inside['maximumSampledInteriorDistance_m'] or 0)
            crossing = bool(result.is_collision)
            classification = ('sampled-solid-intrusion' if intrusion > .0001 else
                              'surface-crossing-needs-review' if crossing else
                              'near-touch' if 0 <= raw_distance <= .0002 else 'separated')
            patch_teeth = sorted(set(str(labels[arch][i]) for i in dental_ids))
            points = np.array([c.pos for c in contacts])
            closest = np.array(distance_result.nearest_points) if raw_distance >= 0 and not crossing else np.empty((0, 3))
            closest_tooth = None
            if closest.shape == (2, 3) and np.isfinite(closest).all():
                _, _, triangle = teeth.nearest.on_surface(closest[1:2])
                closest_tooth = str(labels[arch][int(triangle[0])])
            record = {'case': pose['case'], 'controls': pose['controls'], 'pair': ['TONGUE', arch],
                      'classification': classification, 'surfaceCrossing': crossing,
                      'triangleContactCount': len(contacts), 'contactLimitHit': len(contacts) >= a.contact_limit,
                      'minimumSurfaceDistance_m': float(raw_distance) if raw_distance >= 0 else None,
                      'closestSurfacePoints_m': closest.tolist() if closest.shape == (2, 3) and np.isfinite(closest).all() else None,
                      'closestTooth': closest_tooth,
                      'negativeFclDistanceNotUsedAsPenetrationDepth': raw_distance < 0,
                      'crossingPatchTeeth': patch_teeth,
                      'crossingBounds_m': [points.min(0).tolist(), points.max(0).tolist()] if len(points) else None,
                      'crossingWitnesses_m': bounded_rows(points, 12).tolist() if len(points) else [],
                      'toothSurfaceInsideTongue': dental_inside, 'tongueSurfaceInsideTeeth': tongue_inside,
                      'tongueWatertight': bool(tongue.is_watertight), 'dentalWatertight': bool(teeth.is_watertight)}
            records.append(record)
            progress = a.out/'progress.json.tmp'
            progress.write_text(json.dumps({'assetSha256': digest, 'complete': False, 'records': records}, indent=2)+'\n')
            progress.replace(a.out/'progress.json')
            print(json.dumps({'case': pose['case'], 'arch': arch, 'classification': classification,
                              'triangleContacts': len(contacts), 'sampledIntrusion_mm': intrusion*1000}), flush=True)
    worst = sorted(records, key=lambda row: (-max(row['toothSurfaceInsideTongue']['maximumSampledInteriorDistance_m'] or 0,
                                                row['tongueSurfaceInsideTeeth']['maximumSampledInteriorDistance_m'] or 0),
                                            row['minimumSurfaceDistance_m'] if row['minimumSurfaceDistance_m'] is not None else 0))
    clear = all(row['classification'] in ['separated', 'near-touch'] and
                row['tongueWatertight'] and row['dentalWatertight'] and not row['contactLimitHit'] for row in records)
    report = {'assetSha256': digest, 'frame': '+X anterior, +Y superior, +Z subject right; metres',
              'evaluatedBy': 'Blender official GLB importer, explicit runtime morph correction and rigid jaw state',
              'cases': len(poses), 'pairsChecked': len(records), 'contactLimit': a.contact_limit,
              'maximumSamplesPerDirection': a.samples, 'nearTouchDistance_m': .0002,
              'sampledIntrusionReviewThreshold_m': .0001, 'toothComponentAssignments': assignments,
              'componentLabelingMethod': 'Delivered rest-pose component vertices matched against original source tooth vertices; multiple components per tooth allowed',
              'records': records, 'worstRecordIndices': [records.index(row) for row in worst[:5]],
              'selectedDentalClearancePass': clear, 'anatomyAccepted': False, 'expertAcceptance': 'pending',
              'scope': 'Selected tongue/dental poses only. Surface collision and finite inside-solid surface sampling; not exact penetration depth, intersection volume, all controls, self-intersection audit, gingival or palatal contact, biomechanics or clinical acceptance.',
              'cacheSourceGeometryRedistributed': False, 'sourceAttribution': manifest['attribution']}
    report['poseExporterSha256'] = hashlib.sha256(exporter.read_bytes()).hexdigest()
    if not a.no_plots:
        for filename, record in [('worst-contact.png', worst[0]), ('rest-contact.png', next((row for row in records if row['case'] == 'rest' and row['pair'][1] == 'LOWER_DENTITION'), records[0]))]:
            pose = next(row for row in poses if row['case'] == record['case'])
            diagnostic_plot(record, pose['file'], a.out/filename, cache)
    (a.out/'contact-review.json').write_text(json.dumps(report, indent=2)+'\n')
    (a.out/'progress.json').write_text(json.dumps({'assetSha256': digest, 'complete': True, 'report': 'contact-review.json', 'records': records}, indent=2)+'\n')
    print(json.dumps({'report': str((a.out/'contact-review.json').resolve()), 'assetSha256': digest,
                      'selectedDentalClearancePass': clear, 'cases': len(poses), 'pairs': len(records)}), flush=True)
    if a.gate and not clear:
        raise SystemExit('Selected dental contact gate needs review')


if __name__ == '__main__':
    main()
