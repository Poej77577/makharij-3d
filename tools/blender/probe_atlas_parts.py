"""Selective read-only measurement of atlas parts; no template/script execution."""
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--selection', required=True)
p.add_argument('--out', required=True)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
names = json.loads(Path(args.selection).read_text())
with bpy.data.libraries.load(args.source, link=False) as (available, selected):
    assert all(name in available.objects for name in names)
    selected.objects = names
parts = []
for ob in selected.objects:
    if ob is not None:
        bpy.context.collection.objects.link(ob)
bpy.context.view_layer.update()
for ob in selected.objects:
    if ob is None:
        continue
    if ob.type != 'MESH':
        parts.append({'name': ob.name, 'type': ob.type})
        continue
    ob.data.calc_loop_triangles()
    q = np.array([ob.matrix_world @ vertex.co for vertex in ob.data.vertices])
    parts.append({'name': ob.name, 'type': ob.type, 'vertices': len(q), 'triangles': len(ob.data.loop_triangles),
                  'boundsNative': [q.min(0).tolist(), q.max(0).tolist()], 'matrixWorld': [list(row) for row in ob.matrix_world],
                  'materials': [m.name if m else None for m in ob.data.materials],
                  'modifiers': [{'name': m.name, 'type': m.type} for m in ob.modifiers],
                  'customPropertyKeys': list(ob.keys())})
Path(args.out).write_text(json.dumps({'source': args.source, 'parts': parts}, indent=2) + '\n')
print(json.dumps([{'name': x['name'], 'type': x['type'], 'vertices': x.get('vertices'), 'boundsNative': x.get('boundsNative')} for x in parts if x['name'] in ['Tongue','Gingiva','Soft palate','Mucosa of nasal cavity','Mandible','Epiglottis','Uvula of palate']], indent=2))
