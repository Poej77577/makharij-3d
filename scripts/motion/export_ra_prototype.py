"""Export actual inspected Badin tongue rest/preparation/contact morphs.
No scientific approval. Run Blender --python this.py -- --fit-dir data/motion/...
"""
import bpy,json,hashlib,sys,argparse
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
args=argparse.ArgumentParser();args.add_argument('--fit-dir',required=True);opts=args.parse_args(sys.argv[sys.argv.index('--')+1:])
folder=ROOT/opts.fit_dir;report=json.loads((folder/'tongue-fit.json').read_text());rest_path=ROOT/'assets/anatomy/rest-meshes.json'
assert hashlib.sha256(rest_path.read_bytes()).hexdigest()==report['restSha256'],'Rest changed since fit; recalibrate, never silently export'
fit=report['results']['ra'];assert fit['pathSafeAgainstInitiallyClearObstacles'] and not report['baselineBlockers']
assert fit['targetRegion']['minimumDistance_mm']<.3,'Actual source tip failed intended contact region'
base=json.loads(rest_path.read_text());p=np.array(base['parts']['TONGUE']['positions']).reshape(-1,3);x,y,z=p.T
prep=p.copy();prep[:,0]-=report['tipParameters_mm']['retraction']*.001*np.exp(-((x-.081)/.009)**2-((y+.001)/.020)**2-(z/.012)**4)
target=np.load(folder/'tongue-targets.npz')['ra']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/anatomy/makharij-rest.blend'))
ob=bpy.data.objects['TONGUE'];assert len(ob.data.vertices)==len(p)
assert np.max(abs(np.array([tuple(v.co)for v in ob.data.vertices])-p))<1e-8
ob.shape_key_add(name='Basis')
for name,values in [('ra_prepared',prep),('ra_contact',target)]:
 key=ob.shape_key_add(name=name);key.data.foreach_set('co',np.asarray(values,dtype=np.float32).ravel())
ob['motionStatus']='technical prototype; anatomy and qualified tajwid review pending'
ob['raFitRestSha256']=report['restSha256'];ob['raContactGap_mm']=fit['targetRegion']['minimumDistance_mm']
# Offline timeline mirrors the runtime's staged retraction, lift and return.
def smooth(u):u=max(0,min(1,u));return u*u*(3-2*u)
def weights(t):
 if t<.08:return 0,0
 if t<.26:return smooth((t-.08)/.18),0
 if t<.40:
  lift=smooth((t-.26)/.14);return 1-lift,lift
 if t<.42:return 0,1
 if t<.70:
  lift=1-smooth((t-.42)/.28);return 1-lift,lift
 if t<.86:return 1-smooth((t-.70)/.16),0
 return 0,0
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=1;scene.frame_end=97
for i in range(97):
 a,b=weights(i/96)
 for name,value in [('ra_prepared',a),('ra_contact',b)]:
  key=ob.data.shape_keys.key_blocks[name];key.value=value;key.keyframe_insert('value',frame=i+1)
for f in ob.data.shape_keys.animation_data.action.fcurves:
 for k in f.keyframe_points:k.interpolation='LINEAR'
scene.frame_set(1);scene['motionStatus']='Ra technical prototype only; whole platform incomplete'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/anatomy/makharij-ra-prototype.blend'))
bpy.ops.object.select_all(action='DESELECT')
for part in scene.objects:
 if part.type=='MESH':part.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/anatomy/makharij-ra-prototype.glb'),export_format='GLB',export_yup=False,use_selection=True,export_extras=True,export_animations=False,export_morph=True)
print('Exported actual Ra prototype with two source-sampled morphs',fit['targetRegion']['minimumDistance_mm'])
