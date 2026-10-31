"""Audit the actual binary delivered to the browser, after export.
Weld coincident render vertices (UV/normal seams) at 0.1 micrometre tolerance.
This checks topology, not biological or pronunciation correctness.
"""
import json,struct,hashlib,platform,sys
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];path=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'public/models/makharij-rest.glb');b=path.read_bytes()
magic,version,size=struct.unpack_from('<4sII',b);assert magic==b'glTF'and version==2 and size==len(b)
pos=12;g=None;binary=None
while pos<len(b):
 n,t=struct.unpack_from('<II',b,pos);chunk=b[pos+8:pos+8+n]
 if t==0x4e4f534a:g=json.loads(chunk)
 elif t==0x004e4942:binary=chunk
 pos+=n+8
widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16};dtypes={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}
def accessor(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];dt=np.dtype(dtypes[a['componentType']]);w=widths[a['type']];offset=v.get('byteOffset',0)+a.get('byteOffset',0)
 return np.ndarray((a['count'],w),dtype=dt,buffer=binary,offset=offset,strides=(v.get('byteStride',w*dt.itemsize),dt.itemsize)).copy()
meshes=[];total=0
for m in g['meshes']:
 vs=[];fs=[];base=0
 for p in m['primitives']:
  assert p.get('mode',4)==4
  v=accessor(p['attributes']['POSITION']);f=accessor(p['indices']).ravel().reshape(-1,3)
  assert np.isfinite(v).all()and f.max()<len(v)and f.min()>=0
  vs.append(v);fs.append(f+base);base+=len(v)
 if not vs:continue
 v=np.concatenate(vs);f=np.concatenate(fs);_,inv=np.unique(np.round(v/1e-7).astype(np.int64),axis=0,return_inverse=True);f=inv[f]
 # Ignore collapsed triangles created only by the seam weld; record their count.
 good=(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,0]!=f[:,2]);collapsed=int((~good).sum());f=f[good]
 e=Counter(tuple(sorted((int(t[i]),int(t[(i+1)%3]))))for t in f for i in range(3))
 a=vs[0];meshes.append({'name':m['name'],'renderVertices':len(v),'triangles':len(f),'collapsedByWeld':collapsed,'boundaryEdges':sum(c==1 for c in e.values()),'nonmanifoldEdges':sum(c>2 for c in e.values()),'boundsMeters':[v.min(0).tolist(),v.max(0).tolist()]});total+=len(f)
report={'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'gltfVersion':g['asset']['version'],'meshCount':len(meshes),'triangles':total,'unit':'metres by glTF contract','exportYupConversion':False,'axes':'source authored as X posterior, Y superior, Z lateral; both view groups share coordinates','weldToleranceMeters':1e-7,'meshes':meshes,'geometryChecksPassed':all(m['boundaryEdges']==0 and m['nonmanifoldEdges']==0 for m in meshes),'anatomicalApproval':False,'tajwidApproval':False,'interOrganCollisionVerified':False,'articulationVerified':False}
(ROOT/('work/candidate-audit.json' if len(sys.argv)>1 else 'docs/final-glb-audit.json')).write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items()if k!='meshes'},indent=2))
for m in meshes:
 if m['boundaryEdges']or m['nonmanifoldEdges']:print('TOPOLOGY ISSUE',m['name'],m['boundaryEdges'],m['nonmanifoldEdges'])
