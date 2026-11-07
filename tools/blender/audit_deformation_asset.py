"""Read actual rig/shape/weight data without running a source .blend script.

Inventory is not visual or anatomical approval, nor proof of valid motion.
Use before adopting any candidate advertised as rigged or animation-ready.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import bpy

p = argparse.ArgumentParser()
p.add_argument('--input', required=True)
p.add_argument('--report', required=True)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
source, target = Path(args.input).resolve(), Path(args.report).resolve()
digest = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False, load_ui=False)
bpy.context.view_layer.update()
rigs, meshes = [], []
for ob in bpy.context.scene.objects:
    if ob.type == 'ARMATURE':
        rigs.append({'name': ob.name, 'bones': [{'name': b.name, 'parent': b.parent.name if b.parent else None,
            'deform': bool(b.bone.use_deform), 'constraints': [c.type for c in b.constraints]}
            for b in ob.pose.bones]})
    if ob.type != 'MESH':
        continue
    weights = set()
    group_totals = {}
    for vertex in ob.data.vertices:
        for assignment in vertex.groups:
            if assignment.weight > 1e-8:
                weights.add(vertex.index)
                name = ob.vertex_groups[assignment.group].name
                group_totals[name] = group_totals.get(name, 0) + 1
    meshes.append({'name': ob.name, 'vertices': len(ob.data.vertices), 'polygons': len(ob.data.polygons),
        'weightedVertices': len(weights), 'weightGroupVertexCounts': group_totals,
        'shapeKeys': [k.name for k in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else [],
        'modifiers': [{'type': m.type, 'name': m.name, 'armature': m.object.name if m.type == 'ARMATURE' and m.object else None}
            for m in ob.modifiers], 'parent': ob.parent.name if ob.parent else None})
notices = []
for text in bpy.data.texts:
    for line in text.as_string().splitlines():
        if re.search(r'license|copyright|creative commons|makehuman', line, re.I):
            notices.append({'text': text.name, 'line': line[:200]})
            if sum(n['text'] == text.name for n in notices) >= 8:
                break
report = {'sourceFile': source.name, 'sourceSha256': digest, 'sourceBlenderVersion': list(bpy.data.version),
    'inspectorBlenderVersion': bpy.app.version_string, 'sceneUnits': {'system': bpy.context.scene.unit_settings.system,
        'scaleLength': bpy.context.scene.unit_settings.scale_length}, 'armatures': rigs, 'meshes': meshes,
    'actions': [{'name': a.name, 'frames': list(a.frame_range)} for a in bpy.data.actions],
    'embeddedNoticeSnippets': notices, 'embeddedTextNames': [t.name for t in bpy.data.texts],
    'embeddedCodeExecuted': False, 'isAcceptedAnatomy': False,
    'scope': 'Actual native rig, weight and shape-key inventory only; license, topology, visual quality and usable motion require separate verification'}
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'sourceSha256': digest, 'armatures': len(rigs), 'meshes': len(meshes),
    'boneNames': [b['name'] for r in rigs for b in r['bones']], 'embeddedNotices': notices}, indent=2))
