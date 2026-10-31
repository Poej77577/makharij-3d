#!/usr/bin/env python3
"""Find conservative smooth source-tongue fields using exact triangle FCL checks.

A single source-derived smooth nonrigid field is scaled to its FIRST obstacle
contact. We do not project each vertex independently. All parameter bounds and
contact-region labels are artistic until independently reviewed. Baseline hits
are reported as blockers, never described as passed. Separate final samples and
browser integration remain necessary.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import fcl
import trimesh
from trimesh.collision import CollisionManager

parser=argparse.ArgumentParser();parser.add_argument('--rest',required=True,type=Path);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--poses',nargs='+',default=['ra','qaf'],choices=['ra','qaf','ayn']);parser.add_argument('--regions',required=True,type=Path)
parser.add_argument('--tip-retraction-mm',type=float,default=3);parser.add_argument('--tip-lift-mm',type=float,default=12)
args=parser.parse_args();raw=args.rest.read_bytes();source=json.loads(raw);assert source['units']=='m'
parts={n:(np.array(d['positions'],float).reshape(-1,3),np.array(d['indices'],int).reshape(-1,3))for n,d in source['parts'].items()};p,faces=parts['TONGUE'];regions=json.loads(args.regions.read_text());assert regions['restSha256']==hashlib.sha256(raw).hexdigest()
oldnorm=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]]);oldarea=np.linalg.norm(oldnorm,axis=1);valid=oldarea>1e-14
def collision_object(vertices,triangles):
 model=fcl.BVHModel();model.beginModel(len(vertices),len(triangles));model.addSubModel(np.asarray(vertices,dtype=float),np.asarray(triangles,dtype=np.int32));model.endModel()
 return fcl.CollisionObject(model)
def collision_distance(first,second):
 hit=fcl.collide(first,second,fcl.CollisionRequest(num_max_contacts=1,enable_contact=False),fcl.CollisionResult())>0
 distance=float(fcl.distance(first,second,fcl.DistanceRequest(),fcl.DistanceResult()))
 return hit,distance
obstacles={};baseline={};baseline_blocked=[]
base_object=collision_object(p,faces)
for name in ['UPPER_TEETH','LOWER_TEETH','HARD_PALATE','SOFT_PALATE','GINGIVA_UPPER','GINGIVA_LOWER','PHARYNX']:
 if name not in parts:continue
 v,f=parts[name];obj=collision_object(v,f);hit,distance=collision_distance(base_object,obj);baseline[name]={'hit':bool(hit),'distance_m':distance}
 if hit:baseline_blocked.append(name)
 else:obstacles[name]=obj
print('Baseline blocked obstacles:',baseline_blocked,flush=True)
x,y,z=p.T
fields={
 'ra':np.column_stack((-args.tip_retraction_mm*.001*np.exp(-((x-.081)/.009)**2-((y+.001)/.020)**2-(z/.012)**4),args.tip_lift_mm*.001*np.exp(-((x-.081)/.009)**2-((y+.001)/.020)**2-(z/.012)**4)+.001*np.exp(-((x-.067)/.012)**2-((y-.003)/.020)**2-(z/.014)**4),np.zeros(len(p)))),
 'qaf':np.column_stack((-.0007*np.exp(-((x-.028)/.011)**2-((y-.004)/.020)**2-(z/.014)**4),.014*np.exp(-((x-.028)/.011)**2-((y-.004)/.020)**2-(z/.014)**4),np.zeros(len(p)))),
 'ayn':np.column_stack((-.006*np.exp(-((x-.019)/.018)**2-((y+.010)/.030)**2-(z/.020)**4),-.001*np.exp(-((x-.019)/.018)**2-((y+.010)/.030)**2-(z/.020)**4),np.zeros(len(p))))
}

def evaluate(delta,amplitude,details=False):
 q=(p+amplitude*delta).astype(np.float32).astype(float);dynamic=collision_object(q,faces)
 norm=np.cross(q[faces[:,1]]-q[faces[:,0]],q[faces[:,2]]-q[faces[:,0]]);area=np.linalg.norm(norm,axis=1);ratio=area[valid]/oldarea[valid]
 minratio=float(ratio.min());acceptable=minratio>.10;rows={}
 for name,obj in obstacles.items():
  hit,distance=collision_distance(dynamic,obj);clearance=min(.00012,baseline[name]['distance_m']*.75)
  safe=not hit and distance>=clearance
  acceptable=acceptable and safe
  rows[name]={'hit':hit,'distance_m':distance,'requiredClearance_m':clearance,'safe':safe}
 return bool(acceptable),q,{'minimumAreaRatio':minratio,'nearCollapsedFaces':int(np.sum(ratio<.01)),'restRelativeNegativeFaceDot':int(np.sum((np.sum(oldnorm*norm,axis=1)<0)&valid)),'obstacles':rows}

results={};targets={}
for pose in args.poses:
 delta=fields[pose];last_safe=0.;first_fail=None
 # Find first failure along the actual path, not a safe final value beyond an
 # intervening collision. Every retained interval is also checked at its mid.
 for a in np.linspace(.025,1,40):
  safe,q,row=evaluate(delta,float(a))
  if not safe:first_fail=float(a);break
  last_safe=float(a)
 if first_fail is not None:
  low,high=last_safe,first_fail
  for iteration in range(15):
   mid=(low+high)/2;safe,q,row=evaluate(delta,mid)
   if safe:low=mid
   else:high=mid
  amplitude=low
 else:amplitude=1.
 safe,q,row=evaluate(delta,amplitude)
 # Verify 65 actual scalar samples against exact triangles before handoff.
 samples=[]
 for a in np.linspace(0,amplitude,65):
  okay,qq,rr=evaluate(delta,float(a));samples.append({'amplitude':float(a),'safe':okay,'minimumAreaRatio':rr['minimumAreaRatio']})
 if not all(s['safe']for s in samples):safe=False
 fromname,toname={'ra':('tongue-tip','upper-alveolar'),'qaf':('posterior-dorsum','velum-oral'),'ayn':('tongue-root','pharyngeal-wall')}[pose]
 source_region=regions['regions'][fromname];target_region=regions['regions'][toname];vv,ff=parts[target_region['node']];target=trimesh.Trimesh(vv,ff[np.array(target_region['triangles'])],process=False);ids=np.array(source_region['vertices']);closest,distances,triangle=trimesh.proximity.closest_point(target,q[ids]);near=distances<.0003
 result={'amplitude':amplitude,'firstFailureBracket':first_fail,'pathSafeAgainstInitiallyClearObstacles':safe,'baselineBlockers':baseline_blocked,'targetRegion':{'from':fromname,'to':toname,'minimumDistance_mm':float(distances.min()*1000),'p10Distance_mm':float(np.quantile(distances,.1)*1000),'medianDistance_mm':float(np.median(distances)*1000),'within0_3mm':int(near.sum()),'totalRegionVertices':len(ids)},'quality':row,'pathSamples':samples,'maxDisplacement_mm':float(np.linalg.norm(q-p,axis=1).max()*1000),'meanDisplacement_mm':float(np.linalg.norm(q-p,axis=1).mean()*1000)}
 results[pose]=result;targets[pose]=q.astype(np.float32);print(pose,json.dumps({k:v for k,v in result.items()if k!='pathSamples'}),flush=True)
args.out.mkdir(parents=True,exist_ok=True);(args.out/'fit-script-used.py').write_text(Path(__file__).read_text());np.savez_compressed(args.out/'tongue-targets.npz',**targets)
report={'tipParameters_mm':{'retraction':args.tip_retraction_mm,'lift':args.tip_lift_mm},'version':'badin-smooth-field-first-contact-1','restSha256':hashlib.sha256(raw).hexdigest(),'rest':str(args.rest),'units':'m','method':'Localized analytic nonrigid field; single scalar amplitude searched to FIRST exact triangle obstacle contact and minimum area ratio; 65 uniform scalar samples independently in generator, final integration QA still pending','baseline':baseline,'baselineBlockers':baseline_blocked,'results':results,'scientificReview':'pending','isAnatomicalApproval':False}
(args.out/'tongue-fit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
