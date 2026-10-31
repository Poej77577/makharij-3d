import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
import bmesh
ROOT=Path('/workspace/makharij-3d'); OUT=ROOT/'assets/anatomy/inspection'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
colors={'TONGUE':(.62,.32,.31,1),'UPPER_TEETH':(.9,.86,.73,1),'LOWER_TEETH':(.9,.86,.73,1),'UPPER_LIP':(.63,.35,.33,1),'LOWER_LIP':(.63,.35,.33,1),'UPPER_COVER':(.7,.6,.49,1),'LOWER_COVER':(.55,.48,.41,1),'LEFT_COVER':(.55,.48,.41,1),'RIGHT_COVER':(.55,.48,.41,1),'EPIGLOTTIS':(.58,.45,.6,1),'UVULA':(.65,.49,.6,1),'MAXILLA':(.7,.6,.49,1),'JAW':(.7,.64,.54,1),'AIRWAY':(.48,.65,.65,1),'FACE':(.6,.49,.41,1)}
def mat(name):
 m=bpy.data.materials.new(name);m.diffuse_color=colors.get(name,(.5,.5,.5,1));m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.48
 return m
mats={n:mat(n) for n in colors}
def obj_file(path,prefix,transform):
 vs=[];groups={};current=prefix
 for l in path.read_text(errors='replace').splitlines():
  p=l.split()
  if not p:continue
  if p[0]=='v':vs.append(transform(tuple(map(float,p[1:4]))))
  elif p[0]=='g' and prefix=='VTL':current='_'.join(p[1:]);groups.setdefault(current,[])
  elif p[0]=='f':groups.setdefault(current,[]).append([int(x.split('/')[0])-1 for x in p[1:]])
 objects=[]
 for name,faces in groups.items():
  if not faces:continue
  ids=sorted({i for f in faces for i in f});mapping={v:i for i,v in enumerate(ids)}
  mesh=bpy.data.meshes.new(name);mesh.from_pydata([vs[i] for i in ids],[],[[mapping[i] for i in f] for f in faces]);mesh.update()
  ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.data.materials.append(mats.get(name,mats['FACE']))
  for p in mesh.polygons:p.use_smooth=True
  objects.append(ob)
 return objects

def cut(objects):
 for ob in objects:
  bm=bmesh.new();bm.from_mesh(ob.data)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=(0,0,0),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
  bm.to_mesh(ob.data);bm.free();ob.data.update()

def lighting(center):
 bpy.context.scene.world.color=(.17,.2,.22)
 for pos,power,size in [((.14,.10,.22),110, .15),((-.10,.10,.12),60,.12),((.08,-.10,-.16),50,.12)]:
  ld=bpy.data.lights.new('Softbox','AREA');ld.energy=power*.006;ld.shape='DISK';ld.size=size
  ob=bpy.data.objects.new('Softbox',ld);bpy.context.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector(center)-ob.location).to_track_quat('-Z','Y').to_euler()

def render(name,campos,target,ortho):
 cam=bpy.context.scene.camera
 cam.location=campos;f=(Vector(target)-cam.location).normalized();r=f.cross(Vector((0,1,0))).normalized();u=r.cross(f);cam.rotation_euler=Matrix(((r.x,u.x,-f.x),(r.y,u.y,-f.y),(r.z,u.z,-f.z))).to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=ortho
 bpy.context.scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=False;scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.render.film_transparent=False
cd=bpy.data.cameras.new('Inspection camera');cam=bpy.data.objects.new('Inspection camera',cd);bpy.context.collection.objects.link(cam);scene.camera=cam
lighting((.025,-.025,0))
vtl=obj_file(ROOT/'assets/candidates/vtl-neutral.obj','VTL',lambda v:tuple(x*.01 for x in v))
render('vtl-full-oblique',(.19,.04,.20),(.015,-.025,0),.15)
cut(vtl);render('vtl-section',(.015,-.025,.25),(.015,-.025,0),.135)
for ob in vtl:bpy.data.objects.remove(ob,do_unlink=True)
base=ROOT/'assets/candidates/artisynth_models/src/artisynth/models/face/geometry'
mapnames={'badintongue.obj':'TONGUE','upperteeth.obj':'UPPER_TEETH','lowerteeth.obj':'LOWER_TEETH','badinface_upperlip_filled.obj':'UPPER_LIP','badinface_lowerlip_filled.obj':'LOWER_LIP','badinmaxilla.obj':'MAXILLA','badinjaw.obj':'JAW'}
badin=[]
for fname,name in mapnames.items():badin+=obj_file(base/fname,name,lambda v:(.14-v[0],v[2]-.1,v[1]))
render('badin-full-oblique',(.24,.07,.24),(.05,-.005,0),.13)
render('badin-front',(.28,.015,0),(.06,.015,0),.12)
cut(badin);render('badin-section',(.055,-.005,.25),(.055,-.005,0),.13)
# Airways are a closed air-volume segmentation, not tissue. Inspection separate.
air=obj_file(base/'badinairway.obj','AIRWAY',lambda v:(.14-v[0],v[2]-.1,v[1]));cut(air);render('badin-with-airway',(.055,-.005,.25),(.055,-.005,0),.13)
print('Inspection renders at',OUT)
