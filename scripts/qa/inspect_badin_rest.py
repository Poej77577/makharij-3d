#!/usr/bin/env python3
"""Reproduce unrepaired Badin source rest inspection and FCL pair report.
Run PYTHONPATH=/tmp/makharij-qa-deps python scripts/qa/inspect_badin_rest.py.
Meter units are source-contract input, not inferred from dimensions.
"""
from pathlib import Path
import itertools,json
import numpy as np
import trimesh
from trimesh.collision import CollisionManager
from inspect_mesh import inspect

root=Path(__file__).resolve().parents[2]
base=root/'assets/candidates/artisynth_models/src/artisynth/models/face/geometry'
out=root/'research/qa';out.mkdir(parents=True,exist_ok=True)
names=['badintongue.obj','upperteeth.obj','lowerteeth.obj','badinface_upperlip_filled.obj','badinface_lowerlip_filled.obj']
reports=[inspect(base/n) for n in names+['badinairway.obj']]
(out/'badin-source-inspection.json').write_text(json.dumps(reports,indent=2))
meshes={n:trimesh.load_mesh(base/n,process=False) for n in names}
rows=[]
for a,b in itertools.combinations(names,2):
 manager=CollisionManager();manager.add_object(a,meshes[a]);hit,data=manager.in_collision_single(meshes[b],return_data=True)
 row={'pair':[a,b],'surface_intersection':bool(hit),'returned_contacts':len(data),'minimum_surface_distance_mm':manager.min_distance_single(meshes[b])*1000}
 if data:
  points=np.array([contact.point for contact in data])*1000
  row['contact_bounds_mm']=[points.min(0).tolist(),points.max(0).tolist()]
 rows.append(row)
report={'unit_assumption':'meters per supplied source contract','no_repair':True,'results':rows,'scope':'FCL triangle surfaces; dental meshes open, no solid interior inference.'}
(out/'badin-rest-raw-collisions.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'pairs':len(rows),'surface_intersections':sum(r['surface_intersection'] for r in rows),'output':str(out)}))
