"""Bake restrained portable mucosal PBR detail with the reviewed MIT skill.

No anatomy or papilla geometry is manufactured by this material stage. Clay
evidence remains available separately. Geometry and all morph positions are fixed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/method-evidence/oral-sculpt')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder = ROOT/a.folder
master = folder/'oral-unit.blend'
untextured = folder/'oral-unit.untextured.blend'
existing = json.loads((folder/'oral-manifest.json').read_text())
if existing.get('materials'):
    assert hashlib.sha256(untextured.read_bytes()).hexdigest() == existing['untexturedBlendSha256']
else:
    shutil.copyfile(master, untextured)
bpy.ops.wm.open_mainfile(filepath=str(untextured), use_scripts=False, load_ui=False)
scene = bpy.context.scene
scene.frame_set(1)
scene.cycles.use_denoising = False
tongue = bpy.data.objects['TONGUE']
before = np.array([v.co[:] for v in tongue.data.vertices], dtype='<f4').tobytes()
bpy.ops.object.select_all(action='DESELECT')
tongue.select_set(True)
bpy.context.view_layer.objects.active = tongue
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.018)
bpy.ops.object.mode_set(mode='OBJECT')
high_collection = bpy.data.collections.new('HIGH')
scene.collection.children.link(high_collection)
high = tongue.copy()
high.data = tongue.data.copy()
high.name = 'TONGUE_SculptSource'
high_collection.objects.link(high)
mat = high.data.materials[0].copy()
mat.name = 'Original mucosal surface detail'
high.data.materials.clear()
high.data.materials.append(mat)
nodes, links = mat.node_tree.nodes, mat.node_tree.links
bs = nodes.get('Principled BSDF')
geo = nodes.new('ShaderNodeNewGeometry')
macro = nodes.new('ShaderNodeTexNoise')
macro.inputs['Scale'].default_value = 450
macro.inputs['Detail'].default_value = 2
links.new(geo.outputs['Position'], macro.inputs['Vector'])
ramp = nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (.36, .078, .067, 1)
ramp.color_ramp.elements[1].color = (.47, .135, .112, 1)
links.new(macro.outputs['Fac'], ramp.inputs['Fac'])
links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
fine = nodes.new('ShaderNodeTexNoise')
fine.inputs['Scale'].default_value = 4000
fine.inputs['Detail'].default_value = 2
links.new(geo.outputs['Position'], fine.inputs['Vector'])
bump = nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = .20
bump.inputs['Distance'].default_value = .000018
links.new(fine.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], bs.inputs['Normal'])
rough = nodes.new('ShaderNodeMapRange')
rough.inputs['From Min'].default_value = 0
rough.inputs['From Max'].default_value = 1
rough.inputs['To Min'].default_value = .40
rough.inputs['To Max'].default_value = .55
links.new(fine.outputs['Fac'], rough.inputs['Value'])
links.new(rough.outputs['Result'], bs.inputs['Roughness'])
prepared = folder/'oral-material-prepared.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(prepared), compress=True)
skill = ROOT/'.agents/skills/blender-image-to-3d/scripts/bake_maps.py'
modspec = importlib.util.spec_from_file_location('pinned_surface_bake', skill)
baker = importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(baker)
baker.main(baker.parse(['--blend', str(prepared), '--low', 'LOW', '--high', 'HIGH',
                       '--only', 'TONGUE', '--match-by-name', '--surface-from', 'high',
                       '--maps', 'normal,basecolor,roughness', '--res', '1024', '--samples', '8',
                       '--extrusion', '.00015', '--ray-dist', '.0004', '--margin', '12',
                       '--out', str(folder/'textures'), '--rebuild-material']))
tongue = bpy.data.objects['TONGUE']
after = np.array([v.co[:] for v in tongue.data.vertices], dtype='<f4').tobytes()
assert before == after, 'Material baking changed source geometry'
for ob in bpy.data.collections['HIGH'].objects:
    ob.hide_render = True
    ob.hide_set(True)
for image in bpy.data.images:
    if image.name.startswith('TONGUE_') and image.has_data:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.data.collections['LOW'].objects:
    ob.select_set(True)
bpy.data.objects['JAW_PIVOT'].select_set(True)
bpy.ops.export_scene.gltf(filepath=str(folder/'oral-unit.glb'), export_format='GLB', use_selection=True,
                         export_extras=True, export_animations=True, export_morph=True,
                         export_yup=True, export_force_sampling=True, export_frame_range=True)
manifest = json.loads((folder/'oral-manifest.json').read_text())
manifest['untexturedBlendFile'] = untextured.name
manifest['untexturedBlendSha256'] = hashlib.sha256(untextured.read_bytes()).hexdigest()
manifest['blendSha256'] = hashlib.sha256(master.read_bytes()).hexdigest()
manifest['glbSha256'] = hashlib.sha256((folder/'oral-unit.glb').read_bytes()).hexdigest()
manifest['materials'] = {'method': 'Pinned MIT skill: high-to-low normal / basecolor / roughness bake',
                         'geometryChanged': False, 'resolution': 1024, 'normalConvention': 'OpenGL +Y',
                         'histologyClaim': False, 'papillaGeometryAdded': False,
                         'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder/'textures').glob('*.png')}}
(folder/'oral-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
prepared.unlink()
print(json.dumps({'baked': list(manifest['materials']['files']), 'geometryChanged': False}, indent=2))
