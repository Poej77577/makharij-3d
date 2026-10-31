"""Sample localized controls on inspected Badin meshes (Blender Python).

Source anatomy is never generated here. Input is the prepared canonical-meter
mesh from Agent B. Deformations are artistic surface controls, not muscle/FEM
simulation. BVH segment clipping is a preventative constraint, not a proof of
absence of triangle intersection; Agent F separately checks delivered samples.

blender -b --python scripts/motion/build_badin_motion.py -- --rest ... --out data/motion
"""
import argparse, json, math, pathlib, sys, hashlib
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TIMES=[0,.08,.16,.24,.32,.38,.40,.42,.46,.54,.62,.70,.78,.86,.94,1]
DURATIONS={'ra':3.2,'qaf':4.2,'mim':4.6,'fa':4.2,'ayn':4.6}
ACTIVE=['TONGUE','UPPER_LIP','LOWER_LIP','SOFT_PALATE','LOWER_TEETH']
CLEARANCE=.00020

def smooth(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)
def envelope(t,start,onset,release,end):
    return float(smooth((t-start)/(onset-start))) if t<onset else 1. if t<release else 1.-float(smooth((t-release)/(end-release)))
def activation(id,t):
    if id=='ra': return envelope(t,.12,.40,.42,.70)
    if id=='mim': return envelope(t,.16,.40,.70,.86)
    if id=='qaf': return envelope(t,.12,.38,.54,.86)
    return envelope(t,.12,.38,.70,.86)
def weights(p):
    x,y,z=p.T
    return {
      'tip':np.exp(-((x-.080)/.012)**2-((y+.001)/.020)**2),
      'blade':np.exp(-((x-.067)/.015)**2-((y-.003)/.024)**2),
      'dorsum':np.exp(-((x-.041)/.019)**2-((y-.006)/.023)**2),
      'root':np.exp(-((x-.019)/.018)**2-((y+.010)/.030)**2),
      'posteriorDorsum':np.exp(-((x-.028)/.016)**2-((y-.004)/.023)**2),
      'edges':np.exp(-((x-.058)/.030)**2)*smooth((np.abs(z)-.008)/.010),
      'groove':np.exp(-((x-.058)/.027)**2-(z/.008)**2),
    }

def topology(mesh):
    p=np.asarray(mesh['positions'],dtype=float).reshape(-1,3)
    f=np.asarray(mesh['indices'],dtype=int).reshape(-1,3)
    return p,f

def clip_to_obstacles(original,target,bvhs,clearance=CLEARANCE):
    result=target.copy(); clipped=0
    for i,(p,q) in enumerate(zip(original,target)):
      delta=q-p;length=float(np.linalg.norm(delta))
      if length<1e-9: continue
      direction=delta/length; allowed=length
      for bvh in bvhs:
        hit,normal,index,distance=bvh.ray_cast(Vector(p),Vector(direction),length+clearance)
        if hit is not None and distance is not None and distance>=0:
          allowed=min(allowed,max(0.,distance-clearance))
      if allowed<length:
        result[i]=p+direction*allowed;clipped+=1
    return result,clipped

def state(id,t,base,bvhs,velum_delta=None):
    amount=activation(id,t); result={n:p.copy() for n,(p,f) in base.items()}; report={}
    if 'TONGUE' in result:
      p=base['TONGUE'][0]; q=p.copy();w=weights(p)
      if id=='ra':
        q[:,1]+=amount*(.015*w['tip']+.0025*w['blade']);q[:,0]+=amount*.0008*w['tip']
      elif id=='qaf':
        q[:,1]+=amount*(.014*w['posteriorDorsum']+.002*w['root']);q[:,0]-=amount*.0015*w['posteriorDorsum']
      elif id=='ayn':
        q[:,0]-=amount*.006*w['root'];q[:,1]-=amount*.001*w['root']
      q,count=clip_to_obstacles(p,q,[bvhs[n] for n in ['UPPER_TEETH','LOWER_TEETH','HARD_PALATE','SOFT_PALATE','PHARYNX'] if n in bvhs]);result['TONGUE']=q;report['TONGUE_clipped_vertices']=count
    for name in ['UPPER_LIP','LOWER_LIP']:
      if name not in result:continue
      p=base[name][0];q=p.copy();x,y,z=p.T
      lateral=np.exp(-(z/.025)**4)
      # Local free lip border movement blends into source lip attachment.
      rim=np.exp(-((x-.091)/.014)**2)*lateral
      if id=='mim':
        q[:,1]+=amount*rim*(-.0025 if name=='UPPER_LIP' else .0085)
      elif id=='fa' and name=='LOWER_LIP':
        q[:,1]+=amount*.010*rim;q[:,0]-=amount*.004*rim
      q,count=clip_to_obstacles(p,q,[bvhs[n] for n in ['UPPER_TEETH','LOWER_TEETH'] if n in bvhs]);result[name]=q;report[name+'_clipped_vertices']=count
    if id=='mim' and 'UPPER_LIP' in result and 'LOWER_LIP' in result:
      upper_bvh=BVHTree.FromPolygons([tuple(p) for p in result['UPPER_LIP']],[tuple(f) for f in base['UPPER_LIP'][1]],all_triangles=True)
      result['LOWER_LIP'],count=clip_to_obstacles(base['LOWER_LIP'][0],result['LOWER_LIP'],[upper_bvh])
      report['LOWER_LIP_mutual_contact_clipped_vertices']=count
    if id=='mim' and 'SOFT_PALATE' in result:
      if velum_delta is None:
        raise ValueError('Mim requires the acquired registered softpalate_down target; no invented replacement')
      p=base['SOFT_PALATE'][0]
      nasal=envelope(t,.08,.24,.78,.94)
      result['SOFT_PALATE']=p+nasal*velum_delta
    return result,report

def deformation_quality(values,base):
    report={}
    for name,q in values.items():
      p,faces=base[name];displacement=np.linalg.norm(q-p,axis=1)
      if float(displacement.max())<1e-8:continue
      normal0=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]])
      normal1=np.cross(q[faces[:,1]]-q[faces[:,0]],q[faces[:,2]]-q[faces[:,0]])
      area0=np.linalg.norm(normal0,axis=1);area1=np.linalg.norm(normal1,axis=1);valid=area0>1e-14
      report[name]={'maxDisplacement_mm':float(displacement.max()*1000),'meanDisplacement_mm':float(displacement.mean()*1000),'changedVertices':int(np.sum(displacement>1e-7)),'restRelativeNegativeFaceDot':int(np.sum((np.sum(normal0*normal1,axis=1)<0)&valid)),'nearCollapsedFaces':int(np.sum((area1<area0*.01)&valid)),'minimumAreaRatio':float((area1[valid]/area0[valid]).min())}
    return report

def write_positions(path,state):
    """Float32 absolute meters, named arrays; no faces/topology duplication."""
    np.savez_compressed(path,**{name:p.astype(np.float32) for name,p in state.items()})

def changed_parts(values,base):
    return {name:p for name,p in values.items() if np.max(np.abs(p-base[name][0]))>1e-8}

def geometry_hash(values):
    if not values:return None
    h=hashlib.sha256()
    for name in sorted(values):h.update(name.encode());h.update(values[name].astype(np.float32).tobytes())
    return h.hexdigest()

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--rest',required=True);parser.add_argument('--out',required=True);parser.add_argument('--softpalate-variants',required=True)
    opts=parser.parse_args(args);rest_path=pathlib.Path(opts.rest);out=pathlib.Path(opts.out);out.mkdir(parents=True,exist_ok=True)
    source=json.loads(rest_path.read_text());assert source.get('units',source.get('unit'))=='m','Prepared anatomy must be canonical meters'
    base={name:topology(mesh) for name,mesh in source['parts'].items()};bvhs={name:BVHTree.FromPolygons([tuple(v) for v in p],[tuple(f) for f in fs],all_triangles=True) for name,(p,fs) in base.items()}
    if 'TONGUE'not in base:raise ValueError('Missing TONGUE')
    variants=json.loads(pathlib.Path(opts.softpalate_variants).read_text())
    velum_down=np.asarray(variants['softpalate_down']['positions']).reshape(-1,3)
    velum_init=np.asarray(variants['softpalate_init']['positions']).reshape(-1,3)
    velum_delta=velum_down-velum_init
    assert np.array_equal(np.asarray(variants['softpalate_down']['indices']),np.asarray(variants['softpalate_init']['indices'])), 'Registered velum targets must have identical topology'
    assert velum_down.shape==base['SOFT_PALATE'][0].shape, 'Prepared velum must preserve acquired vertex correspondence'
    manifest={'version':'badin-local-surface-1','softPalateMotion':'preparedRest + nasalActivation*(sourceDown-sourceInit); preserves B baseline clearance correction','units':'m','rest':str(rest_path),'restSha256':hashlib.sha256(rest_path.read_bytes()).hexdigest(),'softpalateVariantsSha256':hashlib.sha256(pathlib.Path(opts.softpalate_variants).read_bytes()).hexdigest(),'positionEncoding':'npz-float32-absolute-meters-dynamic-parts-only','interpolation':'piecewise-linear absolute canonical vertex positions between adjacent normalized frame times; static and absent parts use exact prepared rest; no runtime contact projection','keyAliases':{},'clearance_m':CLEARANCE,'sourceAnatomy':'Badin/ArtiSynth prepared rest, source provenance recorded by A/B','anatomicalReview':'pending','tajwidReview':'pending','clinicalRanges':False,'surfaceClipIsNotFullCollisionProof':True,'motions':{}}
    unique_geometry={}
    for id in DURATIONS:
      folder=out/id;folder.mkdir(exist_ok=True);frames=[]
      for index,t in enumerate(TIMES):
        values,report=state(id,t,base,bvhs,velum_delta);key=f'{id}_{index:02d}'
        dynamic=changed_parts(values,base);fingerprint=geometry_hash(dynamic)
        if fingerprint is None:
          alias=None;filename=None
        elif fingerprint in unique_geometry:
          alias,filename=unique_geometry[fingerprint]
        else:
          alias=key;filename=f'{id}/{key}.npz';write_positions(out/filename,dynamic);unique_geometry[fingerprint]=(alias,filename)
        manifest['keyAliases'][key]=alias
        frames.append({'key':key,'geometryKey':alias,'t':t,'file':filename,'activation':activation(id,t),'constraintReport':report,'deformationQuality':deformation_quality(values,base)})
      manifest['motions'][id]={'duration':DURATIONS[id],'frames':frames}
      print('Sampled',id,'frames',len(frames),'unique geometry so far',len(unique_geometry),flush=True)
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    # Independent controls are exported separately, with explicit source weights.
    demos=out/'control-demos';demos.mkdir(exist_ok=True);p=base['TONGUE'][0];w=weights(p);demo_specs={'tip-lift':('tip',1,.010),'tip-advance':('tip',0,.003),'tip-retract':('tip',0,-.003),'blade-lift':('blade',1,.007),'dorsum-lift':('dorsum',1,.010),'root-retract':('root',0,-.004),'edges-lift':('edges',1,.004),'groove':('groove',1,-.002)}
    for name,(field,axis,displacement) in demo_specs.items():
      q=p.copy();q[:,axis]+=w[field]*displacement;q,count=clip_to_obstacles(p,q,[bvhs[n] for n in ['UPPER_TEETH','LOWER_TEETH','HARD_PALATE','SOFT_PALATE','PHARYNX'] if n in bvhs]);write_positions(demos/f'{name}.npz',{'TONGUE':q})
    # Additional source-surface controls, independent of tongue demonstrations.
    for control in ['lips-close','lips-open','lips-round','lips-protrude','jaw-open','velum-down']:
      values={}
      if control.startswith('lips-'):
        for name in ['UPPER_LIP','LOWER_LIP']:
          if name not in base:continue
          p=base[name][0];q=p.copy();x,y,z=p.T;rim=np.exp(-((x-.091)/.014)**2)*np.exp(-(z/.025)**4)
          if control=='lips-close':q[:,1]+=rim*(-.0025 if name=='UPPER_LIP'else .0085)
          elif control=='lips-open':q[:,1]+=rim*(.002 if name=='UPPER_LIP'else -.005)
          elif control=='lips-round':q[:,2]*=(1-.18*rim);q[:,0]+=.0025*rim
          elif control=='lips-protrude':q[:,0]+=.003*rim
          q,count=clip_to_obstacles(p,q,[bvhs[n]for n in ['UPPER_TEETH','LOWER_TEETH']if n in bvhs]);values[name]=q
        if control=='lips-close'and 'UPPER_LIP'in values and 'LOWER_LIP'in values:
          upper=BVHTree.FromPolygons([tuple(p)for p in values['UPPER_LIP']],[tuple(f)for f in base['UPPER_LIP'][1]],all_triangles=True)
          values['LOWER_LIP'],_=clip_to_obstacles(base['LOWER_LIP'][0],values['LOWER_LIP'],[upper])
      elif control=='jaw-open':
        angle=math.radians(-3);origin=np.array([.003,.037,0])
        for name in ['LOWER_TEETH','GINGIVA_LOWER','LOWER_LIP']:
          if name not in base:continue
          p=base[name][0];q=p-origin;x=q[:,0].copy();y=q[:,1].copy();q[:,0]=x*math.cos(angle)-y*math.sin(angle);q[:,1]=x*math.sin(angle)+y*math.cos(angle);values[name]=q+origin
      else:values['SOFT_PALATE']=base['SOFT_PALATE'][0]+velum_delta
      write_positions(demos/f'{control}.npz',values)
    (out/'control-calibration.json').write_text(json.dumps({'basis':'Prepared Badin canonical meters','axes':{'x':'anterior','y':'superior','z':'lateral'},'landmarkSources':'Raw source midsagittal vertices transformed by x=.14-source.x,y=source.z-.1,z=source.y','artisticRangesNotClinical':True,'sourceLandmarks':{'tip':[.082426,-.000084,0],'blade':[.075419,.004954,0],'dorsum':[.045189,.013659,0],'root':[.027610,.009471,0]},'additionalIndependentControls':['lips-close','lips-open','lips-round','lips-protrude','jaw-open','velum-down'],'jawPivot_m':[.003,.037,0],'velumControl':'Acquired registered down-init delta added to prepared INIT+clearance baseline, preserving 132 unchanged source attachment vertices and B baseline clearance correction','independentTongueControls':{n:{'field':f,'axis':a,'demonstrationDisplacement_m':d}for n,(f,a,d) in demo_specs.items()},'constraint':'Segment swept vertex rays against prepared crown/palate/pharynx triangles, then external triangle collision checks required','limitations':['No muscle force simulation','No verified clinical parameter ranges','Actual softpalate_down target is registered with verified source transform; donor provenance remains A/B responsibility','Surface clipping alone cannot rule out edge/triangle crossings']},ensure_ascii=False,indent=2))
    print('Sampled real prepared anatomy:',len(DURATIONS)*len(TIMES),'frames; unique geometry',len(unique_geometry),'independent controls',len(demo_specs)+6)
if __name__=='__main__':main()
