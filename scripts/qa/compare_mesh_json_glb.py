#!/usr/bin/env python3
"""Compare evaluated base geometry in GLB to canonical rest JSON positions/indices.
Checks exact world-space coordinates in source units, topology and named parts;
does not evaluate morphs or skinning and does not prove anatomical correctness.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import trimesh
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('mesh',type=Path);parser.add_argument('json',type=Path);parser.add_argument('--out',type=Path,required=True)
a=parser.parse_args();source=json.loads(a.json.read_text());scene=trimesh.load_scene(a.mesh,process=False);rows=[];errors=[]
for node in scene.graph.nodes_geometry:
 matrix,name=scene.graph[node];m=scene.geometry[name].copy();m.apply_transform(matrix)
 if node not in source['parts']:errors.append('Unexpected GLB part '+node);continue
 p=source['parts'][node];v=np.array(p['positions']).reshape(-1,3);f=np.array(p['indices']).reshape(-1,3)
 row={'node':node,'same_vertex_count':len(v)==len(m.vertices),'same_triangle_count':len(f)==len(m.faces),'max_vertex_difference_source_units':float(abs(v-m.vertices).max()) if v.shape==m.vertices.shape else None,'indices_equal':bool(np.array_equal(f,m.faces))};row['max_expanded_triangle_corner_difference_source_units']=float(abs(v[f]-m.vertices[m.faces]).max()) if f.shape==m.faces.shape else None
 row['vertex_index_contract_preserved']=row['indices_equal'] and row['max_vertex_difference_source_units']==0
 rows.append(row)
 if row['max_expanded_triangle_corner_difference_source_units']!=0:errors.append('Surface triangle geometry difference '+node)
missing=set(source['parts'])-set(scene.graph.nodes_geometry);errors.extend('Missing GLB part '+n for n in missing)
report={'mesh':str(a.mesh),'mesh_sha256':hashlib.sha256(a.mesh.read_bytes()).hexdigest(),'json':str(a.json),'json_sha256':hashlib.sha256(a.json.read_bytes()).hexdigest(),'units':source.get('units'),'axes':source.get('axes'),'results':rows,'errors':errors}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2));print(json.dumps({'parts':len(rows),'errors':errors,'output':str(a.out)}));raise SystemExit(bool(errors))
