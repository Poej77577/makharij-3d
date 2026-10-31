"""Conforming refinement of acquired contact triangles; surface shape retained.
New samples lie on original triangle edges. This adds authoring degrees of
freedom for contact, not new anatomical measurements or a donor surface.
"""
import bpy

def refine_lip_contacts(ob,masks):
 me=ob.data;points=[tuple(v.co)for v in me.vertices];faces=[tuple(f.vertices)for f in me.polygons];colors=[tuple(c.color)for c in me.color_attributes['TissueColor'].data]
 selected=set(masks['upperContactTriangles'])|set(masks['lowerContactTriangles']);marked=set()
 for i in selected:
  a,b,c=faces[i]
  for e in [(a,b),(b,c),(c,a)]:marked.add(tuple(sorted(e)))
 arrays={k:list(masks[k])for k in ['sourceNodeIds','upperWeights','lowerWeights','jawWeights']};mid={}
 for a,b in sorted(marked):
  mid[(a,b)]=len(points);points.append(tuple((x+y)/2 for x,y in zip(points[a],points[b])));colors.append(tuple((x+y)/2 for x,y in zip(colors[a],colors[b])))
  for k,v in arrays.items():v.append(-1 if k=='sourceNodeIds'else(v[a]+v[b])/2)
 children=[];parents=[]
 for index,(a,b,c) in enumerate(faces):
  ab=mid.get(tuple(sorted((a,b))));bc=mid.get(tuple(sorted((b,c))));ca=mid.get(tuple(sorted((c,a))));count=sum(x is not None for x in [ab,bc,ca])
  if count==0:new=[(a,b,c)]
  elif count==3:new=[(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]
  elif count==1:
   if ab is not None:new=[(a,ab,c),(ab,b,c)]
   elif bc is not None:new=[(b,bc,a),(bc,c,a)]
   else:new=[(c,ca,b),(ca,a,b)]
  else:
   if ab is None:new=[(c,ca,bc),(ca,a,b),(ca,b,bc)]
   elif bc is None:new=[(a,ab,ca),(ab,b,c),(ab,c,ca)]
   else:new=[(b,bc,ab),(bc,c,a),(bc,a,ab)]
  children.extend(new);parents.extend([index]*len(new))
 for attr in list(me.color_attributes):me.color_attributes.remove(attr)
 if 'SOURCE_NODE_ID'in me.attributes:me.attributes.remove(me.attributes['SOURCE_NODE_ID'])
 me.clear_geometry();me.from_pydata(points,[],children);me.update();attr=me.color_attributes.new(name='TissueColor',type='FLOAT_COLOR',domain='POINT')
 for i,color in enumerate(colors):attr.data[i].color=color
 source=me.attributes.new(name='SOURCE_NODE_ID',type='INT',domain='POINT')
 for i,value in enumerate(arrays['sourceNodeIds']):source.data[i].value=value
 for face in me.polygons:face.use_smooth=True;face.material_index=0
 updated=dict(masks);updated.update(arrays)
 for side in ['upper','lower']:
  original=set(masks[side+'ContactTriangles']);ids=[i for i,p in enumerate(parents)if p in original];updated[side+'ContactTriangles']=ids;updated[side+'ContactVertices']=sorted({v for i in ids for v in children[i]})
 for group in list(ob.vertex_groups):ob.vertex_groups.remove(group)
 for label,key in [('Source upper lip','upperWeights'),('Source lower lip','lowerWeights'),('Source jaw','jawWeights')]:
  group=ob.vertex_groups.new(name=label)
  for i,w in enumerate(updated[key]):
   if w>.00001:group.add([i],w,'REPLACE')
 metadata={'method':'conforming red/green triangle edge refinement of source contact patches','originalVertices':len(masks['sourceNodeIds']),'newVertices':len(points),'originalTriangles':len(faces),'newTriangles':len(children),'newAnatomicalMeasurements':False,'generatedSourceNodeId':-1,'surfacePositionChange':'existing points unchanged; generated points are original edge midpoints'}
 return updated,metadata
