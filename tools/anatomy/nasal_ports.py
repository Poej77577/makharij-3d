"""Actual MakeHuman nostril ports, in project metres (+X front,+Y up,+Z right).

Pinned CC0 base topology. Delete only the two inner vestibular closing disks;
keep original source point positions, external alar rim, lip topology and UVs.
The resulting evaluated/subdivided boundary rings are authoritative for a
nasal continuation. Ring coordinates are artistic source data, not clinical
nostril measurements. No closed source cap is relabelled as a real airway.
"""
from collections import Counter, defaultdict
from math import sqrt

BASE_SHA256 = '8e761e6624b8f54536409135d1636da63b32486a90d4897f84e121d144f6fb4c'
CAP_VERTEX_SETS = {'nostril_right': set(range(381,399)),
                   'nostril_left': set(range(7141,7159))}


def _loops(edges):
    links=defaultdict(set)
    for a,b in edges:links[a].add(b);links[b].add(a)
    if any(len(v)!=2 for v in links.values()):
        raise ValueError('Boundary has branching/open chains')
    remaining=set(links);result=[]
    while remaining:
        first=min(remaining);loop=[first];prev=None;cur=first
        while True:
            nxt=min(v for v in links[cur] if v!=prev)
            if nxt==first:break
            if nxt in loop:raise ValueError('Invalid boundary cycle')
            loop.append(nxt);prev,cur=cur,nxt
        remaining.difference_update(loop);result.append(loop)
    return result


def _normal(points):
    n=[0.,0.,0.]
    for a,b in zip(points,points[1:]+points[:1]):
        n[0]+=a[1]*b[2]-a[2]*b[1]
        n[1]+=a[2]*b[0]-a[0]*b[2]
        n[2]+=a[0]*b[1]-a[1]*b[0]
    length=sqrt(sum(v*v for v in n))
    if length<1e-12:raise ValueError('Degenerate port ring')
    return [v/length for v in n]


def makehuman_nasal_cap_faces(head, points_project, source_base_sha256):
    if source_base_sha256!=BASE_SHA256:raise ValueError('Unverified MakeHuman base identity')
    removed=set();report={}
    for name,cap in CAP_VERTEX_SETS.items():
        ids=[fi for fi in head['groups']['body'] if set(head['faces'][fi])<=cap]
        if len(ids)!=11:raise ValueError(name+': expected original 11-quad blind disk')
        counts=Counter(tuple(sorted((a,b)))for fi in ids for a,b in zip(head['faces'][fi],head['faces'][fi][1:]+head['faces'][fi][:1]))
        loops=_loops([e for e,c in counts.items()if c==1])
        if len(loops)!=1 or len(loops[0])!=12:raise ValueError('Nostril cap disk boundary changed')
        ring=loops[0];removed.update(ids)
        report[name]={'removedSourceFaceIds':ids,'removedQuadCount':len(ids),
                      'sourceBoundaryVertexIds':ring,
                      'sourceRingPositions_m':[[float(q)for q in points_project[i]]for i in ring],
                      'retainedOriginalVestibularWall':True}
    return removed,{'enabled':True,'sourceBaseSha256':source_base_sha256,
                    'sourceCapsWereBlind':True,'sourcePositionsChanged':False,
                    'exteriorAndLipFacesDeleted':False,'ports':report}


def find_nasal_boundary_ports(points, faces, source_vertex_ids=None):
    """Find actual ring indices after geometry evaluation; no nominal anchors."""
    faces=[list(f)for f in faces]
    counts=Counter(tuple(sorted((a,b)))for f in faces for a,b in zip(f,f[1:]+f[:1]))
    loops=_loops([e for e,c in counts.items()if c==1]);ports=[]
    for ring in loops:
        q=[[float(v)for v in points[i]]for i in ring];center=[sum(p[a]for p in q)/len(q)for a in range(3)]
        if not(.003<center[0]<.025 and .020<center[1]<.038 and .003<abs(center[2])<.016):continue
        normal=_normal(q)
        if normal[1]<0:ring=ring[::-1];q=q[::-1];normal=[-v for v in normal]
        name='nostril_right' if center[2]>0 else 'nostril_left'
        port={'id':name,'name':name,'role':'inlet','center_m':center,
              'inward_normal':normal,'ring_vertex_positions_m':q,'ring_m':q,
              'face_vertex_ids':ring,'ringVertexCount':len(ring)}
        if source_vertex_ids is not None:port['source_vertex_ids']=[int(source_vertex_ids[i])for i in ring]
        ports.append(port)
    if ports and (len(ports)!=2 or len({p['id']for p in ports})!=2):
        raise ValueError('Expected exactly bilateral nostril boundaries')
    return sorted(ports,key=lambda p:p['id'])
