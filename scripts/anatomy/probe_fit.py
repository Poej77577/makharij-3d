"""Bounded source-part registration/contact correction candidate; no source Blender edits."""
import bpy,json,math,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
src=ROOT/'assets/anatomy/rest-meshes.json';d=json.loads(src.read_text());assert d['version']=='badin-prepared-rest-v3'
report={'inputSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'unmeasuredTechnicalFit':True,'changes':[]}
for name in ['TONGUE','UPPER_LIP','LOWER_LIP']:
 part=d['parts'][name];p=np.array(part['positions']).reshape(-1,3);q=p.copy();f=np.array(part['indices']).reshape(-1,3)
 if name=='TONGUE':q[:,2]+=.0018*np.exp(-((p[:,0]-.0335)/.008)**2-((p[:,1]+.004)/.008)**2-((p[:,2]+.022)/.008)**2)
 elif name=='UPPER_LIP':q+=np.array([.0021,.001,0])
 else:q+=np.array([.0018,-.0008,0])
 a=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]);b=np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]])
 flips=int(np.sum(np.sum(a*b,axis=1)<0));assert flips==0
 report['changes'].append({'part':name,'maxDelta_mm':float(np.linalg.norm(q-p,axis=1).max()*1000),'reversedFaces':flips})
 part['positions']=q.reshape(-1).tolist()
d['version']='badin-rest-v4-probe';Path('/tmp/badin-v4-probe.json').write_text(json.dumps(d,separators=(',',':')));Path('/tmp/badin-v4-probe-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for name,part in d['parts'].items():
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(np.array(part['positions']).reshape(-1,3).tolist(),[],np.array(part['indices']).reshape(-1,3).tolist());mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
bpy.ops.export_scene.gltf(filepath='/tmp/badin-v4-probe.glb',export_format='GLB',export_yup=False)
print(json.dumps(report))
