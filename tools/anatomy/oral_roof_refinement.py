"""Bounded oral-roof authoring, in project metres (+X anterior,+Y up,+Z right).

No medical/donor registration. Upper gingiva retains its source identity and
existing palatal mucosal surface. This module authors ONLY posterior soft
palate/uvular tissue; it does not supply hard-palatal bone. Run before rigging,
subdivision or shape-key baking. New gingival positions are an indicated
CC-BY-SA adaptation of the retained BodyParts3D/Z-Anatomy surface.
"""
from math import exp, sqrt
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _s(t):
    t = max(0., min(1., t))
    return t*t*(3.-2.*t)


def _bvh(points, faces):
    return BVHTree.FromPolygons([Vector(p) for p in points], faces, all_triangles=False)


def refine_gingival_ends(points, faces, teeth_points, teeth_faces, jaw):
    """Same source vertices/faces; local smooth deformation behind distal molar.

    A 2.5-mm actual-tooth-surface exclusion mask locks cervical contacts. The
    untouched anterior/near-tooth arrays permit source-ID verification. No
    cutting, filling, smoothing of the tooth margin or replacement meshes.
    """
    if jaw not in ('upper', 'lower'):
        raise ValueError('jaw must be upper or lower')
    ps = [Vector(p) for p in points]
    dental = _bvh(teeth_points, teeth_faces)
    distal = min(p[0] for p in teeth_points)
    proposed, locked, active = [], [], []
    tooth_width = max(abs(v[2]) for v in teeth_points)
    for i, p in enumerate(ps):
        near = dental.find_nearest(p)
        d = near[3] if near[0] is not None else 1.
        lock = d <= .0025
        if lock:
            locked.append(i)
        free = _s((d-.0025)/.0025)
        w = _s((distal+.008-p.x)/.008)*free
        q = p.copy()
        if w:
            # Inferred local terminal shaping; source posterior extensions are
            # 5.0 mm lower / 6.8 mm upper beyond the distal second-molar extent.
            q.x += .0015*w*_s((distal+.003-p.x)/.008)
            ceiling = .0055 if jaw == 'lower' else .0205
            excess = max(0., p.y-ceiling)
            q.y -= (.82 if jaw == 'lower' else .45)*w*excess
            q.z -= (1 if p.z >= 0 else -1)*.55*w*max(0., abs(p.z)-tooth_width-.0006)
            active.append(i)
        proposed.append(q)
    # Only a displacement magnitude reduction is allowed if the smooth field
    # inverts any existing triangle; no remesh or silently repaired topology.
    factor = 1.
    def inverted(scale):
        count = 0
        for face in faces:
            for j in range(1, len(face)-1):
                ids = [face[0], face[j], face[j+1]]
                a,b,c = [ps[k] for k in ids]
                u,v,w = [ps[k]+scale*(proposed[k]-ps[k]) for k in ids]
                n0=(b-a).cross(c-a); n1=(v-u).cross(w-u)
                if n0.length_squared > 1e-20 and (n1.length_squared < 1e-20 or n0.dot(n1) <= 0):
                    count += 1
        return count
    while inverted(factor) and factor > .25:
        factor *= .8
    if inverted(factor):
        raise RuntimeError('Posterior gum deformation would invert source triangles')
    out = [p+factor*(q-p) for p,q in zip(ps, proposed)]
    distances = [(q-p).length for p,q in zip(ps,out)]
    return [tuple(q) for q in out], {
        'sourceTopologyRetained': True, 'jaw':jaw,
        'sourceVertices':len(ps),'sourceFaces':len(faces),
        'distalToothExtentX_m':distal,'toothProtectedDistance_m':.0025,
        'toothProtectedVertices':len(locked),
        'toothProtectedMaximumDisplacement_m':max((distances[i] for i in locked),default=0),
        'changedVertices':sum(d>1e-9 for d in distances),
        'maximumDisplacement_m':max(distances,default=0),
        'acceptedDisplacementFactor':factor,'invertedSourceTriangles':0,
        'sourceBounds_m':[[min(p[a] for p in ps)for a in range(3)],[max(p[a] for p in ps)for a in range(3)]],
        'candidateBounds_m':[[min(p[a] for p in out)for a in range(3)],[max(p[a] for p in out)for a in range(3)]],
        'limitations':['Inferred local terminal shape; not retromolar clinical validation',
                      'Surface-distance locking does not prove every cervical contact',
                      'No topology change, new primitive or source relabeling'],
    }


def make_posterior_soft_palate(upper_gum_points, upper_gum_faces, *, nu=48, nv=48):
    """Closed posterior patch attached to real retained upper-gingival mucosa.

    The anterior authored hard plate is deliberately absent. Each anterior
    sample is an actual upward BVH hit, 1.5 mm inside the retained posterior
    mucosal footprint. A <=0.05-mm embedding makes a narrow attachment overlap;
    this is NOT a welded single tissue or a clinical mucosal registration.
    All free-edge dimensions and the uvular projection are inferred.
    """
    gum = _bvh(upper_gum_points, upper_gum_faces)
    width = .0185  # inferred, bounded inside source posterior dental arch
    anchors=[]; source_hits=[]; normals=[]; tangent_slopes=[]
    for j in range(nv+1):
        v=2*j/nv-1; z=width*v
        def upward(x):
            return gum.ray_cast(Vector((x,-.004,z)), Vector((0,1,0)),.050)
        # Detect actual source footprint; no nominal straight seam in X.
        samples=[-.062+i*.00025 for i in range(169)]
        found=next((x for x in samples if upward(x)[0] is not None),None)
        if found is None:
            raise RuntimeError('No source palatal mucosal footprint at z='+str(z))
        lo,hi=found-.00025,found
        for _ in range(15):
            m=(lo+hi)/2
            if upward(m)[0] is None:lo=m
            else:hi=m
        hit,normal,_,_=upward(hi+.0015)
        if hit is None or abs(normal.y)<.1:
            raise RuntimeError('Invalid attachment mucosa hit')
        # Embed just inside the closed source; quantify exact surface offset.
        anchor=hit-normal*.00005
        source_hits.append(tuple(hit));anchors.append(anchor);normals.append(normal)
        tangent_slopes.append(max(-.65,min(.65,-normal.x/normal.y)))
    cap_thickness=[]
    for p in anchors:
        exit_hit, _, _, distance = gum.ray_cast(p+Vector((0,.0001,0)),Vector((0,1,0)),.020)
        if exit_hit is None or distance < .0005:
            raise RuntimeError('No safe superior source thickness at attachment')
        cap_thickness.append(min(.002, distance+.0001-.00015))
    lower=[]
    for i in range(nu+1):
        u=i/nu
        for j in range(nv+1):
            v=2*j/nv-1; root=anchors[j]
            uvular=exp(-(v/.21)**2)
            xe=-.069+.0015*abs(v)**1.6-.0045*uvular
            ye=.011+.0015*abs(v)-.0095*uvular
            dx=xe-root.x
            x=root.x+dx*u
            # Cubic Hermite patch; derivative from the actual mucosal surface
            # at the attachment, one continuous descent to the free edge.
            m0=dx*tangent_slopes[j]
            m1=-.008-.007*uvular
            y=(2*u**3-3*u*u+1)*root.y+(u**3-2*u*u+u)*m0+(-2*u**3+3*u*u)*ye+(u**3-u*u)*m1
            z=root.z*(1-.12*_s(u))
            lower.append(Vector((x,y,z)))
    # A superior offset preserves the injective sagittal/transverse graph.
    # Normal extrusion folded at the narrow free uvular edge in the invalid
    # first construction; never silently accept that self intersection.
    upper=[]; normal_thickness=[]; row=nv+1
    for i in range(nu+1):
        for j in range(nv+1):
            p=lower[i*row+j]
            du=lower[min(i+1,nu)*row+j]-lower[max(i-1,0)*row+j]
            dv=lower[i*row+min(j+1,nv)]-lower[i*row+max(j-1,0)]
            n=du.cross(dv).normalized()
            if n.y<0:n=-n
            u=i/nu;v=2*j/nv-1
            desired=.0020+.0008*exp(-(v/.24)**4)*_s((u-.35)/.65)
            thickness=cap_thickness[j]+(desired-cap_thickness[j])*_s(u/.12)
            upper.append(p+Vector((0,thickness,0)))
            normal_thickness.append(thickness*abs(n.y))
    coords=lower+upper; count=len(lower);faces=[]
    for layer in range(2):
        off=layer*count
        for i in range(nu):
            for j in range(nv):
                a=off+i*row+j;face=(a,a+1,a+row+1,a+row)
                faces.append(face if layer==0 else face[::-1])
    perimeter=([j for j in range(row)]+[i*row+nv for i in range(1,nu+1)]+
               [nu*row+j for j in range(nv-1,-1,-1)]+[i*row for i in range(nu-1,0,-1)])
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append((a,b,count+b,count+a))
    gaps=[gum.find_nearest(p)[3] for p in anchors]
    return [tuple(v)for v in coords],faces,{
        'role':'Authored posterior soft-palate and integrated uvular tissue only',
        'anteriorContext':'Retained upper gingival source includes palatal mucosal surface; no hard-palatal bone claim',
        'attachmentMethod':'Actual upward BVH mucosal hits; 1.5-mm anterior overlap strip; 0.05-mm inward embedding',
        'attachmentSourcePoints_m':source_hits,'attachmentProposedPoints_m':[tuple(v)for v in anchors],
        'attachmentMaximumNearestSurfaceGap_m':max(gaps),
        'attachmentMeanNearestSurfaceGap_m':sum(gaps)/len(gaps),
        'singleWeldedTissue':False,'inferred':['free-edge shape','uvular extent','tissue thickness','transverse taper'],
        'thicknessMethod':'Superior graph offset, checked by local normal projection; no normal-offset fold',
        'minimumProjectedNormalThickness_m':min(normal_thickness),
        'uvulaIsSeparatePrimitive':False,'authoredAnteriorHardPlate':False,
        'deformationGrid':{'longitudinalSegments':nu,'transverseSegments':nv,'verticesPerLayer':count,'ordering':'lower grid row-major, then upper; u=(index%verticesPerLayer)//(nv+1)/nu'},
        'limitations':['Narrow intentional overlap is not a measured histological junction',
                      'Lateral pharyngeal pillars and nasal/pharyngeal closure are absent',
                      'New topology requires fresh velum morphs, UVs and contact checks'],
    }
