"""Continuous lip contact candidate with actual surface-point constraints.
ARAP is a geometric shape authoring tool; it is not a muscle/force simulation.
"""
from pathlib import Path
import json,hashlib,argparse
import numpy as np,trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from scipy.sparse.csgraph import connected_components
from trimesh.collision import CollisionManager
ROOT=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser();parser.add_argument('--rest',default='research/qa/prepared-rest-v10-meshes.json');parser.add_argument('--out',default='data/motion/mim-joint-v10');opts=parser.parse_args();src=ROOT/opts.rest;raw=src.read_bytes();d=json.loads(raw);m=d['parts']['LIP_CONTEXT']['masks'];p=np.array(d['parts']['LIP_CONTEXT']['positions']).reshape(-1,3);faces=np.array(d['parts']['LIP_CONTEXT']['indices']).reshape(-1,3);uf=np.array(m['upperContactTriangles']);lf=np.array(m['lowerContactTriangles']);jawTargets=np.load(ROOT/'data/motion/mim-jaw-v10/targets.npz');jawClosed=jawTargets['LIP_CONTEXT'];jawWeights=np.array(m['jawWeights']);upper=trimesh.Trimesh(jawClosed,faces[uf],process=False);lower=trimesh.Trimesh(jawClosed,faces[lf],process=False)
def closest_segments(A,B):
 best=(float('inf'),None,None,None,None)
 for pts,seg,inverse in [(A.reshape(-1,2),B,False),(B.reshape(-1,2),A,True)]:
  a=seg[:,0];v=seg[:,1]-a;den=(v*v).sum(1)
  for k,point in enumerate(pts):
   t=np.clip(((point-a)*v).sum(1)/np.maximum(den,1e-30),0,1);q=a+v*t[:,None];dist=((q-point)**2).sum(1);i=int(dist.argmin())
   if dist[i]<best[0]:best=(float(dist[i]),q[i]if inverse else point,point if inverse else q[i],i if inverse else k//2,k//2 if inverse else i)
 return best
# Exact cut segments of the acquired contact faces give real barycentric handles.
cr=[];cc=[];cv=[];original=[];closed=[];sections=[]
for z in np.linspace(-.020,.020,49):
 A,at=trimesh.intersections.mesh_plane(upper,[0,0,1],[0,0,z],return_faces=True);B,bt=trimesh.intersections.mesh_plane(lower,[0,0,1],[0,0,z],return_faces=True)
 if not len(A)or not len(B):continue
 distance,up,lp,ui,li=closest_segments(A[:,:,:2],B[:,:,:2]);up=np.r_[up,z];lp=np.r_[lp,z];seam=(up+lp)/2;seam[0]+=.001
 for point,tri,sign in [(up,faces[uf[at[ui]]],1),(lp,faces[lf[bt[li]]],-1)]:
  w=trimesh.triangles.points_to_barycentric(jawClosed[tri][None],point[None])[0];row=len(original)
  for index,value in zip(tri,w):cr.append(row);cc.append(int(index));cv.append(float(value))
  target=seam.copy();target[1]+=sign*.0001;original.append(point);closed.append(target)
 sections.append(float(z))
C=coo_matrix((cv,(cr,cc)),shape=(len(original),len(p))).tocsc();original=C@p;closed=np.array(closed)
# A common smooth free-border seam avoids nearest-depth branch jumps in mucosa.
from scipy.interpolate import UnivariateSpline
centers=(closed[0::2]+closed[1::2])/2;zgrid=np.array(sections)
for axis in [0,1]:
 curve=UnivariateSpline(zgrid,centers[:,axis],s=len(zgrid)*(.00015**2),k=3);values=curve(zgrid);closed[0::2,axis]=values;closed[1::2,axis]=values
closed[0::2,1]+=.0001;closed[1::2,1]-=.0001
prepared=original+np.array([.0035,0,0])
edges,counts=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0,return_counts=True);a,b=edges.T;rest_edges=p[a]-p[b];degree=np.bincount(edges.ravel(),minlength=len(p));L=coo_matrix((np.r_[degree,-np.ones(2*len(edges))],(np.r_[np.arange(len(p)),a,b],np.r_[np.arange(len(p)),b,a])),shape=(len(p),len(p))).tocsc();near=np.array(m['upperWeights'])+np.array(m['lowerWeights']);boundary=np.unique(edges[counts==1]);fixedset=set(np.flatnonzero(near<.04))|set(boundary[near[boundary]<.8]);components,labels=connected_components(L,directed=False)
for comp in range(components):
 ids=np.flatnonzero(labels==comp)
 if not fixedset.intersection(ids):fixedset.add(int(ids[0]))
fixed=np.array(sorted(fixedset));free=np.array(sorted(set(range(len(p)))-fixedset));Cf=C[:,free];Cc=C[:,fixed];strength=1000.;system=(L[free][:,free]+strength*(Cf.T@Cf)).tocsc();solver=splu(system);fixedrhs=L[free][:,fixed]@p[fixed]
def solve(q,target,fixedvalues):
 fixedrhs=L[free][:,fixed]@fixedvalues
 contactrhs=strength*(Cf.T@(target-Cc@fixedvalues))
 for _ in range(12):
  current=q[a]-q[b];outer=current[:,:,None]*rest_edges[:,None,:];S=np.zeros((len(p),3,3));np.add.at(S,a,outer);np.add.at(S,b,outer);U,_,Vt=np.linalg.svd(S);sgn=np.linalg.det(U@Vt);U[:,:,2]*=np.where(sgn<0,-1,1)[:,None];R=U@Vt;term=np.einsum('nij,nj->ni',(R[a]+R[b])*.5,rest_edges);rhs=np.zeros_like(p);np.add.at(rhs,a,term);np.add.at(rhs,b,-term);q[fixed]=fixedvalues;q[free]=solver.solve(rhs[free]-fixedrhs+contactrhs)
 return q
obstacles=CollisionManager()
for name in ['UPPER_TEETH','LOWER_TEETH','TONGUE']:
 part=d['parts'][name];vv=jawTargets['TONGUE'] if name=='TONGUE' else np.array(part['positions']).reshape(-1,3);obstacles.add_object(name,trimesh.Trimesh(vv,np.array(part['indices']).reshape(-1,3),process=False))
old=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]]);oldarea=np.linalg.norm(old,axis=1);q=p.copy();states=[p.copy()];rows=[{'stage':'rest','fraction':0.,'obstacleIntersections':[],'minimumAreaRatio':1.}]
def jawpose(points,t,weighted=False):
 angle=np.deg2rad(6)*t*(jawWeights if weighted else 1);out=points.copy();xx=points[:,0]-.003;yy=points[:,1]-.037;out[:,0]=.003+np.cos(angle)*xx-np.sin(angle)*yy;out[:,1]=.037+np.sin(angle)*xx+np.cos(angle)*yy;return out
for t in np.linspace(0,1,25):
 qjaw=jawpose(p,t,True);u=np.clip((t-.5)/.5,0,1);closing=u*u*(3-2*u);target=C@qjaw+closing*(closed-C@jawClosed);q=solve(q,target,qjaw[fixed]);angle=np.deg2rad(6)*t;cs,sn=np.cos(angle),np.sin(angle);X=np.eye(4);X[:2,:2]=[[cs,-sn],[sn,cs]];X[:2,3]=np.array([.003,.037])-X[:2,:2]@np.array([.003,.037]);obstacles.set_transform('LOWER_TEETH',X)
 area=np.linalg.norm(np.cross(q[faces[:,1]]-q[faces[:,0]],q[faces[:,2]]-q[faces[:,0]]),axis=1)/oldarea;hit,names=obstacles.in_collision_single(trimesh.Trimesh(q,faces,process=False),return_names=True);rows.append({'stage':'joint-jaw-close','fraction':float(t),'obstacleIntersections':list(names),'minimumAreaRatio':float(area.min())});states.append(q.copy())
Umesh=trimesh.Trimesh(q,faces[uf],process=False);Lmesh=trimesh.Trimesh(q,faces[lf],process=False);gaps=[]
for z in np.linspace(-.019,.019,32):
 A=trimesh.intersections.mesh_plane(Umesh,[0,0,1],[0,0,z])[:,:,:2];B=trimesh.intersections.mesh_plane(Lmesh,[0,0,1],[0,0,z])[:,:,:2];gaps.append(float(np.sqrt(closest_segments(A,B)[0])*1000)if len(A)and len(B)else None)
uf2=uf[abs(q[faces[uf]].mean(1)[:,2])<.0195];lf2=lf[abs(q[faces[lf]].mean(1)[:,2])<.0195];selfman=CollisionManager();selfman.add_object('upper',trimesh.Trimesh(q,faces[uf2],process=False));selfhit=selfman.in_collision_single(trimesh.Trimesh(q,faces[lf2],process=False))
out=ROOT/opts.out;out.mkdir(exist_ok=True);np.savez_compressed(out/'states.npz',**{f's{i:02d}':v.astype(np.float32)for i,v in enumerate(states)});report={'restSha256':hashlib.sha256(raw).hexdigest(),'source':'actual acquired FEM lip contact faces, jaw-coordinated closure with exact triangle-plane handles','jawDegrees':6,'tonguePreparation':'mim-jaw-v10/targets.npz swept-dental clearance','surfacePointConstraints':len(original),'anchors':len(fixed),'sections_m':sections,'states':rows,'crossSectionGaps_mm':gaps,'centralUpperLowerIntersection':bool(selfhit),'maxDisplacement_mm':float(np.linalg.norm(q-p,axis=1).max()*1000),'constraintResidualMax_mm':float(np.linalg.norm(C@q-closed,axis=1).max()*1000),'scope':'candidate; requires final exported geometry/path/closure checks'};(out/'fit-script-used.py').write_text(Path(__file__).read_text());(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k not in ['states','sections_m']}));print('Failed states',sum(bool(v['obstacleIntersections'])or v['minimumAreaRatio']<.1 for v in rows))
