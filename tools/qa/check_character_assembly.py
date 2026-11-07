"""Independent diagnostic checks of delivered mixed-source static geometry.

This checker does not change the source mesh, fit, collision threshold, or
review state. Inspection mode reports real defects; --gate fails on them.
"""
import argparse
import json
from pathlib import Path

import fcl
import numpy as np
import trimesh
from delivered_character import load_verified_character

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--gate', action='store_true')
args = parser.parse_args()
folder = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
manifest, data, delivered = load_verified_character()
meshes, objects, topology = {}, {}, {}
for name, part in data['parts'].items():
    p = delivered[name].vertices
    faces = delivered[name].faces
    assert np.isfinite(p).all() and len(p) and len(faces), name
    assert faces.min() >= 0 and faces.max() < len(p), name
    mesh = trimesh.Trimesh(p, faces, process=False)
    areas = mesh.area_faces
    assert (areas > 1e-15).all(), f'{name}: zero-area triangle'
    edges, count = np.unique(np.sort(mesh.edges, axis=1), axis=0, return_counts=True)
    claimed = part['closedTissueVolumeClaimed']
    if claimed:
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
    meshes[name] = mesh
    tree = fcl.BVHModel()
    tree.beginModel(len(p), len(faces))
    tree.addSubModel(p, faces.astype(np.int32))
    tree.endModel()
    objects[name] = fcl.CollisionObject(tree)
    topology[name] = {'vertices': len(p), 'triangles': len(faces), 'closedTissueVolumeClaimed': claimed,
                      'isWatertight': bool(mesh.is_watertight), 'consistentWinding': bool(mesh.is_winding_consistent),
                      'boundaryEdges': int((count == 1).sum()), 'nonmanifoldEdges': int((count > 2).sum()),
                      'minimumTriangleArea_m2': float(areas.min()), 'bounds_m': mesh.bounds.tolist()}

# These pairs must not intersect at rest; intended tongue-floor/root attachment
# is a separate review and cannot be used to waive dental/roof penetration.
critical_pairs = [('TONGUE', n) for n in ['UPPER_TEETH', 'LOWER_TEETH', 'HARD_PALATE', 'SOFT_PALATE']]
critical_pairs += [('HEAD_SKIN', n) for n in ['UPPER_TEETH', 'LOWER_TEETH', 'HARD_PALATE', 'SOFT_PALATE']]
diagnostic_pairs = [('HEAD_SKIN', n) for n in ['TONGUE', 'PHARYNX', 'MOUTH_FLOOR_LEFT', 'MOUTH_FLOOR_RIGHT', 'THYROID', 'CRICOID']]
diagnostic_pairs += [('TONGUE', n) for n in ['PHARYNX', 'MOUTH_FLOOR_LEFT', 'MOUTH_FLOOR_RIGHT', 'GINGIVA_UPPER', 'GINGIVA_LOWER']]
critical_pairs += [('NASAL_LINING', n) for n in ['TONGUE', 'HARD_PALATE', 'UPPER_TEETH', 'LOWER_TEETH']]
diagnostic_pairs += [('NASAL_LINING', n) for n in ['SOFT_PALATE', 'PHARYNX', 'HEAD_SKIN']]
collisions, distances, failures = [], [], []
for a, b in critical_pairs + diagnostic_pairs:
    result = fcl.CollisionResult()
    fcl.collide(objects[a], objects[b], fcl.CollisionRequest(num_max_contacts=1000, enable_contact=True), result)
    distance = fcl.distance(objects[a], objects[b], fcl.DistanceRequest(), fcl.DistanceResult())
    record = {'pair': [a, b], 'minimumSurfaceDistance_m': float(distance), 'criticalRestClearance': (a, b) in critical_pairs}
    distances.append(record)
    if result.is_collision:
        q = np.array([contact.pos for contact in result.contacts])
        record = {**record, 'reportedTriangleContacts': len(q), 'contactBounds_m': [q.min(0).tolist(), q.max(0).tolist()] if len(q) else None,
                  'contactSample_m': q[:8].tolist()}
        collisions.append(record)
        if (a, b) in critical_pairs:
            failures.append({'pair': [a, b], 'reason': 'rest tissue/crown surface intersection'})

result = {'assetSha256': manifest['glbSha256'], 'topology': topology, 'surfaceDistances': distances,
          'surfaceIntersections': collisions, 'criticalRestClearancePassed': not failures, 'failures': failures,
          'anatomyAccepted': False, 'scope': 'Independent actual GLB decode, static triangle topology and FCL surface checks. No attachment continuity, airway patency, deformation or expert approval.',
          'stillRequired': manifest['unfinished'], 'gateRequested': args.gate}
(folder / 'geometry-diagnostics.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'triangles': sum(v['triangles'] for v in topology.values()), 'closedVolumeChecks': sum(v['closedTissueVolumeClaimed'] for v in topology.values()),
                  'criticalFailures': failures, 'diagnosticIntersectionPairs': [r['pair'] for r in collisions], 'anatomyAccepted': False}, indent=2))
if args.gate and (failures or manifest['unfinished']):
    raise SystemExit('M2 GATE FAILED: resolve recorded geometry and structural tasks before accepting anatomy')
