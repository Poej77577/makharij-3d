#!/usr/bin/env python3
"""Triangle intersection and minimum-distance report for exported motion samples.
Manifest schema: {"unit":"m|cm|mm", "samples":[{"pose":"ra", "phase":0.1,
"file":"relative/path.glb"}], "pairs":[["Tongue","UpperTeeth"]]}.
Names match scene graph node names; transforms are applied. This detects surface
intersections using FCL, not a physiological definition of valid contact. Internal
volumetric containment is not established by zero surface intersections. Export
samples from the actual final renderer/deformer, including intermediate phases.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import trimesh
from trimesh.collision import CollisionManager
import struct

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('manifest',type=Path)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--merge-primitives',action='store_true',help='Aggregate material primitives of one logical glTF mesh without changing triangle positions')
args=parser.parse_args()
spec=json.loads(args.manifest.read_text())
unit=spec.get('unit')
if unit not in ('m','cm','mm'):
 raise SystemExit('Explicit verified source unit m, cm, or mm required')
scale={'m':1000.,'cm':10.,'mm':1.}[unit]
if not spec.get('samples') or not spec.get('pairs'):
 raise SystemExit('Nonempty samples and exact node pairs required')
rows=[];failures=[]
for sample in spec['samples']:
 path=(args.manifest.parent/sample['file']).resolve()
 if path.suffix.lower() in ('.glb','.gltf'):
  if path.suffix.lower()=='.glb':
   blob=path.read_bytes()
   if blob[:4]!=b'glTF':raise SystemExit(f'{path}: invalid GLB header')
   length,kind=struct.unpack_from('<II',blob,12)
   if kind!=0x4e4f534a:raise SystemExit(f'{path}: first GLB chunk must be JSON')
   gltf=json.loads(blob[20:20+length])
  else:gltf=json.loads(path.read_text())
  if gltf.get('animations'):
   raise SystemExit(f'{path}: pose samples must be baked positions, not animation channels')
  for node in gltf.get('nodes',[]):
   if 'mesh' in node:
    if 'skin' in node:
     raise SystemExit(f'{path}: pose samples must have skinning baked into positions')
    weights=node.get('weights',gltf['meshes'][node['mesh']].get('weights',[]))
    if weights and any(abs(w)>1e-12 for w in weights):
     raise SystemExit(f'{path}: nonzero morph weights require baked positions for triangle QA')
 scene=trimesh.load_scene(path,process=False,merge_primitives=args.merge_primitives)
 nodes={}
 for name in scene.graph.nodes_geometry:
  matrix,geom_name=scene.graph[name]
  mesh=scene.geometry[geom_name]
  if isinstance(mesh,trimesh.Trimesh):
   mesh=mesh.copy();mesh.apply_transform(matrix);mesh.apply_scale(scale);nodes[name]=mesh
 for first,second in spec['pairs']:
  row={'pose':sample['pose'],'phase':sample['phase'],'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pair':[first,second]}
  if first not in nodes or second not in nodes:
   row['error']='Required exact node missing';failures.append(row)
  else:
   a,b=nodes[first],nodes[second]
   if not np.isfinite(a.vertices).all() or not np.isfinite(b.vertices).all():
    row['error']='Nonfinite vertices';failures.append(row)
   else:
    manager=CollisionManager();manager.add_object(first,a)
    hit,contacts=manager.in_collision_single(b,return_data=True)
    row.update({'surface_intersection':bool(hit),'returned_contact_count':len(contacts),'minimum_surface_distance_mm':float(manager.min_distance_single(b)),'first_watertight':bool(a.is_watertight),'second_watertight':bool(b.is_watertight)})
  rows.append(row)
report={'merge_material_primitives':args.merge_primitives,'manifest':str(args.manifest),'unit_converted_to':'mm','samples':len(spec['samples']),'results':rows,'errors':len(failures),'scope':'Discrete exported final mesh samples. Triangle surface intersections and nearest distance only; no all-time, interior containment, anatomical or contact validity approval.'}
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'samples':len(spec['samples']),'pairs_checked':len(rows),'errors':len(failures),'surface_intersections':sum(r.get('surface_intersection',False) for r in rows),'report':str(args.out)}))
raise SystemExit(1 if failures else 0)
