"""Actual atlas geometry views, with independently computed tissue sections."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix

p = argparse.ArgumentParser()
p.add_argument('--folder', required=True)
p.add_argument('--samples', type=int, default=24)
p.add_argument('--resolution', type=int, default=720)
p.add_argument('--views', nargs='+', help='Optional actual views to render during targeted anatomical review')
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.folder).resolve()
main_sections = json.loads((out / 'atlas-sections.json').read_text())
nasal_sections = json.loads((out / 'atlas-nasal-sections.json').read_text())
manifest = json.loads((out / 'atlas-study.manifest.json').read_text())
assert main_sections['assetSha256'] == nasal_sections['assetSha256'] == manifest['glbSha256']
assert hashlib.sha256((out / 'atlas-study.glb').read_bytes()).hexdigest() == manifest['glbSha256']
assert hashlib.sha256((out / 'atlas-study.blend').read_bytes()).hexdigest() == manifest['blendSha256']
assert not main_sections['sectionFailures'] and not nasal_sections['sectionFailures']
bpy.ops.wm.open_mainfile(filepath=str(out / 'atlas-study.blend'), use_scripts=False, load_ui=False)
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
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -.65
scene.world = bpy.data.worlds.new('Atlas review neutral background')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.65, .69, .72, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .30
translation = Vector(manifest.get('atlasPlacement', {}).get('translation_m', (0, 0, 0)))
fitted = 'HEAD_SKIN' in objects
target = Vector((-.035, -.025, 0)) + translation
for offset, power, size in [((.2, .25, -.3), 4, .22), ((.15, 0, .25), 2, .20), ((-.2, .2, -.1), 3, .20)]:
    data = bpy.data.lights.new('Atlas review softbox', 'AREA')
    data.energy, data.size = power, size
    ob = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(ob)
    ob.location = target + Vector(offset)
    ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()
camera = bpy.data.objects.new('Atlas review camera', bpy.data.cameras.new('Atlas review camera'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
views = {'atlas-three-quarter': ((1, .08, -1.4), (.035, .080, 0) if fitted else (-.03, -.035, 0), .40 if fitted else .23),
         'atlas-sagittal': ((0, 0, -1), Vector((-.038, -.018, 0)) + translation, .230),
         'atlas-mouth': ((0, 0, -1), Vector((-.036, .003, 0)) + translation, .105),
         'atlas-nose': ((0, 0, -1), Vector((-.018, .047, 0)) + translation, .085),
         'atlas-tongue': ((1, .3, -1.5), Vector((-.033, -.020, 0)) + translation, .11)}
captures = {}

def cut_material(original, key):
    mat = bpy.data.materials.new(key + ' physical section appearance')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = original.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value
    bs.inputs['Roughness'].default_value = .57
    position = nodes.new('ShaderNodeNewGeometry')
    origin = nodes.new('ShaderNodeVectorMath'); origin.operation = 'SUBTRACT'; origin.inputs[1].default_value = translation
    links.new(position.outputs['Position'], origin.inputs[0])
    noise = nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 720; noise.inputs['Detail'].default_value = 3
    links.new(origin.outputs['Vector'], noise.inputs['Vector'])
    def math_node(operation, a, b=None):
        node = nodes.new('ShaderNodeMath'); node.operation = operation
        for i, value in enumerate([a, b] if b is not None else [a]):
            if isinstance(value, (int, float)):
                node.inputs[i].default_value = value
            else:
                links.new(value, node.inputs[i])
        return node.outputs[0]
    pattern = noise.outputs['Fac']
    colors = None
    if 'TONGUE' in key or 'MUSCLE' in key or 'CONSTRICTOR' in key:
        separate = nodes.new('ShaderNodeSeparateXYZ')
        links.new(origin.outputs['Vector'], separate.inputs[0])
        x, y = separate.outputs['X'], separate.outputs['Y']
        if 'GENIOGLOSSUS' in key:
            angle = math_node('ARCTAN2', math_node('SUBTRACT', y, -.028), math_node('SUBTRACT', x, -.014))
            phase = math_node('MULTIPLY', angle, 460)
        elif 'TONGUE' in key:
            # Intrinsic fibers curve along the dorsum; the source genioglossus
            # region below has its own fan. Fine lines are illustrative tissue
            # appearance, not measured histology or substitute muscle geometry.
            curve = math_node('MULTIPLY', math_node('POWER', math_node('ADD', x, .040), 2), 3)
            phase = math_node('MULTIPLY', math_node('ADD', y, curve), 13963)
        else:
            phase = math_node('MULTIPLY', y, 13963)
        wave = math_node('SINE', math_node('ADD', phase, math_node('MULTIPLY', noise.outputs['Fac'], 2.1)))
        fine = math_node('POWER', math_node('MULTIPLY', math_node('ADD', wave, 1), .5), 10)
        pattern = math_node('ADD', math_node('MULTIPLY', noise.outputs['Fac'], .60), math_node('MULTIPLY', fine, .40))
        colors = ((.22, .045, .031, 1), (.38, .115, .074, 1))
        bs.inputs['Subsurface Weight'].default_value = .025
    elif key == 'HEAD_SKIN':
        noise.inputs['Scale'].default_value = 1800
        colors = ((.41, .23, .11, 1), (.46, .26, .13, 1))
    elif any(word in key for word in ['MANDIBLE', 'MAXILLA', 'PALATINE_BONE', 'HYOID_BONE']):
        cells = nodes.new('ShaderNodeTexVoronoi'); cells.inputs['Scale'].default_value = 2400
        links.new(origin.outputs['Vector'], cells.inputs['Vector'])
        pattern = math_node('ADD', math_node('MULTIPLY', cells.outputs['Distance'], .70), math_node('MULTIPLY', noise.outputs['Fac'], .30))
        colors = ((.43, .29, .14, 1), (.74, .55, .29, 1))
    if colors:
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = colors[0]
        ramp.color_ramp.elements[1].color = colors[1]
        links.new(pattern, ramp.inputs[0]); links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .15; bump.inputs['Distance'].default_value = .000045
        links.new(pattern, bump.inputs['Height']); links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return mat

for name, (direction, center, scale) in views.items():
    if args.views and name not in args.views:
        continue
    sections = nasal_sections if name == 'atlas-nose' else main_sections
    for ob in objects.values():
        ob.hide_render = bool(ob.get('anatomicalRegionOf'))
    copies = []
    if name == 'atlas-tongue':
        for key, ob in objects.items():
            ob.hide_render = bool(ob.get('anatomicalRegionOf')) or not ('TONGUE' in key or 'GENIOHYOID' in key or 'MYLOHYOID' in key or 'HYOID_BONE' in key)
    if name in ['atlas-sagittal', 'atlas-mouth', 'atlas-nose']:
        for key, original in objects.items():
            original.hide_render = True
            ob = original.copy()
            ob.data = original.data.copy()
            ob.hide_render = bool(original.get('anatomicalRegionOf'))
            scene.collection.objects.link(ob)
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=1e-9,
                                  plane_co=(0, 0, sections['planeZ_m']), plane_no=(0, 0, -1), clear_outer=True)
            bm.to_mesh(ob.data)
            bm.free()
            copies.append(ob)
            if key in sections['caps']:
                cap = sections['caps'][key]
                mesh = bpy.data.meshes.new(key + ' actual section')
                mesh.from_pydata(cap['points'], [], cap['faces'])
                mesh.update()
                cap_ob = bpy.data.objects.new(mesh.name, mesh)
                scene.collection.objects.link(cap_ob)
                mat = cut_material(original, key)
                mesh.materials.append(mat)
                copies.append(cap_ob)
    center = Vector(center)
    camera.data.ortho_scale = scale
    camera.location = center + Vector(direction).normalized() * .7
    forward = (center - camera.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward)
    camera.rotation_euler = Matrix(((right.x, up.x, -forward.x), (right.y, up.y, -forward.y), (right.z, up.z, -forward.z))).to_euler()
    scene.render.filepath = str(out / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    captures[name] = hashlib.sha256((out / (name + '.png')).read_bytes()).hexdigest()
    for ob in copies:
        bpy.data.objects.remove(ob, do_unlink=True)
    for ob in objects.values():
        ob.hide_render = False
(out / 'atlas-captures.json').write_text(json.dumps({'assetSha256': manifest['glbSha256'], 'views': captures,
    'sourceBlendSha256': manifest['blendSha256'], 'sectionPlanes_m': {'oral': main_sections['planeZ_m'], 'nasal': nasal_sections['planeZ_m']},
    'renderer': {'type': 'Cycles CPU', 'threads': 2, 'samples': args.samples, 'resolution': args.resolution},
    'visualReview': 'pending; source candidate is not accepted by image generation alone'}, indent=2) + '\n')
print('ATLAS_CANDIDATE_CAPTURE', out)
