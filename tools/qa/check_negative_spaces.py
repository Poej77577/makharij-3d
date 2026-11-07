"""Validate real 3-D negative-space helpers before any head Boolean operation."""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh
from mesh_self_contacts import self_contact_report

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
checks, failures = [], []
for name in ['nasal-airspace-helper', 'research-airspace-helper', 'lower-airway-helper']:
    path = OUT / (name + '.json')
    data = json.loads(path.read_text())
    mesh = trimesh.Trimesh(np.array(data['positions']).reshape(-1, 3), np.array(data['indices']).reshape(-1, 3), process=False)
    record = {**self_contact_report(name, mesh), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'watertight': bool(mesh.is_watertight), 'consistentWinding': bool(mesh.is_winding_consistent),
              'volume_m3': float(mesh.volume), 'minimumTriangleArea_m2': float(mesh.area_faces.min())}
    checks.append(record)
    if not (record['watertight'] and record['consistentWinding'] and record['volume_m3'] > 0 and record['minimumTriangleArea_m2'] > 1e-15):
        failures.append(name + ': invalid tissue-space boundary')
    if record['nonadjacentIntersectingTrianglePairs'] or record['truncated']:
        failures.append(name + ': self-intersections or incomplete enumeration')
report = {'checks': checks, 'failures': failures, 'passed': not failures, 'scope': 'Negative-space helper topology, volume and nonadjacent FCL self-intersections. No acquired lower-airway or patency claim.'}
(OUT / 'negative-space-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
if failures:
    raise SystemExit('FAIL: invalid negative-space helper')
