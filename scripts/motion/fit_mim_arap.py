"""Geometric continuous-lip closure candidate using source contact masks + ARAP.
This fits a teaching surface, not muscles, forces, clinical timing or audio.
"""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from scipy.sparse.csgraph import connected_components
from trimesh.collision import CollisionManager
ROOT=Path(__file__).resolve().parents[2];source=ROOT/'research/qa/prepared-rest-v6-meshes.json';d=json.loads(source.read_text());m=d['parts']['LIP_CONTEXT']['masks'];p=np.array(d['parts']['LIP_CONTEXT']['positions']).reshape(-1,3);f=np.array(d['parts']['LIP_CONTEXT']['indices']).reshape(-1,3)
u=np.array(m['upperContactVertices']);l=np.array(m['lowerContactVertices']);shared=set(u)&set(l);u=np.array([i for i in u if i not in shared]);l=np.array([i for i in l if i not in shared]);pairs=[];targetlists={}
for z in np.linspace(-.020,.020,23):
 ui=u[abs(p[u,2]-z)<.0013];li=l[abs(p[l,2]-z)<.0013]
 if not len(ui)or not len(li):continue
 dist=((p[ui,None]-p[li])**2).sum(2);i,j=np.unravel_index(dist.argmin(),dist.shape);a,b=int(ui[i]),int(li[j]);seam=(p[a]+p[b])/2;seam[0]+=.0035
 for idx,sign in [(a,1),(b,-1)]:
  value=seam.copy();value[1]+=sign*.00010;targetlists.setdefault(idx,[]).append(value)
 pairs.append((a,b))
handles=np.array(sorted(targetlists));closed=np.array([np.mean(targetlists[i],axis=0)for i in handles]);prepared=p[handles]+np.array([.0035,0,0])
anchors=np.flatnonzero(np.array(m['upperWeights'])+np.array(m['lowerWeights'])<.04);fixed=np.array(sorted(set(anchors)|set(handles)));free=np.array(sorted(set(range(len(p)))-set(fixed)));where={j:i for i,j in enumerate(fixed)}
edges=np.unique(np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0);a,b=edges.T;v=p[a]-p[b];degree=np.bincount(edges.ravel(),minlength=len(p));L=coo_matrix((np.r_[degree,-np.ones(2*len(edges))],(np.r_[np.arange(len(p)),a,b],np.r_[np.arange(len(p)),b,a])),shape=(len(p),len(p))).tocsc();edgecounts=np.unique(np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0,return_counts=True)
boundary=np.unique(edgecounts[0][edgecounts[1]==1]);attach=boundary[(np.array(m['upperWeights'])+np.array(m['lowerWeights']))[boundary]<.8];fixed=np.array(sorted(set(fixed)|set(attach)))
components,labels=connected_components(L,directed=False)
fixedset=set(fixed)
for comp in range(components):
 ids=np.flatnonzero(labels==comp)
 if not any(int(i)in fixedset for i in ids):fixedset.add(int(ids[0]))
fixed=np.array(sorted(fixedset));free=np.array(sorted(set(range(len(p)))-fixedset));where={j:i for i,j in enumerate(fixed)};solver=splu(L[free][:,free]);cross=L[free][:,fixed]
def solve(q,values):
 for _ in range(10):
  e=q[a]-q[b];outer=e[:,:,None]*v[:,None,:];S=np.zeros((len(p),3,3));np.add.at(S,a,outer);np.add.at(S,b,outer);U,_,Vt=np.linalg.svd(S);sign=np.linalg.det(U@Vt);U[:,:,2]*=np.where(sign<0,-1,1)[:,None];R=U@Vt
  rhs=np.zeros_like(p);term=np.einsum('nij,nj->ni',(R[a]+R[b])*.5,v);np.add.at(rhs,a,term);np.add.at(rhs,b,-term);q[fixed]=values;q[free]=solver.solve(rhs[free]-cross@values)
 return q
obstacles=CollisionManager()
for name in ['UPPER_TEETH','LOWER_TEETH','TONGUE']:
 part=d['parts'][name];obstacles.add_object(name,trimesh.Trimesh(np.array(part['positions']).reshape(-1,3),np.array(part['indices']).reshape(-1,3),process=False))
old=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]);oldarea=np.linalg.norm(old,axis=1);q=p.copy();states=[];results=[]
for stage,count,start,end in [('prepare',8,p[handles],prepared),('close',16,prepared,closed)]:
 for t in np.linspace(0,1,count):
  values=p[fixed].copy()
  for idx,value in zip(handles,start+t*(end-start)):values[where[idx]]=value
  q=solve(q,values);area=np.linalg.norm(np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]]),axis=1)/oldarea;hit,names=obstacles.in_collision_single(trimesh.Trimesh(q,f,process=False),return_names=True);states.append(q.copy());results.append({'stage':stage,'fraction':float(t),'obstacleIntersections':list(names),'minimumAreaRatio':float(area.min())})
roof=trimesh.Trimesh(q,f[m['upperContactTriangles']],process=False);ids=np.array(m['lowerContactVertices']);_,dist,_=trimesh.proximity.closest_point(roof,q[ids]);bins=[]
for z0,z1 in zip(np.linspace(-.020,.020,17)[:-1],np.linspace(-.020,.020,17)[1:]):
 sel=(q[ids,2]>=z0)&(q[ids,2]<=z1);bins.append(float(dist[sel].min()*1000)if sel.any()else None)
uf=np.array(m['upperContactTriangles']);lf=np.array(m['lowerContactTriangles']);uf=uf[abs(q[f[uf]].mean(1)[:,2])<.019];lf=lf[abs(q[f[lf]].mean(1)[:,2])<.019];man=CollisionManager();man.add_object('upper',trimesh.Trimesh(q,f[uf],process=False));selfhit=man.in_collision_single(trimesh.Trimesh(q,f[lf],process=False))
out=ROOT/'data/motion/mim-arap-v6c';out.mkdir(exist_ok=True);np.savez_compressed(out/'states.npz',**{f's{i:02d}':v.astype(np.float32)for i,v in enumerate(states)})
def linegap(meshA,meshB,z):
 A=trimesh.intersections.mesh_plane(meshA,[0,0,1],[0,0,z])[:,:,:2];B=trimesh.intersections.mesh_plane(meshB,[0,0,1],[0,0,z])[:,:,:2]
 if not len(A)or not len(B):return None
 best=float('inf')
 for pts,seg in [(A.reshape(-1,2),B),(B.reshape(-1,2),A)]:
  base=seg[:,0];v=seg[:,1]-base;den=(v*v).sum(1)
  for pp in pts:
   t=np.clip(((pp-base)*v).sum(1)/np.maximum(den,1e-30),0,1);best=min(best,float(np.linalg.norm(base+v*t[:,None]-pp,axis=1).min()))
 return best*1000
uppermesh=trimesh.Trimesh(q,f[m['upperContactTriangles']],process=False);lowermesh=trimesh.Trimesh(q,f[m['lowerContactTriangles']],process=False);crossgaps=[linegap(uppermesh,lowermesh,z)for z in np.linspace(-.01875,.01875,16)]
report={'restSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'handles':len(handles),'anchors':len(anchors),'states':results,'actualSurfaceCrossSectionGaps_mm':crossgaps,'centralGapBins_mm':bins,'centralUpperLowerIntersection':bool(selfhit),'maxDisplacement_mm':float(np.linalg.norm(q-p,axis=1).max()*1000),'scope':'candidate only, not integrated or independently verified'};(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='states'}));print('Failedstates',sum(bool(x['obstacleIntersections'])or x['minimumAreaRatio']<.1 for x in results))
