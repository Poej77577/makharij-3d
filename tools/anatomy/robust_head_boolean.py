"""Closed source skin minus independently checked real air-space volumes.

Use robust double-precision manifold operations, with material provenance and
interpolated source UVs. No whole-head voxelization or facial smoothing.
"""
import argparse
import json
from pathlib import Path
import manifold3d as md
import numpy as np
import trimesh

p = argparse.ArgumentParser(); p.add_argument('--folder', required=True); args = p.parse_args()
out = Path(args.folder)
head = json.loads((out / 'head-before-cavities.json').read_text())
spaces = json.loads((out / 'atlas-airspaces.json').read_text())['spaces']
base_id = md.Manifold.reserve_ids(3 + len(spaces))
material_for_id = {base_id + i: i for i in range(3)}

def solid(properties, faces, material_ids):
    properties = np.ascontiguousarray(properties, dtype=np.float64)
    faces = np.array(faces, dtype=np.uint64)
    # Source UV/material seams may duplicate shared positions. Merge positions
    # only; retain every independent UV property for interpolation.
    _, first, inv = np.unique(properties[:, :3], axis=0, return_index=True, return_inverse=True)
    target = first[inv]
    source = np.flatnonzero(target != np.arange(len(properties)))
    materials = np.array(material_ids)
    order = np.argsort(materials, kind='stable')
    faces, materials = faces[order], materials[order]
    starts = np.r_[0, np.flatnonzero(np.diff(materials)) + 1, len(faces)]
    ids = materials[starts[:-1]]
    mesh = md.Mesh64(properties, np.ascontiguousarray(faces),
        merge_from_vert=source.astype(np.uint64), merge_to_vert=target[source].astype(np.uint64),
        run_index=(starts * 3).astype(np.uint64), run_original_id=ids.astype(np.uint32))
    volume = md.Manifold(mesh)
    assert volume.status() == md.Error.NoError and volume.volume() > 0, str(volume.status())
    return volume

current = solid(head['properties'], head['faces'], np.array(head['materialIds']) + base_id)
operations = []
for i, space in enumerate(spaces):
    points = np.array(space['positions']).reshape(-1, 3)
    # Separate coincident source-wall boundaries by a documented submillimeter
    # tolerance. This affects only the negative context envelope; all actual
    # mucosal/organ geometry retains its native anatomical placement.
    center = points.mean(axis=0)
    expanded = center + (points - center) * 1.004
    margin = float(np.linalg.norm(expanded - points, axis=1).max())
    assert margin < .0004
    points = expanded
    faces = np.array(space['indices']).reshape(-1, 3)
    source_id = base_id + 3 + i
    material_for_id[source_id] = 1
    cutter = solid(np.c_[points, points[:, :2] * 10], faces, np.full(len(faces), source_id))
    before, cavity = current.volume(), cutter.volume()
    current = current - cutter
    after = current.volume()
    assert current.status() == md.Error.NoError and after > .002
    assert -1e-10 <= before - after <= cavity + 1e-10
    operations.append({'source': space['name'], 'before_m3': before, 'after_m3': after, 'airspace_m3': cavity,
        'negativeEnvelopeScale': 1.004, 'maximumEnvelopeDisplacement_m': margin})

# GLB stores positions in float32. Remove submicron slivers before that
# conversion, so a mathematically closed double-precision mesh stays closed in
# the actual delivered representation. This does not smooth facial surfaces.
current = current.set_tolerance(1e-6).simplify(1e-6)
mesh = current.to_mesh()
props, faces = np.array(mesh.vert_properties), np.array(mesh.tri_verts)
materials = np.zeros(len(faces), dtype=int)
for i, original in enumerate(mesh.run_original_id):
    materials[np.array(mesh.run_index)[i] // 3:np.array(mesh.run_index)[i + 1] // 3] = material_for_id[original]
check = trimesh.Trimesh(props[:, :3], faces, process=False)
check.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
assert check.is_watertight and check.is_winding_consistent and check.volume > .002
assert abs(check.volume - current.volume()) < 1e-10
record = {'properties': props.tolist(), 'faces': faces.tolist(), 'materialIds': materials.tolist(),
    'operations': operations, 'verification': {'watertight': True, 'windingConsistent': True,
    'volume_m3': float(check.volume), 'minimumFeatureTolerance_m': 1e-6,
    'method': 'Manifold3D source-space Boolean, simplified for actual float32 delivery; original skin UVs/material provenance retained'}}
(out / 'head-boolean-result.json').write_text(json.dumps(record, separators=(',', ':')) + '\n')
print('CLOSED_ANATOMICAL_HEAD', json.dumps(record['verification']))
