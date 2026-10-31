#!/usr/bin/env python3
"""Sample obstacle vertices and triangle centroids inside closed tissue meshes.
Distances are nearest tissue-boundary distances in mm, not continuous penetration
or physiological contact validation. Source/final node transforms are applied.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import trimesh
from trimesh.collision import CollisionManager
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('file',type=Path);parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--weld-exact',action='store_true',help='For containment only, combine exactly equal vertex coordinates without moving triangles or filling holes')
parser.add_argument('--pair',nargs=2,action='append',help='Override default checked pairs: closed tissue node followed by sampled mesh node')
args=parser.parse_args();scene=trimesh.load_scene(args.file,process=False);parts={}
for name in scene.graph.nodes_geometry:
 matrix,g=scene.graph[name];mesh=scene.geometry[g].copy();mesh.apply_transform(matrix);mesh.apply_scale(1000);parts[name]=mesh
rows=[]
for a,b in (args.pair or [('TONGUE','LOWER_TEETH'),('TONGUE','SOFT_PALATE'),('UPPER_LIP','UPPER_TEETH'),('LOWER_LIP','LOWER_TEETH')]):
 tissue,obstacle=parts[a],parts[b]
 normalization=None
 if not tissue.is_volume and args.weld_exact:
  vertices,inverse=np.unique(tissue.vertices,axis=0,return_inverse=True)
  welded=trimesh.Trimesh(vertices=vertices,faces=inverse[tissue.faces],process=False)
  normalization={'operation':'exact-coordinate welding only; no vertex moved, face removed or hole filled','raw_vertices':len(tissue.vertices),'welded_vertices':len(vertices),'raw_is_volume':bool(tissue.is_volume),'welded_is_volume':bool(welded.is_volume)}
  tissue=welded
 if not tissue.is_volume: raise SystemExit(f'{a} must be consistently wound closed positive-volume tissue for containment')
 row={'pair':[a,b],'containment_topology_normalization':normalization};manager=CollisionManager();manager.add_object(a,tissue);hit,contacts=manager.in_collision_single(obstacle,return_data=True)
 if contacts:
  points=np.array([c.point for c in contacts]);row['surface_contact_bounds_mm']=[points.min(0).tolist(),points.max(0).tolist()]
  # Trimesh names the caller's unnamed single mesh __external.
  for side in [a,'__external']:
   indices=set()
   for c in contacts:
    try: indices.add(int(c.index(side)))
    except (ValueError,KeyError): pass
   row['contact_triangle_indices_'+side]=sorted(indices)
 for kind,points in [('vertices',obstacle.vertices),('triangle_centroids',obstacle.triangles_center)]:
  inside=tissue.contains(points);ids=np.flatnonzero(inside);entry={'total_samples':len(points),'inside_samples':len(ids)}
  if len(ids):
   _,distances,_=trimesh.proximity.closest_point(tissue,points[ids]);order=np.argsort(distances)[::-1]
   entry['depth_quantiles_mm']={str(q):float(np.quantile(distances,q)) for q in [0,.5,.9,.95,.99,1]}
   entry['inside_point_bounds_mm']=[points[ids].min(0).tolist(),points[ids].max(0).tolist()]
   entry['deepest_samples']=[{'index':int(ids[i]),'point_mm':points[ids[i]].tolist(),'nearest_tissue_boundary_mm':float(distances[i])} for i in order[:50]]
  row[kind]=entry
 rows.append(row);print(json.dumps({'pair':[a,b],'vertices':row['vertices'].get('depth_quantiles_mm'),'triangle_centroids':row['triangle_centroids'].get('depth_quantiles_mm')}),flush=True)
args.out.parent.mkdir(parents=True,exist_ok=True)
args.out.write_text(json.dumps({'file':str(args.file),'sha256':hashlib.sha256(args.file.read_bytes()).hexdigest(),'source_units':'m converted to mm per verified contract','scope':'Discrete sampled second-mesh vertices and triangle centroids inside first closed, consistently wound positive-volume tissue. Not a solid dental depth or continuous maximum penetration measurement.','results':rows},indent=2))
