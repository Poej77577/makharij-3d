#!/usr/bin/env python3
"""Report contact for calibrated source-landmark vertex/triangle regions.
Manifest: {unit:'m',regions:{tip:{node:'TONGUE',vertices:[...]},alveolar:
{node:'HARD_PALATE',triangles:[...]}},checks:[{pose:'ra',phase:.5,
file:'sample.glb',from:'tip',to:'alveolar'}]}. Indices must match the final
mesh after compression and be independently calibrated; global mesh nearest
distances cannot substitute for correct anatomical regions. Reports proximity,
not correctness/approval of the supplied landmark definition.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import trimesh
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('manifest',type=Path);parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args();spec=json.loads(args.manifest.read_text());unit=spec.get('unit')
if unit not in ('m','cm','mm'):raise SystemExit('Verified unit required')
scale={'m':1000,'cm':10,'mm':1}[unit];rows=[]
for check in spec['checks']:
 path=(args.manifest.parent/check['file']).resolve();scene=trimesh.load_scene(path,process=False)
 def node(name):
  transform,geometry=scene.graph[name];mesh=scene.geometry[geometry].copy();mesh.apply_transform(transform);mesh.apply_scale(scale);return mesh
 first=spec['regions'][check['from']];second=spec['regions'][check['to']]
 a=node(first['node']);b=node(second['node']);ids=np.array(first['vertices'],dtype=int);faces=np.array(second['triangles'],dtype=int)
 if not len(ids) or not len(faces):raise SystemExit('Empty calibrated region invalid')
 if ids.min()<0 or ids.max()>=len(a.vertices) or faces.min()<0 or faces.max()>=len(b.faces):raise SystemExit('Region indices do not match delivered geometry')
 target=trimesh.Trimesh(vertices=b.vertices,faces=b.faces[faces],process=False);points=a.vertices[ids]
 closest,distances,_=trimesh.proximity.closest_point(target,points);order=np.argsort(distances)
 near={}
 for tolerance in [.1,.3,.5,1.,2.]:
  mask=distances<=tolerance;entry={'count':int(mask.sum()),'total_region_samples':len(points)}
  if mask.any():entry['region_point_bounds_mm']=[points[mask].min(0).tolist(),points[mask].max(0).tolist()]
  near[str(tolerance)]=entry
 rows.append({**check,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'minimum_region_distance_mm':float(distances.min()),'distance_quantiles_mm':{str(q):float(np.quantile(distances,q)) for q in [0,.1,.5,.9,1]},'within_tolerance_mm':near,'nearest_samples':[{'from_vertex_index':int(ids[i]),'from_point_mm':points[i].tolist(),'target_surface_point_mm':closest[i].tolist(),'distance_mm':float(distances[i])} for i in order[:30]]})
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps({'scope':'Proximity only for supplied calibrated anatomical regions on actual exported geometry; no anatomical review or full contact width guarantee.','results':rows},indent=2));print(json.dumps({'checks':len(rows),'report':str(args.out)}))
