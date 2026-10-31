"""Authored 3-D nasal lining and conchae in the existing source frame (METERS).

This is an UNMEASURED educational reconstruction, NOT acquired nasal anatomy,
not a registered donor nose, not CFD, and not evidence of anatomical review.
The hard-palate surface anchors the floor; a ray into the actual posterior
pharyngeal surface anchors the open inferior connection. Roof, scroll geometry,
wall thickness and vestibule remain authored assumptions recorded in metadata.

Integration (coordinator owns build_rest.py and binaries):
    from nasal_lining import build_nasal_lining, SUGGESTED_COLORS
    # Add SUGGESTED_COLORS before constructing materials; remove the OLD oval's
    # alpha=.16 special case. These tissue walls should be opaque in section.
    # Remove the old oval NASAL_LINING loft. Then:
    nasal = build_nasal_lining(hard_palate=objects['HARD_PALATE'],
        pharynx=objects['PHARYNX'], face_bounds=objects['LIP_CONTEXT'], create=create)
    # Persist nasal['metadata']; attribute ALL name.startswith('NASAL_') parts
    # as authored, so the generic ArtiSynth source label cannot overwrite it.

create(name, vertices, triangles) uses the existing coordinator mesh constructor.
Inputs accept Blender mesh objects or {positions:[flat xyz],indices:[flat tris]}.
face_bounds can alternatively be {min:[x,y,z],max:[x,y,z]}. No Blender dependency
is needed for geometry generation; returned objects are optional callback results.
The lining is a CLOSED TISSUE shell with OPEN AIR PORTS (annular rims, no air
volume filler). Each concha is a closed, tapered, curved tissue lamella, not a
sphere/cylinder/plane. Bilateral geometry is retained. A septum is deliberately
not supplied by this module: midsagittal teaching views must state its omission.
"""
from collections import Counter
from math import sin, cos, pi, sqrt, isfinite, hypot

VERSION='authored-nasal-lining-v2'
SUGGESTED_COLORS={
    'NASAL_LINING':(.66,.49,.41,1),
    'NASAL_CONCHA_INFERIOR':(.68,.39,.35,1),
    'NASAL_CONCHA_MIDDLE':(.69,.42,.37,1),
    'NASAL_CONCHA_SUPERIOR':(.70,.45,.39,1),
}
WALL=.0012

def _add(a,b):return tuple(x+y for x,y in zip(a,b))
def _sub(a,b):return tuple(x-y for x,y in zip(a,b))
def _mul(a,s):return tuple(x*s for x in a)
def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _length(a):return sqrt(_dot(a,a))
def _unit(a):
    n=_length(a)
    if n<1e-12:raise ValueError('Zero tangent in nasal reconstruction')
    return _mul(a,1/n)
def _mix(a,b,t):return _add(_mul(a,1-t),_mul(b,t))
def _smooth(t):return t*t*(3-2*t)
def _q(values,t):
    a=sorted(values);x=t*(len(a)-1);i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)

def _source(value):
    if hasattr(value,'data') and hasattr(value.data,'vertices'):
        matrix=getattr(value,'matrix_world',None)
        points=[tuple(float(q)for q in (matrix@v.co if matrix is not None else v.co))for v in value.data.vertices]
        polygons=[list(f.vertices)for f in value.data.polygons]
    elif isinstance(value,dict) and 'positions' in value:
        raw=value['positions'];points=[tuple(map(float,raw[i:i+3]))for i in range(0,len(raw),3)]
        raw=value.get('indices',[]);polygons=[raw[i:i+3]for i in range(0,len(raw),3)]
    elif isinstance(value,dict) and 'min' in value and 'max' in value:
        lo,hi=value['min'],value['max']
        points=[(float(x),float(y),float(z))for x in [lo[0],hi[0]]for y in [lo[1],hi[1]]for z in [lo[2],hi[2]]];polygons=[]
    else:
        points=[tuple(map(float,p))for p in value];polygons=[]
    if not points or not all(len(p)==3 and all(isfinite(x)for x in p)for p in points):raise ValueError('Finite source coordinates in meters are required')
    triangles=[]
    for face in polygons:
        for j in range(1,len(face)-1):triangles.append((face[0],face[j],face[j+1]))
    bounds=([min(p[k]for p in points)for k in range(3)],[max(p[k]for p in points)for k in range(3)])
    return {'points':points,'triangles':triangles,'bounds':bounds}

def _closest_triangle(p,a,b,c):
    # Closest point on an actual source triangle, not a bounding-box distance.
    ab,ac,ap=_sub(b,a),_sub(c,a),_sub(p,a);d1,d2=_dot(ab,ap),_dot(ac,ap)
    if d1<=0 and d2<=0:return a
    bp=_sub(p,b);d3,d4=_dot(ab,bp),_dot(ac,bp)
    if d3>=0 and d4<=d3:return b
    vc=d1*d4-d3*d2
    if vc<=0 and d1>=0 and d3<=0:return _add(a,_mul(ab,d1/max(d1-d3,1e-30)))
    cp=_sub(p,c);d5,d6=_dot(ab,cp),_dot(ac,cp)
    if d6>=0 and d5<=d6:return c
    vb=d5*d2-d1*d6
    if vb<=0 and d2>=0 and d6<=0:return _add(a,_mul(ac,d2/max(d2-d6,1e-30)))
    va=d3*d6-d5*d4
    if va<=0 and d4-d3>=0 and d5-d6>=0:
        return _add(b,_mul(_sub(c,b),(d4-d3)/max(d4-d3+d5-d6,1e-30)))
    total=va+vb+vc
    if abs(total)<1e-30:return min([a,b,c],key=lambda v:_length(_sub(v,p)))
    return _add(a,_add(_mul(ab,vb/total),_mul(ac,vc/total)))

def _source_distance(p,source):
    points=source['points'];best=None;distance=float('inf')
    if source['triangles']:
        for f in source['triangles']:
            a,b,c=[points[i]for i in f]
            if _length(_cross(_sub(b,a),_sub(c,a)))<1e-15:continue
            q=_closest_triangle(p,a,b,c);d=_length(_sub(q,p))
            if d<distance:distance,best=d,q
        method='actual source triangle'
    else:
        best=min(points,key=lambda v:_length(_sub(v,p)));distance=_length(_sub(best,p));method='nearest supplied source point (no triangles provided)'
    return {'distance_m':distance,'nearestSourcePoint_m':best,'method':method}

def _posterior_wall(source,y):
    # +X ray from behind the source: first surface is the posterior wall, if hit.
    points=source['points'];origin=(source['bounds'][0][0]-.020,y,0);direction=(1,0,0);hits=[]
    for fi,f in enumerate(source['triangles']):
        a,b,c=[points[i]for i in f];e1,e2=_sub(b,a),_sub(c,a);h=_cross(direction,e2);det=_dot(e1,h)
        if abs(det)<1e-12:continue
        inv=1/det;s=_sub(origin,a);u=inv*_dot(s,h)
        if u<0 or u>1:continue
        q=_cross(s,e1);v=inv*_dot(direction,q)
        if v<0 or u+v>1:continue
        t=inv*_dot(e2,q)
        if t>0:hits.append((t,_add(origin,_mul(direction,t)),fi))
    if hits:
        _,p,face=min(hits);return p,{'method':'+X ray into actual source pharyngeal surface','triangle':face}
    p=(source['bounds'][0][0],y,0)
    return p,{'method':'bounds fallback; posterior source surface intersection NOT established','triangle':None}

def _chaikin(points,iterations=2):
    for unused in range(iterations):
        result=[]
        for i,a in enumerate(points):
            b=points[(i+1)%len(points)];result.extend([_mix(a,b,.25),_mix(a,b,.75)])
        points=result
    return points

# (z fraction, height fraction). Flat floor, vaulted roof, steep lateral walls.
# Corner cutting preserves convexity and does not create a puffy ellipsoidal blob.
OUTLINE=_chaikin([(-.80,0),(.80,0),(1,.15),(1,.55),(.75,.85),(.35,.98),(0,1),(-.35,.98),(-.75,.85),(-1,.55),(-1,.15)])

def _wall_fraction(height):
    candidates=[]
    for i,(z,y) in enumerate(OUTLINE):
        zz,yy=OUTLINE[(i+1)%len(OUTLINE)]
        if min(y,yy)<=height<=max(y,yy) and abs(yy-y)>1e-12:
            candidates.append(z+(zz-z)*(height-y)/(yy-y))
    if not candidates:raise ValueError('Concha attachment lies outside authored wall')
    return max(candidates)

def _orient_check(name,vertices,faces):
    if not all(all(isfinite(x)for x in p)for p in vertices):raise ValueError(name+': nonfinite geometry')
    edges=Counter();directions=Counter();area=float('inf');volume=0.;seen=set()
    for f in faces:
        if len(set(f))!=3:raise ValueError(name+': repeated triangle index')
        key=tuple(sorted(f))
        if key in seen:raise ValueError(name+': duplicate triangle')
        seen.add(key);a,b,c=[vertices[i]for i in f];twice=_length(_cross(_sub(b,a),_sub(c,a)))
        if twice<1e-13:raise ValueError(name+': degenerate triangle')
        area=min(area,twice*.5);volume+=_dot(a,_cross(b,c))/6
        for i in range(3):
            edge=tuple(sorted((f[i],f[(i+1)%3])));edges[edge]+=1;directions[edge]+=1 if f[i]<f[(i+1)%3] else -1
    bad=sum(v!=2 for v in edges.values())
    if bad:raise ValueError(f'{name}: tissue shell has {bad} nonmanifold/boundary edges')
    if any(directions.values()):raise ValueError(name+': inconsistent adjacent triangle winding')
    if abs(volume)<1e-10:raise ValueError(name+': no meaningful tissue volume')
    if volume<0:faces=[(a,c,b)for a,b,c in faces];volume=-volume
    return vertices,faces,{'vertices':len(vertices),'triangles':len(faces),'minimumTriangleArea_m2':area,'closedTissueVolume_m3':volume,'nonmanifoldEdges':bad,'consistentWinding':True}

def _palatal_y(source,x,z):
    # A vertical intersection with the supplied oral roof (not a nearest-bound
    # proxy). Outside its acquired coverage no measured support is invented.
    values=[];points=source['points']
    for f in source['triangles']:
        a,b,c=[points[i]for i in f]
        if x<min(a[0],b[0],c[0])-1e-9 or x>max(a[0],b[0],c[0])+1e-9 or z<min(a[2],b[2],c[2])-1e-9 or z>max(a[2],b[2],c[2])+1e-9:continue
        bx,bz=b[0]-a[0],b[2]-a[2];cx,cz=c[0]-a[0],c[2]-a[2];det=bx*cz-bz*cx
        if abs(det)<1e-14:continue
        u=((x-a[0])*cz-(z-a[2])*cx)/det;v=(bx*(z-a[2])-bz*(x-a[0]))/det
        if u>=-1e-7 and v>=-1e-7 and u+v<=1+1e-7:values.append(a[1]+u*(b[1]-a[1])+v*(c[1]-a[1]))
    return max(values)if values else None

def _floor_outer(c,n,h,palate):
    inner=_sub(c,_mul(n,h));outer=_sub(c,_mul(n,h+WALL));source_y=_palatal_y(palate,outer[0],outer[2])
    if n[1]>.85 and source_y is not None and source_y+.00080<inner[1]-.00060:
        outer=(outer[0],source_y+.00080,outer[2])
    return inner,outer,source_y

def _lining(stations,palate):
    count=len(OUTLINE);vertices=[];faces=[]
    for c,n,h,w in stations:
        cross=[((yy-.5)*2*h,zz*w)for zz,yy in OUTLINE]
        for outer in [False,True]:
            for j,(v,z) in enumerate(cross):
                prev,next_=cross[(j-1)%count],cross[(j+1)%count];dy,dz=next_[0]-prev[0],next_[1]-prev[1];ln=hypot(dy,dz)
                if ln<1e-12:raise ValueError('Zero nasal wall tangent')
                # Outward from air into tissue. No surface spans the empty air lumen.
                vv=v+(-dz/ln*WALL if outer else 0);zz=z+(dy/ln*WALL if outer else 0)
                point=_add(c,_add(_mul(n,vv),(0,0,zz)))
                if outer and n[1]>.85 and OUTLINE[j][1]<.22:
                    source_y=_palatal_y(palate,point[0],point[2]);inner_point=_add(c,_add(_mul(n,v),(0,0,z)))
                    if source_y is not None and source_y+.00080<inner_point[1]-.00060:
                        blend=_smooth(max(0,1-OUTLINE[j][1]/.22));point=(point[0],point[1]+blend*(source_y+.00080-point[1]),point[2])
                vertices.append(point)
    def at(i,j,outer=False):return i*2*count+(count if outer else 0)+j%count
    border_counts=Counter();border_directions={}
    for i in range(len(stations)-1):
        for j in range(count):
            height_fraction=(OUTLINE[j][1]+OUTLINE[(j+1)%count][1])*.5
            # Below/behind the choana the acquired soft palate is the moving
            # anterior wall. Do NOT put a fixed tube wall across that organ.
            if i<14 and height_fraction<.52:continue
            a,b,c,d=at(i,j),at(i,j+1),at(i+1,j+1),at(i+1,j)
            faces.extend([(a,b,c),(a,c,d)])
            for aa,bb in [(a,b),(b,c),(c,d),(d,a)]:
                key=tuple(sorted((aa,bb)));border_counts[key]+=1;border_directions[key]=(aa,bb)
            a,b,c,d=at(i,j,True),at(i+1,j,True),at(i+1,j+1,True),at(i,j+1,True);faces.extend([(a,b,c),(a,c,d)])
    for key,n in border_counts.items():
        if n!=1:continue
        a,b=border_directions[key];ao,bo=a+count,b+count
        faces.extend([(b,a,ao),(b,ao,bo)])
    # The skipped window has no unused vertices in the delivered mesh, avoiding
    # GLB/source parity changes when an exporter drops unreferenced points.
    used=sorted({i for f in faces for i in f});remap={v:i for i,v in enumerate(used)}
    vertices=[vertices[i]for i in used];faces=[tuple(remap[i]for i in f)for f in faces]
    vertices,faces,check=_orient_check('NASAL_LINING',vertices,faces)
    check.update({'posteriorOpenAnterior':True,'fixedAnteriorDuctWall':False,'movingAnteriorBoundary':'existing acquired SOFT_PALATE, not the authored lining','windowEndStation':14})
    return vertices,faces,check


def _open_curve(points,count):
    # Corner-cutting stays within the authored control polygon; unlike an
    # interpolating spline it cannot overshoot into a tight scroll loop.
    for unused in range(3):
        out=[points[0]]
        for a,b in zip(points,points[1:]):out.extend([_mix(a,b,.25),_mix(a,b,.75)])
        points=out+[points[-1]]
    lengths=[0.]
    for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+_length(_sub(b,a)))
    result=[];j=0
    for k in range(count):
        d=lengths[-1]*k/(count-1)
        while j+1<len(lengths)-1 and lengths[j+1]<d:j+=1
        t=(d-lengths[j])/max(lengths[j+1]-lengths[j],1e-20);result.append(_mix(points[j],points[j+1],t))
    return result

def _crosses(a,b,c,d):
    def side(p,q,r):return(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return side(a,b,c)*side(a,b,d)<-1e-22 and side(c,d,a)*side(c,d,b)<-1e-22

def _simple_band(plus,minus):
    ring=plus+minus[::-1];count=len(ring)
    for i in range(count):
        for j in range(i+1,count):
            if j==i+1 or(i==0 and j==count-1):continue
            if _crosses(ring[i],ring[(i+1)%count],ring[j],ring[(j+1)%count]):return False
    return True

SCROLLS={
    'INFERIOR':{'curve':[(1,.48),(.90,.48),(.72,.44),(.53,.35),(.47,.23),(.56,.16),(.67,.18)],'interval':(.05,.95),'thickness':.0016,'stations':23},
    'MIDDLE':{'curve':[(1,.88),(.90,.86),(.71,.81),(.48,.72),(.40,.63),(.50,.58),(.65,.60)],'interval':(.12,.82),'thickness':.0012,'stations':21},
    'SUPERIOR':{'curve':[(1,.975),(.92,.965),(.72,.94),(.45,.895),(.32,.85),(.42,.815),(.60,.825)],'interval':(.08,.52),'thickness':.00065,'stations':17},
}

def _concha(kind,profile):
    settings=SCROLLS[kind];curve=settings['curve'];a,b=settings['interval'];long_count=settings['stations'];across=25;vertices=[];faces=[];minimum_thickness=float('inf');sections_checked=0
    wall_z=_wall_fraction(curve[0][1]);template=_open_curve(curve,across)
    for side in [-1,1]:
        offset=len(vertices)
        for i in range(long_count):
            s=i/(long_count-1);u=a+(b-a)*s;c,n,h,w=profile(u);height=2*h;taper=.12+.88*sin(pi*s)**.7
            attach=(height*(curve[0][1]-.5),w*wall_z+.00010)  # .1 mm intentional tissue attachment into lining.
            center=[]
            for zf,yf in template:
                target=(height*(yf-.5),w*zf*wall_z)
                center.append((attach[0]+taper*(target[0]-attach[0]),attach[1]+taper*(target[1]-attach[1])))
            plus=[];minus=[]
            for j,p in enumerate(center):
                before,after=center[max(0,j-1)],center[min(across-1,j+1)];dy,dz=after[0]-before[0],after[1]-before[1];length=hypot(dy,dz)
                if length<1e-12:raise ValueError(kind+': zero scroll tangent')
                full=settings['thickness']*taper*(.8+.2*sin(pi*j/(across-1)))
                if 0<j<across-1:
                    A,B,C=center[j-1],center[j],center[j+1];ab=_length(_sub(B,A));bc=_length(_sub(C,B));ac=_length(_sub(C,A));area2=abs((B[0]-A[0])*(C[1]-A[1])-(B[1]-A[1])*(C[0]-A[0]))
                    if area2>1e-18:full=min(full,.55*ab*bc*ac/(2*area2))
                minimum_thickness=min(minimum_thickness,full)
                delta=(-dz/length*full*.5,dy/length*full*.5)
                plus.append((p[0]+delta[0],p[1]+delta[1]));minus.append((p[0]-delta[0],p[1]-delta[1]))
            if not _simple_band(plus,minus):raise ValueError(kind+': self-crossing lamella section; reduce thickness/curvature')
            sections_checked+=1
            for sheet in [plus,minus]:
                for yy,zz in sheet:vertices.append(_add(c,_add(_mul(n,yy),(0,0,side*zz))))
        def at(i,j,minus=False):return offset+i*2*across+(across if minus else 0)+j
        for i in range(long_count-1):
            for j in range(across-1):
                aa,bb,cc,dd=at(i,j),at(i+1,j),at(i+1,j+1),at(i,j+1);faces.extend([(aa,bb,cc),(aa,cc,dd)])
                aa,bb,cc,dd=at(i,j,True),at(i,j+1,True),at(i+1,j+1,True),at(i+1,j,True);faces.extend([(aa,bb,cc),(aa,cc,dd)])
            for j,reverse in [(0,False),(across-1,True)]:
                aa,bb,cc,dd=at(i,j),at(i,j,True),at(i+1,j,True),at(i+1,j)
                if reverse:aa,bb,cc,dd=dd,cc,bb,aa
                faces.extend([(aa,bb,cc),(aa,cc,dd)])
        # Close the curved ribbon end by LOCAL thickness quads; a centroid fan
        # across a concave C-section would incorrectly fill the meatus.
        for i,reverse in [(0,False),(long_count-1,True)]:
            for j in range(across-1):
                aa,bb,cc,dd=at(i,j),at(i,j+1),at(i,j+1,True),at(i,j,True)
                if reverse:aa,bb,cc,dd=dd,cc,bb,aa
                faces.extend([(aa,bb,cc),(aa,cc,dd)])
    name='NASAL_CONCHA_'+kind
    # Left and right are disconnected tissue volumes: each component must be
    # oriented separately because mirroring reverses triangle winding.
    halfv=len(vertices)//2;halff=len(faces)//2
    leftv,leftf,leftcheck=_orient_check(name+' LEFT',vertices[:halfv],faces[:halff])
    rightfaces=[tuple(i-halfv for i in f)for f in faces[halff:]]
    rightv,rightf,rightcheck=_orient_check(name+' RIGHT',vertices[halfv:],rightfaces)
    faces=leftf+[tuple(i+halfv for i in f)for f in rightf]
    return vertices,faces,{'left':leftcheck,'right':rightcheck,'minimumFullThickness_m':minimum_thickness,'nominalCentralFullThickness_m':settings['thickness'],'planarSectionsChecked':sections_checked,'allSectionsSimple':True,'attachmentOverlap_m':.00010,'source':'authored tapered scroll, not acquired turbinates','intervalOfNasalBody':list(settings['interval'])}

def build_nasal_lining(*,hard_palate,pharynx,face_bounds,create,include_superior=True):
    palate=_source(hard_palate);ph=_source(pharynx);face=_source(face_bounds)
    plo,phi=palate['bounds'];flo,fhi=face['bounds'];p_span=phi[0]-plo[0];p_width=phi[2]-plo[2]
    if not .020<p_span<.150 or not .020<p_width<.120:raise ValueError('Expected human palate coordinates in METERS in the frozen X-anterior/Y-up/Z-lateral frame')
    portal_y=min(ph['bounds'][1][1]-.002,.020)
    wall_anchor,wall_method=_posterior_wall(ph,portal_y);posterior_x=wall_anchor[0]+.0058
    rear_x=max(plo[0]+.010,posterior_x+.016)
    front_x=min(phi[0]+.014,fhi[0]-.012);exit_x=max(front_x+.014,fhi[0]-.003)
    if front_x-rear_x<.030 or exit_x-front_x>.045:raise ValueError('Source bounds cannot support the authored nasal body without reauthoring')
    midline=[p for p in palate['points']if abs(p[2])<p_width*.22]or palate['points'];max_roof=_q([p[1]for p in midline],.99)
    def oral_roof(x):
        samples=[p[1]for p in midline if abs(p[0]-x)<p_span*.18]
        if not samples:samples=[p[1]for p in sorted(midline,key=lambda p:abs(p[0]-x))[:16]]
        return _q(samples,.98)
    floor_rear=max(oral_roof(rear_x)+.0035,max_roof+.0025)
    floor_middle=max(oral_roof((rear_x+front_x)*.5)+.0035,max_roof+.0035)
    floor_front=max(oral_roof(phi[0])+.0040,floor_rear-.0065)
    width=max(.011,min(.017,p_width*.27));body_length=front_x-rear_x
    def profile(u):
        floor=(1-u)**2*floor_rear+2*u*(1-u)*floor_middle+u*u*floor_front
        height=.028*(1-.20*_smooth(u))+.002*sin(pi*u)**2
        width_here=width*(.86+.12*sin(pi*u)-.30*_smooth(u))
        df=2*((1-u)*(floor_middle-floor_rear)+u*(floor_front-floor_middle))
        dh=-.028*.20*6*u*(1-u)+.004*pi*sin(pi*u)*cos(pi*u)
        slope=(df+dh*.5)/body_length;n=_unit((-slope,1,0))
        flare=.60+.40*_smooth(min(1,u/.25))
        return((rear_x+body_length*u,floor+height*.5,0),n,height*.5*flare,width_here)
    rear,n0,h0,w0=profile(0);radius=rear_x-posterior_x;arc_start_y=rear[1]-radius
    if radius<h0+WALL+.004:raise ValueError('Posterior bend radius would fold the authored nasal wall')
    if portal_y>=arc_start_y-.003:
        portal_y=arc_start_y-.008;wall_anchor,wall_method=_posterior_wall(ph,portal_y)
        # Keep the planned tangent path; record its ACTUAL surface distance below.
    stations=[]
    for i in range(4):
        t=i/3;stations.append(((posterior_x,portal_y+(arc_start_y-portal_y)*t,0),(-1,0,0),.0048+.0012*t,.010))
    for i in range(1,11):
        t=i/10;theta=pi-pi*.5*t;c=(rear_x+radius*cos(theta),arc_start_y+radius*sin(theta),0);n=(cos(theta),sin(theta),0)
        stations.append((c,n,.006+(h0-.006)*_smooth(t),.010+(w0-.010)*_smooth(t)))
    for i in range(1,29):stations.append(profile(i/28))
    start,nstart,hstart,wstart=profile(1);end=(exit_x,floor_front+.006,0);distance=exit_x-front_x
    tangent_start=(nstart[1],-nstart[0],0);tangent_end=_unit((1,-.08,0));c1=_add(start,_mul(tangent_start,distance/3));c2=_sub(end,_mul(tangent_end,distance/3))
    for i in range(1,9):
        t=i/8;s=1-t;c=_add(_add(_mul(start,s**3),_mul(c1,3*s*s*t)),_add(_mul(c2,3*s*t*t),_mul(end,t**3)))
        tangent=_add(_add(_mul(_sub(c1,start),3*s*s),_mul(_sub(c2,c1),6*s*t)),_mul(_sub(end,c2),3*t*t));tangent=_unit(tangent);n=(-tangent[1],tangent[0],0)
        stations.append((c,n,hstart+(.0046-hstart)*_smooth(t),wstart+(.0058-wstart)*_smooth(t)))
    made={};checks={}
    vertices,faces,check=_lining(stations,palate);made['NASAL_LINING']=create('NASAL_LINING',vertices,faces);checks['NASAL_LINING']=check
    for kind in ['INFERIOR','MIDDLE']+(['SUPERIOR']if include_superior else[]):
        vertices,faces,check=_concha(kind,profile);name='NASAL_CONCHA_'+kind;made[name]=create(name,vertices,faces);checks[name]=check
    for name,ob in made.items():
        if hasattr(ob,'data')and hasattr(ob.data,'polygons'):
            for f in ob.data.polygons:f.use_smooth=True
        try:
            ob['partId']=name;ob['metersPerUnit']=1.;ob['source']='AUTHORED UNMEASURED nasal reconstruction, not acquired donor anatomy';ob['assetVersion']=VERSION
        except(TypeError,AttributeError):pass
    floor_anchors=[]
    last_supported=max(.1,min(1,(phi[0]-.003-rear_x)/body_length))
    first_supported=1/28
    for u in [first_supported+(last_supported-first_supported)*k/4 for k in range(5)]:
        c,n,h,w=profile(u);inner,outer,source_y=_floor_outer(c,n,h,palate)
        floor_anchors.append({'bodyFraction':u,'innerFloor_m':inner,'outerWall_m':outer,'verticalSourceRoofHitY_m':source_y,'sourceCoverage':source_y is not None,'actualHardPalateSurfaceDistance':_source_distance(outer,palate)})
    posterior_outer=(posterior_x-.0048-WALL,portal_y,0)
    ca,na,ha,wa=profile(1);ai,ao,ay=_floor_outer(ca,na,ha,palate)
    anterior_floor={'inner_m':ai,'outer_m':ao,'sourceCoverage':ay is not None,'sourceDistance':_source_distance(ao,palate),'meaning':'anterior extension/vestibule beyond acquired palatal coverage remains authored; not a measured palate connection'}
    metadata={'version':VERSION,'units':'m','axes':{'X':'anterior','Y':'superior','Z':'lateral'},'sourceStatus':'AUTHORED UNMEASURED reconstruction from oral/face frame; no acquired nasal donor surface','clinicalOrTajwidApproval':False,'nominalWallThickness_m':WALL,'palatalFloorLayer':'outer floor is source-conforming 0.8mm above actual oral roof wherever its vertical triangle intersection exists; variable authored separator thickness, no acquired bone claim','palatalSeparator_m':{'rear':floor_rear,'middle':floor_middle,'front':floor_front},'sourceBounds_m':{'hardPalate':palate['bounds'],'pharynx':ph['bounds'],'face':face['bounds']},'anchors':{'palateFloor':floor_anchors,'anteriorFloorExtension':anterior_floor,'posteriorSourceWall':{'point_m':wall_anchor,**wall_method},'posteriorOuterLining_m':posterior_outer,'posteriorConnectionDistance':_source_distance(posterior_outer,ph),'posteriorOpenPortCenter_m':stations[0][0],'anteriorVestibuleOpenPortCenter_m':end,'nasalBodyRear_m':rear,'nasalBodyFront_m':start},'formulas':{'floor':'quadratic Bezier from actual midline palatal roof quantiles + authored 2.5–4mm separator; anterior floor at least rear-6.5mm','airHeight_m':'reference H=.028*(1-.20*smoothstep(u))+.002*sin(pi*u)^2; posterior choana flares from .60*H to H during first25% of body; center follows reference H','halfWidth_m':'min(.017,.27*sourcePalateWidth)*(.86+.12*sin(pi*u)-.30*smoothstep(u))','posterior':'superior pharyngeal open port, AP half-height4.8mm; posterior and side tissue only through the bend, anterior/floor C-window leaves existing SOFT_PALATE as the moving wall; fixed full floor starts anterior to the bend over hard palate; source apposition measured below','vestibule':'cubic Bezier tangent transition, open air port behind anterior source face bound','conchae':'closed curved scroll ribbons, bilateral, tapered to12% at longitudinal ends; local thickness caps, no centroid fan across C-shaped meatus'},'checks':checks,'limits':['Roof, vestibule, conchae and wall thickness are authored assumptions, not measurements. Tapered concha tips are very thin; retain float32 positions or validate any quantized export against minimumFullThickness_m.','Septum omitted for the teaching cutaway; no claim of complete bilateral nasal anatomy.','Posterior source apposition is reported quantitatively, not assumed a measured registration. The open-anterior transition deliberately leaves the acquired velum as its moving anterior wall.','Concha root intentionally embeds .1mm in lining for tissue attachment; this is not an independent donor fit.','Finite topology/section checks do not replace global intersections, final GLB checks or qualified anatomical review.']}
    return {'objects':made,'metadata':metadata}
