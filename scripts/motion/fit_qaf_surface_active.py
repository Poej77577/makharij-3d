"""Posterior source surface contact band, with nearby organs held clear.
Technical geometric calibration, no qualified anatomical/tajwid approval.
"""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh
from scipy.sparse import coo_matrix
from trimesh.collision import CollisionManager
from surface_arap import SurfaceArap
ROOT=Path(__file__).resolve().parents[2];src=ROOT/'research/qa/prepared-rest-v10-meshes.json';raw=src.read_bytes();d=json.loads(raw);p=np.array(d['parts']['TONGUE']['positions']).reshape(-1,3);f=np.array(d['parts']['TONGUE']['indices']).reshape(-1,3);regions=json.load(open(ROOT/'data/motion/contact-regions-v6.json'))['regions'];vp=np.array(d['parts']['SOFT_PALATE']['positions']).reshape(-1,3);vf=np.array(d['parts']['SOFT_PALATE']['indices']).reshape(-1,3);vf=vf[regions['velum-oral']['triangles']];cent=p[f].mean(1);selected=np.flatnonzero((cent[:,0]>.018)&(cent[:,0]<.037)&(cent[:,1]>.001)&(abs(cent[:,2])<.016));tonguePatch=trimesh.Trimesh(p,f[selected],process=False);velum=trimesh.Trimesh(vp,vf,process=False)
def pair(A,B):
 best=(float('inf'),None,None,None)
 for pts,seg,inverse in [(A.reshape(-1,2),B,False),(B.reshape(-1,2),A,True)]:
  base=seg[:,0];v=seg[:,1]-base;den=(v*v).sum(1)
  for k,point in enumerate(pts):
   t=np.clip(((point-base)*v).sum(1)/np.maximum(den,1e-30),0,1);q=base+v*t[:,None];dist=((q-point)**2).sum(1);i=int(dist.argmin())
   if dist[i]<best[0]:best=(float(dist[i]),q[i]if inverse else point,point if inverse else q[i],i if inverse else k//2)
 return best
rows=[];cols=[];values=[];starts=[];targets=[];zs=[]
for z in np.linspace(-.012,.012,25):
 A,at=trimesh.intersections.mesh_plane(tonguePatch,[0,0,1],[0,0,z],return_faces=True);B=trimesh.intersections.mesh_plane(velum,[0,0,1],[0,0,z])
 if not len(A)or not len(B):continue
 _,point,target,idx=pair(A[:,:,:2],B[:,:,:2]);point=np.r_[point,z];target=np.r_[target,z];direction=(target-point)/np.linalg.norm(target-point);target=target-direction*.00025;tri=f[selected[at[idx]]];w=trimesh.triangles.points_to_barycentric(p[tri][None],point[None])[0]
 for index,v in zip(tri,w):rows.append(len(starts));cols.append(int(index));values.append(float(v))
 starts.append(point);targets.append(target);zs.append(float(z))
C=coo_matrix((values,(rows,cols)),shape=(len(starts),len(p))).tocsc();starts=C@p;targets=np.array(targets);x,y,z=p.T;fixed=set(np.flatnonzero((x<.011)|(x>.050)|(y<-.015)|(abs(z)>.026)|((x>.037)&(y>.009))))
obstacles=CollisionManager()
for name in ['UPPER_TEETH','LOWER_TEETH','HARD_PALATE','SOFT_PALATE','GINGIVA_UPPER','GINGIVA_LOWER','PHARYNX','LIP_CONTEXT']+[n for n in d['parts']if n.startswith('NASAL_')]:
 part=d['parts'][name];mesh=trimesh.Trimesh(np.array(part['positions']).reshape(-1,3),np.array(part['indices']).reshape(-1,3),process=False);obstacles.add_object(name,mesh)
 if name in ['PHARYNX','UPPER_TEETH','LOWER_TEETH','GINGIVA_UPPER','GINGIVA_LOWER']:
  _,distance,_=trimesh.proximity.closest_point(mesh,p);fixed.update(np.flatnonzero(distance<.0015))
 if name=='SOFT_PALATE':
  _,distance,_=trimesh.proximity.closest_point(mesh,p);fixed.update(np.flatnonzero((distance<.001)&(abs(z)>.014)))
old=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1);activeHistory=[]
for activeIteration in range(5):
 solver=SurfaceArap(p,f,C,sorted(fixed));q=p.copy();states=[];results=[];blockingVertices=set()
 for t in np.linspace(0,1,25):
  q=solver.solve(q,starts+t*(targets-starts));area=np.linalg.norm(np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]]),axis=1)/old;hit,names,contacts=obstacles.in_collision_single(trimesh.Trimesh(q,f,process=False),return_names=True,return_data=True)
  for contact in contacts:
   if 'SOFT_PALATE' not in contact.names:
    blockingVertices.update(map(int,f[contact.index('__external')]))
  states.append(q.copy());results.append({'fraction':float(t),'collisions':list(names),'minimumAreaRatio':float(area.min())})
 for qa,qb in zip(states[:-1],states[1:]):
  mid=(qa+qb)*.5;hit,names,contacts=obstacles.in_collision_single(trimesh.Trimesh(mid,f,process=False),return_names=True,return_data=True)
  for contact in contacts:
   if 'SOFT_PALATE'not in contact.names:blockingVertices.update(map(int,f[contact.index('__external')]))
 activeHistory.append({'iteration':activeIteration,'restAnchors':len(fixed),'blockingVertices':len(blockingVertices),'newRestAnchors':len(blockingVertices-fixed)})
 if not blockingVertices-fixed:break
 fixed.update(blockingVertices)
actual=trimesh.Trimesh(q,f[selected],process=False);gaps=[]
for z in np.linspace(-.0115,.0115,24):
 A=trimesh.intersections.mesh_plane(actual,[0,0,1],[0,0,z])[:,:,:2];B=trimesh.intersections.mesh_plane(velum,[0,0,1],[0,0,z])[:,:,:2];gaps.append(float(np.sqrt(pair(A,B)[0])*1000)if len(A)and len(B)else None)
out=ROOT/'data/motion/qaf-surface-active-v10';out.mkdir(exist_ok=True);np.savez_compressed(out/'states.npz',**{f's{i:02d}':v.astype(np.float32)for i,v in enumerate(states)});report={'restSha256':hashlib.sha256(raw).hexdigest(),'sourceContactBand_m':zs,'constraints':len(targets),'activeHistory':activeHistory,'heldClearSourceVertices':len(solver.fixed),'states':results,'crossSectionGaps_mm':gaps,'constraintResidualMax_mm':float(np.linalg.norm(C@q-targets,axis=1).max()*1000),'maxDisplacement_mm':float(np.linalg.norm(q-p,axis=1).max()*1000),'scope':'candidate only, no final GLB/path or qualified review'};(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k not in ['states','sourceContactBand_m']}));print('Failed states',sum(bool(v['collisions'])or v['minimumAreaRatio']<.1 for v in results))
