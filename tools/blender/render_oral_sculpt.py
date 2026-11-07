"""Actual neutral/material oral review via the pinned Blender skill.

Every pose/section is an evaluated disposable copy of the native master.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/method-evidence/oral-sculpt')
p.add_argument('--poses', action='store_true')
p.add_argument('--materials', action='store_true')
p.add_argument('--res', type=int, default=900)
p.add_argument('--master', default='oral-unit.blend')
p.add_argument('--labels', nargs='+')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder = (ROOT/a.folder).resolve()
master = folder/a.master
skill = ROOT/'.agents/skills/blender-image-to-3d/scripts/review_render.py'
spec = importlib.util.spec_from_file_location('oral_review_skill', skill)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
mode = 'material' if a.materials else 'clay'
records = []


def review(label, controls, names=None, cut=False, views='threequarter', reference=None):
    if a.labels and label not in a.labels:
        return
    bpy.ops.wm.open_mainfile(filepath=str(master), use_scripts=False, load_ui=False)
    scene = bpy.context.scene
    scene.frame_set(1)
    original = list(bpy.data.collections['LOW'].objects)
    for ob in original:
        if ob.data.shape_keys:
            if ob.data.shape_keys.animation_data:
                ob.data.shape_keys.animation_data.action = None
            for key in ob.data.shape_keys.key_blocks[1:]:
                if not key.name.startswith('JAW_X_'):
                    key.value = controls.get(key.name, 0)
            ob.data.shape_keys.update_tag()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    keep = []
    for original_ob in original:
        name = original_ob.name
        if names is not None and name not in names:
            continue
        mesh = bpy.data.meshes.new_from_object(original_ob.evaluated_get(dg), depsgraph=dg)
        mesh.transform(original_ob.evaluated_get(dg).matrix_world)
        ob = bpy.data.objects.new(name+'_review_copy', mesh)
        scene.collection.objects.link(ob)
        if cut:
            # Physical cut faces have no surface UVs. Use untextured tissue
            # material, never project the external normal/colour atlas onto an
            # invented cap UV (which creates black shards in material review).
            cut_material = bpy.data.materials.new(name+'_actual_section')
            cut_material.use_nodes = True
            color = (.40, .095, .085, 1) if name == 'TONGUE' else (.82, .78, .66, 1) if 'DENTITION' in name else (.47, .16, .14, 1)
            shader = cut_material.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Base Color'].default_value = color
            shader.inputs['Roughness'].default_value = .7
            cap_material_index = len(mesh.materials)
            mesh.materials.append(cut_material)
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                                  dist=1e-8, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                                  clear_outer=True, clear_inner=False)
            edges = [e for e in bm.edges if e.is_boundary and all(abs(v.co.x) < 2e-7 for v in e.verts)]
            if edges:
                result = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
                for face in result.get('faces', []):
                    face.smooth = False
                    face.material_index = cap_material_index
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(mesh)
            bm.free()
        bpy.data.objects.remove(original_ob, do_unlink=True)
        ob.name = name
        keep.append(name)
    with tempfile.TemporaryDirectory(prefix='makharij-oral-review-') as temp:
        snapshot = Path(temp)/'review-copy.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(snapshot), compress=True)
        out = folder/'review'/mode/label
        argv = ['--blend', str(snapshot), '--out', str(out), '--only', ','.join(keep),
                '--fit', ','.join(keep), '--views', views, '--mode', mode,
                '--engine', 'cycles', '--res', str(a.res), '--samples', '32']
        if reference:
            argv += ['--ref-cam', *map(str, reference)]
        renderer.main(renderer.parse(argv))
    records.append({'label': label, 'controls': controls, 'meshes': keep, 'actualMeshSection': cut,
                    'views': views, 'referenceCamera': reference,
                    'images': {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in out.glob('*.png')}})


review('isolated', {}, ['TONGUE'], views='side,top,threequarter', reference=(0, -65, 0))
review('mouth', {'JAW_OPEN': .75}, views='threequarter', reference=(25, 28, 55))
review('floor', {}, ['TONGUE', 'ORAL_FLOOR', 'LINGUAL_FRENULUM', 'LOWER_DENTITION', 'LOWER_GINGIVA'],
       views='', reference=(25, 38, 55))
review('sagittal', {'JAW_OPEN': .55}, cut=True, views='side,threequarter')
if a.poses:
    for label, key in [('tip', 'TIP_ELEVATE'), ('dorsum', 'DORSUM_ELEVATE'), ('root', 'ROOT_RETRACT')]:
        review(label, {key: 1, 'JAW_OPEN': .6}, cut=True, views='side')
(folder/('review-'+mode+'.json')).write_text(json.dumps({
    'masterSha256': hashlib.sha256(master.read_bytes()).hexdigest(),
    'masterFile': master.name,
    'skillSha256': hashlib.sha256(skill.read_bytes()).hexdigest(),
    'mode': mode, 'records': records, 'clinicalAcceptance': 'not assessed'
}, indent=2)+'\n')
