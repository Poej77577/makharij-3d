"""Trim authored lining against the acquired moving velum; no source edits.
The moving soft palate supplies this boundary. A .15mm authoring clearance is
not a measured physiological gap and must not be presented as clinical data.
"""
import bpy,bmesh

def trim_nasal_interface(lining,velum,clearance=.00015):
 before=(len(lining.data.vertices),len(lining.data.polygons))
 ghost=velum.copy();ghost.data=velum.data.copy();ghost.name='TEMP_VELUM_CLEARANCE';bpy.context.collection.objects.link(ghost);ghost.data.update()
 for v in ghost.data.vertices:v.co+=v.normal*clearance
 ghost.data.update();mod=lining.modifiers.new('Acquired velum boundary trim','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=ghost
 bpy.context.view_layer.objects.active=lining;lining.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name);lining.select_set(False)
 mesh=ghost.data;bpy.data.objects.remove(ghost,do_unlink=True);bpy.data.meshes.remove(mesh)
 bm=bmesh.new();bm.from_mesh(lining.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));volume=bm.calc_volume(signed=True);bm.to_mesh(lining.data);bm.free();lining.data.update()
 if not lining.data.vertices or volume<=0:raise ValueError('Authored lining trim produced invalid/empty tissue')
 for f in lining.data.polygons:f.use_smooth=True
 return {'operation':'difference of authored lining and outward-offset acquired velum; moving tissue remains the cavity boundary','clearance_m':clearance,'verticesBefore':before[0],'trianglesBefore':before[1],'verticesAfter':len(lining.data.vertices),'trianglesAfter':len(lining.data.polygons),'closedTissueVolume_m3':volume,'clinicalMeasurement':False}
