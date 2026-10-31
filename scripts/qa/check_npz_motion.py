#!/usr/bin/env python3
"""Independently inspect actual NPZ evaluated geometry and interval midpoints.
Requires exact rest SHA. Tests triangle collisions, deformation quality and
fixed supplied source-landmark proximity; no anatomical approval is inferred.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh
from trimesh.collision import CollisionManager
p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--rest',type=Path,required=True);p.add_argument('--regions',type=Path,required=True);p.add_argument('--poses',nargs='+',default=['ra','qaf','mim']);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
spec=json.loads(args.manifest.read_text());blob=args.rest.read_bytes();sha=hashlib.sha256(blob).hexdigest()
if sha!=spec['restSha256']:raise SystemExit('Exact rest SHA mismatch; do not mix source versions')
regions=json.loads(args.regions.read_text())
if regions['restSha256']!=sha:raise SystemExit('Region source SHA mismatch')
if spec['units']!='m':raise SystemExit('Expected verified canonical meters')
rest=json.loads(blob);vertices={n:np.array(part['positions']).reshape(-1,3) for n,part in rest['parts'].items()};faces={n:np.array(part['indices']).reshape(-1,3) for n,part in rest['parts'].items()}
base_cross={n:np.cross(v[faces[n][:,1]]-v[faces[n][:,0]],v[faces[n][:,2]]-v[faces[n][:,0]]) for n,v in vertices.items()}
cache_npz={};cache_eval={};rows=[]
pairs=[('TONGUE',n) for n in ['UPPER_TEETH','LOWER_TEETH','HARD_PALATE','SOFT_PALATE','GINGIVA_UPPER','GINGIVA_LOWER']]+[('UPPER_LIP','UPPER_TEETH'),('LOWER_LIP','LOWER_TEETH'),('LOWER_LIP','UPPER_TEETH'),('UPPER_LIP','LOWER_LIP')]
semantics={'ra':('tongue-tip','upper-alveolar'),'qaf':('posterior-dorsum','velum-oral'),'mim':('lower-lip-seam','upper-lip-seam-surface'),'fa':('lower-lip-inner','upper-incisor-free-edge'),'ayn':('tongue-root','pharyngeal-wall')}
def frame(f):
 if not f['file']:return {}
 path=args.manifest.parent/f['file']
 if str(path) not in cache_npz:
  z=np.load(path);cache_npz[str(path)]={k:z[k].astype(float) for k in z.files}
 return cache_npz[str(path)]
def digest(dynamic):
 h=hashlib.sha256()
 for n,v in sorted(dynamic.items()):h.update(n.encode());h.update(v.tobytes())
 return h.hexdigest()
def evaluate(dynamic,pose):
 signature=digest(dynamic);key=(signature,pose)
 if key in cache_eval:return cache_eval[key]
 pos={**vertices,**dynamic};meshes={n:trimesh.Trimesh(vertices=v*1000,faces=faces[n],process=False) for n,v in pos.items()};quality={}
 for n,v in dynamic.items():
  if v.shape!=vertices[n].shape or not np.isfinite(v).all():raise SystemExit(f'Invalid sampled vertex array {n}')
  cross=np.cross(v[faces[n][:,1]]-v[faces[n][:,0]],v[faces[n][:,2]]-v[faces[n][:,0]]);ratio=np.linalg.norm(cross,axis=1)/np.linalg.norm(base_cross[n],axis=1);dots=(cross*base_cross[n]).sum(1);bad=np.flatnonzero(ratio<.01)
  quality[n]={'max_displacement_mm':float(np.linalg.norm(v-vertices[n],axis=1).max()*1000),'negative_rest_normal_dots':int((dots<0).sum()),'minimum_area_ratio':float(ratio.min()),'area_ratio_below_1pct_triangles':bad.tolist()}
 collisions=[]
 for a,b in pairs:
  manager=CollisionManager();manager.add_object(a,meshes[a]);hit,data=manager.in_collision_single(meshes[b],return_data=True)
  r={'pair':[a,b],'surface_intersection':bool(hit),'returned_contacts':len(data),'minimum_surface_distance_mm':float(manager.min_distance_single(meshes[b]))}
  if data:
   points=np.array([c.point for c in data]);r['contact_bounds_mm']=[points.min(0).tolist(),points.max(0).tolist()]
  collisions.append(r)
 first,second=semantics[pose];a,b=regions['regions'][first],regions['regions'][second];pts=pos[a['node']][a['vertices']]*1000;target=trimesh.Trimesh(vertices=pos[b['node']]*1000,faces=faces[b['node']][b['triangles']],process=False);closest,dist,_=trimesh.proximity.closest_point(target,pts);near={}
 for tolerance in [.1,.3,.5,1.,2.]:
  mask=dist<=tolerance;entry={'count':int(mask.sum()),'total':len(pts)}
  if mask.any():entry['sample_bounds_mm']=[pts[mask].min(0).tolist(),pts[mask].max(0).tolist()]
  near[str(tolerance)]=entry
 semantic={'source_region':first,'target_region':second,'minimum_mm':float(dist.min()),'median_mm':float(np.median(dist)),'near_tolerances_mm':near,'nearest_pair_mm':[pts[dist.argmin()].tolist(),closest[dist.argmin()].tolist()]}
 if pose=='mim':
  u=regions['regions']['upper-lip-seam'];up=pos[u['node']][u['vertices']]*1000
  semantic['seam_lower_to_upper_nearest_vertex_gaps_mm']=[{'lower_source_vertex':int(i),'lateral_z_mm':float(point[2]),'gap_mm':float(np.linalg.norm(up-point,axis=1).min())} for i,point in zip(a['vertices'],pts)]
  delta=pos['SOFT_PALATE']-vertices['SOFT_PALATE'];semantic['velum_mean_delta_y_mm']=float(delta[:,1].mean()*1000);semantic['velum_max_displacement_mm']=float(np.linalg.norm(delta,axis=1).max()*1000)
 result={'geometry_sha256':signature,'quality':quality,'collisions':collisions,'semantic_region_proximity':semantic};cache_eval[key]=result;return result
for pose in args.poses:
 fs=spec['motions'][pose]['frames'];samples=[]
 for i,f in enumerate(fs):
  samples.append((f['t'],'keyframe',frame(f),[f['key']]))
  if i+1<len(fs):
   nxt=fs[i+1];aa,bb=frame(f),frame(nxt);d={n:(aa.get(n,vertices[n])+bb.get(n,vertices[n]))*.5 for n in aa.keys()|bb.keys()};samples.append(((f['t']+nxt['t'])*.5,'interval-midpoint',d,[f['key'],nxt['key']]))
 for t,kind,d,keys in samples:
  row={'pose':pose,'t':t,'kind':kind,'source_frame_keys':keys,**evaluate(d,pose)};rows.append(row)
 print(json.dumps({'pose':pose,'states':len(samples),'unique_cached_pose_geometries':sum(k[1]==pose for k in cache_eval),'states_with_any_intersection':sum(any(c['surface_intersection'] for c in r['collisions']) for r in rows if r['pose']==pose),'minimum_semantic_distance_mm':min(r['semantic_region_proximity']['minimum_mm'] for r in rows if r['pose']==pose)}),flush=True)
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps({'manifest':str(args.manifest),'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),'rest_sha256':sha,'regions_sha256':hashlib.sha256(args.regions.read_bytes()).hexdigest(),'interpolation':spec['interpolation'],'scope':'Exact evaluated supplied NPZ keyframes and arithmetic interval midpoints in canonical meters. Actual surface intersections and fixed supplied region proximity only. Not all-time collision proof, scientific validation, or final GLB/browser parity.','results':rows},indent=2))
