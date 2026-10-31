#!/usr/bin/env python3
"""Record explicit anatomical-region indices from the prepared source geometry.
These fixed source-coordinate criteria are artistic annotation awaiting a human
anatomist/phonetic reviewer. They do not select vertices by lowest pose distance.
Regenerate after topology changes; compare saved source hash before using.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

parser=argparse.ArgumentParser();parser.add_argument('--rest',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args();raw=args.rest.read_bytes();source=json.loads(raw);assert source['units']=='m'
parts={n:(np.array(d['positions']).reshape(-1,3),np.array(d['indices']).reshape(-1,3))for n,d in source['parts'].items()}
regions={}
def points(name,node,test,criterion):
 p,f=parts[node];ids=np.flatnonzero(test(p));assert len(ids),f'Empty anatomical source region {name}'
 regions[name]={'node':node,'vertices':ids.tolist(),'calibrationCriterion':criterion,'restBounds_m':[p[ids].min(0).tolist(),p[ids].max(0).tolist()]}
def faces(name,node,test,criterion):
 p,f=parts[node];centers=p[f].mean(1);ids=np.flatnonzero(test(centers));assert len(ids),f'Empty anatomical target region {name}'
 regions[name]={'node':node,'triangles':ids.tolist(),'calibrationCriterion':criterion,'restTriangleCentroidBounds_m':[centers[ids].min(0).tolist(),centers[ids].max(0).tolist()]}
points('tongue-tip','TONGUE',lambda p:(p[:,0]>.074)&(p[:,1]>-.006)&(abs(p[:,2])<.010),'Anterior superior tongue tip in prepared source: x>.074,y>-.006,|z|<.010m')
faces('upper-alveolar','HARD_PALATE',lambda p:(p[:,0]>.073)&(p[:,0]<.083)&(p[:,1]>.005)&(p[:,1]<.017)&(abs(p[:,2])<.010),'Hard-palate anterior alveolar region source box .073<x<.083,.005<y<.017,|z|<.010m')
points('posterior-dorsum','TONGUE',lambda p:(p[:,0]>.020)&(p[:,0]<.036)&(p[:,1]>-.001)&(abs(p[:,2])<.012),'Posterior superior tongue source region .020<x<.036,y>-.001,|z|<.012m')
faces('velum-oral','SOFT_PALATE',lambda p:(p[:,0]>.018)&(p[:,0]<.0335)&(p[:,1]>.010)&(p[:,1]<.025)&(abs(p[:,2])<.012),'Anterior oral soft-palate surface region, source box .018<x<.0335,.010<y<.025,|z|<.012m')
points('lower-lip-inner','LOWER_LIP',lambda p:(p[:,0]>.083)&(p[:,0]<.096)&(p[:,1]>-.016)&(abs(p[:,2])<.012),'Central superior/inner lower-lip tissue near oral free border; .083<x<.096,y>-.016,|z|<.012m')
faces('upper-incisor-free-edge','UPPER_TEETH',lambda p:(p[:,0]>.083)&(p[:,1]<.004)&(abs(p[:,2])<.009),'Central upper anterior incisor free-edge region x>.083,y<.004,|z|<.009m; excludes lateral molars')
points('tongue-root','TONGUE',lambda p:(p[:,0]>.010)&(p[:,0]<.025)&(p[:,1]>-.020)&(p[:,1]<.008)&(abs(p[:,2])<.015),'Posterior tongue-root source box, not an acquired laryngeal constrictor')
faces('pharyngeal-wall','PHARYNX',lambda p:(p[:,0]<.023)&(p[:,1]>-.025)&(p[:,1]<.020)&(abs(p[:,2])<.018),'Posterior pharyngeal wall source region x<.023,-.025<y<.020,|z|<.018m')
# Border path selected by source anatomy (vertical extrema in fixed lateral bins),
# never by proximity to the other moving lip. These preserve lateral width data.
for node,label,extreme in [('LOWER_LIP','lower-lip-seam',np.argmax),('UPPER_LIP','upper-lip-seam',np.argmin)]:
 p,f=parts[node];selected=[];bins=[]
 for z in np.linspace(-.015,.015,31):
  candidates=np.flatnonzero((abs(p[:,2]-z)<.0012)&(p[:,0]>.085))
  if not len(candidates):continue
  i=int(candidates[extreme(p[candidates,1])]);selected.append(i);bins.append({'z_m':float(z),'vertex':i})
 assert len(set(selected))>=12,f'Insufficient central free border points {node}'
 regions[label]={'node':node,'vertices':sorted(set(selected)),'lateralBins':bins,'calibrationCriterion':'Rest-source vertical border extrema in fixed lateral bins +/-15mm, anterior x>.085m; not pose-distance optimized; human verification pending'}
faces('upper-lip-seam-surface','UPPER_LIP',lambda p:(p[:,0]>.084)&(p[:,1]<.007)&(abs(p[:,2])<.019),'Anterior inferior upper-lip seam surface source box x>.084,y<.007,|z|<.019m')
result={'unit':'m','restSource':str(args.rest),'restSha256':hashlib.sha256(raw).hexdigest(),'calibrationStatus':'artistic source-region annotation; independent anatomical/tajwid review pending','notAContactPass':True,'regions':regions,'checks':[]}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'output':str(args.output),'regions':{n:len(d.get('vertices',d.get('triangles',[])))for n,d in regions.items()}},ensure_ascii=False))
