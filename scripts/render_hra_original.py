import bpy,json
from pathlib import Path
from mathutils import Vector
import argparse, sys
parser = argparse.ArgumentParser(description="Read-only HRA original asset inspection in Blender")
parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parents[1] / "work/research/nih-hra")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
ROOT = args.input_dir.resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_hra_original import verify
verify(ROOT / "3d-vh-m-mouth.glb")
(ROOT / "evidence").mkdir(exist_ok=True)

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'3d-vh-m-mouth.glb'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.world.color=(.095,.105,.11)
s=scene.display.shading;s.light='STUDIO';s.studio_light='paint.sl';s.color_type='MATERIAL';s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.background_type='WORLD'
camdata=bpy.data.cameras.new('Original source inspection');cam=bpy.data.objects.new('Original source inspection',camdata);scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.155
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
bounds={}
for o in objects:
 vs=[o.matrix_world@Vector(c)for c in o.bound_box]
 bounds[o.name]=[min(p[i]for p in vs)for i in range(3)]+[max(p[i]for p in vs)for i in range(3)]
(ROOT/'render-bounds.json').write_text(json.dumps(bounds,indent=2))
target=Vector((0,-.075,.73))
def camera(pos,clip=.001):
 cam.location=pos;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.clip_start=clip;camdata.clip_end=2

def render(name,pos,clip=.001,hide=()):
 for o in objects:o.hide_render=any(t in o.name for t in hide)
 camera(pos,clip);scene.render.filepath=str(ROOT/'evidence'/name);bpy.ops.render.render(write_still=True)
render('original-oblique.png',(.24,-.29,.87))
render('original-front.png',(0,-.4,.73))
# Camera clipping only: no tissue reshaping, surface fill, or closing caps.
render('original-midline.png',(.3,-.075,.73),.3001,('parotid','submandibular'))
render('original-internal.png',(.24,-.29,.87),.001,('buccal_mucosa','mandible','parotid','submandibular'))
print('ORIGINAL_INSPECTION_RENDERED')
