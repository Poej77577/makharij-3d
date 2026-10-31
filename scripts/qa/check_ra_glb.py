"""Check decoded delivered GLB morphs throughout the actual staged Ra cycle.
No anatomical/tajwid approval. Independent of the field fitter's vertex data.
"""
import json,struct,hashlib
from pathlib import Path
import numpy as np,fcl,trimesh
ROOT=Path(__file__).resolve().parents[2];path=ROOT/'assets/anatomy/makharij-ra-prototype.glb';blob=path.read_bytes();jlen,jtype=struct.unpack_from('<I4s',blob,12);g=json.loads(blob[20:20+jlen]);blen,btype=struct.unpack_from('<I4s',blob,20+jlen);assert btype==b'BIN\0';binary=blob[28+jlen:28+jlen+blen]
def read(i):
 a=g['accessors'][i];dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]);n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
 if 'bufferView' in a:
  v=g['bufferViews'][a['bufferView']];out=np.ndarray((a['count'],n),dtype=dtype,buffer=binary,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',n*dtype.itemsize),dtype.itemsize)).copy()
 else:out=np.zeros((a['count'],n),dtype=dtype)
 if a.get('sparse'):
  sp=a['sparse'];ix=sp['indices'];iv=g['bufferViews'][ix['bufferView']];idt=np.dtype({5125:'<u4',5123:'<u2',5121:'u1'}[ix['componentType']]);indices=np.frombuffer(binary,dtype=idt,count=sp['count'],offset=iv.get('byteOffset',0)+ix.get('byteOffset',0));val=sp['values'];vv=g['bufferViews'][val['bufferView']];values=np.frombuffer(binary,dtype=dtype,count=sp['count']*n,offset=vv.get('byteOffset',0)+val.get('byteOffset',0)).reshape(-1,n);out[indices]=values
 return out
parts={};targets={}
for node in g['nodes']:
 if 'mesh' not in node:continue
 assert not node.get('translation') and not node.get('rotation') and not node.get('scale') and not node.get('matrix'),'World transforms need explicit evaluation'
 mesh=g['meshes'][node['mesh']];assert len(mesh['primitives'])==1
 prim=mesh['primitives'][0];p=read(prim['attributes']['POSITION']).astype(float);f=read(prim['indices']).reshape(-1,3);parts[node['name']]=(p,f)
 if node['name']=='TONGUE':
  for name,t in zip(mesh['extras']['targetNames'],prim.get('targets',[])):targets[name]=read(t['POSITION']).astype(float)
assert set(targets)=={'ra_prepared','ra_contact'};p,faces=parts['TONGUE'];rest=json.loads((ROOT/'assets/anatomy/rest-meshes.json').read_text());assert np.array_equal(faces,np.asarray(rest['parts']['TONGUE']['indices']).reshape(-1,3));assert np.max(abs(p-np.asarray(rest['parts']['TONGUE']['positions']).reshape(-1,3)))<1e-8
regions=json.loads((ROOT/'data/motion/contact-regions-v9.json').read_text())['regions'];tip=np.asarray(regions['tongue-tip']['vertices']);roofids=np.asarray(regions['upper-alveolar']['triangles']);rp,rf=parts['HARD_PALATE'];roof=trimesh.Trimesh(rp*1000,rf[roofids],process=False)
def obj(v,f):
 m=fcl.BVHModel();m.beginModel(len(v),len(f));m.addSubModel(np.asarray(v,dtype=float),np.asarray(f,dtype=np.int32));m.endModel();return fcl.CollisionObject(m)
obstacles={n:obj(*parts[n]) for n in ['UPPER_TEETH','LOWER_TEETH','HARD_PALATE','SOFT_PALATE','GINGIVA_UPPER','GINGIVA_LOWER','PHARYNX','LIP_CONTEXT']+[n for n in parts if n.startswith('NASAL_')]}
def smooth(u):u=np.clip(u,0,1);return u*u*(3-2*u)
def weights(t):
 if t<.08:return 0,0
 if t<.26:return smooth((t-.08)/.18),0
 if t<.40:
  k=smooth((t-.26)/.14);return 1-k,k
 if t<.42:return 0,1
 if t<.70:
  k=1-smooth((t-.42)/.28);return 1-k,k
 if t<.86:return 1-smooth((t-.70)/.16),0
 return 0,0
closedSections={}
for name in ['TONGUE','SOFT_PALATE']+[n for n in parts if n.startswith('NASAL_')]:
 mesh=trimesh.Trimesh(*parts[name],process=False);closedSections[name]={'watertight':bool(mesh.is_watertight),'consistentWinding':bool(mesh.is_winding_consistent)}
 assert all(closedSections[name].values()),f'Computed section needs closed, consistently wound tissue: {name}'
oldn=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]]);oldarea=np.linalg.norm(oldn,axis=1);assert (oldarea>1e-14).all()
rows=[];failures=[];peakgap=None
for t in sorted(set(np.linspace(0,1,97).tolist()+[.08,.26,.40,.41,.42,.70,.86])):
 a,b=weights(t);q=p+a*targets['ra_prepared']+b*targets['ra_contact'];model=obj(q,faces);collisions=[n for n,o in obstacles.items() if fcl.collide(model,o,fcl.CollisionRequest(),fcl.CollisionResult())]
 n=np.cross(q[faces[:,1]]-q[faces[:,0]],q[faces[:,2]]-q[faces[:,0]]);minratio=float((np.linalg.norm(n,axis=1)/oldarea).min());row={'t':t,'weights':[float(a),float(b)],'collisions':collisions,'minAreaRatio':minratio};rows.append(row)
 if collisions or minratio<.1:failures.append(row)
 if t==.41:
  _,dist,_=trimesh.proximity.closest_point(roof,q[tip]*1000);peakgap=float(dist.min());near=int(np.sum(dist<.3));maxmove=float(np.linalg.norm(q-p,axis=1).max()*1000)
assert peakgap is not None
if peakgap>.3:failures.append({'intendedContactGap_mm':peakgap})
report={'asset':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(blob).hexdigest(),'samples':len(rows),'testedObstaclePairsPerState':len(obstacles),'failures':failures,'minimumTriangleAreaRatio':min(r['minAreaRatio']for r in rows),'contactRegionGap_mm':peakgap,'nearContactTipVertices':near,'maxTongueDisplacement_mm':maxmove,'computedSectionGeometry':closedSections,'actualTargets':list(targets),'duration_s':3.2,'rows':rows,'scope':'Actual exported GLB decoded and evaluated at discrete cycle times, triangle intersections+area ratios+source-calibrated ROI distances only. No all-time, internal containment or anatomical/tajwid approval.'}
out=ROOT/'research/qa/ra-glb-v10.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['rows','scope','asset','actualTargets']},ensure_ascii=False));raise SystemExit(1 if failures else 0)
