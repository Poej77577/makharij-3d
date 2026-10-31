"""Candidate smooth monotonic tissue maps; geometry authoring, not muscle physics.
Independent checks below include every stored state and interval midpoint.
"""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh
from scipy.ndimage import maximum_filter,gaussian_filter,map_coordinates
from scipy.interpolate import UnivariateSpline
from trimesh.collision import CollisionManager
ROOT=Path(__file__).resolve().parents[2];src=ROOT/'research/qa/prepared-rest-v10-meshes.json';d=json.loads(src.read_bytes());parts={n:(np.array(v['positions']).reshape(-1,3),np.array(v['indices']).reshape(-1,3))for n,v in d['parts'].items()};p,f=parts['LIP_CONTEXT'];m=d['parts']['LIP_CONTEXT']['masks'];uf=np.array(m['upperContactTriangles']);lf=np.array(m['lowerContactTriangles']);U=set(f[uf].ravel());L=set(f[lf].ravel());ui=np.array(sorted(U-L));li=np.array(sorted(L-U));raw=np.load(ROOT/'data/motion/mim-joint-v10b/states.npz');states=[raw[k].astype(float) for k in sorted(raw.files)];oldreport=json.loads((ROOT/'data/motion/mim-joint-v10b/report.json').read_bytes())
def rotate(v,t):
 a=np.deg2rad(4)*t;q=v.copy();x=v[:,0]-.003;y=v[:,1]-.037;q[:,0]=.003+np.cos(a)*x-np.sin(a)*y;q[:,1]=.037+np.sin(a)*x+np.cos(a)*y;return q
# Outermost radial dental boundary throughout the 4-degree jaw sweep.
dental=trimesh.util.concatenate([trimesh.Trimesh(*parts['UPPER_TEETH'],process=False)]+[trimesh.Trimesh(rotate(parts['LOWER_TEETH'][0],t),parts['LOWER_TEETH'][1],process=False)for t in np.linspace(0,1,7)])
ygrid=np.linspace(-.035,.025,121);theta=np.linspace(-1.35,1.35,181);yy,aa=np.meshgrid(ygrid,theta,indexing='ij');origins=np.c_[np.full(yy.size,.020),yy.ravel(),np.zeros(yy.size)];directions=np.c_[np.cos(aa.ravel()),np.zeros(yy.size),np.sin(aa.ravel())];loc,ids,_=dental.ray.intersects_location(origins,directions,multiple_hits=True);limit=np.zeros(len(origins));np.maximum.at(limit,ids,np.linalg.norm(loc-origins[ids],axis=1));limit=limit.reshape(yy.shape);limit=gaussian_filter(maximum_filter(limit,size=7),sigma=.7)+.0005

def outside(q,fraction=1):
 q=q.copy();r=np.hypot(q[:,0]-.020,q[:,2]);angle=np.arctan2(q[:,2],q[:,0]-.020);coords=[(q[:,1]-ygrid[0])/(ygrid[1]-ygrid[0]),(angle-theta[0])/(theta[1]-theta[0])];bound=map_coordinates(limit,coords,order=1,mode='constant',cval=0);delta=.00025*np.logaddexp(0,(bound-r)/.00025);support=np.clip((p[:,0]-.060)/.015,0,1);support=support*support*(3-2*support);s=1+fraction*support*delta/np.maximum(r,1e-6);q[:,0]=.020+(q[:,0]-.020)*s;q[:,2]*=s;return q
# Get actual final free-border Y envelopes, not just a nearest corner pair.
zgrid=np.linspace(-.019,.019,81);final=states[-1];centers=[]
for z in zgrid:
 up=trimesh.intersections.mesh_plane(trimesh.Trimesh(final,f[uf],process=False),[0,0,1],[0,0,z]).reshape(-1,3);lo=trimesh.intersections.mesh_plane(trimesh.Trimesh(final,f[lf],process=False),[0,0,1],[0,0,z]).reshape(-1,3);centers.append((up[:,1].min()+lo[:,1].max())/2)
seam=UnivariateSpline(zgrid,centers,s=len(zgrid)*.0001**2,ext=3)
def separate(q,fraction):
 q=q.copy();center=seam(q[:,2]);fade=np.clip((.021-abs(p[:,2]))/.003,0,1);fade=fade*fade*(3-2*fade);sigma=.0002;gap=.0001
 for indices,sign in [(ui,1),(li,-1)]:
  distance=sign*(q[indices,1]-center[indices])-gap;correction=sigma*np.logaddexp(0,-distance/sigma);q[indices,1]+=sign*correction*fade[indices]*fraction
 return q
outstates=[];rows=[];oldarea=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1);tprep=np.load(ROOT/'data/motion/mim-jaw-v10/targets.npz')['TONGUE'];baseT=parts['TONGUE'][0]
# The preparatory clearance precedes jaw movement. Stored source rows retain provenance.
for i,(q,row)in enumerate(zip(states,oldreport['states'])):
 stage=row['stage'];t=row['fraction'];prep=t if stage=='tissue-prepare' else (0 if stage=='rest' else 1);close=np.clip((t-.5)/.5,0,1)if stage=='joint-jaw-close'else 0;close=close*close*(3-2*close);outstates.append(outside(separate(q,close),prep));rows.append({'stage':stage,'fraction':t,'jawFraction':t if stage=='joint-jaw-close'else 0,'preparationFraction':prep})
checks=[]
for i in range(2*len(outstates)-1):
 k=i//2;mid=i%2;q=outstates[k]if not mid else (outstates[k]+outstates[k+1])*.5;pose=rows[k].copy()
 if mid:
  for key in ['jawFraction','preparationFraction']:pose[key]=(rows[k][key]+rows[k+1][key])*.5
 cm=CollisionManager()
 for name in ['UPPER_TEETH','LOWER_TEETH','TONGUE','GINGIVA_UPPER','GINGIVA_LOWER','HARD_PALATE','SOFT_PALATE']:
  v,faces=parts[name]
  if name in ['LOWER_TEETH','GINGIVA_LOWER']:v=rotate(v,pose['jawFraction'])
  if name=='TONGUE':v=baseT+pose['preparationFraction']*(tprep-baseT)
  cm.add_object(name,trimesh.Trimesh(v,faces,process=False))
 hit,names=cm.in_collision_single(trimesh.Trimesh(q,f,process=False),return_names=True);centralU=uf[abs(q[f[uf]].mean(1)[:,2])<.019];centralL=lf[abs(q[f[lf]].mean(1)[:,2])<.019];selfm=CollisionManager();selfm.add_object('upper',trimesh.Trimesh(q,f[centralU],process=False));selfhit=selfm.in_collision_single(trimesh.Trimesh(q,f[centralL],process=False));ratio=np.linalg.norm(np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]]),axis=1)/oldarea;checks.append({'stateIndex':i/2,'intersections':sorted(names),'centralUpperLowerIntersection':bool(selfhit),'minimumAreaRatio':float(ratio.min())})
print('Checks',len(checks),'obstacle failed',sum(bool(r['intersections'])for r in checks),'self failed',sum(r['centralUpperLowerIntersection']for r in checks),'minarea',min(r['minimumAreaRatio']for r in checks))
out=ROOT/'data/motion/mim-clearance-v10';out.mkdir(exist_ok=True);np.savez_compressed(out/'states.npz',**{f's{i:02d}':v.astype(np.float32)for i,v in enumerate(outstates)});report={'restSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sourceCandidate':'mim-joint-v10b','states':rows,'checks':checks,'scope':'candidate only; closure and final GLB checks pending'};(out/'report.json').write_text(json.dumps(report,indent=2));print('Saved',out)
