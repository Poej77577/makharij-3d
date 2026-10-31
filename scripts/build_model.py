"""Rebuild the editable rest study. Blender 4.3+. Source dimensions are mm.
Acquired surfaces are not scan supports. Nasal wall is an authored teaching loft.
The model is experimental; no clinical or tajwid validation is implied.
"""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for m in list(bpy.data.materials):bpy.data.materials.remove(m)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
COLORS={'tongue':(.66,.31,.34,1),'skin':(.76,.58,.46,1),'oral_wall':(.67,.43,.42,1),'soft_palate':(.70,.42,.46,1),'nasal_wall':(.69,.56,.48,1),'teeth':(.91,.88,.76,1),'gum':(.63,.36,.36,1),'lip':(.63,.32,.34,1)}
mats={}
for name,c in COLORS.items():
 m=bpy.data.materials.new(name);m.diffuse_color=c;m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=c;p.inputs['Roughness'].default_value=.5
 mats[name]=m
full=bpy.data.objects.new('full',None);scene.collection.objects.link(full)
section=bpy.data.objects.new('section',None);scene.collection.objects.link(section)
def display(p):return ((p[0]-100)*.001,(p[2]-100)*.001,-p[1]*.001)
def source(p):return Vector((p[0]*1000+100,-p[2]*1000,p[1]*1000+100))
def make(name,v,f,mat,parent=full):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update()
 o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);o.parent=parent;me.materials.append(mats[mat])
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 return o
def obj_source(name,path,mat,filter_fn=None):
 verts=[];faces=[]
 for line in (ROOT/path).read_text().splitlines():
  s=line.split()
  if not s:continue
  if s[0]=='v':verts.append([float(x)*1000 for x in s[1:4]])
  elif s[0]=='f':faces.append([int(x.split('/')[0])-1 for x in s[1:]])
 if filter_fn:faces=[f for f in faces if filter_fn(sum((Vector(verts[i])for i in f),Vector())/len(f))]
 ids=sorted(set(i for f in faces for i in f));mp={i:j for j,i in enumerate(ids)}
 return make(name,[display(verts[i])for i in ids],[[mp[i]for i in f]for f in faces],mat)
def modifier(o,kind,**kw):
 bpy.context.view_layer.objects.active=o
 mod=o.modifiers.new(kind,kind)
 for k,v in kw.items():setattr(mod,k,v)
 bpy.ops.object.modifier_apply(modifier=mod.name)
def is_velum(c):return c.x>106 and c.z>101 and c.x<137
skin=obj_source('skin','model/source/artisynth/badinface.obj','skin')
modifier(skin,'SUBSURF',levels=1)
# Open the acquired lower face with a smooth jaw field; no detached lip primitive.
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def jaw_open(p):
 x,y,z=p; a=math.radians(4);dx=x-140;dz=z-130
 q=Vector((140+math.cos(a)*dx-math.sin(a)*dz,y,130+math.sin(a)*dx+math.cos(a)*dz))
 central=(1-smooth(20,32,abs(y)))*(1-smooth(56,75,x))
 w=((1-smooth(100.4,100.9,z))*central+(1-smooth(97.5,103,z))*(1-central))*(1-smooth(105,145,x))
 return Vector(p)+(q-Vector(p))*w
for v in skin.data.vertices:v.co=display(jaw_open(source(v.co)))
oral=obj_source('oral_wall','model/source/artisynth/badinpalate.obj','oral_wall',lambda c:not is_velum(c))
velum=obj_source('soft_palate','model/source/artisynth/badinpalate.obj','soft_palate',is_velum)
for o in [oral,velum]:
 modifier(o,'SOLIDIFY',thickness=.0012,offset=0)
 modifier(o,'SUBSURF',levels=1)
tongue=obj_source('tongue','model/source/artisynth/badintongue.obj','tongue')
modifier(tongue,'SUBSURF',levels=2)
# Restore physical dimensions from OrganUI's uniformly scaled BodyParts3D GLB.
old=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'model/source/bodyparts3d/teeth.glb'))
dental=[]
for o in list(set(bpy.data.objects)-old):
 if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True);continue
 if 'maxilla' in o.name or 'mandible' in o.name:bpy.data.objects.remove(o,do_unlink=True);continue
 name=o.name
 coords=[o.matrix_world@v.co for v in o.data.vertices]
 for v,c in zip(o.data.vertices,coords):v.co=display((96+40*c.y,40*c.x,125+40*c.z-(6 if name.startswith('lower')else 0)))
 o.matrix_world.identity();o.parent=full
 o.data.materials.clear();o.data.materials.append(mats['gum'if 'gum'in name else'teeth'])
 for p in o.data.polygons:p.use_smooth=True
 dental.append(o)
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=1e-7)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
 if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
 bm.to_mesh(o.data);bm.free()
 if 'gum'not in name:
  # Show acquired crowns only. Roots are removed at a per-tooth cervical plane;
  # the dataset's real gingiva remains around them. No scan bases are retained.
  bm=bmesh.new();bm.from_mesh(o.data)
  is_lower=name.startswith('lower');yy=[v.co.y for v in bm.verts]
  h=.009 if 'incisor'in name else .010 if 'canine'in name else .007
  level=max(yy)-h if is_lower else min(yy)+h
  result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,level,0),plane_no=(0,-1 if is_lower else 1,0),clear_outer=True)
  edges=[e for e in bm.edges if e.is_boundary]
  if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
  bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
 else:
  modifier(o,'SOLIDIFY',thickness=.0005,offset=0)
# An authored floor of mouth joins the acquired lingual base to the lower gingival region.
# This intentionally overlaps the base inside tissue; it does not fill the oral airspace.
cs=[(54,84,75,18),(63,86,61,23),(80,73,50,26),(99,66,48,27),(114,70,53,24),(125,76,65,17)]
v=[];f=[];N=24
for x,top,bottom,width in cs:
 for j in range(N):
  a=2*math.pi*j/N
  v.append(display((x,width*math.cos(a),(top+bottom)/2+(top-bottom)/2*math.sin(a))))
for i in range(len(cs)-1):
 for j in range(N):f.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
f.extend([tuple(range(N-1,-1,-1)),tuple((len(cs)-1)*N+j for j in range(N))])
floor=make('mouth_floor',v,f,'gum');modifier(floor,'SUBSURF',levels=2)
# A hollow, continuous nasal passage formed by anatomical section contours.
# It is a fitted teaching approximation, not a segmented nasal scan or CFD domain.
controls=[(36,130,5,4),(43,137,9,9),(58,140,12,14),(80,140,14,17),(104,139,13,17),(123,133,12,14),(134,122,11,9),(134,115,10,6)]
def catmull(p0,p1,p2,p3,t):return .5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
rings=[]
for i in range(len(controls)-1):
 for j in range(5):
  ps=[Vector(controls[max(0,min(len(controls)-1,k))])for k in [i-1,i,i+1,i+2]]
  rings.append(catmull(*ps,j/5))
rings.append(Vector(controls[-1]));vs=[];fs=[];N=36
for c in rings:
 for j in range(N):
  a=2*math.pi*j/N
  vs.append(display((c[0],c[2]*math.cos(a),c[1]+c[3]*math.sin(a))))
for i in range(len(rings)-1):
 for j in range(N):fs.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
nasal=make('nasal_wall',vs,fs,'nasal_wall');modifier(nasal,'SOLIDIFY',thickness=.001,offset=0)
# Create a capped sagittal view from the same volumetric geometry before deformation.
for o in list(full.children):
 cp=o.copy();cp.data=o.data.copy();cp.name=o.name+'__section';scene.collection.objects.link(cp);cp.parent=section
 bm=bmesh.new();bm.from_mesh(cp.data)
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.0000001,plane_co=(0,0,0),plane_no=(0,0,1),clear_outer=True)
 cut=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z)<1e-6 for v in e.verts)]
 if cut:bmesh.ops.holes_fill(bm,edges=cut,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(cp.data);bm.free();cp.data.update()
# Save rest first; movement development must not change this neutral source.
for o in full.children:o.hide_render=True
scene.world.color=(.81,.83,.80);scene.render.engine='BLENDER_WORKBENCH'
s=scene.display.shading;s.light='STUDIO';s.studio_light='paint.sl';s.color_type='MATERIAL';s.show_shadows=True;s.show_cavity=True;s.cavity_type='BOTH';s.curvature_ridge_factor=1.1;s.curvature_valley_factor=1.0;s.background_type='WORLD';s.show_specular_highlight=True
camdata=bpy.data.cameras.new('Study Camera');cam=bpy.data.objects.new('Study Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100

def camera(pos,target,scale):
 cam.location=pos;z=(cam.location-Vector(target)).normalized();x=Vector((0,1,0)).cross(z).normalized();y=z.cross(x)
 from mathutils import Matrix
 cam.rotation_euler=Matrix((x,y,z)).transposed().to_euler();camdata.ortho_scale=scale

def still(name,pos,target,scale,mode='section',hide=()):
 for parent in [full,section]:
  for o in parent.children:o.hide_render=parent.name!=mode or o.name.split('__')[0] in hide
 camera(pos,target,scale);scene.render.filepath=str(ROOT/'public/evidence'/name);bpy.ops.render.render(write_still=True)
still('rest-side.png',(-.012,.005,.3),(-.012,.005,0),.155)
still('rest-front.png',(-.35,.005,0),(-.04,.005,0),.085,'full')
still('rest-oblique.png',(-.18,.1,.25),(-.015,0,0),.17,'full',('skin',))
still('tongue-palate.png',(-.015,.014,.25),(-.015,.014,0),.105,'section',('skin','nasal_wall'))
still('nasal-pharynx.png',(.017,.022,.25),(.017,.022,0),.103,'section',('skin',))
for parent in [full,section]:
 for o in parent.children:o.hide_render=parent==full
camera((-.012,.005,.3),(-.012,.005,0),.155)
# Disable the section group in the delivered default asset through extras, not deleted geometry.
full['view']='full';section['view']='section';scene['model_status']='experimental anatomical rest study; expert review pending'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'model/makharij-rest.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'public/models/makharij-rest.glb'),export_format='GLB',export_yup=False,export_extras=True,export_animations=False,export_cameras=False,export_lights=False)
stats={}
for o in list(full.children)+list(section.children):
 bm=bmesh.new();bm.from_mesh(o.data)
 stats[o.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'volume_m3':bm.calc_volume(signed=True)};bm.free()
(ROOT/'docs/rest-geometry.json').write_text(json.dumps(stats,indent=2))
print('MODEL_BUILD_COMPLETE')
