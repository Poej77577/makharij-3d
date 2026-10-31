"""Inspect actual continuous FEM skin/lip source, without duplicated filled lips."""
import bpy,bmesh,re,json,collections,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'assets/source/artiSynth/face/geometry';OUT=ROOT/'assets/anatomy';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'makharij-rest.blend'))
for name in ['UPPER_LIP','LOWER_LIP','FACE_CONTEXT']:
 if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
nodes={}
for line in (SRC/'badinface_oop_csa_midsagittal.node').read_text().splitlines():
 t=re.findall(r'[-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+',line)
 if len(t)>=4:
  p=list(map(float,t[1:4]));nodes[int(t[0])]=(.14-p[0],p[2]-.1,p[1])
keys=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)];counts=collections.Counter();faces={}
for line in (SRC/'badinface_oop_csa_midsagittal.elem').read_text().splitlines():
 ids=list(map(int,line.split()))[:8]
 for q in keys:
  f=tuple(ids[i] for i in q);k=tuple(sorted(f));counts[k]+=1;faces[k]=f
boundary=[]
for k,c in counts.items():
 if c!=1:continue
 f=list(dict.fromkeys(faces[k]))
 for j in range(1,len(f)-1):boundary.append([f[0],f[j],f[j+1]])
ids=sorted({i for f in boundary for i in f});ix={k:i for i,k in enumerate(ids)}
me=bpy.data.meshes.new('LIP_CONTEXT');me.from_pydata([nodes[i] for i in ids],[],[[ix[i] for i in f] for f in boundary]);me.update();ob=bpy.data.objects.new('LIP_CONTEXT',me);bpy.context.collection.objects.link(ob)
bm=bmesh.new();bm.from_mesh(me)
# True source clipping with all original oral surfaces retained. No hand-made mouth aperture.
for point,no in [((.065,0,0),(-1,0,0)),((0,.043,0),(0,1,0)),((0,-.04,0),(0,-1,0)),((0,0,.046),(0,0,1)),((0,0,-.046),(0,0,-1))]:
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=point,plane_no=no,clear_outer=True,clear_inner=False)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
# Source contact quad node numbers, not guessed contact points.
sets=[]
for side in ['upper','lower']:
 path=SRC/(side+'_lip_surface_Ian.elem.txt')
 if not path.exists():path=ROOT/'assets/candidates/artisynth_models/src/artisynth/models/face/geometry'/(side+'_lip_surface_Ian.elem.txt')
 nums=set(map(int,path.read_text().split()));tree=KDTree(len(nums))
 for j,k in enumerate(nums):tree.insert(Vector(nodes[k]),j)
 tree.balance();sets.append(tree)
base=[v.co.copy() for v in me.vertices];weights=[]
for v in me.vertices:
 du=sets[0].find(v.co)[2];dl=sets[1].find(v.co)[2]
 wu=1/(du+.0003)**2;wl=1/(dl+.0003)**2;near=math.exp(-(min(du,dl)/.016)**2)
 coarse=max(0,min(1,(.004-v.co.y)/.023));w=near*wl/(wu+wl)+(1-near)*coarse
 weights.append(w);a=math.radians(-6)*w;cx,cy=.003,.037;x,y=v.co.x-cx,v.co.y-cy
 v.co.x=cx+math.cos(a)*x-math.sin(a)*y;v.co.y=cy+math.sin(a)*x+math.cos(a)*y
# Actual source lip contact region highlighted as a continuous tissue material field.
for name,color in [('Skin source',(.66,.49,.39,1)),('Vermilion source',(.60,.28,.29,1)),('Oral lining source',(.58,.35,.33,1))]:
 mat=bpy.data.materials.new(name);mat.diffuse_color=color;mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=.6;me.materials.append(mat)
for f in me.polygons:
 center=sum((base[i] for i in f.vertices),Vector())/len(f.vertices);d=min(t.find(center)[2]for t in sets);f.material_index=1 if d<.004 else 0;f.use_smooth=True
ob['source']='continuous boundary of official active FEM face, no duplicated filled lip source';ob['units']='m'
# Save actual inspection candidate and masks for C, not accepted replacement.
obj={n:{'positions':[q for v in o.data.vertices for q in v.co],'indices':[i for f in o.data.polygons for i in f.vertices]}for n,o in [(o.name,o)for o in bpy.context.scene.objects if o.type=='MESH']}
obj['LIP_CONTEXT']['jawWeights']=weights
(OUT/'fem-lip-prototype.json').write_text(json.dumps({'version':'FEM-LIP-INSPECTION-ONLY','units':'m','parts':obj},separators=(',',':')))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fem-lip-prototype.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'fem-lip-prototype.glb'),export_format='GLB',use_selection=True,export_yup=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False;scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
cam=scene.camera
if cam is None:
 cd=bpy.data.cameras.new('prototype');cam=bpy.data.objects.new('prototype',cd);bpy.context.collection.objects.link(cam);scene.camera=cam
# Previous rest scene contains tested softbox lights; create when source .blend has no lights.
if not any(o.type=='LIGHT'for o in scene.objects):
 for p,power in [((.16,.13,.2),.7),((-.07,.09,.12),.4)]:
  ld=bpy.data.lights.new('Source inspection softbox','AREA');ld.energy=power;ld.size=.15;l=bpy.data.objects.new('Source inspection softbox',ld);bpy.context.collection.objects.link(l);l.location=p;l.rotation_euler=(Vector((.07,0,0))-l.location).to_track_quat('-Z','Y').to_euler()
def render(name,pos,target,scale):
 cam.location=pos;f=(Vector(target)-cam.location).normalized();r=f.cross(Vector((0,1,0))).normalized();u=r.cross(f);cam.rotation_euler=Matrix(((r.x,u.x,-f.x),(r.y,u.y,-f.y),(r.z,u.z,-f.z))).to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.render.filepath=str(OUT/'rest-evidence'/name);bpy.ops.render.render(write_still=True)
for n in ['PHARYNX','SOFT_PALATE','NASAL_LINING']:
 if n in bpy.data.objects:bpy.data.objects[n].hide_render=True
render('continuous-fem-front.png',(.3,-.004,0),(.08,-.004,0),.11)
for n in ['PHARYNX','SOFT_PALATE','NASAL_LINING']:
 if n in bpy.data.objects:bpy.data.objects[n].hide_render=False
render('continuous-fem-oblique.png',(.2,.05,.18),(.063,.003,0),.14)
print('SOURCE CONTINUOUS FEM',len(me.vertices),len(me.polygons))
