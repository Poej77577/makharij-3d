"""Measure actual evaluated vertex motion and return for one source rig bone.

No source file or geometry is exported. Motion is a mechanical observation,
not anatomical validation, a clinical measurement or permission to reuse data.
"""
import argparse
import hashlib
import json
from math import radians
from pathlib import Path
import sys
import bpy
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--input', required=True)
p.add_argument('--report', required=True)
p.add_argument('--rig', required=True)
p.add_argument('--bone', required=True)
p.add_argument('--axis', choices=['X', 'Y', 'Z'], default='X')
p.add_argument('--angle', type=float, default=8)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
source = Path(args.input).resolve()
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
rig = bpy.data.objects[args.rig]
bone = rig.pose.bones[args.bone]
objects = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH' and len(ob.data.vertices)]
def snapshot():
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    result = {}
    for ob in objects:
        evaluated = ob.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        result[ob.name] = np.array([evaluated.matrix_world @ v.co for v in mesh.vertices])
        evaluated.to_mesh_clear()
    return result

rest = snapshot()
original_basis, original_mode = bone.matrix_basis.copy(), bone.rotation_mode
bone.rotation_mode = 'XYZ'
bone.rotation_euler['XYZ'.index(args.axis)] += radians(args.angle)
rig.update_tag()
posed = snapshot()
bone.rotation_mode = original_mode
bone.matrix_basis = original_basis
rig.update_tag()
returned = snapshot()
records = []
for name, points in rest.items():
    assert points.shape == posed[name].shape == returned[name].shape, 'Changing topology cannot be exported as ordinary morph targets'
    displacement = np.linalg.norm(posed[name] - points, axis=1)
    return_error = float(np.linalg.norm(returned[name] - points, axis=1).max())
    diagonal = float(np.linalg.norm(points.max(0) - points.min(0)))
    assert return_error <= max(1e-8, diagonal * 1e-5), 'Pose failed to return: ' + name
    records.append({'mesh': name, 'evaluatedVertices': len(points), 'changedVertices': int((displacement > max(diagonal * 1e-7, 1e-9)).sum()),
        'maxDisplacement_nativeUnits': float(displacement.max()), 'returnError_nativeUnits': return_error})
report = {'sourceSha256': source_sha, 'rig': args.rig, 'bone': args.bone, 'axis': args.axis, 'angle_deg': args.angle,
    'meshes': records, 'anyActualVertexMovement': any(r['changedVertices'] for r in records),
    'sourceWritten': False, 'embeddedCodeExecuted': False, 'isAcceptedAnatomy': False,
    'scope': 'Actual evaluated native vertex movement and return only; original scale not assumed clinical; no full speech rig or visual acceptance claim'}
target = Path(args.report).resolve(); target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'bone': args.bone, 'actualMovement': report['anyActualVertexMovement'],
    'changedMeshes': [r for r in records if r['changedVertices']], 'unchangedMeshes': [r['mesh'] for r in records if not r['changedVertices']]}, indent=2))
if not report['anyActualVertexMovement']:
    raise SystemExit('FAIL: bone exists but did not change evaluated geometry')
