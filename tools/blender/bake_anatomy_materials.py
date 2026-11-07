"""Bake authored tongue microstructure into a portable GLB tangent normal map.

This is an illustrative material, not scanned papillae or measured histology.
The exported model retains the same anatomical geometry and source identities.
"""
import argparse
import hashlib
import json
from math import radians
from pathlib import Path
import sys
import bpy

p = argparse.ArgumentParser()
p.add_argument('--folder', required=True)
p.add_argument('--resolution', type=int, default=2048)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.folder).resolve()
record = json.loads((out / 'atlas-study.manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(out / 'atlas-study.blend'), use_scripts=False, load_ui=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 1
scene.cycles.use_denoising = False
bpy.ops.object.select_all(action='DESELECT')
tongue = bpy.data.objects['ATLAS_TONGUE']
tongue.select_set(True)
bpy.context.view_layer.objects.active = tongue
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=radians(66), island_margin=.008)
bpy.ops.object.mode_set(mode='OBJECT')
image = bpy.data.images.new('Authored tongue dorsal microstructure — tangent normal', width=args.resolution, height=args.resolution, alpha=False)
image.colorspace_settings.name = 'Non-Color'
material = tongue.data.materials[0]
nodes, links = material.node_tree.nodes, material.node_tree.links
texture = nodes.new('ShaderNodeTexImage')
texture.name = 'Portable authored tongue normal'
texture.image = image
nodes.active = texture
scene.render.bake.margin = 10
scene.render.bake.use_selected_to_active = False
scene.render.bake.normal_space = 'TANGENT'
bpy.ops.object.bake(type='NORMAL')
image.filepath_raw = str(out / 'tongue-normal.png')
image.file_format = 'PNG'
image.save()
image.pack()
bs = nodes.get('Principled BSDF')
for link in list(bs.inputs['Normal'].links):
    links.remove(link)
normal = nodes.new('ShaderNodeNormalMap')
normal.space = 'TANGENT'
normal.inputs['Strength'].default_value = 1
links.new(texture.outputs['Color'], normal.inputs['Color'])
links.new(normal.outputs['Normal'], bs.inputs['Normal'])
used = {bs, normal, texture, nodes.get('Material Output')}
for node in list(nodes):
    if node not in used:
        nodes.remove(node)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'atlas-study.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(out / 'atlas-study.glb'), export_format='GLB', use_selection=True,
                          export_yup=False, export_apply=True, export_extras=True, export_animations=False)
record['portableMaterials'] = {'tongueNormalMap': 'tongue-normal.png', 'resolution': args.resolution,
    'authoredNotScanned': True, 'method': 'Cycles tangent-space normal bake of region-limited dorsal microstructure',
    'sha256': hashlib.sha256((out / 'tongue-normal.png').read_bytes()).hexdigest()}
record['blendSha256'] = hashlib.sha256((out / 'atlas-study.blend').read_bytes()).hexdigest()
record['glbSha256'] = hashlib.sha256((out / 'atlas-study.glb').read_bytes()).hexdigest()
(out / 'atlas-study.manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print('PORTABLE_TONGUE_MATERIAL', json.dumps(record['portableMaterials']))
