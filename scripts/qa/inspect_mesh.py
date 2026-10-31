#!/usr/bin/env python3
"""Inspect acquired meshes without repairing them or asserting scientific validity.
Run with PYTHONPATH=/tmp/makharij-qa-deps python scripts/qa/inspect_mesh.py FILE --out REPORT.
World transforms are applied; dimensions remain in source units until a separately
verified axis/unit contract is supplied. Open surfaces have no signed-volume claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh


def inspect(path):
    scene = trimesh.load_scene(path, process=False)
    records = []
    failures = []
    for node in scene.graph.nodes_geometry:
        transform, geometry_name = scene.graph[node]
        source = scene.geometry[geometry_name]
        if not isinstance(source, trimesh.Trimesh):
            records.append({'node': node, 'geometry': geometry_name, 'type': type(source).__name__})
            continue
        mesh = source.copy()
        mesh.apply_transform(transform)
        finite = bool(np.isfinite(mesh.vertices).all())
        if not finite or not len(mesh.faces):
            failures.append(f'{node}: invalid or empty mesh')
        areas = mesh.area_faces if finite and len(mesh.faces) else np.array([])
        records.append({
            'node': node, 'geometry': geometry_name, 'type': 'Trimesh',
            'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
            'finite_vertices': finite,
            'bounds_source_units': mesh.bounds.tolist() if finite and len(mesh.vertices) else None,
            'extents_source_units': mesh.extents.tolist() if finite and len(mesh.vertices) else None,
            'world_transform': transform.tolist(),
            'watertight': bool(mesh.is_watertight),
            'winding_consistent': bool(mesh.is_winding_consistent),
            'is_volume': bool(mesh.is_volume),
            'degenerate_triangles': int(np.count_nonzero(areas <= 0)),
            'boundary_edges': int(np.count_nonzero(np.bincount(mesh.edges_unique_inverse) == 1)),
            'signed_volume_source_units_cubed': float(mesh.volume) if mesh.is_volume else None,
            'euler_number': int(mesh.euler_number),
        })
    if not records:
        failures.append('No geometry nodes loaded')
    return {'file': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size, 'loader': f'trimesh {trimesh.__version__}',
            'scene_geometry_count': len(scene.geometry), 'instances': records,
            'failures': failures,
            'scope': 'Unrepaired source geometry and transforms only. No anatomical, rig, collision, cavity or license approval.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.file)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'file': report['file'], 'instances': len(report['instances']), 'failures': report['failures'], 'report': str(args.out)}, ensure_ascii=False))
    raise SystemExit(1 if report['failures'] else 0)
