"""Calibrate a smooth posterior tongue band to acquired velum surface points.
Targets are source mesh geometry; this is artistic geometric calibration, not
physiological measurement. Global triangle constraints are applied separately.
"""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[2];src=ROOT/'research/qa/prepared-rest-v6-meshes.json';raw=src.read_bytes();d=json.loads(raw);regions=json.load(open(ROOT/'data/motion/contact-regions-v6.json'))['regions'];p=np.array(d['parts']['TONGUE']['positions']).reshape(-1,3);ids=np.array(regions['posterior-dorsum']['vertices']);reg=regions['velum-oral'];v=np.array(d['parts'][reg['node']]['positions']).reshape(-1,3);f=np.array(d['parts'][reg['node']]['indices']).reshape(-1,3);roof=trimesh.Trimesh(v,f[reg['triangles']],process=False);near,dist,_=trimesh.proximity.closest_point(roof,p[ids]);chosen=set()
for z in np.linspace(-.012,.012,13):
 candidates=np.flatnonzero(abs(p[ids,2]-z)<.0013)
 if len(candidates):chosen.add(int(candidates[dist[candidates].argmin()]))
chosen=sorted(chosen,key=lambda i:p[ids[i],2]);keep=[]
for i in chosen:
 if keep and p[ids[i],2]-p[ids[keep[-1]],2]<.0003:
  if dist[i]<dist[keep[-1]]:keep[-1]=i
 else:keep.append(i)
selected=ids[keep];c=p[selected];delta=near[keep]-c;z=c[:,2];values=PchipInterpolator(z,np.column_stack([c[:,:2],delta]),axis=0)(np.clip(p[:,2],z[0],z[-1]));x0,y0=values[:,0],values[:,1];w=np.exp(-((p[:,0]-x0)/.0055)**2-((p[:,1]-y0)/.0065)**2);edge=np.clip((.021-abs(p[:,2]))/(.021-max(abs(z))),0,1);edge=edge*edge*(3-2*edge);field=values[:,2:]*w[:,None]*edge[:,None]
out=ROOT/'data/motion/qaf-contact-band-v6';out.mkdir(exist_ok=True);np.savez_compressed(out/'field.npz',delta=field.astype(np.float64));report={'restSha256':hashlib.sha256(raw).hexdigest(),'controlVertexIds':selected.tolist(),'sourcePoints_m':c.tolist(),'targetVelumPoints_m':near[keep].tolist(),'fieldWidths_m':[.0055,.0065],'zTaperEnds_m':[-.021,.021],'targetRegion':'unchanged acquired velum-oral indices','status':'candidate field, requires full collision/path and transverse-gap checks'};(out/'calibration.json').write_text(json.dumps(report,indent=2));print('Actual posterior source band anchors',len(selected),'lateral range mm',z[[0,-1]]*1000)
