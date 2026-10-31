from pathlib import Path
import numpy as np,json,hashlib
root=Path(__file__).resolve().parents[2]
p=root/'assets/candidates/artisynth_models/src/artisynth/models'
def vertices(path):return np.array([[float(x) for x in l.split()[1:4]]for l in path.read_text().splitlines()if l.startswith('v ')])
a=vertices(p/'jawTongue/geometry/softpalate_orig.obj');b=vertices(p/'jawTongue/geometry/softpalate_init.obj')
angle=.106345;R=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
t=np.array([-7.2117,0,12.08155]);res=np.linalg.norm(a@R.T+t-b,axis=1)
M=np.eye(4);M[:3,:3]=R;M[:3,3]=t
f=p/'face/geometry/badinairway.obj';j=p/'jawTongue/geometry/badinairway.obj'
output={'speaker_donor_identity':'unknown; do not claim common subject','source':'AirwaySkinDemo.java XSoftPalate + BadinJawHyoid.java setMesh','original_units':'mm','matrix_orig_to_init':M.tolist(),'original_to_init_rms_mm':float(np.sqrt(np.mean(res**2))),'original_to_init_max_mm':float(res.max()),'source_vertex_count':len(a),'shared_raw_airway_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'raw_airway_identical_bytes':f.read_bytes()==j.read_bytes(),'raw_airway_corresponding_max_delta_m':float(np.linalg.norm(vertices(f)-vertices(j),axis=1).max()),'palate_raw_to_mm_transform':np.diag([1000,1000,1000,1]).tolist(),'softpalate_init_to_mm_transform':np.eye(4).tolist(),'limitations':['Pose registration of model files is verified; anatomical registration to donor imaging is not.','Tooth source donor not established.','No acquired nasal cavity mesh identified.']}
(root/'docs/assets/registration-evidence.json').write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))
# Verify pose frames using unchanged attachment vertices, not matching counts alone.
def mesh(path):
 lines=path.read_text().splitlines()
 return np.array([[float(x)for x in l.split()[1:4]]for l in lines if l.startswith('v ')]),[l for l in lines if l.startswith('f ')]
geom=p/'jawTongue/geometry'
init,fi=mesh(geom/'softpalate_init.obj');up,fu=mesh(geom/'softpalate_up.obj');down,fd=mesh(geom/'softpalate_down.obj');orig,fo=mesh(geom/'softpalate_orig.obj')
mask=(np.linalg.norm(up-init,axis=1)<.001)&(np.linalg.norm(down-init,axis=1)<.001)
anchors=init[mask]
evidence={'topology_faces_identical':fi==fu==fd==fo,'anchor_indices':np.where(mask)[0].tolist(),'anchor_count':int(mask.sum()),'anchor_bounds_mm':[anchors.min(0).tolist(),anchors.max(0).tolist()],'anchor_centered_singular_values':np.linalg.svd(anchors-anchors.mean(0))[1].tolist(),'comparisons':[],'interpretation':'Full-rank unchanged 3D anchors establish up/down/init same frame; they do not establish non-intersection or anatomical validity.'}
for name,pose in [('up',up),('down',down),('orig',orig)]:
 x=pose[mask];cx=x.mean(0);cy=anchors.mean(0);uu,ss,vt=np.linalg.svd((x-cx).T@(anchors-cy));RR=vt.T@uu.T
 if np.linalg.det(RR)<0:vt[-1]*=-1;RR=vt.T@uu.T
 tt=cy-RR@cx;MM=np.eye(4);MM[:3,:3]=RR;MM[:3,3]=tt
 residual=np.linalg.norm(x@RR.T+tt-anchors,axis=1)
 evidence['comparisons'].append({'name':name,'raw_anchor_rms_mm':float(np.sqrt(np.mean(np.sum((x-anchors)**2,axis=1)))),'rigid_fit_matrix_to_init':MM.tolist(),'fit_rms_mm':float(np.sqrt(np.mean(residual**2))),'fit_max_mm':float(residual.max())})
(root/'docs/assets/softpalate-frame-anchors.json').write_text(json.dumps(evidence,indent=2))
print('Soft-palate frame anchors:',len(anchors),'full-rank singular values:',evidence['anchor_centered_singular_values'])
