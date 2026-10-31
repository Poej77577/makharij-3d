"""Continuous source FEM lip tissue with original contact-node masks.

No duplicate filled-lip meshes, no invented mouth aperture. The mouth opening is
part of the acquired hexahedral boundary. All fit offsets are unmeasured visual
registration corrections. This module does not claim scientific validity.
"""
import bpy, bmesh, collections, hashlib, itertools, math, re
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

def build_continuous_lips(source_dir, create):
    node_path=source_dir/'badinface_oop_csa_midsagittal.node'
    elem_path=source_dir/'badinface_oop_csa_midsagittal.elem'
    contact_paths=[source_dir/(side+'_lip_surface_Ian.elem.txt') for side in ['upper','lower']]
    nodes={}
    for line in node_path.read_text().splitlines():
        t=re.findall(r'[-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+',line)
        if len(t)>=4:
            p=list(map(float,t[1:4]));nodes[int(t[0])]=(.14-p[0],p[2]-.1,p[1])
    quad_keys=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    counts=collections.Counter(); faces={}
    for line in elem_path.read_text().splitlines():
        ids=list(map(int,line.split()))[:8]
        for q in quad_keys:
            face=tuple(ids[i]for i in q);key=tuple(sorted(face));counts[key]+=1;faces[key]=face
    triangles=[];seen_triangles=set();duplicate_source_triangles=0
    for key,count in counts.items():
        if count!=1:continue
        face=list(dict.fromkeys(faces[key]))  # ANSYS can encode wedge/degenerate hex faces.
        for j in range(1,len(face)-1):
            tri=[face[0],face[j],face[j+1]];tkey=tuple(sorted(tri))
            if tkey in seen_triangles:duplicate_source_triangles+=1;continue
            seen_triangles.add(tkey);triangles.append(tri)
    ids=sorted({i for f in triangles for i in f});index={k:i for i,k in enumerate(ids)}
    ob=create('LIP_CONTEXT',[nodes[i]for i in ids],[[index[i]for i in f]for f in triangles])
    me=ob.data;bm=bmesh.new();bm.from_mesh(me)
    source_layer=bm.verts.layers.int.new('SOURCE_NODE_ID')
    bm.verts.ensure_lookup_table()
    for i,v in enumerate(bm.verts):v[source_layer]=ids[i]
    # Keep the real oral lining, free border and exterior together. No normal filter/aperture cut.
    for point,no in [((.065,0,0),(-1,0,0)),((0,.043,0),(0,1,0)),((0,-.04,0),(0,-1,0)),((0,0,.046),(0,0,1)),((0,0,-.046),(0,0,-1))]:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=point,plane_no=no,clear_outer=True,clear_inner=False)
    dead=[f for f in bm.faces if f.calc_area()<1e-14]
    if dead:bmesh.ops.delete(bm,geom=dead,context='FACES')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    repaired=me.validate(verbose=False,clean_customdata=False);me.update(calc_edges=True,calc_edges_loose=True)
    print('FEM boundary validation repaired invalid source topology:',repaired,flush=True)
    source_attribute=me.attributes['SOURCE_NODE_ID']
    source_ids=[]
    for i,v in enumerate(me.vertices):
        sid=int(source_attribute.data[i].value)
        source_ids.append(sid if sid in nodes and (v.co-Vector(nodes[sid])).length<1e-7 else -1)
    contact_quads=[];trees=[]
    for path in contact_paths:
        quads=[list(map(int,line.split()))for line in path.read_text().splitlines()if line.strip()]
        contact_quads.append(quads);nums=sorted({i for f in quads for i in f});tree=KDTree(len(nums))
        for j,k in enumerate(nums):tree.insert(Vector(nodes[k]),j)
        tree.balance();trees.append(tree)
    base=[v.co.copy()for v in me.vertices];upper=[];lower=[];jaw=[]
    for v in me.vertices:
        du=trees[0].find(v.co)[2];dl=trees[1].find(v.co)[2]
        wu=1/(du+.0003)**2;wl=1/(dl+.0003)**2;near=math.exp(-(min(du,dl)/.016)**2)
        upper.append(math.exp(-(du/.018)**2)*wu/(wu+wl))
        lower.append(math.exp(-(dl/.018)**2)*wl/(wu+wl))
        coarse=max(0,min(1,(.004-v.co.y)/.023));w=near*wl/(wu+wl)+(1-near)*coarse;jaw.append(w)
        a=math.radians(-6)*w;cx,cy=.003,.037;x,y=v.co.x-cx,v.co.y-cy
        v.co.x=cx+math.cos(a)*x-math.sin(a)*y;v.co.y=cy+math.sin(a)*x+math.cos(a)*y
    prefit=np.array([tuple(v.co)for v in me.vertices]);fit_delta=[]
    # Source-continuous version of the previously inspected positive affine lip fit.
    # Blend through the open-mouth interval, so the outer tissue has no detached seam.
    for v in me.vertices:
        t=max(0,min(1,(v.co.y+.010)/.012));t=t*t*(3-2*t)
        up=Vector(((v.co.x-.020)*.015+.0022,0,v.co.z*.015));lo=Vector((.0008,-.0008,0))
        delta=up*t+lo*(1-t);v.co+=delta;fit_delta.append(delta.length)
    # Coordinator v6: bounded positive affine fit of the coherent tissue to the
    # published dental cast. FCL v5 probe found this smallest tested fit clearing
    # both arches; it is an unmeasured registration correction, not physiology.
    for i,v in enumerate(me.vertices):
        v.co.x=.020+(v.co.x-.020)*1.01+.001
        v.co.z*=1.01
        fit_delta[i]=(v.co-Vector(prefit[i])).length
    faces_array=np.array([list(f.vertices)for f in me.polygons]);q=np.array([tuple(v.co)for v in me.vertices])
    a=np.cross(prefit[faces_array[:,1]]-prefit[faces_array[:,0]],prefit[faces_array[:,2]]-prefit[faces_array[:,0]])
    b=np.cross(q[faces_array[:,1]]-q[faces_array[:,0]],q[faces_array[:,2]]-q[faces_array[:,0]])
    significant=np.linalg.norm(a,axis=1)>1e-14
    reversed_count=int(np.sum((np.sum(a*b,axis=1)<=0)&significant))
    collapsed_count=int(np.sum((np.linalg.norm(b,axis=1)<np.linalg.norm(a,axis=1)*.03)&significant))
    if reversed_count or collapsed_count:raise ValueError(f'Continuous lip fit rejected: {reversed_count} flipped, {collapsed_count} collapsed triangles')
    # One point-colour material keeps a single semantic GLB primitive and smooth colour edges.
    me.materials.clear();mat=bpy.data.materials.new('Continuous source lip tissue');mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.65
    vc=mat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='TissueColor';mat.node_tree.links.new(vc.outputs['Color'],bs.inputs['Base Color']);me.materials.append(mat)
    colors=me.color_attributes.new(name='TissueColor',type='FLOAT_COLOR',domain='POINT')
    skin=np.array([.66,.49,.39]);lip=np.array([.60,.28,.29])
    for i,p in enumerate(base):
        d=min(t.find(p)[2]for t in trees);mix=math.exp(-(d/.0045)**2);rgb=skin*(1-mix)+lip*mix
        colors.data[i].color=(*rgb,1)
    for face in me.polygons:face.use_smooth=True;face.material_index=0
    source_triangles=[];source_vertices=[]
    for quads in contact_quads:
        keys={frozenset(c)for f in quads for c in itertools.combinations(f,3)}
        tri=[i for i,f in enumerate(me.polygons)if frozenset(source_ids[v]for v in f.vertices)in keys]
        source_triangles.append(tri);source_vertices.append(sorted({v for i in tri for v in me.polygons[i].vertices}))
    masks={'sourceNodeIds':source_ids,'upperContactVertices':source_vertices[0],'lowerContactVertices':source_vertices[1],'upperContactTriangles':source_triangles[0],'lowerContactTriangles':source_triangles[1],'upperWeights':upper,'lowerWeights':lower,'jawWeights':jaw}
    for name,values in [('Source upper lip',upper),('Source lower lip',lower),('Source jaw',jaw)]:
        group=ob.vertex_groups.new(name=name)
        for i,w in enumerate(values):
            if w>.00001:group.add([i],w,'REPLACE')
    report={'method':'positive affine registration blended continuously through actual open-mouth tissue','maxDisplacement_mm':max(fit_delta)*1000,'reversed_triangles':reversed_count,'collapsed_triangles':collapsed_count,'upperFormula':{'x':'.020+(x-.020)*1.015+.0022','z':'z*1.015','y':'unchanged'},'lowerTranslation_m':[.0008,-.0008,0],'unmeasuredTechnicalFit':True,'sourcePart':'active FEM boundary; duplicated filled lip meshes discarded','additionalWholeTissueFit':{'radialScale':1.01,'archOriginX_m':.020,'anteriorTranslation_m':.001,'additionalMaxDisplacement_mm':2.0321493774652364,'evidence':'research/coordinator/v5-lip-fit-probe.json','unmeasured':True},'clinicalApproval':False,'sourceBoundaryTopologyRepair':repaired,'duplicateSourceTrianglesRemoved':duplicate_source_triangles}
    provenance={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [node_path,elem_path,*contact_paths]}
    if me.validate(verbose=False,clean_customdata=False):raise ValueError('Unexpected invalid final lip mesh; no accepted candidate written')
    return ob,masks,report,provenance
