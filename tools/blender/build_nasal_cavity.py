"""One continuous hollow nasal mucosal wall; separate closed air analysis.

Run in Blender with --disable-autoexec and a trailing --. A reviewed Manifold
worker unions authored ring sweeps and subtracts the inner air volume. The
front outer caps explicitly contain the *same* inner cap triangles: their
subtraction leaves an annulus, never a runtime airflow plug. No old head Boolean
or source nasal-mucosa-as-air relabelling is used. All hidden shapes are inferred.
"""
from pathlib import Path
import argparse,hashlib,json,math,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def norm(v):return v/max(np.linalg.norm(v),1e-15)
def frame(t):
 t=norm(t);lat=norm(np.array([0.,0.,1.])-t*t[2]);return lat,norm(np.cross(t,lat))
def triangulate_face(f):return [(f[0],f[j],f[j+1])for j in range(1,len(f)-1)]
def sweep(sections,n=24,port=None,thickness=0,samples=8,section_axis=None,external_start=False,external_end=False):
 centers=np.array([s['center_m']for s in sections],dtype=float);radii=np.array([s['radii_m']for s in sections]);tang=[]
 for i in range(len(centers)):
  v=centers[min(i+1,len(centers)-1)]-centers[max(i-1,0)]
  tang.append(norm(v))
 if section_axis is not None:tang=[norm(np.array(section_axis,dtype=float)) for _ in centers]
 if port is not None:tang[0]=norm(np.array(port['inward_normal']))
 lat0,sec0=frame(tang[0])
 if port is not None:
  actual=np.array(port['ring_vertex_positions_m']);d=actual-centers[0];uu=d@lat0;vv=d@sec0;ww=d@tang[0]
  radii[0]=[max(abs(uu)),max(abs(vv))];theta=np.unwrap(np.arctan2(vv,uu));u0=uu/radii[0,0];v0=vv/radii[0,1]
 else:
  theta=np.linspace(0,2*math.pi,n,endpoint=False);u0=np.cos(theta);v0=np.sin(theta);ww=np.zeros(n);actual=None
 n=len(theta);rings=[];path=[]
 for segment in range(len(centers)-1):
  length=np.linalg.norm(centers[segment+1]-centers[segment]);a,b=centers[segment:segment+2]
  for k in range(samples):
   t=k/samples;h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t;h01=-2*t**3+3*t*t;h11=t**3-t*t
   c=(h00*a+h10*length*tang[segment]+h01*b+h11*length*tang[segment+1]) if port is not None and segment==0 else a+(b-a)*smooth(t)
   tangent=norm((1-smooth(t))*tang[segment]+smooth(t)*tang[segment+1])
   lat,sec=frame(tangent);rr=(1-t)*radii[segment]+t*radii[segment+1];mix=smooth(np.linalg.norm(c-centers[0])/.009)
   u=(1-mix)*u0+mix*np.cos(theta);v=(1-mix)*v0+mix*np.sin(theta)
   ring=c+np.outer((rr[0]+thickness)*u,lat)+np.outer((rr[1]+thickness)*v,sec)+np.outer((1-mix)*ww,tangent)
   if segment==0 and k==0 and actual is not None and thickness==0:ring=actual.copy()
   rings.append(ring);path.append(c.tolist())
 lat,sec=frame(tang[-1]);ring=centers[-1]+np.outer((radii[-1,0]+thickness)*np.cos(theta),lat)+np.outer((radii[-1,1]+thickness)*np.sin(theta),sec);rings.append(ring);path.append(centers[-1].tolist())
 if thickness:
  if not external_start:rings.insert(0,rings[0]-thickness*tang[0])
  if not external_end:rings.append(rings[-1]+thickness*tang[-1])
 verts=np.concatenate(rings).tolist();faces=[]
 for i in range(len(rings)-1):
  for j in range(n):faces+=triangulate_face((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
 cap_rings=[]
 for end,sgn in [(0,-1),(len(rings)-1,1)]:
  # The outer cap shares the exact inner core, even for a nonplanar source ring.
  if end==0 and actual is not None:inner=actual
  else:
   lat,sec=frame(tang[0]if end==0 else tang[-1]);ci=centers[0]if end==0 else centers[-1];ri=radii[0]if end==0 else radii[-1];inner=ci+np.outer(ri[0]*np.cos(theta),lat)+np.outer(ri[1]*np.sin(theta),sec)
  external=(end==0 and external_start)or(end==len(rings)-1 and external_end)
  if thickness and external:
   off=len(verts);verts.extend(inner.tolist())
   for j in range(n):
    q=(j+1)%n;f=(end*n+j,end*n+q,off+q,off+j)
    if sgn<0:f=f[::-1]
    faces+=triangulate_face(f)
   ids=list(range(off,off+n))
  else:
   ids=[end*n+j for j in range(n)]
   if thickness:inner=rings[end]
  mid=len(verts);verts.append(np.mean(inner,axis=0).tolist())
  for j in range(n):
   f=(mid,ids[j],ids[(j+1)%n]);faces.append(f if sgn>0 else f[::-1])
  cap_rings.append(inner)
 p=np.asarray(verts);f=np.asarray(faces,dtype=np.uint32);volume=np.einsum('ij,ij->i',p[f[:,0]],np.cross(p[f[:,1]],p[f[:,2]])).sum()/6
 if volume<0:f=f[:,::-1]
 return p,f,path,cap_rings[-1]
def worker(config):
 import manifold3d as md
 from scipy.spatial import cKDTree
 spec=config['spec'];ports=config['ports'];inner=[];outer=[];guides={};samples=spec['samplesPerSegment'];outlet=None
 def solid(p,f):
  m=md.Manifold(md.Mesh(vert_properties=np.asarray(p*1000,dtype=np.float32),tri_verts=np.asarray(f,dtype=np.uint32)))
  if str(m.status())!='Error.NoError':raise RuntimeError('Invalid sweep: '+str(m.status()))
  return m
 for port in ports:
  sign=1 if port['center_m'][2]>0 else -1
  sections=[{'center_m':port['center_m'],'radii_m':[.002,.002]}]
  sections +=[{'center_m':[s['center_m'][0],s['center_m'][1],sign*s['center_m'][2]],'radii_m':s['radii_m']}for s in spec['bilateralSections']]
  p,f,path,_=sweep(sections,port=port,samples=samples,section_axis=(-1,0,0));inner.append(solid(p,f));guides[port['id']]=path
  p,f,_,_=sweep(sections,port=port,thickness=spec['wallThickness_m'],samples=samples,section_axis=(-1,0,0),external_start=True);outer.append(solid(p,f))
 p,f,common,outlet=sweep(spec['commonSections'],n=32,samples=samples,section_axis=(0,-1,0));inner.append(solid(p,f));p,f,_,_=sweep(spec['commonSections'],n=32,thickness=spec['wallThickness_m'],samples=samples,section_axis=(0,-1,0),external_end=True);outer.append(solid(p,f))
 air=inner[0]+inner[1]+inner[2];outside=outer[0]+outer[1]+outer[2];uncovered=air-outside
 if not uncovered.is_empty() and uncovered.volume()>1e-5:raise RuntimeError('Air is not contained in outer mucosal envelope: '+str(uncovered.volume())+' bbox '+str(uncovered.bounding_box()))
 wall=outside-air
 if wall.is_empty()or str(wall.status())!='Error.NoError':raise RuntimeError('Mucosal difference failed')
 if len(wall.decompose())!=1 or len(air.decompose())!=1:raise RuntimeError('Nasal passage/wall must be single connected components')
 if wall.genus()!=2 or air.genus()!=0:raise RuntimeError('Expected exactly three wall ports (genus2), closed air genus0; got '+str((wall.genus(),air.genus())))
 meshes={}
 all_port_points=np.concatenate([np.array(p['ring_vertex_positions_m'])for p in ports]+[outlet]);tree=cKDTree(all_port_points)
 for name,m in [('NASAL_MUCOSA',wall),('NASAL_AIR_NEGATIVE',air)]:
  me=m.to_mesh();p=np.asarray(me.vert_properties[:,:3],dtype=float)/1000;f=np.asarray(me.tri_verts,dtype=np.int32)
  d,idx=tree.query(p);snap=d<2e-7;p[snap]=all_port_points[idx[snap]]
  meshes[name+'_points']=p;meshes[name+'_faces']=f
  distances=cKDTree(p).query(all_port_points)[0]
  if max(distances)>2e-7:raise RuntimeError(name+' lost actual port vertices '+str(max(distances)))
 out=Path(config['out']);np.savez_compressed(out/'nasal-geometry.npz',**meshes)
 oc=np.mean(outlet,axis=0).tolist();on=norm(np.array(spec['commonSections'][-2]['center_m'])-np.array(oc)).tolist()
 outlet_port={'id':'nasopharynx_outlet','name':'nasopharynx_outlet','role':'outlet','center_m':oc,'inward_normal':on,'ring_vertex_positions_m':outlet.tolist(),'ring_m':outlet.tolist()}
 paths=[]
 for port in ports:
  # Both branch centerlines overlap the common chamber; join them without a
  # discontinuous shortcut through septal tissue.
  join=min(range(len(common)),key=lambda i:np.linalg.norm(np.array(common[i])-np.array(guides[port['id']][-1])))
  path=guides[port['id']]+common[join:];path[0]=port['center_m'];path[-1]=oc
  paths.append({'inlet':port['id'],'outlet':outlet_port['id'],'points_m':path})
 record={'ports':ports+[outlet_port],'guide_paths':paths,'wallVolume_m3':wall.volume()/1e9,'airVolume_m3':air.volume()/1e9,'wallComponents':len(wall.decompose()),'airComponents':len(air.decompose()),'wallGenus':wall.genus(),'airGenus':air.genus(),'expectedWallGenus':2,'expectedAirGenus':0,'externalAirPorts':3,'innerNotContainedVolume_m3':uncovered.volume()/1e9,'geometryMethod':'Continuous authored source-ring sweeps; bilateral/common Manifold unions; outer-minus-inner hollow positive wall, exact shared inner-cap core removed from every runtime port.'}
 (out/'geometry-record.json').write_text(json.dumps(record,indent=2))
 print(json.dumps({'wallTriangles':wall.num_tri(),'airTriangles':air.num_tri(),'airComponents':len(air.decompose()),'wallComponents':len(wall.decompose())}))
def build(args):
 import bpy,bmesh
 from mathutils import Vector
 spec_path=ROOT/'data/anatomy/nasal-cavity.json';spec=json.loads(spec_path.read_text());face_folder=ROOT/'artifacts/method-evidence/face-context';oral_folder=ROOT/'artifacts/method-evidence/oral-sculpt';fm=json.loads((face_folder/'face-manifest.json').read_text());om=json.loads((oral_folder/'oral-manifest.json').read_text())
 if sha(face_folder/'face-context.glb')!=fm['glbSha256']:raise RuntimeError('Face identity mismatch')
 ports=fm.get('nasalPorts',[])
 if len(ports)!=2:raise RuntimeError('Build the default open-nostril face first')
 if sha(face_folder/'face-context.blend')!=fm['blendSha256']:raise RuntimeError('Native face identity mismatch')
 bpy.ops.wm.open_mainfile(filepath=str(face_folder/'face-context.blend'),use_scripts=False,load_ui=False)
 face=bpy.data.objects['HEAD_EXTERNAL'];basis=face.data.shape_keys.key_blocks['Basis'];control_names=['JAW_OPEN','LIP_PRESS','LIP_ROUND','LIP_PROTRUDE'];port_deltas={}
 for control in control_names:
  key=face.data.shape_keys.key_blocks[control];port_deltas[control]={}
  for port in ports:
   delta=[]
   for i in port['face_vertex_ids']:
    d=key.data[i].co-basis.data[i].co;delta.append((-d.y,d.z,-d.x))
   port_deltas[control][port['id']]=np.array(delta)
 out=(ROOT/args.out).resolve();out.mkdir(parents=True,exist_ok=True);config={'spec':spec,'ports':ports,'out':str(out)};cp=out/'geometry-config.json';cp.write_text(json.dumps(config,indent=2))
 subprocess.run([str(ROOT/'.venv-qa/bin/python'),str(Path(__file__).resolve()),'--geometry-worker',str(cp)],check=True)
 data=np.load(out/'nasal-geometry.npz');record=json.loads((out/'geometry-record.json').read_text());bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 objects={}
 for name in ['NASAL_MUCOSA','NASAL_AIR_NEGATIVE']:
  p=data[name+'_points'];me=bpy.data.meshes.new(name+'_continuous_surface');me.from_pydata([(-v[2],-v[0],v[1])for v in p],[],data[name+'_faces']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);objects[name]=ob
  for f in me.polygons:f.use_smooth=True
  mat=bpy.data.materials.new('Authored nasal mucosal tissue'if name=='NASAL_MUCOSA'else'ANALYSIS AIR ENVELOPE - NEVER DISPLAY');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.48,.17,.14,1)if name=='NASAL_MUCOSA'else(.1,.35,.7,1);bs.inputs['Roughness'].default_value=.55;me.materials.append(mat)
  ob['role']='Positive hollow tissue wall with three unblocked air ports'if name=='NASAL_MUCOSA'else'Closed negative-air analysis envelope; not runtime displayed tissue';ob['dimensionsInferred']=True;ob['clinicalAcceptance']=False
  ob.shape_key_add(name='Basis')
  fields={control:np.zeros_like(p)for control in control_names}
  for port in ports:
   ring=np.array(port['ring_vertex_positions_m']);a=ring;b=np.roll(ring,-1,axis=0);ab=b-a
   t=np.clip(np.sum((p[:,None,:]-a[None,:,:])*ab[None,:,:],axis=2)/np.sum(ab*ab,axis=1)[None,:],0,1)
   closest=a[None,:,:]+t[:,:,None]*ab[None,:,:];dist=np.linalg.norm(p[:,None,:]-closest,axis=2);idx=np.argmin(dist,axis=1);picked=t[np.arange(len(p)),idx];nearest=dist[np.arange(len(p)),idx]
   w=np.clip((nearest-.001)/.007,0,1);w=1-w*w*(3-2*w)
   for control in control_names:
    d=port_deltas[control][port['id']];interp=(1-picked[:,None])*d[idx]+picked[:,None]*d[(idx+1)%len(ring)];fields[control]+=w[:,None]*interp
  for control in control_names:
   key=ob.shape_key_add(name=control)
   for v,q in zip(key.data,p+fields[control]):v.co=(-q[2],-q[0],q[1])
 objects['NASAL_AIR_NEGATIVE'].hide_render=True
 objects['NASAL_AIR_NEGATIVE'].hide_set(True)
 bpy.ops.wm.save_as_mainfile(filepath=str(out/'nasal-cavity.blend'),compress=True)
 for name,filename in [('NASAL_MUCOSA','nasal-cavity.glb'),('NASAL_AIR_NEGATIVE','nasal-airspace.analysis.glb')]:
  bpy.ops.object.select_all(action='DESELECT');objects[name].hide_set(False);objects[name].select_set(True);bpy.context.view_layer.objects.active=objects[name]
  bpy.ops.export_scene.gltf(filepath=str(out/filename),export_format='GLB',use_selection=True,export_extras=True,export_animations=False,export_morph=True,export_yup=True)
 if sha(face_folder/'face-context.glb')!=fm['glbSha256']:raise RuntimeError('Face changed during nasal build')
 manifest={'status':'experimental-connected-empty-passage','productionSelected':False,'clinicalAcceptance':False,'visualReview':'pending','parts':['NASAL_MUCOSA'],'glbSha256':sha(out/'nasal-cavity.glb'),'analysisGlbSha256':sha(out/'nasal-airspace.analysis.glb'),'analysisParts':['NASAL_AIR_NEGATIVE'],'analysisFile':'nasal-airspace.analysis.glb','faceSourceGlbSha256':fm['glbSha256'],'oralSourceGlbSha256':om['glbSha256'],'blendSha256':sha(out/'nasal-cavity.blend'),'specSha256':sha(spec_path),'gltfToProject':[[0,0,1],[0,1,0],[-1,0,0]],'recommendedSectionZ_m':spec['recommendedSectionZ_m'],'guidePaths_m':{('right'if p['inlet'].endswith('right')else'left'):p['points_m']for p in record['guide_paths']},'inferred':spec['inferred'],'limitations':spec['limitations'],'referenceBounds':spec['sourceReferenceBounds_m'],'sourceReferenceRole':'Original open positive nasal mucosa/nasopharyngeal tissue used only as bounds, not relabelled negative air','portsMatchActualEvaluatedNostrils':True,'controls':control_names,'portFollowing':{'method':'Exact source-boundary key deltas, nearest-segment interpolation; full follow within1mm of ring, smooth decay to zero at8mm','faceNativeSha256':fm['blendSha256'],'maximumBoundaryDeltas_m':{control:{port['id']:float(np.linalg.norm(port_deltas[control][port['id']],axis=1).max())for port in ports}for control in control_names}},**record}
 (out/'nasal-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'runtime':manifest['glbSha256'],'analysis':manifest['analysisGlbSha256'],'face':manifest['faceSourceGlbSha256'],'ports':len(record['ports'])}))
if __name__=='__main__':
 if '--geometry-worker'in sys.argv:worker(json.loads(Path(sys.argv[sys.argv.index('--geometry-worker')+1]).read_text()))
 else:
  p=argparse.ArgumentParser();p.add_argument('--out',default='artifacts/method-evidence/nasal-cavity');build(p.parse_args(sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]))
