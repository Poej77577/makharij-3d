"""Decode actual GLB nodes/world transforms and verify source/export identity."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'

def load_verified_character():
    manifest = json.loads((FOLDER / 'assembly.manifest.json').read_text())
    source = json.loads((FOLDER / 'evaluated-meshes.json').read_text())
    for filename, key in [('character-assembly.glb', 'glbSha256'), ('character-assembly.blend', 'blendSha256')]:
        assert hashlib.sha256((FOLDER / filename).read_bytes()).hexdigest() == manifest[key], filename
    for path, sha in manifest['inputs'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    scene = trimesh.load_scene(FOLDER / 'character-assembly.glb', process=False)
    grouped = {}
    for node in scene.graph.nodes_geometry:
        transform, geometry = scene.graph[node]
        name = node
        while name not in source['parts']:
            name = scene.graph.transforms.parents.get(name)
            assert name and name != 'world', f'Unexpected visible GLB node: {node}'
        mesh = scene.geometry[geometry]
        world = trimesh.transform_points(mesh.vertices, transform)
        grouped.setdefault(name, []).append(trimesh.Trimesh(world, mesh.faces, process=False))
    assert set(grouped) == set(source['parts']), 'Missing or extra delivered anatomy'
    meshes, checks = {}, {}
    for name, parts in grouped.items():
        mesh = trimesh.util.concatenate(parts)
        p = np.array(source['parts'][name]['positions']).reshape(-1, 3)
        expected_triangles = len(source['parts'][name]['indices']) // 3
        forward_error = float(cKDTree(p).query(mesh.vertices)[0].max())
        reverse_error = float(cKDTree(mesh.vertices).query(p)[0].max())
        assert max(forward_error, reverse_error) < 1e-6, f'{name}: source/export points differ'
        assert len(mesh.faces) == expected_triangles, f'{name}: source/export triangle inventory differs'
        # UV/material/normal boundaries can split GLB indices. Weld an analysis
        # copy at sub-nanometer precision only; never modify the delivered file.
        mesh.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
        if name == 'HEAD_SKIN':
            assert mesh.bounds[1, 1] > .19 and mesh.bounds[0, 1] < -.13, 'Head/neck context was lost during reconstruction'
            assert mesh.extents[2] > .14 and mesh.volume > .002, 'Head volume/scale guard failed'
        meshes[name] = mesh
        checks[name] = {'triangles': len(mesh.faces), 'geometryPositionMaxError_m': max(forward_error, reverse_error),
                        'sourceBoundsMaxError_m': float(abs(mesh.bounds - np.array([p.min(0), p.max(0)])).max())}
    result = {'assetSha256': manifest['glbSha256'], 'parts': checks, 'frame': source['frame'],
              'isAcceptedAnatomy': manifest['isAcceptedAnatomy'], 'scope': 'Actual GLB decode, world transform, per-part source/export positions and triangle inventory; no anatomical approval'}
    (FOLDER / 'export-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return manifest, source, meshes

if __name__ == '__main__':
    manifest, source, meshes = load_verified_character()
    print(json.dumps({'actualGlbParts': len(meshes), 'actualGlbTriangles': sum(len(m.faces) for m in meshes.values()),
                      'sourceExportFrameVerified': True, 'completeAnatomyAccepted': manifest['isAcceptedAnatomy']}, indent=2))
