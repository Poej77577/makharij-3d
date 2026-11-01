"""Read-only inspection of the unmodified HRA Mouth Male GLB in Blender.
No remesh, sculpt, deformation, fitting, asset optimization, or source export.
"""
import bpy,bmesh,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
import argparse, sys
parser = argparse.ArgumentParser(description="Read-only HRA original asset inspection in Blender")
parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parents[1] / "work/research/nih-hra")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
ROOT = args.input_dir.resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_hra_original import verify
verify(ROOT / "3d-vh-m-mouth.glb")
(ROOT / "evidence").mkdir(exist_ok=True)

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'3d-vh-m-mouth.glb'))
def native(v):return Vector((v.x,v.z,-v.y))
def gltf_vertices(o):return[native(o.matrix_world@v.co)for v in o.data.vertices]
items=[];trees={}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 vs=gltf_vertices(o);o.data.calc_loop_triangles();tris=[tuple(t.vertices)for t in o.data.loop_triangles]
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold for e in bm.edges)
 entry={'name':o.name,'verticesInGlb':len(o.data.vertices),'verticesAfterSeamWeld':len(bm.verts),'facesAfterSeamWeld':len(bm.faces),'trianglesInGlb':len(tris),'boundaryEdgesAfterWeld':boundary,'nonmanifoldEdgesAfterWeld':nonmanifold,'signedVolumeMlIfClosed':float(bm.calc_volume(signed=True)*1e6)if nonmanifold==0 else None,'boundsNativeMeters':[[min(v[k]for v in vs)for k in range(3)],[max(v[k]for v in vs)for k in range(3)]],'dimensionsMm':[(max(v[k]for v in vs)-min(v[k]for v in vs))*1000 for k in range(3)]}
 bm.free();items.append(entry)
 if o.name in ['VH_M_dorsal_tongue','VH_M_ventral_tongue','VH_M_posterior_part_of_tongue','VH_M_hard_palate','VH_M_mucosa_of_soft_palate']:
  trees[o.name]=BVHTree.FromPolygons(vs,tris,all_triangles=True)
 print('MESH',entry)
profile=[]
for lateral in [0,.01,-.01]:
 for ap in [.045,.05,.055,.06,.065,.07,.075,.08,.085,.09,.095,.1]:
  t=trees['VH_M_dorsal_tongue'].ray_cast(Vector((lateral,.80,ap)),Vector((0,-1,0)),.15)[0]
  hits=[trees[k].ray_cast(Vector((lateral,.70,ap)),Vector((0,1,0)),.15)[0]for k in ['VH_M_hard_palate','VH_M_mucosa_of_soft_palate']];hits=[h for h in hits if h]
  if t and hits:profile.append({'lateralMm':lateral*1000,'apMm':ap*1000,'dorsalUpperYmm':t.y*1000,'firstPalateSurfaceYmm':min(h.y for h in hits)*1000,'verticalGapMm':(min(h.y for h in hits)-t.y)*1000})
report={'blenderVersion':bpy.app.version_string,'fileOpened':str(ROOT/'3d-vh-m-mouth.glb'),'sourceModified':False,'gltfUnits':'metres by glTF2 specification','gltfNativeAxesInferredFromNamedParts':{'X':'positive patient-left (left glands at +X, right at -X)','Y':'positive superior (upper dental/palatal structures higher)','Z':'positive anterior (dental front and tongue tip at larger Z than posterior tongue)'},'blenderImportAxes':'Blender world (X,Y,Z)=(glTF X,-glTF Z,glTF Y); root/world transforms retained','meshCount':len(items),'vertexCount':sum(x['verticesInGlb']for x in items),'triangleCount':sum(x['trianglesInGlb']for x in items),'materials':len(bpy.data.materials),'armatureCount':sum(o.type=='ARMATURE'for o in bpy.context.scene.objects),'shapeKeyMeshes':[o.name for o in bpy.context.scene.objects if o.type=='MESH'and o.data.shape_keys],'objects':items,'sampledDorsumPalateVerticalRays':profile,'measurementCaveat':'First intersections of labelled mucosal/palatal surfaces; these are mesh-geometry samples in supplied fixed pose, not physiological airspace measurements or proof of connected airway.'}
(ROOT/'blender-inspection.json').write_text(json.dumps(report,indent=2))
print('INSPECTION_COMPLETE',len(items),sum(x['trianglesInGlb']for x in items))
