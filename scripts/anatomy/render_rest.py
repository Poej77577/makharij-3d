"""Two actual-source resting views: front crop and left-facing sagittal section.

This is evidence for the prepared candidate, not a phoneme or scientific review.
The full delivered GLB and original meshes remain bilateral and uncut.
"""
import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'assets/anatomy/rest-evidence';OUT.mkdir(exist_ok=True)
model=ROOT/'assets/anatomy/makharij-rest.glb';model_sha=hashlib.sha256(model.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/anatomy/makharij-rest.blend'))
scene=bpy.context.scene
for o in list(scene.objects):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False
scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.world.color=(.10,.13,.15)
base=[o for o in scene.objects if o.type=='MESH']
for pos,power,size in [((.16,.13,-.20),.65,.14),((-.07,.09,-.12),.35,.15),((.06,-.06,.15),.30,.12)]:
 ld=bpy.data.lights.new('Source inspection softbox','AREA');ld.energy=power;ld.shape='DISK';ld.size=size;o=bpy.data.objects.new('Source inspection softbox',ld);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((.06,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Source inspection');cam=bpy.data.objects.new('Source inspection',cd);bpy.context.collection.objects.link(cam);scene.camera=cam

def render(name,pos,target,scale):
 cam.location=pos;f=(Vector(target)-cam.location).normalized();r=f.cross(Vector((0,1,0))).normalized();u=r.cross(f)
 cam.rotation_euler=Matrix(((r.x,u.x,-f.x),(r.y,u.y,-f.y),(r.z,u.z,-f.z))).to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
# Surgical front crop: true neutral source lip opening, with rear throat outside this teaching view.
front_hidden=['NASAL_LINING','PHARYNX','SOFT_PALATE']
for o in base:o.hide_render=o.name in front_hidden
render('rest-v5-front',(.30,-.004,0),(.08,-.004,0),.11)
for o in base:o.hide_render=True
cut=[]
for source in base:
 o=source.copy();o.data=source.data.copy();bpy.context.collection.objects.link(o);o.hide_render=False;cut.append(o)
 bm=bmesh.new();bm.from_mesh(o.data)
 # Negative-Z near hemisphere removed. Camera from -Z makes +X anterior point LEFT.
 res=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,0),plane_no=(0,0,-1),clear_outer=True,clear_inner=False)
 if source.name=='TONGUE':
  edges=[e for e in res['geom_cut']if isinstance(e,bmesh.types.BMEdge)and e.is_boundary]
  if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
render('rest-v5-sagittal-left',(.057,.004,-.27),(.057,.004,0),.145)
for o in cut:bpy.data.objects.remove(o,do_unlink=True)
for o in base:o.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/anatomy/makharij-rest.blend'))
(OUT/'rest-v5-evidence.json').write_text(json.dumps({'asset':'badin-prepared-rest-v5','glbSha256':model_sha,'views':{'rest-v5-front.png':{'kind':'actual neutral source front crop','hiddenOutsideTeachingField':front_hidden},'rest-v5-sagittal-left.png':{'kind':'temporary actual source midsagittal section','cameraSide':'negative Z; +X projects LEFT','tongueSectionCap':True,'fullDeliveredGLBCut':False}},'nasalReferenceStatus':'existing unmeasured oval approximation DOES NOT meet requested conchae/cavity reference; rebuild pending','review':'not independently anatomical/tajwid reviewed'},indent=2,ensure_ascii=False)+'\n')
print('EVIDENCE',model_sha)
