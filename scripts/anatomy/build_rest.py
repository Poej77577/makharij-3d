"""Source-based preparation, raw source geometry preserved separately. No primitive anatomy."""
import bpy,bmesh,math,json,hashlib,re,collections
from mathutils.bvhtree import BVHTree
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from continuous_lips import build_continuous_lips
from refine_lip_contacts import refine_lip_contacts
from trim_nasal_interface import trim_nasal_interface
from nasal_lining import build_nasal_lining, SUGGESTED_COLORS
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'assets/anatomy';OUT.mkdir(parents=True,exist_ok=True)
FACE=ROOT/'assets/source/artiSynth/face/geometry';JAW=ROOT/'assets/source/artiSynth/jawTongue/geometry'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
COLORS={'TONGUE':(.66,.36,.34,1),'UPPER_TEETH':(.87,.84,.74,1),'LOWER_TEETH':(.87,.84,.74,1),'UPPER_LIP':(.64,.34,.33,1),'LOWER_LIP':(.64,.34,.33,1),'HARD_PALATE':(.72,.57,.46,1),'SOFT_PALATE':(.64,.42,.53,1),'PHARYNX':(.53,.42,.46,1),'LIP_CONTEXT':(.67,.53,.43,1),'GINGIVA_UPPER':(.63,.43,.39,1),'GINGIVA_LOWER':(.63,.43,.39,1),'NASAL_LINING':(.58,.65,.63,1)}
COLORS.update(SUGGESTED_COLORS)
def material(name):
 m=bpy.data.materials.new(name);m.diffuse_color=COLORS[name];m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=COLORS[name];bs.inputs['Roughness'].default_value=.55
 return m
MATS={n:material(n) for n in COLORS};objects={};sources={}
def create(name,vs,fs):
 mesh=bpy.data.meshes.new(name)
 if name=='FACE_CONTEXT':print('FEM source mesh data',len(vs),len(fs),flush=True)
 mesh.from_pydata(vs,[],fs)
 if name=='FACE_CONTEXT':print('FEM from_pydata done',flush=True)
 mesh.update()
 if name=='FACE_CONTEXT':print('FEM update done',flush=True)
 ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.data.materials.append(MATS[name]);objects[name]=ob
 for p in mesh.polygons:p.use_smooth=True
 return ob

def read(path,scale=1):
 vs=[];fs=[]
 for line in path.read_text(errors='replace').splitlines():
  p=line.split()
  if not p:continue
  if p[0]=='v':
   v=[float(s)*scale for s in p[1:4]];vs.append((.14-v[0],v[2]-.1,v[1]))
  elif p[0]=='f':
   f=[int(s.split('/')[0])-1 for s in p[1:]]
   for k in range(1,len(f)-1):fs.append([f[0],f[k],f[k+1]])
 sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
 return vs,fs

def crop(ob,point,normal,cap=False):
 bm=bmesh.new();bm.from_mesh(ob.data);result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=point,plane_no=normal,clear_outer=True,clear_inner=False)
 if cap:
  edges=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
  if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()

def clean(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 deg=[f for f in bm.faces if f.calc_area()<1e-14]
 if deg:bmesh.ops.delete(bm,geom=deg,context='FACES')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()

def subdiv(ob,level):
 bpy.context.view_layer.objects.active=ob;ob.select_set(True);mod=ob.modifiers.new('Source-surface refinement','SUBSURF');mod.levels=level;mod.render_levels=level;bpy.ops.object.modifier_apply(modifier=mod.name);ob.select_set(False);clean(ob)

def jaw_open(ob):
 a=math.radians(-6);cx,cy=.003,.037
 for v in ob.data.vertices:
  x,y=v.co.x-cx,v.co.y-cy;v.co.x=cx+math.cos(a)*x-math.sin(a)*y;v.co.y=cy+math.sin(a)*x+math.cos(a)*y

print('STAGE Source tongue:',flush=True)
# Source tongue: closed full-volume surface, not created from a primitive.
vs,fs=read(FACE/'badintongue.obj');tongue=create('TONGUE',vs,fs);clean(tongue);subdiv(tongue,2)
# Local medial clearance at measured source-crown intersection patch, not a global shrink.
# F v3 hit bounds X31..35,Y-2.2..-4.3,Z-19.4..-22.7mm; all coordinates meters.
for v in tongue.data.vertices:
 x,y,z=v.co;v.co.z+=.0018*math.exp(-((x-.0335)/.008)**2-((y+.004)/.008)**2-((z+.022)/.008)**2)
print('STAGE Real dental cast crowns:',flush=True)
# Real dental cast crowns: SOURCE CREST-INFORMED SLOPED gingival display planes.
# Earlier horizontal crop retained plaster floor; never shrink tongue to fit that support.
# canonical y=native z-.1; lower plane nativeZ=.1056-.16*canonicalX.
for name,file,point,normal in [('UPPER_TEETH','upperteeth.obj',(0,.0115,0),(.025,1,0)),('LOWER_TEETH','lowerteeth.obj',(0,.0056,0),(-.16,-1,0))]:
 vs,fs=read(FACE/file);ob=create(name,vs,fs);crop(ob,point,normal,False);clean(ob)
 if name.startswith('LOWER'):jaw_open(ob)
print('STAGE Thin support margin',flush=True)
# Thin support margin bands from identical casts, leaving the oral horseshoe OPEN.
for name,file,pointA,normalA,pointB,normalB in [('GINGIVA_UPPER','upperteeth.obj',(0,.0145,0),(.025,1,0),(0,.0115,0),(-.025,-1,0)),('GINGIVA_LOWER','lowerteeth.obj',(0,.0056,0),(.16,1,0),(0,.0036,0),(-.16,-1,0))]:
 vs,fs=read(FACE/file);ob=create(name,vs,fs);crop(ob,pointA,normalA,False);crop(ob,pointB,normalB,False);clean(ob)
 if name.endswith('LOWER'):jaw_open(ob)
# Trim only unsupported cast-derived lower gingival display margin; do not deform tongue.
gum=objects['GINGIVA_LOWER'];beforeGumTriangles=len(gum.data.polygons)
tongueBVH=BVHTree.FromPolygons([v.co for v in tongue.data.vertices],[list(f.vertices)for f in tongue.data.polygons],all_triangles=True)
def gumClearance(p):
 co,no,idx,dist=tongueBVH.find_nearest(p)
 return (p-co).dot(no)-.00035 if co is not None and dist<.004 else .004
vv=[v.co.copy()for v in gum.data.vertices];newV=[];newF=[]
for f in gum.data.polygons:
 poly=[vv[i]for i in f.vertices];out=[]
 for i,A in enumerate(poly):
  B=poly[(i+1)%len(poly)];da,db=gumClearance(A),gumClearance(B)
  if da>=0:out.append(A)
  if (da>=0)!=(db>=0):out.append(A+(B-A)*(da/(da-db)))
 if len(out)>=3:
  start=len(newV);newV.extend(out)
  for j in range(1,len(out)-1):newF.append([start,start+j,start+j+1])
gum.data.clear_geometry();gum.data.from_pydata(newV,[],newF);gum.data.update();clean(gum)
gumTrim={'method':'source cast margin clipped outside tongue with .35mm target clearance','beforeTriangles':beforeGumTriangles,'afterTriangles':len(gum.data.polygons),'tongueChanged':False}
print('STAGE Same published raw-frame',flush=True)
# Same published raw-frame palatal and pharyngeal wall; preserve native source surfaces.
vs,fs=read(JAW/'badinpalate.obj');bins={'HARD_PALATE':[],'PHARYNX':[]}
for f in fs:
 c=sum((Vector(vs[i]) for i in f),Vector())/3
 bins['HARD_PALATE' if c.y>.007 and c.x>.028 else 'PHARYNX'].append(f)
for name,faces in bins.items():
 ids=sorted({i for f in faces for i in f});ix={v:i for i,v in enumerate(ids)};ob=create(name,[vs[i] for i in ids],[[ix[i] for i in f] for f in faces]);clean(ob)
print('STAGE Published registered INIT',flush=True)
# Published registered INIT soft palate. Named up is NOT safer; source up penetrates tongue.
vs,fs=read(JAW/'softpalate_init.obj',.001);ob=create('SOFT_PALATE',vs,fs);clean(ob)
# Tiny local technical clearance adjustment against closed source tongue, attachments fixed.
tongueBVH=BVHTree.FromPolygons([v.co for v in tongue.data.vertices],[list(p.vertices) for p in tongue.data.polygons],all_triangles=True)
baseSoft=[v.co.copy() for v in ob.data.vertices];softCorrections=[]
up,_=read(JAW/'softpalate_up.obj',.001);down,_=read(JAW/'softpalate_down.obj',.001)
anchors=[i for i,v in enumerate(baseSoft) if (v-Vector(up[i])).length<1e-9 and (v-Vector(down[i])).length<1e-9]
for i,v in enumerate(ob.data.vertices):
 if i in anchors:continue
 hit=tongueBVH.find_nearest(v.co)
 if hit[0] is None:continue
 co,no,idx,dist=hit;signed=(v.co-co).dot(no)
 if signed<.00030 and dist<.001:
  target=co+no*.00030;delta=target-v.co
  if delta.length<=.00075:v.co=target;softCorrections.append((i,delta.length))
print('STAGE continuous FEM lips',flush=True)
ob,lipMasks,lipFitReport,lipSources=build_continuous_lips(FACE,create)
lipMasks,lipRefinement=refine_lip_contacts(ob,lipMasks)
lipFitReport['contactSurfaceRefinement']=lipRefinement
for path,sha in lipSources.items():sources[str(Path(path).relative_to(ROOT))]=sha
print('STAGE nose',flush=True)
sources['scripts/anatomy/nasal_lining.py']=hashlib.sha256((ROOT/'scripts/anatomy/nasal_lining.py').read_bytes()).hexdigest()
nasal=build_nasal_lining(hard_palate=objects['HARD_PALATE'],pharynx=objects['PHARYNX'],face_bounds=objects['LIP_CONTEXT'],create=create)
nasal['metadata']['softPalateBoundaryTrim']=trim_nasal_interface(objects['NASAL_LINING'],objects['SOFT_PALATE'])
(OUT/'nasal-reconstruction.json').write_text(json.dumps(nasal['metadata'],ensure_ascii=False,indent=2))
print('STAGE serialize',flush=True)
# Scene contract and semantic metadata.
for name,ob in objects.items():
 ob['partId']=name;ob['metersPerUnit']=1.;ob['source']='authored source-landmark nasal approximation' if name.startswith('NASAL_') else 'ArtiSynth published research surface, see provenance';ob['review']='not anatomically/tajwid independently reviewed'
 bpy.context.view_layer.objects.active=ob
 if name!='LIP_CONTEXT':clean(ob)
 for polygon in ob.data.polygons:polygon.use_smooth=True
parts={}
for name,ob in objects.items():
 parts[name]={'positions':[q for v in ob.data.vertices for q in v.co], 'indices':[i for p in ob.data.polygons for i in p.vertices]}
 if name=='LIP_CONTEXT':parts[name]['masks']=lipMasks
# Soft-palate raw aligned morph inputs remain native indexed, no claim measured movement.
rawSoft={}
for name in ['softpalate_init','softpalate_up','softpalate_down']:
 v,f=read(JAW/(name+'.obj'),.001);rawSoft[name]={'positions':[q for p in v for q in p],'indices':[i for f0 in f for i in f0]}
(OUT/'softpalate-native-variants.json').write_text(json.dumps(rawSoft,separators=(',',':')))
contract={'version':'badin-prepared-rest-v10','units':'m','axes':{'X':'anterior','Y':'superior','Z':'lateral'},'transformFromRawMeters':[[ -1,0,0,.14],[0,0,1,-.1],[0,1,0,0],[0,0,0,1]],'parts':parts,'sources':sources,'edits':{'upperGingivalPlaneCanonical':'y=.0115-.025*x; keep below','lowerGingivalPlaneNative':'z=.1056-.16*canonicalX; keep above','dentalRootCaps':'none; horseshoe stays open','lowerGingivalTrim':gumTrim,'softPalateSourceRest':'registered INIT + local clearance against tongue','softPalateCorrectionMax_m':max([d for _,d in softCorrections],default=0),'softPalateCorrectionVertices':len(softCorrections),'softPalateFixedAttachmentVertices':len(anchors),'localTongueFit':{'method':'smooth positive-Z medial patch from F actual crown contacts','amplitude_m':.0018,'center_m':[.0335,-.004,-.022],'widths_m':[.008,.008,.008],'measuredHumanCalibration':False},'lowerJawRestRotation_deg':-6,'lowerJawHingeCanonical_m':[.003,.037,0],'lipContextFit':lipFitReport,'discardedParts':['UPPER_LIP filled object','LOWER_LIP filled object','hand-cut FACE_CONTEXT ring'],'nasalLining':nasal['metadata']},'status':'PREPARED NOT GATE PASSED'}
(OUT/'lip-source-masks.json').write_text(json.dumps({'assetVersion':'badin-prepared-rest-v10','part':'LIP_CONTEXT','units':'m','masks':lipMasks,'fit':lipFitReport,'sources':lipSources},separators=(',',':')))
(OUT/'rest-meshes.json').write_text(json.dumps(contract,separators=(',',':')))
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1;scene['assetVersion']='badin-prepared-rest-v10';scene['metersPerUnit']=1
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'makharij-rest.blend'))
# Export only semantic anatomy meshes; no cameras/lights.
bpy.ops.object.select_all(action='DESELECT')
for ob in objects.values():ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'makharij-rest.glb'),export_format='GLB',use_selection=True,export_yup=False,export_extras=True,export_apply=False)
print('PREPARED',[(n,len(o.data.vertices),len(o.data.polygons)) for n,o in objects.items()])
