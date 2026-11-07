"""Capture real source geometry with independently computed tissue sections."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
parser = argparse.ArgumentParser()
parser.add_argument('--resolution', type=int, default=720)
parser.add_argument('--samples', type=int, default=48)
parser.add_argument('--views', default='front,side,three-quarter,mouth,sagittal,oral-section')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
manifest = json.loads((OUT / 'assembly.manifest.json').read_text())
sections = json.loads((OUT / 'computed-sections.json').read_text())
assert sections['assetSha256'] == manifest['glbSha256'], 'Recompute sections after changing geometry'
assert hashlib.sha256((OUT / 'character-assembly.blend').read_bytes()).hexdigest() == manifest['blendSha256']
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'character-assembly.blend'))
scene = bpy.context.scene
objects = {ob.name: ob for ob in scene.objects if ob.type == 'MESH'}
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = args.samples
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = args.resolution
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('Neutral studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.65, .69, .72, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
for pos, power, size in [((.4, .5, -.5), 10, .45), ((.2, .05, .4), 6, .4), ((-.25, .15, -.2), 6, .35)]:
    light = bpy.data.lights.new('Studio softbox', 'AREA')
    light.energy, light.size = power, size
    ob = bpy.data.objects.new('Studio softbox', light)
    scene.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (Vector((.075, .035, 0)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
camera = bpy.data.objects.new('Review camera', bpy.data.cameras.new('Review camera'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
views = {'front': ((1, .01, 0), (.065, .065, 0), .40),
         'side': ((0, 0, -1), (.065, .065, 0), .40),
         'three-quarter': ((1, .10, -1), (.065, .065, 0), .40),
         'sagittal': ((0, 0, -1), (.07, .04, 0), .39),
         'mouth': ((1, .03, -.15), (.12, .03, 0), .115),
         'oral-section': ((0, 0, -1), (.11, .027, 0), .145)}

def section_material(original, name):
    mat = original.data.materials[0].copy()
    mat.name = name + ' true computed volume section'
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value = .68
    if name == 'HEAD_SKIN':
        bs.inputs['Base Color'].default_value = (.48, .29, .205, 1)
    # A fine shader pattern explains exposed muscle visually; its scale,
    # direction and pigmentation are authored, not measured fiber anatomy.
    if name in ['TONGUE', 'MOUTH_FLOOR_LEFT', 'MOUTH_FLOOR_RIGHT']:
        wave = nodes.new('ShaderNodeTexWave')
        wave.bands_direction = 'Y'
        wave.inputs['Scale'].default_value = 700
        wave.inputs['Distortion'].default_value = 6
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .18
        bump.inputs['Distance'].default_value = .00008
        links.new(wave.outputs['Color'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return mat

captures = {}
for view in args.views.split(','):
    direction, target, scale = views[view]
    copies = []
    if view in ['sagittal', 'oral-section']:
        for name, original in objects.items():
            original.hide_render = True
            ob = original.copy()
            ob.data = original.data.copy()
            scene.collection.objects.link(ob)
            ob.hide_render = False
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            for mod in list(ob.modifiers):
                bpy.ops.object.modifier_apply(modifier=mod.name)
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-9,
                                  plane_co=(0, 0, sections['planeZ_m']), plane_no=(0, 0, -1), clear_outer=True, clear_inner=False)
            bm.to_mesh(ob.data)
            bm.free()
            copies.append(ob)
            if name in sections['caps']:
                cap = sections['caps'][name]
                mesh = bpy.data.meshes.new(name + ' computed volume section')
                mesh.from_pydata(cap['points'], [], cap['faces'])
                mesh.update()
                cap_ob = bpy.data.objects.new(name + ' computed volume section', mesh)
                scene.collection.objects.link(cap_ob)
                mesh.materials.append(section_material(original, name))
                copies.append(cap_ob)
    center = Vector(target)
    camera.data.ortho_scale = scale
    camera.location = center + Vector(direction).normalized() * .8
    forward = (center - camera.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward)
    camera.rotation_euler = Matrix(((right.x, up.x, -forward.x), (right.y, up.y, -forward.y), (right.z, up.z, -forward.z))).to_euler()
    scene.render.filepath = str(OUT / (view + '.png'))
    bpy.ops.render.render(write_still=True)
    captures[view] = hashlib.sha256((OUT / (view + '.png')).read_bytes()).hexdigest()
    for ob in copies:
        bpy.data.objects.remove(ob, do_unlink=True)
    for ob in objects.values():
        ob.hide_render = False
record = {'assetSha256': manifest['glbSha256'], 'sourceBlendSha256': manifest['blendSha256'],
          'rendererCodeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'sectionFileSha256': hashlib.sha256((OUT / 'computed-sections.json').read_bytes()).hexdigest(),
          'renderer': {'engine': 'Cycles CPU', 'samples': args.samples, 'resolution': args.resolution, 'threads': 2},
          'views': captures, 'sectionMethod': sections['scope'], 'visualAnatomyReview': 'pending',
          'materialLimit': 'Procedural skin and exposed-muscle details are authored illustration shading, not scanned tissue or measured fiber directions.'}
(OUT / 'capture-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print('CHARACTER_REVIEW_CAPTURE', OUT)
