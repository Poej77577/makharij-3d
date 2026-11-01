import json,struct,numpy as np
from pathlib import Path
import argparse
from fetch_hra_original import verify
parser=argparse.ArgumentParser(description="Audit groups of surfaces in the pinned original HRA GLB; no asset changes")
parser.add_argument("--input-dir",type=Path,default=Path(__file__).resolve().parents[1]/"work/research/nih-hra")
root=parser.parse_args().input_dir.resolve()
verify(root/'3d-vh-m-mouth.glb')
raw=(root/'3d-vh-m-mouth.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);p=20+n;blen,btype=struct.unpack_from('<II',raw,p);binary=memoryview(raw)[p+8:p+8+blen]
types={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'};dims={'VEC3':3,'SCALAR':1}
def read(k):
 a=g['accessors'][k];v=g['bufferViews'][a['bufferView']];t=np.dtype(types[a['componentType']]);w=dims[a['type']];return np.ndarray((a['count'],w),dtype=t,buffer=binary,offset=a.get('byteOffset',0)+v.get('byteOffset',0),strides=(v.get('byteStride',w*t.itemsize),t.itemsize)).copy()
def audit(names):
 verts=[];faces=[];base=0
 for m in g['meshes']:
  if m['name'] not in names:continue
  for p in m['primitives']:
   v=read(p['attributes']['POSITION']);f=read(p['indices']).astype(np.int64).reshape(-1,3);verts.append(v);faces.append(f+base);base+=len(v)
 v=np.concatenate(verts);f=np.concatenate(faces);uv,ix,inv=np.unique(np.rint(v/1e-7).astype(np.int64),return_index=True,return_inverse=True,axis=0);p=v[ix];f=inv[f];e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);ue,count=np.unique(e,return_counts=True,axis=0);boundary=ue[count==1];bad=ue[count>2];pv=p[boundary.reshape(-1)]
 return{'parts':names,'positions':len(v),'weldedPositions':len(p),'triangles':len(f),'boundaryEdges':len(boundary),'nonmanifoldEdges':len(bad),'boundaryBoundsNativeMeters':[pv.min(0).tolist(),pv.max(0).tolist()]if len(pv)else None,'signedVolumeMlOnlyIfClosed':float(np.einsum('ij,ij->i',p[f[:,0]],np.cross(p[f[:,1]],p[f[:,2]])).sum()/6*1e6)if not len(boundary)and not len(bad)else None}
out={}
for label,names in [('tongue_surfaces_together',['VH_M_posterior_part_of_tongue','VH_M_dorsal_tongue','VH_M_ventral_tongue']),('tongue_with_papillae',['VH_M_posterior_part_of_tongue','VH_M_dorsal_tongue','VH_M_ventral_tongue','VH_M_fungiform_papillae','VH_M_circumvallate_papillae']),('palate_surfaces_together',['VH_M_hard_palate','VH_M_mucosa_of_soft_palate']),('all_oral_mucosal_parts',['VH_M_posterior_part_of_tongue','VH_M_dorsal_tongue','VH_M_ventral_tongue','VH_M_mouth_floor','VH_M_buccal_mucosa','VH_M_gingiva_of_lower_jaw','VH_M_ginviva_of_upper_jaw','VH_M_hard_palate','VH_M_mucosa_of_soft_palate','VH_M_frenulum_of_upper_lip','VH_M_frenulum_of_lower_lip'])]:
 out[label]=audit(names)
(root/'group-surface-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
