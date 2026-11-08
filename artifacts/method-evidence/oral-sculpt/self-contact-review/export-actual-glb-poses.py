
from pathlib import Path
import hashlib,json,sys
import bpy,numpy as np
c=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
a=Path(c['asset'])
if hashlib.sha256(a.read_bytes()).hexdigest()!=c['expectedSha256']:
    raise RuntimeError('GLB changed before reimport')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(a))
for ob in bpy.context.scene.objects:
    if ob.type=='MESH' and ob.data.shape_keys:
        ob.data.shape_keys.animation_data_clear()
jaw=bpy.data.objects[c['manifest']['jawBinding']['node']]
jaw.animation_data_clear();jaw.rotation_mode='XYZ';jaw.rotation_euler.x=0
ob=bpy.data.objects['TONGUE']
keys=ob.data.shape_keys
if keys is None or not {'TIP_ELEVATE','DORSUM_ELEVATE','ROOT_RETRACT'}.issubset(keys.key_blocks.keys()):
    raise RuntimeError('Actual GLB lacks required tongue morphs')
rows=[]
for i,(label,values)in enumerate(c['cases']):
    for mesh in bpy.context.scene.objects:
        if mesh.type!='MESH' or not mesh.data.shape_keys:continue
        for k in mesh.data.shape_keys.key_blocks[1:]:
            pair=c['manifest']['correctives'].get(k.name)
            k.value=values.get(pair[0],0)*values.get(pair[1],0) if pair else values.get(k.name,0)
        mesh.data.shape_keys.update_tag()
    jaw.rotation_euler.x=0
    bpy.context.view_layer.update()
    e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles()
    world=[e.matrix_world@v.co for v in m.vertices]
    points=np.array([(-v.y,v.z,-v.x)for v in world],dtype=np.float64)
    faces=np.array([t.vertices for t in m.loop_triangles],dtype=np.int32)
    e.to_mesh_clear()
    p=Path(c['output'])/('pose-%02d.npz'%i)
    np.savez_compressed(p,vertices=points,faces=faces)
    rows.append({'case':label,'controls':values,'jawOpen':0,'file':str(p)})
if hashlib.sha256(a.read_bytes()).hexdigest()!=c['expectedSha256']:
    raise RuntimeError('GLB changed during pose export')
Path(c['output'],'poses.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'actualGlbPoses':len(rows),'assetSha256':c['expectedSha256']}))
