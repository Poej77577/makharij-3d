"""External-face source/export checks. No closed-cranium or clinical claim."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/method-evidence/face-context')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder = ROOT/a.folder
m = json.loads((folder/'face-manifest.json').read_text())
for ext in ['blend', 'glb']:
    assert hashlib.sha256((folder/('face-context.'+ext)).read_bytes()).hexdigest() == m[ext+'Sha256']
cases = [('rest', {})]
for control in ['JAW_OPEN', 'LIP_PRESS', 'LIP_ROUND', 'LIP_PROTRUDE']:
    for value in [.5, 1]:
        cases.append((control+'_'+str(value), {control: value}))
cases += [('combined', {'JAW_OPEN': .6, 'LIP_ROUND': .4, 'LIP_PROTRUDE': .3}), ('return', {})]


def points(ob):
    evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = [evaluated.matrix_world@v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return result


def maximum_distance(first, second):
    tree = KDTree(len(second))
    for i, point in enumerate(second):
        tree.insert(point, i)
    tree.balance()
    return max(tree.find(point)[2] for point in first)


bpy.ops.wm.open_mainfile(filepath=str(folder/'face-context.blend'), use_scripts=False, load_ui=False)
master = bpy.data.objects[m['nativeControlMaster']]
master.animation_data_clear()
source = {}
for label, values in cases:
    for name in m['controls']:
        master[name] = float(values.get(name, 0))
    master.update_tag()
    bpy.context.view_layer.update()
    source[label] = {name: points(bpy.data.objects[name]) for name in m['parts']}
source_shapes = [key.name for key in bpy.data.objects['HEAD_EXTERNAL'].data.shape_keys.key_blocks][1:]
assert 'source_vertex_id' in bpy.data.objects['SOURCE_HEAD'].data.attributes
assert bpy.data.objects['HEAD_EXTERNAL']['context_only']

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(folder/'face-context.glb'))
objects = {name: bpy.data.objects.get(name) for name in m['parts']}
assert all(ob is not None for ob in objects.values())
keys = objects['HEAD_EXTERNAL'].data.shape_keys
assert [key.name for key in keys.key_blocks][1:] == source_shapes
keys.animation_data_clear()
results, failures = [], []
for label, values in cases:
    for key in keys.key_blocks[1:]:
        key.value = values.get(key.name, 0)
    keys.update_tag()
    bpy.context.view_layer.update()
    row = {'case': label, 'controls': values, 'partErrors_m': {}}
    for name, ob in objects.items():
        actual, expected = points(ob), source[label][name]
        error = max(maximum_distance(actual, expected), maximum_distance(expected, actual))
        row['partErrors_m'][name] = error
        if error > 2e-6:
            failures.append(label+'/'+name+': source/GLB deviation')
    results.append(row)
raw = (folder/'face-context.glb').read_bytes()
size, kind = struct.unpack_from('<II', raw, 12)
assert kind == 0x4E4F534A
document = json.loads(raw[20:20+size])
color_present = any('COLOR_0' in primitive['attributes'] for mesh in document['meshes'] for primitive in mesh['primitives'])
eye_modes = [item.get('alphaMode', 'OPAQUE') for item in document['materials'] if 'eye texture' in item.get('name', '').lower()]
if not color_present:
    failures.append('Authored skin/vermilion vertex colors did not export')
if not eye_modes or any(mode == 'OPAQUE' for mode in eye_modes):
    failures.append('Original corneal alpha was not retained')
report = {'scope': 'Actual external face/eye data and 11 source/GLB poses',
          'clinicalAcceptance': 'pending', 'fullInternalHeadComplete': False,
          'contextSurfaceOnly': True, 'cranialVolumeCertified': False,
          'blendSha256': m['blendSha256'], 'glbSha256': m['glbSha256'],
          'sourceShapes': source_shapes, 'nativeSingleControlOwner': m['nativeControlMaster'],
          'vertexColorsExported': color_present, 'eyeMaterialAlphaModes': eye_modes,
          'cases': results, 'failures': failures, 'technicalPass': not failures}
(folder/'technical-review.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'technicalPass': not failures, 'cases': len(cases), 'failures': failures}, indent=2))
if failures:
    raise RuntimeError('Face context source/export check failed')
