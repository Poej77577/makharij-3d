"""Independent checks of the exported head study; never accepts full anatomy."""
from pathlib import Path
import hashlib
import json

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
folder = ROOT / 'artifacts/milestone-evidence/M1/makehuman-adult-head-study/rest'
record = json.loads((folder / 'head-study.manifest.json').read_text())
blob = (folder / 'head-study.glb').read_bytes()
assert hashlib.sha256(blob).hexdigest() == record['glbSha256']
assert hashlib.sha256((folder / 'head-study.blend').read_bytes()).hexdigest() == record['blendSha256']
assert record['isAcceptedAnatomy'] is False
for path, sha in record['sourceSha256'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path

scene = trimesh.load_scene(folder / 'head-study.glb', process=False)
vertices, meshes = [], []
for node in scene.graph.nodes_geometry:
    transform, name = scene.graph[node]
    mesh = scene.geometry[name]
    world = trimesh.transform_points(mesh.vertices, transform)
    assert np.isfinite(world).all()
    assert 'helper' not in node.lower(), 'Fitting helper exported as visible anatomy'
    vertices.append(world)
    meshes.append({'node': node, 'vertices': len(world), 'triangles': len(mesh.faces)})
assert len(meshes) >= 2, 'Expected skin and source-fitted eyes'
q = np.vstack(vertices)
bounds = np.array([q.min(0), q.max(0)])
error = float(abs(bounds - np.array(record['evaluatedSourceBounds_m'])).max())
assert error < 1e-6, f'Source/export frame or evaluated geometry mismatch: {error} m'
size = bounds[1] - bounds[0]
assert .15 < size[1] < .5, 'Head-study meter-scale transfer guard failed'
result = {
    'assetSha256': record['glbSha256'],
    'sourceBlendSha256': record['blendSha256'],
    'worldBoundsMaxError_m': error,
    'dimensions_m': size.tolist(),
    'meshes': meshes,
    'sourceFilesUnchanged': True,
    'visibleFittingHelpers': False,
    'completeAnatomyAccepted': False,
    'missing': record['missing'],
    'scope': 'Exported static geometry, units/frame and source identity only. No internal registration, collision, visual-quality, articulation or expert approval.',
}
(folder / 'export-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
