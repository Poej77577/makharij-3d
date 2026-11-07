"""Neutral review using the pinned MIT Blender skill, including real mesh cuts.

Review cuts are disposable copies; never change the deformation source mesh.
"""
import argparse
import importlib.util
from pathlib import Path
import sys

import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/method-evidence/tongue-pilot')
p.add_argument('--stage', default='baseline')
p.add_argument('--poses', action='store_true')
p.add_argument('--context-only', action='store_true')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder = (ROOT/a.folder).resolve()
master = folder/'tongue-pilot.blend'
review = folder/'review'/a.stage
skill = ROOT/'.agents/skills/blender-image-to-3d/scripts/review_render.py'
spec = importlib.util.spec_from_file_location('pinned_clay_review', skill)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def render(source, out, names, views, frame=1, ref=None):
    argv = ['--blend', str(source), '--out', str(out), '--only', ','.join(names),
            '--fit', ','.join(names), '--views', views, '--mode', 'clay',
            '--engine', 'cycles', '--res', '768', '--samples', '16', '--frame', str(frame)]
    if ref:
        argv += ['--ref-cam', *map(str, ref)]
    renderer.main(renderer.parse(argv))


if not a.context_only:
    render(master, review/'isolated', ['PILOT_TONGUE'], 'side,top,threequarter', ref=(0, -65, 0))
bpy.ops.wm.open_mainfile(filepath=str(master), use_scripts=False, load_ui=False)
names = [ob.name for ob in bpy.context.scene.objects if ob.type == 'MESH']
render(master, review/'context-whole', names, 'threequarter')

# The skill renders the delivered shapes; the sagittal review below physically
# cuts copies at native X=0 (canonical subject-right/left midline).
bpy.ops.wm.open_mainfile(filepath=str(master), use_scripts=False, load_ui=False)
bpy.context.scene.frame_set(1)
dg = bpy.context.evaluated_depsgraph_get()
for ob in list(bpy.context.scene.objects):
    if ob.type != 'MESH':
        continue
    mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    replacement = bpy.data.objects.new(ob.name+'_section_copy', mesh)
    bpy.context.scene.collection.objects.link(replacement)
    replacement.matrix_world = ob.matrix_world.copy()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                          dist=1e-8, plane_co=(0, 0, 0), plane_no=(1, 0, 0),
                          clear_outer=True, clear_inner=False)
    if not ob.name.startswith('INFERRED_'):
        cut_edges = [e for e in bm.edges if e.is_boundary and
                     all(abs(v.co.x) < 2e-7 for v in e.verts)]
        if cut_edges:
            result = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
            for face in result.get('faces', []):
                face.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    old_name = ob.name
    bpy.data.objects.remove(ob, do_unlink=True)
    replacement.name = old_name
section = review/'review-only-sagittal.blend'
section.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(section), compress=True)
render(section, review/'context-section', names, 'side,threequarter')
if a.poses:
    for name, frame in [('tip', 25), ('dorsum', 73), ('root', 121), ('return', 145)]:
        render(master, review/name, ['PILOT_TONGUE'], 'side,threequarter', frame)
