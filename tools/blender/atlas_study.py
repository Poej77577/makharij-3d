"""Actual native atlas head/neck geometry, read with template execution disabled.

Original source modifiers and world placement are evaluated. No upstream app
code, definitions or unrelated brain/inner-ear/kidney models enter the study.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--selection', required=True)
p.add_argument('--out', required=True)
args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
selection = json.loads(Path(args.selection).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(args.source, link=False) as (available, selected):
    assert all(name in available.objects for name in selection)
    selected.objects = selection
originals = [ob for ob in selected.objects if ob and ob.type == 'MESH']
for ob in originals:
    bpy.context.collection.objects.link(ob)
    ob.hide_viewport = False
    ob.hide_render = False
    ob.hide_set(False)
bpy.context.view_layer.update()
dependency = bpy.context.evaluated_depsgraph_get()
native = {}
construction_native = {}
for ob in originals:
    evaluated = ob.evaluated_get(dependency)
    mesh = evaluated.to_mesh()
    points = np.array([evaluated.matrix_world @ v.co for v in mesh.vertices])
    faces = [list(poly.vertices) for poly in mesh.polygons]
    reverse = evaluated.matrix_world.to_3x3().determinant() < 0
    if reverse:
        faces = [face[::-1] for face in faces]
    native[ob.name] = {'points': points, 'faces': faces, 'reverseWorldWinding': reverse,
                       'sourceBaseVertices': len(ob.data.vertices), 'sourceModifiers': [
                           {'type': m.type, 'enabled': m.show_viewport,
                            **({'levels': m.levels} if m.type == 'SUBSURF' else {}),
                            **({'thickness_m': m.thickness, 'offset': m.offset} if m.type == 'SOLIDIFY' else {})}
                           for m in ob.modifiers]}
    evaluated.to_mesh_clear()
    solidify = [m for m in ob.modifiers if m.type == 'SOLIDIFY' and m.show_viewport]
    if solidify:
        for modifier in solidify:
            modifier.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = ob.evaluated_get(dependency)
        surface = evaluated.to_mesh()
        points = np.array([evaluated.matrix_world @ v.co for v in surface.vertices])
        faces = [list(poly.vertices) for poly in surface.polygons]
        if evaluated.matrix_world.to_3x3().determinant() < 0:
            faces = [face[::-1] for face in faces]
        construction_native[ob.name] = {'points': points, 'faces': faces,
                                         'role': 'Original mirrored/subdivided source surface before tissue thickening'}
        evaluated.to_mesh_clear()
        for modifier in solidify:
            modifier.show_viewport = True
        bpy.context.view_layer.update()

# Right-handed rotation: anterior -nativeY, superior nativeZ, right -nativeX.
# Origin is a real upper anterior dental edge, not a guessed head translation.
incisors = np.vstack([native[name]['points'] for name in ['Upper medial incisor.l', 'Upper medial incisor.r']])
q = np.column_stack([-incisors[:, 1], incisors[:, 2], -incisors[:, 0]])
mid = q[abs(q[:, 2]) < .003]
tip = mid[mid[:, 1] < mid[:, 1].min() + .001]
anchor = tip[tip[:, 0].argmax()].copy()
anchor[2] = 0  # Preserve the atlas's explicit midsagittal mirror plane.
construction = {}
for name, data in construction_native.items():
    points = data['points']
    q = np.column_stack([-points[:, 1], points[:, 2], -points[:, 0]]) - anchor
    construction[name] = {'positions': q.ravel().tolist(), 'faces': data['faces'], 'role': data['role']}
(out / 'atlas-construction-surfaces.json').write_text(json.dumps({'parts': construction}, separators=(',', ':')) + '\n')

def material(name, color, organic=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = .5
    if organic:
        bs.inputs['Subsurface Weight'].default_value = .04
        bs.inputs['Subsurface Radius'].default_value = (.0007, .00035, .0002)
        noise = mat.node_tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 1300
        bump = mat.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .12
        bump.inputs['Distance'].default_value = .00007
        mat.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return mat

mats = {'bone': material('Illustrated bone', (.64, .52, .33)),
        'tooth': material('Ivory enamel', (.76, .72, .60)),
        'muscle': material('Muscle tissue', (.38, .105, .075), True),
        'mucosa': material('Moist mucosal tissue', (.48, .19, .15), True),
        'cartilage': material('Cartilage', (.48, .60, .49))}
objects, records = {}, {}
for name, data in native.items():
    points = data['points']
    q = np.column_stack([-points[:, 1], points[:, 2], -points[:, 0]]) - anchor
    identifier = 'ATLAS_' + re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_').upper()
    mesh = bpy.data.meshes.new(identifier)
    mesh.from_pydata(q, [], data['faces'])
    mesh.update()
    ob = bpy.data.objects.new(identifier, mesh)
    bpy.context.collection.objects.link(ob)
    if re.search(r'incisor|canine|premolar|molar tooth', name, re.I):
        kind = 'tooth'
    elif 'cartilage' in name.lower() or name == 'Epiglottis':
        kind = 'cartilage'
    elif re.search(r'bone|Mandible|Maxilla|Vomer', name):
        kind = 'bone'
    elif 'muscle' in name.lower() or 'constrictor' in name.lower():
        kind = 'muscle'
    else:
        kind = 'mucosa'
    mesh.materials.append(mats[kind])
    for poly in mesh.polygons:
        poly.use_smooth = True
    ob['sourceObjectName'] = name
    ob['sourceLicense'] = 'CC-BY-SA-4.0, retained BodyParts3D attribution'
    ob['reviewStatus'] = 'source candidate; not accepted teaching anatomy'
    objects[identifier] = ob
    records[identifier] = {'sourceObjectName': name, 'sourceBaseVertices': data['sourceBaseVertices'],
                            'originalModifiersEvaluated': data['sourceModifiers'], 'negativeWorldScaleWindingCorrected': data['reverseWorldWinding'],
                            'materialClass': kind, 'sourceKind': 'Atlas authored anatomy derived from BodyParts3D; no clinical registration claim'}

# Save a self-contained geometry subset; no upstream scripts or unrelated data.
keep = set(objects.values())
for ob in list(bpy.data.objects):
    if ob not in keep:
        bpy.data.objects.remove(ob, do_unlink=True)
for text in list(bpy.data.texts):
    bpy.data.texts.remove(text)
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene['studyStatus'] = 'New atlas candidate after user rejection; no visual acceptance or rig'
scene['sourceUnits'] = 'Source Scene METRIC, scale_length1; source display unit CENTIMETERS'
scene['canonicalFrame'] = '+X anterior, +Y superior, +Z subject right; meters'
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'atlas-study.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(out / 'atlas-study.glb'), export_format='GLB', use_selection=True,
                          export_yup=False, export_apply=True, export_extras=True, export_animations=False)
parts = {}
for name, ob in objects.items():
    mesh = ob.data
    mesh.calc_loop_triangles()
    parts[name] = {'positions': [c for v in mesh.vertices for c in v.co], 'indices': [i for t in mesh.loop_triangles for i in t.vertices], 'source': records[name]}
(out / 'atlas-meshes.json').write_text(json.dumps({'parts': parts, 'frame': {'units': 'm', 'anterior': '+X', 'superior': '+Y', 'right': '+Z'}}, separators=(',', ':')) + '\n')
with Path(args.source).open('rb') as f:
    source_sha = hashlib.file_digest(f, 'sha256').hexdigest()
record = {'sourceSha256': source_sha, 'sourceRepository': 'https://github.com/Z-Anatomy/Models-of-human-anatomy',
          'sourceCommit': '8dd357ed52a675db0c5f8d7fa9a8621cbfeee713', 'sourceAtlasUnits': {'system': 'METRIC', 'scaleLength': 1, 'display': 'CENTIMETERS'},
          'canonicalDentalAnchorBeforeTranslation_m': anchor.tolist(), 'rotation': [[0,-1,0],[0,0,1],[-1,0,0]],
          'sourceSurfaceShapeModified': False, 'coordinatesConvertedByDocumentedRigidFrame': True, 'sourceModifiersEvaluated': True, 'applicationTemplateInstalled': False,
          'scriptExecutionEnabled': False, 'sourceMetadataDefinitionsCopied': False, 'parts': records,
          'glbSha256': hashlib.sha256((out / 'atlas-study.glb').read_bytes()).hexdigest(),
          'blendSha256': hashlib.sha256((out / 'atlas-study.blend').read_bytes()).hexdigest(),
          'isAcceptedAnatomy': False, 'status': 'Actual source candidate for visual comparison; not final anatomy or articulation'}
(out / 'atlas-study.manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print('ATLAS_STUDY', json.dumps({'parts': len(parts), 'triangles': sum(len(p['indices']) // 3 for p in parts.values()), 'folder': str(out)}))
