"""Build concrete A/B cavity redesign proposals from the rejected 3D source.
Units in anatomical editing fields: mm. glTF is exported in metres.
These are authored educational design studies, not clinical anatomy measurements.
"""
import bpy,bmesh,json,math,struct
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/models/redesign';EVID=ROOT/'public/evidence/redesign'
OUT.mkdir(parents=True,exist_ok=True);EVID.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'model/makharij-rest.blend'))
scene=bpy.context.scene
source_full=bpy.data.objects['full'];source_section=bpy.data.objects['section']
originals=list(source_full.children)
# The old source and all old evidence are retained; the rejected model is not relabelled.
for o in list(source_section.children):bpy.data.objects.remove(o,do_unlink=True)
bpy.data.objects.remove(source_section,do_unlink=True)
for o in originals:o.hide_render=True
source_full.name='rejected_full'

def src(p):return Vector((p.x*1000+100,-p.z*1000,p.y*1000+100))
def dsp(p):return Vector(((p[0]-100)/1000,(p[2]-100)/1000,-p[1]/1000))
def S(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def field(p,c,kind):
 x,y,z=p
 if kind=='tongue':
  d=S(55,78,x)*(1-S(114,128,x))*S(78,106,z)
  r=S(108,126,x)*S(60,82,z)*(1-S(115,128,z))
  w=S(60,80,x)*(1-S(120,131,x))*S(65,95,z)
  return Vector((x-c['root']*r,y*(1-c['lateral']*w),z-c['dorsum']*d))
 if kind=='wall':
  w=S(125,137,x)*S(45,65,z)*(1-S(110,132,z))
  return Vector((x+c['wall']*w,y,z))
 return Vector(p)
def recalc(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
def mod(o,kind,**kw):
 bpy.context.view_layer.objects.active=o;m=o.modifiers.new(kind,kind)
 for k,v in kw.items():setattr(m,k,v)
 bpy.ops.object.modifier_apply(modifier=m.name)
def make_part(name,vs,fs,mat,parent,variant):
 mesh=bpy.data.meshes.new(name+'_'+variant);mesh.from_pydata(vs,[],fs);mesh.update();o=bpy.data.objects.new(name+'_'+variant,mesh);scene.collection.objects.link(o);o.parent=parent;o['part']=name;mesh.materials.append(mat)
 for p in mesh.polygons:p.use_smooth=True
 recalc(o);return o

def section_clone(full,variant):
 group=bpy.data.objects.new('section_'+variant,None);scene.collection.objects.link(group);group['view']='section'
 for o in list(full.children):
  cp=o.copy();cp.data=o.data.copy();cp.name=o['part']+'__section_'+variant;scene.collection.objects.link(cp);cp.parent=group
  bm=bmesh.new();bm.from_mesh(cp.data)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,0),plane_no=(0,0,1),clear_outer=True)
  edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z)<1e-6 for v in e.verts)]
  if edges:
   filled=bmesh.ops.holes_fill(bm,edges=edges,sides=0)
   for f in filled['faces']:f.smooth=False
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(cp.data);bm.free();cp.data.update()
 return group

def bvh(o):
 o.data.calc_loop_triangles();vs=[src(v.co)for v in o.data.vertices];fs=[tuple(t.vertices)for t in o.data.loop_triangles]
 return BVHTree.FromPolygons(vs,fs,all_triangles=True)
def geometry(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 result={'vertices':len(bm.verts),'faces':len(bm.faces),'boundaryEdges':sum(e.is_boundary for e in bm.edges),'nonmanifoldEdges':sum(not e.is_manifold for e in bm.edges),'volumeMm3':abs(bm.calc_volume(signed=True))*1e9}
 bm.free();return result

def measurements(full):
 parts={o['part']:o for o in full.children};tongue=bvh(parts['tongue']);walls=[bvh(parts[n])for n in ['oral_wall','soft_palate']]
 oral=[];pharynx=[]
 for x in range(62,112,4):
  t=tongue.ray_cast(Vector((x,0,160)),Vector((0,0,-1)),150)[0]
  hits=[w.ray_cast(Vector((x,0,80)),Vector((0,0,1)),100)[0]for w in walls];hits=[h for h in hits if h]
  if t and hits:oral.append({'xMm':x,'tongueHeightMm':float(t.z),'roofHeightMm':min(h.z for h in hits),'gapMm':min(h.z for h in hits)-float(t.z)})
 for z in range(72,96,4):
  t=tongue.ray_cast(Vector((160,0,z)),Vector((-1,0,0)),150)[0]
  hits=[w.ray_cast(Vector((130,0,z)),Vector((1,0,0)),100)[0]for w in walls];hits=[h for h in hits if h]
  if t and hits:pharynx.append({'heightMm':z,'tongueBackMm':float(t.x),'wallFrontMm':min(h.x for h in hits),'gapMm':min(h.x for h in hits)-float(t.x)})
 return {'tongueVolumeMm3':geometry(parts['tongue'])['volumeMm3'],'oralProfile':oral,'pharyngealProfile':pharynx,'meshAudit':{k:geometry(o)for k,o in parts.items()}}

def canonical_glb(path):
 data=path.read_bytes();jlen,jtype=struct.unpack_from('<II',data,12);g=json.loads(data[20:20+jlen])
 for node in g.get('nodes',[]):
  e=node.get('extras',{})
  if 'view'in e:node['name']=e['view']
  elif 'part'in e:node['name']=e['part']+('__section'if'__section_'in node.get('name','')else'')
 j=json.dumps(g,separators=(',',':'),ensure_ascii=False).encode();j+=b' '*((-len(j))%4);tail=data[20+jlen:]
 path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(j)+len(tail))+struct.pack('<II',len(j),jtype)+j+tail)

def export_groups(full,section,label):
 bpy.ops.object.select_all(action='DESELECT')
 for o in [full,section,*full.children,*section.children]:o.select_set(True)
 path=OUT/(label+'.glb')
 bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=False,export_extras=True,export_animations=False,export_cameras=False,export_lights=False,use_selection=True)
 canonical_glb(path)

def floor_from_profile(full,label):
 # Slim, inferior tissue bridge. Final profile is reviewed separately from the tongue.
 controls=[(55,84,81,16),(61,81,77.5,18),(68,72,68.5,22),(77,59,55.5,23),(91,58,54.5,24),(103,57,53.5,24),(112,64,60.5,22),(122,65,61.5,16)]
 vs=[];fs=[];N=24
 for x,top,bottom,width in controls:
  for j in range(N):
   a=2*math.pi*j/N;vs.append(dsp((x,width*math.cos(a),(top+bottom)/2+(top-bottom)/2*math.sin(a))))
 for i in range(len(controls)-1):
  for j in range(N):fs.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
 fs.extend([tuple(range(N-1,-1,-1)),tuple((len(controls)-1)*N+j for j in range(N))])
 floor=make_part('mouth_floor',vs,fs,bpy.data.materials['gum'],full,label);mod(floor,'SUBSURF',levels=2)
 return floor

CONFIGS={'baseline':None,'reference':{'dorsum':11,'root':6,'lateral':.08,'wall':4.5}}
reports={};groups={}
for label,c in CONFIGS.items():
 group=bpy.data.objects.new('full_'+label,None);scene.collection.objects.link(group);group['view']='full';group['proposal']=label;group['anatomical_status']='design proposal for user review; not anatomically approved'
 for orig in originals:
  name=orig.name
  if c and name=='mouth_floor':continue
  cp=orig.copy();cp.data=orig.data.copy()if c and name in ['tongue','oral_wall','soft_palate','nasal_wall']else orig.data;cp.name=name+'_'+label;scene.collection.objects.link(cp);cp.parent=group;cp['part']=name;cp.hide_render=False
  if c and name in ['tongue','oral_wall','soft_palate','nasal_wall']:
   for v in cp.data.vertices:v.co=dsp(field(src(v.co),c,'tongue'if name=='tongue'else'wall'))
   recalc(cp)
 if c:
  tongue=next(o for o in group.children if o['part']=='tongue')
  # One connected tissue volume: the thin bridge joins the existing tongue base.
  bridge=floor_from_profile(group,label)
  mod(tongue,'BOOLEAN',operation='UNION',solver='EXACT',object=bridge)
  bpy.data.objects.remove(bridge,do_unlink=True)
  mod(tongue,'REMESH',mode='VOXEL',voxel_size=.00065,use_smooth_shade=True)
  mod(tongue,'SMOOTH',factor=.35,iterations=3)
  mod(tongue,'DECIMATE',ratio=.4,use_collapse_triangulate=True)
  tongue['contains_floor_bridge']=True
  recalc(tongue)
 sec=section_clone(group,label);groups[label]=(group,sec);reports[label]=measurements(group)
 export_groups(group,sec,label)
 for o in list(group.children)+list(sec.children):o.hide_render=True

# All proposals use exactly the same orthographic camera, scale, lighting, and materials.
scene.render.engine='BLENDER_WORKBENCH';shade=scene.display.shading;shade.light='STUDIO';shade.studio_light='paint.sl';shade.color_type='MATERIAL';shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.075,.085,.09)
cam=scene.camera
cam.data.type='ORTHO';scene.render.resolution_x=1500;scene.render.resolution_y=1150;scene.render.resolution_percentage=100

def camera(pos,target,scale):
 cam.location=pos;z=(cam.location-Vector(target)).normalized();x=Vector((0,1,0)).cross(z).normalized();y=z.cross(x);cam.rotation_euler=Matrix((x,y,z)).transposed().to_euler();cam.data.ortho_scale=scale

def render(label,view,hide=()):
 for pair in groups.values():
  for parent in pair:
   for o in parent.children:o.hide_render=True
 full,sec=groups[label];parent=sec if view=='side'else full
 for o in parent.children:o.hide_render=o['part']in hide
 if view=='side':camera((-.003,-.003,.3),(-.003,-.003,0),.132)
 elif view=='oblique':camera((-.15,.07,.22),(-.003,-.008,0),.145)
 else:camera((-.32,-.005,0),(-.04,-.005,0),.078)
 scene.render.filepath=str(EVID/(label+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
for label in CONFIGS:
 render(label,'side',('skin','nasal_wall'))
 if label!='baseline':render(label,'oblique',('skin','nasal_wall'))
for pair in groups.values():
 for parent in pair:
  for o in parent.children:o.hide_render=True;o.hide_set(True)
for o in groups['reference'][1].children:o.hide_render=False;o.hide_set(False)
for o in originals:o.hide_set(True)
camera((-.003,-.003,.3),(-.003,-.003,0),.132)
scene['redesign_status']='Reference-proportioned redesign is a user-review proposal. The original model was rejected. No speech articulation approval.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/makharij-redesigns.blend'))
(ROOT/'docs/redesign-metrics.json').write_text(json.dumps(reports,indent=2))
print('REDESIGN_BUILD_COMPLETE')
