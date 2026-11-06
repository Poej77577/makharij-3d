"""Actual candidate lip/jaw/tongue geometry rendered from two views.
Diagnostic actuator only: velum/nasal control is absent and cast margins overlap.
Never saves over the source Blender file. Source NPZ hashes identify the motion.
"""
from pathlib import Path
import sys,json,hashlib,argparse
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser();parser.add_argument('--indices',default='all');opts=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
folder=ROOT/'data/motion/mim-local-contact-v10';rest=ROOT/'assets/anatomy/rest-meshes.json';d=json.loads(rest.read_bytes());report=json.loads((folder/'report.json').read_bytes());assert hashlib.sha256(rest.read_bytes()).hexdigest()==report['restSha256'];archive=np.load(folder/'states.npz');states=[archive[k]for k in sorted(archive.files)];rows=report['states'];selected=list(range(len(states)))if opts.indices=='all'else list(map(int,opts.indices.split(',')));out=ROOT/'research/qa/mim-actuator-v10';out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/anatomy/makharij-rest.blend'));scene=bpy.context.scene
for o in list(scene.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
base={o.name:o for o in scene.objects if o.type=='MESH'};original={n:np.array(d['parts'][n]['positions']).reshape(-1,3)for n in base};tonguePrep=np.load(ROOT/'data/motion/mim-jaw-v10/targets.npz')['TONGUE'];cuts={}
closed={'TONGUE','SOFT_PALATE'}|{n for n in base if n.startswith('NASAL_')}
for name,o in base.items():
 q=o.copy();q.data=o.data.copy();bpy.context.collection.objects.link(q);q.name='SECTION_'+name;cuts[name]=q
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.view_settings.view_transform='AgX';scene.world.color=(.11,.14,.16)
for position,power,size in [((.16,.13,-.20),.65,.14),((-.07,.09,-.12),.35,.15),((.06,-.06,.15),.30,.12),((.22,.08,.02),.45,.12)]:
 light=bpy.data.lights.new('Diagnostic softbox','AREA');light.energy=power;light.shape='DISK';light.size=size;ob=bpy.data.objects.new('Diagnostic softbox',light);scene.collection.objects.link(ob);ob.location=position;ob.rotation_euler=(Vector((.06,0,0))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Diagnostic camera',bpy.data.cameras.new('Diagnostic camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
def camera(position,target,scale):
 cam.location=position;f=(Vector(target)-cam.location).normalized();r=f.cross(Vector((0,1,0))).normalized();u=r.cross(f);cam.rotation_euler=Matrix(((r.x,u.x,-f.x),(r.y,u.y,-f.y),(r.z,u.z,-f.z))).to_euler();cam.data.ortho_scale=scale

def rotate(v,t):
 angle=np.deg2rad(4)*t;p=v.copy();x=v[:,0]-.003;y=v[:,1]-.037;p[:,0]=.003+np.cos(angle)*x-np.sin(angle)*y;p[:,1]=.037+np.sin(angle)*x+np.cos(angle)*y;return p
for i in selected:
 row=rows[i]
 for name,ob in base.items():
  p=original[name]
  if name=='LIP_CONTEXT':p=states[i]
  elif name=='TONGUE':p=p+row['preparationFraction']*(tonguePrep-p)
  elif name in ['LOWER_TEETH','GINGIVA_LOWER']:p=rotate(p,row['jawFraction'])
  ob.data.vertices.foreach_set('co',np.asarray(p,dtype=np.float32).ravel());ob.data.update()
  cut=cuts[name];bm=bmesh.new();bm.from_mesh(ob.data);res=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,0),plane_no=(0,0,-1),clear_outer=True,clear_inner=False)
  if name in closed:
   edges=[e for e in res['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
   if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cut.data);bm.free();cut.data.update()
 for view in ['front','side']:
  for ob in base.values():ob.hide_render=view!='front'
  for ob in cuts.values():ob.hide_render=view!='side'
  if view=='front':camera((.30,-.005,0),(.085,-.005,0),.095)
  else:camera((.057,.004,-.27),(.057,.004,0),.145)
  target=out/view;target.mkdir(exist_ok=True);scene.render.filepath=str(target/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
 print('ACTUATOR_FRAME',i,flush=True)
evidence={'restSha256':hashlib.sha256(rest.read_bytes()).hexdigest(),'motionSha256':hashlib.sha256((folder/'states.npz').read_bytes()).hexdigest(),'sourceFrames':selected,'views':['source front','actual deformed volume midsagittal cut'],'coupling':'source lip target per frame, tongue clearance preparation, rigid lower jaw 4-degree closure','limits':['not complete Mim: velum and nasal motion absent','cast-derived gingival display margins overlap lip tissue in documented states','no audio or qualified review','frame rendering does not replace final delivered-GLB validation'],'sourceBlendModified':False};(out/'render-evidence.json').write_text(json.dumps(evidence,indent=2));print('DIAGNOSTIC',out)
