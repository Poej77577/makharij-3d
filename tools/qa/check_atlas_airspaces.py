"""Independent topology/self-intersection preflight for actual atlas airspaces."""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from mesh_self_contacts import self_contact_report

p = argparse.ArgumentParser(); p.add_argument('--folder', required=True); args = p.parse_args()
folder = Path(args.folder)
data = json.loads((folder / 'atlas-airspaces.json').read_text())
checks, failures = [], []
for part in data['spaces']:
    mesh = trimesh.Trimesh(np.array(part['positions']).reshape(-1, 3), np.array(part['indices']).reshape(-1, 3), process=False)
    r = {**self_contact_report(part['name'], mesh), 'watertight': bool(mesh.is_watertight),
         'windingConsistent': bool(mesh.is_winding_consistent), 'volume_m3': float(mesh.volume), 'minimumArea_m2': float(mesh.area_faces.min())}
    checks.append(r)
    if not r['watertight'] or not r['windingConsistent'] or r['volume_m3'] <= 0 or r['minimumArea_m2'] <= 1e-15 or r['nonadjacentIntersectingTrianglePairs'] or r['truncated']:
        failures.append(part['name'])
(folder / 'atlas-airspace-verification.json').write_text(json.dumps({'checks': checks, 'failures': failures, 'passed': not failures}, indent=2) + '\n')
print(json.dumps({'airspaces': checks, 'failures': failures}, indent=2))
if failures:
    raise SystemExit('FAIL: actual source air-space closure requires repair before head subtraction')
