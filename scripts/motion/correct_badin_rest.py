"""Conservative cross-sectional fitting to *isolated tooth crowns*, not scan casts.

Run only AFTER B has removed dental plaster/root support spanning the arch.
Blender -b --python this.py -- --input rest.json --output /tmp/rest-refit.json

The source tongue/lips are retained. Coordinates are warped monotonically along
rays from the dental arch's interior. This differs from independently pushing
vertices along unreliable nearest-face normals of open crown meshes. The helper
rejects large displacements, reversed triangles and local collapses; it still
requires independent exact triangle-contact/visual checks. No clinical claim.
"""
import argparse, json, pathlib, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARCH_X=.020
MAX_R=.15
MARGIN=.00040

def mesh_arrays(part):
    return np.array(part['positions'],float).reshape(-1,3),np.array(part['indices'],int).reshape(-1,3)
def bvh_mesh(p,f):return BVHTree.FromPolygons([tuple(v)for v in p],[tuple(t)for t in f],all_triangles=True)
def hits(bvh,y,angle):
    direction=Vector((math.cos(angle),0,math.sin(angle)))
    origin=Vector((ARCH_X,y,0)); distances=[]; travelled=0.
    for unused in range(24):
        p,n,face,d=bvh.ray_cast(origin,direction,MAX_R-travelled)
        if p is None or d is None:break
        distance=travelled+d
        if distance>MAX_R:break
        distances.append(distance)
        travelled=distance+.000005;origin=Vector((ARCH_X,y,0))+direction*travelled
    return distances

def fit_radial(name,p,f,obstacles,mode):
    own=bvh_mesh(p,f);q=p.copy();changed=0;cache={}
    for i,(x,y,z) in enumerate(p):
        dx=x-ARCH_X;r=math.hypot(dx,z)
        if r<.0001:continue
        angle=math.atan2(z,dx)
        # Exact profiles; surrounding rays bridge small crown sampling gaps.
        dental=[]
        for obstacle in obstacles:
            for dy,da in [(0,0),(-.0003,0),(.0003,0),(0,-.008),(0,.008)]:
                dental.extend(hits(obstacle,y+dy,angle+da))
        tissue=hits(own,y,angle)
        if not dental or not tissue:continue
        inner=min(tissue);outer=max(tissue)
        if mode=='inside':
            allowed=min(dental)-MARGIN
            if outer<=allowed or allowed<=.002:continue
            scale=allowed/max(outer,1e-9)
            rr=r*scale
        else:
            boundary=max(dental)+MARGIN
            if inner>=boundary or outer-inner<.00005:continue
            new_outer=max(outer,boundary+.0008)
            rr=boundary+(r-inner)*(new_outer-boundary)/(outer-inner)
        if abs(rr-r)>.00001:
            q[i,0]=ARCH_X+dx*rr/r;q[i,2]=z*rr/r;changed+=1
    return q,changed

def validate(name,old,new,faces,limit):
    d=np.linalg.norm(new-old,axis=1)
    oldn=np.cross(old[faces[:,1]]-old[faces[:,0]],old[faces[:,2]]-old[faces[:,0]])
    newn=np.cross(new[faces[:,1]]-new[faces[:,0]],new[faces[:,2]]-new[faces[:,0]])
    oldarea=np.linalg.norm(oldn,axis=1);newarea=np.linalg.norm(newn,axis=1)
    valid=oldarea>1e-14
    reversed_count=int(np.sum((np.sum(oldn*newn,axis=1)<=0)&valid))
    collapsed=int(np.sum((newarea<oldarea*.03)&valid))
    report={'part':name,'max_displacement_mm':float(d.max()*1000),'mean_displacement_mm':float(d.mean()*1000),'p95_displacement_mm':float(np.quantile(d,.95)*1000),'reversed_triangles':reversed_count,'collapsed_triangles':collapsed,'limit_mm':limit*1000,'accepted':bool(d.max()<=limit and not reversed_count and not collapsed)}
    return report

def main():
    global MARGIN
    argv=sys.argv[sys.argv.index('--')+1:]if'--'in sys.argv else[]
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);parser.add_argument('--max-tongue-mm',type=float,default=3);parser.add_argument('--max-lip-mm',type=float,default=4);parser.add_argument('--parts',nargs='+',default=['UPPER_LIP','LOWER_LIP'],choices=['TONGUE','UPPER_LIP','LOWER_LIP']);parser.add_argument('--margin-mm',type=float,default=.4)
    args=parser.parse_args(argv);MARGIN=args.margin_mm*.001;data=json.loads(pathlib.Path(args.input).read_text());assert data.get('units')=='m'
    parts=data['parts'];arrays={k:mesh_arrays(v)for k,v in parts.items()}
    obstacles={k:bvh_mesh(*arrays[k])for k in ['UPPER_TEETH','LOWER_TEETH']if k in arrays}
    # Guard against a dental support/cast floor being silently treated as crowns.
    if 'LOWER_TEETH'in arrays:
        p,f=arrays['LOWER_TEETH'];suspect=np.sum((abs(p[:,2])<.008)&(p[:,0]<.070)&(p[:,0]>.027)&(p[:,1]<-.012))
        if suspect>50:raise ValueError(f'Lower dental cast-floor guard: {suspect} central support vertices. Isolate crowns first; do not fit tongue around scan base.')
    report={'method':'monotone radial crown envelope refit','archOrigin_m':[ARCH_X,0,0],'margin_m':MARGIN,'source':args.input,'changes':[],'isFullCollisionApproval':False}
    for name,mode in [('TONGUE','inside'),('UPPER_LIP','outside'),('LOWER_LIP','outside')]:
        if name not in arrays or name not in args.parts:continue
        p,f=arrays[name];new,count=fit_radial(name,p,f,list(obstacles.values()),mode)
        row=validate(name,p,new,f,args.max_tongue_mm*.001 if name=='TONGUE'else args.max_lip_mm*.001);row['moved_vertices']=count;report['changes'].append(row)
        parts[name]['positions']=new.reshape(-1).round(9).tolist()
    report['accepted']=all(r['accepted']for r in report['changes'])
    data['restRefit']=report
    output=pathlib.Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(data,separators=(',',':')))
    output.with_suffix('.report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not report['accepted']:raise SystemExit('Rejected: movement cap or local orientation/collapse test failed; do not integrate output.')
if __name__=='__main__':main()
