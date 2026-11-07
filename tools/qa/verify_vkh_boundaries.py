"""Check extracted source boundaries against independently summed cell volumes."""
import json
from pathlib import Path
import sys
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/anatomy'))
from mesh_sources import load_tetra_boundary, load_tetgen_boundary, canonical_vkh, file_sha, load_obj

source = ROOT / 'assets/source/vkh-upper-airway/src/artisynth/models/vkhUpperAirway/geometry/fem'
checks = []
cache_path = ROOT / 'artifacts/milestone-evidence/M1/vkh-upper-airway/source-meshes.json'
cached = json.loads(cache_path.read_text())['parts']
for name in ['Tongue', 'Pharynx', 'Palatine_aponeurosis', 'Suprahyoid_muscles_L', 'Suprahyoid_muscles_R', 'Airway-final2.1']:
    node_path = source / (name + '.node')
    tetgen = name == 'Airway-final2.1'
    cell_path = source / (name + ('.ele' if tetgen else '.elem'))
    data = (load_tetgen_boundary if tetgen else load_tetra_boundary)(node_path, cell_path)
    mesh = trimesh.Trimesh(canonical_vkh(data['points']), data['faces'], process=False)
    # Independent file read and cell-volume accumulation; does not use the
    # boundary adapter's orientation, face incidence or geometry calculations.
    lines = [line.split('#', 1)[0].split() for line in node_path.read_text().splitlines()]
    lines = [row for row in lines if row]
    rows = lines[1:] if tetgen else lines
    source_points = {int(row[0]): np.array(list(map(float, row[1:4]))) for row in rows}
    total = 0.
    cell_lines = [line.split('#', 1)[0].split() for line in cell_path.read_text().splitlines()]
    cell_lines = [row for row in cell_lines if row]
    if tetgen:
        cell_lines = cell_lines[1:]
    for row in cell_lines:
        ids = list(map(int, row[1:5] if tetgen else row[:4]))
        a, b, c, d = [source_points[i] for i in ids]
        total += abs(float(np.dot(b - a, np.cross(c - a, d - a)))) / 6 * 1e-9
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
    relative = abs(mesh.volume - total) / total
    assert relative < 1e-9, f'{name}: boundary/cell volume differs by {relative}'
    assert data['skippedDegenerateCells'] == 0, name
    if name in cached:
        saved = cached[name]
        assert np.array_equal(data['sourceNodeIds'], np.array(saved['sourceNodeIds'])), name
        assert np.max(abs(canonical_vkh(data['points']) - np.array(saved['positions']).reshape(-1, 3))) < 1e-12, name
        assert np.array_equal(data['faces'], np.array(saved['indices']).reshape(-1, 3)), name
    checks.append({'name': name, 'cells': data['cells'], 'boundaryTriangles': len(mesh.faces), 'watertight': True,
                   'consistentOutwardWinding': True, 'cellVolume_m3': total, 'boundaryVolume_m3': float(mesh.volume),
                   'relativeVolumeError': relative, 'sourceSha256': {str(path.relative_to(ROOT)): file_sha(path) for path in [node_path, cell_path]}})
for name in ['Maxilla', 'Mandible', 'Hyoid', 'Thyroid', 'Cricoid']:
    original = load_obj(source.parent / f'rigidBodies/{name}.obj')
    assert np.max(abs(canonical_vkh(original['points']) - np.array(cached[name]['positions']).reshape(-1, 3))) < 1e-12, name
    assert original['faces'] == cached[name]['faces'], name
result = {'checks': checks, 'cachedAssemblyMatchesOriginalSources': True, 'scope': 'Source tetrahedral extraction, independently summed volume, canonical frame and cached FEM/bone identity only; no donor registration, fit, articulation or expert approval'}
out = ROOT / 'artifacts/milestone-evidence/M1/vkh-upper-airway/extraction-verification.json'
out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'sourceBoundariesVerified': len(checks), 'sourceCells': sum(c['cells'] for c in checks), 'maximumRelativeVolumeError': max(c['relativeVolumeError'] for c in checks)}, indent=2))
