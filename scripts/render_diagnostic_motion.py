"""Render frozen FAILED v4 movement for engineering review, never student content.
blender -b -t 4 --python scripts/render_diagnostic_motion.py
"""
import bpy, json, math, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/motion/diagnostic-v4/rest-meshes.json'
MOTION=ROOT/'data/motion/diagnostic-v4'; OUT=ROOT/'research/coordinator/motion-v4-failed'
OUT.mkdir(parents=True,exist_ok=True)
base=json.loads(BASE.read_text()); manifest=json.loads((MOTION/'manifest.json').read_text())
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
colors={'TONGUE':(.66,.36,.34,1),'UPPER_TEETH':(.87,.84,.74,1),'LOWER_TEETH':(.87,.84,.74,1),'UPPER_LIP':(.64,.34,.33,1),'LOWER_LIP':(.64,.34,.33,1),'HARD_PALATE':(.72,.57,.46,1),'SOFT_PALATE':(.64,.42,.53,1),'PHARYNX':(.53,.42,.46,1),'GINGIVA_UPPER':(.63,.43,.39,1),'GINGIVA_LOWER':(.63,.43,.39,1)}
objects={}
for name,part in base['parts'].items():
 if name not in colors:continue
 mesh=bpy.data.meshes.new(name); mesh.from_pydata(np.array(part['positions']).reshape(-1,3).tolist(),[],np.array(part['indices']).reshape(-1,3).tolist());mesh.update()
 ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);objects[name]=ob
 for p in mesh.polygons:p.use_smooth=True
 mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;link=mat.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=colors[name];bs.inputs['Roughness'].default_value=.6
 geo=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');test=n.new('ShaderNodeMath');test.operation='GREATER_THAN';test.inputs[1].default_value=0
 tr=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader')
 link.new(geo.outputs['Position'],sep.inputs[0]);link.new(sep.outputs['Z'],test.inputs[0]);link.new(test.outputs[0],mix.inputs[0]);link.new(bs.outputs[0],mix.inputs[1]);link.new(tr.outputs[0],mix.inputs[2]);link.new(mix.outputs[0],n.get('Material Output').inputs['Surface']);mesh.materials.append(mat)
 ob.shape_key_add(name='Basis')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=2;scene.cycles.use_denoising=False;scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.fps=10;scene.world.color=(.06,.08,.09)
for pos,power in [((.16,.13,.2),.6),((-.05,.1,.15),.3)]:
 d=bpy.data.lights.new('Review light','AREA');d.energy=power;d.shape='DISK';d.size=.15;o=bpy.data.objects.new('Review light',d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((.055,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review side');cam=bpy.data.objects.new('Review side',d);bpy.context.collection.objects.link(cam);scene.camera=cam;cam.location=(.059,.008,.25);forward=(Vector((.059,.008,0))-cam.location).normalized();right=forward.cross(Vector((0,1,0))).normalized();up=right.cross(forward);cam.rotation_euler=Matrix(((right.x,up.x,-forward.x),(right.y,up.y,-forward.y),(right.z,up.z,-forward.z))).to_euler();d.type='ORTHO';d.ortho_scale=.115
for id in ['ra','qaf','mim']:
 for ob in objects.values():
  if ob.data.shape_keys:
   ob.data.shape_keys.animation_data_clear()
   for key in list(ob.data.shape_keys.key_blocks)[1:]:ob.shape_key_remove(key)
 frames=manifest['motions'][id]['frames'];duration=manifest['motions'][id]['duration'];count=math.ceil(duration*10)+1
 loaded={}
 for frame in frames:
  if frame['geometryKey'] and frame['geometryKey'] not in loaded:
   values=np.load(MOTION/frame['file']);loaded[frame['geometryKey']]={k:values[k] for k in values.files}
 for name,ob in objects.items():
  for key,parts in loaded.items():
   if name not in parts:continue
   k=ob.shape_key_add(name=key);k.data.foreach_set('co',np.asarray(parts[name],dtype=np.float32).ravel())
  for index in range(count):
   t=index/(count-1);a=0
   while a<len(frames)-2 and t>frames[a+1]['t']:a+=1
   u=(t-frames[a]['t'])/(frames[a+1]['t']-frames[a]['t']);weights={}
   for f,w in [(frames[a],1-u),(frames[a+1],u)]:
    if f['geometryKey']:weights[f['geometryKey']]=weights.get(f['geometryKey'],0)+w
   for k in list(ob.data.shape_keys.key_blocks)[1:]:k.value=weights.get(k.name,0);k.keyframe_insert('value',frame=index+1)
  if ob.data.shape_keys.animation_data:
   for fc in ob.data.shape_keys.animation_data.action.fcurves:
    for kp in fc.keyframe_points:kp.interpolation='LINEAR'
 folder=OUT/id;folder.mkdir(exist_ok=True);scene.frame_start=1;scene.frame_end=count;scene.render.filepath=str(folder/'frame-');bpy.ops.render.render(animation=True)
(OUT/'README.ar.md').write_text('هذه فيديوهات تشخيصية للحركات المرفوضة v4، وليست محتوى تعليميًا صالحًا. فشل ر/ق بسبب طي وتقاطعات؛ الميم لا تحقق الإغلاق. الهندسة من ملف الراحة المجمد وعينات الحركة الفعلية، بمقطع عرض شفاف. لا صوت أو اعتماد أو قياس أداء. راجع تقرير diagnostic-v4-motion.json.\n')
