"""Source-shaped outer nasal context void; all actual tissues remain positive.

A local alpha complex can leave head tissue inside the real nasal passage.
Use the complete outer hull of actual mucosal and turbinate source points for
this negative context envelope. This is not a visible organ or measured flow.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from mesh_sources import ROOT, file_sha

p = argparse.ArgumentParser(); p.add_argument('--folder', required=True); args = p.parse_args()
out = Path(args.folder)
source_path = ROOT / 'assets/source/z-anatomy/construction-surfaces.json'
bone_path = ROOT / 'assets/source/z-anatomy/reference-meshes.json'
source = json.loads(source_path.read_text())['parts']['Mucosa of nasal cavity']
bone = json.loads(bone_path.read_text())['parts']['ATLAS_INFERIOR_NASAL_CONCHA_BONE_R']
mesh = trimesh.Trimesh(np.array(bone['positions']).reshape(-1, 3), np.array(bone['indices']).reshape(-1, 3), process=False)
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
points = np.vstack([np.array(source['positions']).reshape(-1, 3), mesh.vertices + mesh.vertex_normals * .0008])
points = points[points[:, 2] >= -1e-8].copy()
points[:, 2] = np.maximum(points[:, 2], .00035)
points = np.unique(np.round(points, 9), axis=0)
envelope = trimesh.convex.convex_hull(points)
assert envelope.is_watertight and envelope.is_winding_consistent and envelope.volume > 0 and envelope.body_count == 1
spaces = []
for side in [1, -1]:
    q = envelope.vertices.copy(); q[:, 2] *= side
    faces = envelope.faces if side == 1 else envelope.faces[:, ::-1]
    spaces.append({'name': 'Source nasal outer envelope ' + ('right' if side == 1 else 'left'),
        'positions': q.ravel().tolist(), 'indices': faces.ravel().tolist()})
record = {'spaces': spaces, 'sourceSha256': file_sha(source_path), 'sourceBoneSha256': file_sha(bone_path),
    'method': 'Outer hull of actual nasal mucosal and turbinate source points; actual septum, mucosa and conchae remain positive tissues inside',
    'medialReferencePlane_m': .00035, 'sourceTurbinateCoverReference_m': .0008,
    'role': 'Negative context only, never a visible anatomical substitute', 'clinicalMeasurement': False}
(out / 'source-nasal-envelope.json').write_text(json.dumps(record, separators=(',', ':')) + '\n')
print(json.dumps({'method': record['method'], 'halfVolume_m3': envelope.volume, 'sourcePoints': len(points)}, indent=2))
