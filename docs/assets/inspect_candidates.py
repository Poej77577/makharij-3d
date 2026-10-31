from pathlib import Path
from collections import Counter
import json, math, hashlib
base=Path(__file__).resolve().parents[2]
files=[base/'assets/candidates/vtl-neutral.obj']
face=base/'assets/candidates/artisynth_models/src/artisynth/models/face/geometry'
files += [face/(s+'.obj') for s in ('badintongue','badinmaxilla','badinjaw','badinface_upperlip_filled','badinface_lowerlip_filled','badinairway','upperteeth','lowerteeth')]
out=[]
for p in files:
 vs=[]; fs=[];groups=[]
 for l in p.read_text().splitlines():
  a=l.split()
  if not a:continue
  if a[0]=='v':vs.append([float(v) for v in a[1:4]])
  elif a[0]=='f':fs.append([int(v.split('/')[0])-1 for v in a[1:]])
  elif a[0]=='g':groups.append(' '.join(a[1:]))
 edges=Counter(tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in fs for i in range(len(f)))
 triangles=[(f[0],f[i],f[i+1]) for f in fs for i in range(1,len(f)-1)]
 def area(t):
  a,b,c=[vs[i] for i in t];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
  cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
  return math.sqrt(sum(n*n for n in cross))/2
 out.append(dict(path=str(p.relative_to(base)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),vertices=len(vs),polygons=len(fs),triangles=len(triangles),bounds=[[min(v[i] for v in vs),max(v[i] for v in vs)]for i in range(3)],index_boundary_edges=sum(v==1 for v in edges.values()),index_nonmanifold_edges=sum(v>2 for v in edges.values()),degenerate_triangles=sum(area(t)<1e-12 for t in triangles),groups=groups))
(base/'docs/assets/candidate-inspection.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
