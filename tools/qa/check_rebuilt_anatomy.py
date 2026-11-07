"""Independent actual-delivery checks for the new coherent resting anatomy.

These checks establish selected static properties, not scientific approval or
rig readiness. Expected nested tongue muscles are not treated as collisions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from mesh_self_contacts import self_contact_report

p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/milestone-evidence/M2/realistic-rebuild')
p.add_argument('--gate', action='store_true')
args = p.parse_args()
folder = Path(args.folder)
review_path = Path(__file__).resolve().parents[2] / 'assets/calibration/visual-review.json'
review = json.loads(review_path.read_text()) if review_path.exists() else {}
manifest = json.loads((folder / 'atlas-study.manifest.json').read_text())
family = manifest.get('reconstructionFamily', 'atlas-reconstruction-v2')
visual_review = 'fail' if review.get('routeId') == family and review.get('status') == 'rejected' else 'pending'
reference = json.loads((folder / 'atlas-meshes.json').read_text())['parts']
sections = json.loads((folder / 'atlas-sections.json').read_text())
nasal_sections = json.loads((folder / 'atlas-nasal-sections.json').read_text())
asset_sha = hashlib.sha256((folder / 'atlas-study.glb').read_bytes()).hexdigest()
assert asset_sha == manifest['glbSha256'] == sections['assetSha256']
assert asset_sha == nasal_sections['assetSha256']
assert abs(sections['planeZ_m'] - .00501) < 1e-9 and abs(nasal_sections['planeZ_m'] - .00901) < 1e-9
assert hashlib.sha256((folder / 'atlas-study.blend').read_bytes()).hexdigest() == manifest['blendSha256']
scene = trimesh.load_scene(folder / 'atlas-study.glb', process=False)
grouped = {}
for node in scene.graph.nodes_geometry:
    transform, key = scene.graph[node]
    mesh = scene.geometry[key].copy(); mesh.apply_transform(transform)
    ancestor = node
    while ancestor not in reference:
        ancestor = scene.graph.transforms.parents.get(ancestor)
        assert ancestor and ancestor != 'world', node
    grouped.setdefault(ancestor, []).append(mesh)
assert set(grouped) == set(reference)
meshes, records, failures = {}, {}, []
for name, parts in grouped.items():
    mesh = trimesh.util.concatenate(parts)
    expected = reference[name]
    all_points = np.array(expected['positions']).reshape(-1, 3)
    expected_faces = np.array(expected['indices']).reshape(-1, 3)
    points = all_points[np.unique(expected_faces)]
    assert len(mesh.faces) == len(expected['indices']) // 3, name
    error = max(float(cKDTree(points).query(mesh.vertices)[0].max()), float(cKDTree(mesh.vertices).query(points)[0].max()))
    assert error < 1e-7, name
    source_mesh = trimesh.Trimesh(all_points, expected_faces, process=False)
    assert abs(source_mesh.area - mesh.area) < 1e-10, name
    assert abs(source_mesh.volume - mesh.volume) < 1e-10, name
    mesh.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
    meshes[name] = mesh
    records[name] = {'triangles': len(mesh.faces), 'positionMaxError_m': error,
        'unusedSourceVerticesNotExported': len(all_points) - len(points),
        'closedOutwardVolume': bool(mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0),
        'components': int(mesh.body_count), 'volume_m3': float(mesh.volume)}

required = ['HEAD_SKIN', 'ATLAS_TONGUE', 'ATLAS_GINGIVA', 'ATLAS_SOFT_PALATE', 'ATLAS_UVULA_OF_PALATE',
    'ATLAS_MUCOSA_OF_NASAL_CAVITY', 'ATLAS_NASAL_SEPTAL_CARTILAGE', 'ATLAS_NASOPHARYNX', 'ATLAS_OROPHARYNX',
    'ATLAS_LARYNGOPHARYNX', 'ATLAS_EPIGLOTTIS', 'ATLAS_TRACHEA', 'ATLAS_MANDIBLE',
    'ATLAS_INFERIOR_CONCHA_MUCOSA_L', 'ATLAS_INFERIOR_CONCHA_MUCOSA_R']
for name in required:
    if name not in meshes or not records[name]['closedOutwardVolume']:
        failures.append('Required closed tissue missing or invalid: ' + name)
if records['ATLAS_TONGUE']['components'] != 1:
    failures.append('Tongue and root must form one connected closed volume')
if not (25e-6 < records['ATLAS_TONGUE']['volume_m3'] < 85e-6):
    failures.append('Tongue volume outside broad adult sanity bounds')
tissue_surfaces = []
for name in ['ATLAS_TONGUE', 'ATLAS_SOFT_PALATE', 'ATLAS_MUCOSA_OF_NASAL_CAVITY', 'ATLAS_TRACHEA',
    'ATLAS_INFERIOR_CONCHA_MUCOSA_L', 'ATLAS_INFERIOR_CONCHA_MUCOSA_R']:
    mesh = meshes[name]
    contact = self_contact_report(name, mesh, limit=max(300000, len(mesh.faces) * 50))
    tissue_surfaces.append(contact)
    if contact['nonadjacentIntersectingTrianglePairs'] or contact['truncated']:
        failures.append('Authored tissue surface intersects itself or check saturated: ' + name)
failures += ['Invalid tissue section: ' + str(item) for item in sections['sectionFailures']]
failures += ['Invalid nasal tissue section: ' + str(item) for item in nasal_sections['sectionFailures']]

manager = trimesh.collision.CollisionManager()
manager.add_object('whole-tongue', meshes['ATLAS_TONGUE'])
clearances = []
for name, mesh in sorted(meshes.items()):
    if not any(word in name for word in ['INCISOR', 'PREMOLAR', 'MOLAR', 'CANINE', 'MANDIBLE']):
        continue
    intersects, contacts = manager.in_collision_single(mesh, return_data=True)
    distance = float(manager.min_distance_single(mesh))
    clearances.append({'part': name, 'intersectingSurfaces': bool(intersects), 'minimumDistance_m': distance,
        'triangleContacts': len(contacts)})
    if intersects:
        failures.append('Tongue intersects rigid dental/skeletal tissue: ' + name)
air = json.loads((folder / 'atlas-airspace-verification.json').read_text())
if not air['passed']:
    failures.append('Negative airspace preflight failed')
normal = manifest.get('portableMaterials', {})
if normal.get('sha256') != hashlib.sha256((folder / 'tongue-normal.png').read_bytes()).hexdigest():
    failures.append('Portable tongue normal map is missing or stale')
report = {'assetSha256': asset_sha, 'parts': records, 'requiredClosedTissues': required,
    'authoredTissueSurfaces': tissue_surfaces,
    'tongueRigidClearances': clearances, 'airspacePreflightPassed': air['passed'], 'geometryFailures': failures,
    'staticGeometryPassed': not failures, 'visualReview': visual_review, 'visualReviewSource': 'assets/calibration/visual-review.json', 'expertReview': 'pending',
    'isAcceptedAnatomy': False, 'rigReady': False,
    'scope': 'Actual exported GLB identity, selected closed tissue volumes, root continuity, computed sections, tongue/rigid-tissue separation and actual airspace preflight; no clinical registration, motion or expert approval'}
(folder / 'anatomy-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'parts': len(records), 'triangles': sum(r['triangles'] for r in records.values()),
    'tongueComponents': records['ATLAS_TONGUE']['components'], 'rigidPairs': len(clearances),
    'geometryFailures': failures, 'staticGeometryPassed': not failures, 'isAcceptedAnatomy': False}, indent=2))
if failures or args.gate:
    raise SystemExit('FAIL: ' + ('; '.join(failures) if failures else 'Visual review: ' + visual_review + '; expert acceptance pending'))
