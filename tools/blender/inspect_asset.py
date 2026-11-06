"""Read real Blender/OBJ/glTF geometry and emit evidence without editing inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--input', default='assets/anatomy/makharij-rest.blend')
parser.add_argument('--out', default='artifacts/milestone-evidence/M0/legacy-source-inspection.json')
opts = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
source = (ROOT / opts.input).resolve()
if not source.is_file():
    raise FileNotFoundError(source)
sha = hashlib.sha256(source.read_bytes()).hexdigest()
if source.suffix == '.blend':
    bpy.ops.wm.open_mainfile(filepath=str(source))
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix.lower() == '.obj':
        bpy.ops.wm.obj_import(filepath=str(source))
    elif source.suffix.lower() in {'.glb', '.gltf'}:
        bpy.ops.import_scene.gltf(filepath=str(source))
    else:
        raise ValueError('Supported inputs: .blend, .obj, .glb, .gltf')

records = []
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    mesh = ob.data
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    corners = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
    records.append({
        'name': ob.name,
        'vertices': len(mesh.vertices),
        'triangles': len(mesh.loop_triangles),
        'boundaryEdges': sum(e.is_boundary for e in bm.edges),
        'nonManifoldEdges': sum(not e.is_manifold for e in bm.edges),
        'degenerateTriangles': sum(t.area < 1e-14 for t in mesh.loop_triangles),
        'worldBounds': [[min(c[i] for c in corners) for i in range(3)], [max(c[i] for c in corners) for i in range(3)]],
        'materials': [m.name for m in mesh.materials if m],
        'shapeKeys': [k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
        'armatureModifiers': [m.object.name for m in ob.modifiers if m.type == 'ARMATURE' and m.object],
    })
    bm.free()
if not records:
    raise ValueError('No mesh geometry was inspected')
report = {
    'source': str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
    'sha256': sha,
    'blenderVersion': bpy.app.version_string,
    'sceneMetersPerUnit': bpy.context.scene.unit_settings.scale_length,
    'meshCount': len(records),
    'meshes': records,
    'scope': 'Measured file geometry only. No visual, anatomical, license or articulation approval.',
    'inputUnchanged': hashlib.sha256(source.read_bytes()).hexdigest() == sha,
}
if not report['inputUnchanged']:
    raise RuntimeError('Input changed during inspection')
out = (ROOT / opts.out).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'meshCount': len(records), 'sha256': sha, 'report': str(out)}))
