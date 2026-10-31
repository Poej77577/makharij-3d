"""Transfer Ra calibration only after verifying the refined rest surface.
The final exported GLB must still be checked separately. No clinical approval.
"""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[2]
rest=ROOT/'assets/anatomy/rest-meshes.json';raw=rest.read_bytes();data=json.loads(raw);previous=ROOT/'assets/anatomy/makharij-ra-prototype.glb';old=trimesh.load_scene(previous,process=False);checks={}
assert set(old.geometry)==set(data['parts'])
for name,part in data['parts'].items():
 p=np.array(part['positions']).reshape(-1,3);f=np.array(part['indices']).reshape(-1,3);mesh=old.geometry[name]
 if name!='LIP_CONTEXT':
  assert np.array_equal(mesh.vertices,p),name
  assert np.array_equal(mesh.faces,f),name
  checks[name]={'unchangedPositionsAndIndices':True}
 else:
  new=trimesh.Trimesh(p,f,process=False);queryOld=mesh.copy();queryNew=new.copy();queryOld.apply_scale(1000);queryNew.apply_scale(1000);_,a,_=trimesh.proximity.closest_point(queryOld,p*1000);_,b,_=trimesh.proximity.closest_point(queryNew,mesh.vertices*1000);error=float(max(a.max(),b.max())/1000);area=abs(float(new.area-mesh.area));assert error<1e-8 and area<1e-10,(error,area)
  checks[name]={'bidirectionalVertexSurfaceMax_m':error,'queryUnits':'mm for numeric conditioning; stored geometry stays meters','absoluteAreaDifference_m2':area,'oldVertices':len(mesh.vertices),'newVertices':len(p),'scope':'source refinement script also places every new sample on an original triangle edge'}
parent=ROOT/'data/motion/tongue-fit-ra-v9';out=ROOT/'data/motion/tongue-fit-ra-v10';out.mkdir(exist_ok=True);report=json.loads((parent/'tongue-fit.json').read_bytes());prior=report['restSha256'];report['restSha256']=hashlib.sha256(raw).hexdigest();report['rest']='assets/anatomy/rest-meshes.json';report['refinementTransfer']={'parentFit':'data/motion/tongue-fit-ra-v9','parentRestSha256':prior,'comparedGlbSha256':hashlib.sha256(previous.read_bytes()).hexdigest(),'checks':checks,'qualification':'geometric calibration inheritance only; final exported motion needs independent QA'};(out/'tongue-fit.json').write_text(json.dumps(report,indent=2));shutil.copy2(parent/'tongue-targets.npz',out/'tongue-targets.npz');print(json.dumps(report['refinementTransfer'],indent=2))
