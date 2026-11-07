"""Compare actual animated GLB geometry with its native source, in a clean scene.

Mechanical evidence only. This check must never promote anatomical acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

p = argparse.ArgumentParser()
p.add_argument('--blend', required=True)
p.add_argument('--glb', required=True)
p.add_argument('--object', required=True)
p.add_argument('--out', required=True)
p.add_argument('--frames', type=int, nargs='+', default=[1, 13, 25, 49, 61, 73, 97, 109, 121, 145])
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
blend, glb, out = map(lambda v: Path(v).resolve(), (a.blend, a.glb, a.out))
failures = []


def snapshot(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    evaluated = ob.evaluated_get(dg)
    mesh = evaluated.to_mesh()
    points = [evaluated.matrix_world@v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return points


def directed_distance(points, reference):
    tree = KDTree(len(reference))
    for i, point in enumerate(reference):
        tree.insert(point, i)
    tree.balance()
    return max((tree.find(point)[2] for point in points), default=0)


bpy.ops.wm.open_mainfile(filepath=str(blend), use_scripts=False, load_ui=False)
source_ob = bpy.data.objects[a.object]
source_shapes = [key.name for key in source_ob.data.shape_keys.key_blocks][1:]
expected = {}
for frame in a.frames:
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    expected[frame] = snapshot(source_ob)
fps = bpy.context.scene.render.fps
expected_count = len(source_ob.data.vertices)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = fps
bpy.ops.import_scene.gltf(filepath=str(glb))
ob = bpy.data.objects.get(a.object)
if ob is None or ob.type != 'MESH':
    raise RuntimeError('Expected exported mesh is missing')
if len([o for o in bpy.context.scene.objects if o.type == 'MESH']) != 1:
    failures.append('Unexpected context mesh exported')
keys = ob.data.shape_keys
actual_shapes = [key.name for key in keys.key_blocks][1:] if keys else []
if actual_shapes != source_shapes:
    failures.append('Morph names/order changed')
if not keys or not keys.animation_data or not keys.animation_data.action:
    failures.append('Morph animation did not arrive')
results = []
delivered = {}
for frame in a.frames:
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    points = snapshot(ob)
    delivered[frame] = points
    error = max(directed_distance(points, expected[frame]), directed_distance(expected[frame], points))
    if error > 2e-6:
        failures.append(f'Frame {frame}: export deviation {error}m')
    results.append({'frame': frame, 'symmetricNearestSurfaceVertexDistance_m': error,
                    'sourceVertices': len(expected[frame]), 'deliveredVertices': len(points),
                    'morphWeights': {key.name: key.value for key in keys.key_blocks[1:]} if keys else {}})
first, last = a.frames[0], a.frames[-1]
return_error = max(directed_distance(delivered[first], delivered[last]), directed_distance(delivered[last], delivered[first]))
if return_error > 1e-7:
    failures.append('Exported animation does not return to rest')
report = {'scope': 'Actual GLB morph geometry/animation roundtrip only',
          'anatomicalAcceptance': 'not assessed', 'productionSelected': False,
          'blendSha256': hashlib.sha256(blend.read_bytes()).hexdigest(),
          'glbSha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
          'sourceShapeKeys': source_shapes, 'deliveredShapeKeys': actual_shapes,
          'sourceVertices': expected_count, 'deliveredVertices': len(ob.data.vertices),
          'frames': results, 'returnToRestError_m': return_error,
          'failures': failures, 'mechanicalRoundtripPass': not failures}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'report': str(out), 'pass': not failures, 'failures': failures,
                  'maxDeviation_m': max(r['symmetricNearestSurfaceVertexDistance_m'] for r in results),
                  'returnToRestError_m': return_error}, indent=2))
if failures:
    raise RuntimeError('Actual GLB/source comparison failed')
