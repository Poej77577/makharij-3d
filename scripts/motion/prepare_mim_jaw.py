"""Author a coupled jaw/skin/tongue preparation from acquired source surfaces.
Tongue clearance uses a smooth positive radial map of the sampled dental swept
space. It is geometry, not muscle physics or a measured clinical range.
"""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh
from scipy.ndimage import minimum_filter,gaussian_filter,map_coordinates
from trimesh.collision import CollisionManager
ROOT=Path(__file__).resolve().parents[2];src=ROOT/'assets/anatomy/rest-meshes.json';raw=src.read_bytes();d=json.loads(raw);parts={n:(np.array(v['positions']).reshape(-1,3),np.array(v['indices']).reshape(-1,3))for n,v in d['parts'].items()}
def rotate(p,angle):
 q=p.copy();x=p[:,0]-.003;y=p[:,1]-.037;q[:,0]=.003+np.cos(angle)*x-np.sin(angle)*y;q[:,1]=.037+np.sin(angle)*x+np.cos(angle)*y;return q
meshlist=[trimesh.Trimesh(*parts['UPPER_TEETH'],process=False)]
for t in np.linspace(0,1,5):meshlist.append(trimesh.Trimesh(rotate(parts['LOWER_TEETH'][0],np.deg2rad(6)*t),parts['LOWER_TEETH'][1],process=False))
dental=trimesh.util.concatenate(meshlist);tongue=trimesh.Trimesh(*parts['TONGUE'],process=False)
ygrid=np.linspace(-.012,.015,55);angles=np.linspace(-1.6,1.6,183);yy,aa=np.meshgrid(ygrid,angles,indexing='ij');origins=np.column_stack([np.full(yy.size,.020),yy.ravel(),np.zeros(yy.size)]);directions=np.column_stack([np.cos(aa.ravel()),np.zeros(yy.size),np.sin(aa.ravel())])
def radii(mesh,which):
 locations,ids,_=mesh.ray.intersects_location(origins,directions,multiple_hits=True);r=np.linalg.norm(locations-origins[ids],axis=1);out=np.full(len(origins),np.inf if which=='min'else 0.)
 if which=='min':np.minimum.at(out,ids,r)
 else:np.maximum.at(out,ids,r)
 return out.reshape(yy.shape)
limit=radii(dental,'min');extent=radii(tongue,'max');scale=np.ones_like(limit);active=np.isfinite(limit)&(extent>1e-5);scale[active]=np.minimum(1,(limit[active]-.0005)/extent[active]);scale=np.clip(scale,.65,1);scale=gaussian_filter(minimum_filter(scale,size=7,mode='constant',cval=1),sigma=.75,truncate=3,mode='constant',cval=1)
p=parts['TONGUE'][0];radius=np.hypot(p[:,0]-.020,p[:,2]);theta=np.arctan2(p[:,2],p[:,0]-.020);coords=[(p[:,1]-ygrid[0])/(ygrid[1]-ygrid[0]),(theta-angles[0])/(angles[1]-angles[0])];s=map_coordinates(scale,coords,order=1,mode='constant',cval=1);q=p.copy();q[:,0]=.020+(p[:,0]-.020)*s;q[:,2]*=s
states={n:v.copy()for n,(v,f)in parts.items()};states['TONGUE']=q
for n in ['LOWER_TEETH','GINGIVA_LOWER']:states[n]=rotate(parts[n][0],np.deg2rad(6))
states['LIP_CONTEXT']=rotate(parts['LIP_CONTEXT'][0],np.deg2rad(6)*np.array(d['parts']['LIP_CONTEXT']['masks']['jawWeights']))
rows=[]
for a,b in [('TONGUE','LOWER_TEETH'),('TONGUE','UPPER_TEETH'),('TONGUE','HARD_PALATE'),('TONGUE','SOFT_PALATE'),('TONGUE','GINGIVA_LOWER'),('TONGUE','LIP_CONTEXT'),('LIP_CONTEXT','LOWER_TEETH'),('LIP_CONTEXT','UPPER_TEETH')]:
 m=CollisionManager();m.add_object(a,trimesh.Trimesh(states[a],parts[a][1],process=False));hit=m.in_collision_single(trimesh.Trimesh(states[b],parts[b][1],process=False));rows.append({'pair':[a,b],'intersection':bool(hit)})
old=parts['TONGUE'][0];f=parts['TONGUE'][1];a=np.cross(old[f[:,1]]-old[f[:,0]],old[f[:,2]]-old[f[:,0]]);b=np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]]);report={'restSha256':hashlib.sha256(raw).hexdigest(),'jawDegrees':6,'tongueMaxDisplacement_mm':float(np.linalg.norm(q-old,axis=1).max()*1000),'tongueMinAreaRatio':float((np.linalg.norm(b,axis=1)/np.linalg.norm(a,axis=1)).min()),'tongueNegativeFaceDot':int(np.sum(np.sum(a*b,axis=1)<0)),'pairs':rows,'status':'candidate, not integrated or verified through motion'}
out=ROOT/'data/motion/mim-jaw-v10';out.mkdir(exist_ok=True);np.savez_compressed(out/'targets.npz',**states);(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
