"""Create/verify an unchanged compact ArtiSynth source snapshot. Never modifies upstream."""
from pathlib import Path
import hashlib, json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[2]
UPSTREAM=ROOT/'assets/candidates/artisynth_models'
DEST=ROOT/'assets/source/artiSynth'
GEOMETRY={
'face/geometry':['badintongue.obj','upperteeth.obj','lowerteeth.obj','badinface_upperlip_filled.obj','badinface_lowerlip_filled.obj','badinskin.obj','face.node','face.elem','badinface_oop_csa_midsagittal.node','badinface_oop_csa_midsagittal.elem'],
'jawTongue/geometry':['badinpalate.obj','softpalate_orig.obj','softpalate_init.obj','softpalate_up.obj','softpalate_down.obj'],
}
CODE={
'face':['BadinFaceDemo.java','BadinJawTongueFaceDemo.java','MeshEdit.java'],
'jawTongue':['BadinJawHyoid.java','BadinJawHyoidTongue.java','BadinDataDemo.java','AirwaySkinDemo.java','KinematicSoftPalateDemo.java','MeshBlendController.java'],
'palateV2':['SoftPalateModel.java'],
}
paths=[(name,name)for name in ['LICENSE','README','VERSION']]
for folder,names in (GEOMETRY|CODE).items():
 for name in names:paths.append((f'src/artisynth/models/{folder}/{name}',f'{folder}/{name}'))
DEST.mkdir(parents=True,exist_ok=True)
files=[]
for original,relative in paths:
 src=UPSTREAM/original;dst=DEST/relative;digest=hashlib.sha256(src.read_bytes()).hexdigest()
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists() and dst.read_bytes()!=src.read_bytes():raise RuntimeError(f'Existing source differs; refusing overwrite: {relative}')
 if not dst.exists():shutil.copyfile(src,dst)
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
 files.append({'path':relative,'upstream_path':original,'bytes':dst.stat().st_size,'sha256':digest,'source_url':f'https://github.com/artisynth/artisynth_models/blob/e37be3f1b4831f347c055cbf7124b6bd57414f98/{original}','modified':False})
commit=subprocess.check_output(['git','-C',str(UPSTREAM),'rev-parse','HEAD'],text=True).strip()
if commit!='e37be3f1b4831f347c055cbf7124b6bd57414f98':raise RuntimeError('Unexpected upstream commit')
manifest={
 'schema_version':1,'upstream_repository':'https://github.com/artisynth/artisynth_models','upstream_commit':commit,'snapshot_purpose':'Unchanged selected anatomical source meshes and exact upstream provenance code required to rebuild project anatomy; not a runnable full ArtiSynth installation.','created_utc_date':'2026-10-31',
 'license_file':'LICENSE','upstream_copyright':'Copyright (c) 2014, contributing Authors and Organizations as indicated in subpackage COPYRIGHT notices. All rights reserved.','upstream_subpackage_copyright_files':'No tracked file named COPYRIGHT was found in the acquired upstream tree. Original LICENSE and included source files preserved unchanged.',
 'frame_contract':{'face_obj_units':'m','jawTongue_badinpalate_obj_units':'m','jawTongue_softpalate_obj_units':'mm','native_axes':{'X':'posterior','Y':'lateral','Z':'superior'},'canonical_units':'m','canonical_axes':{'X':'anterior','Y':'superior','Z':'lateral'},'native_m_to_canonical_m_matrix':[[-1,0,0,.14],[0,0,1,-.1],[0,1,0,0],[0,0,0,1]],'softpalate_orig_extra_transform':'Apply AirwaySkinDemo.XSoftPalate in native mm before unit/canonical conversion; init/up/down already registered, do not apply twice.','up_down_init_common_frame_evidence':'132 exactly unchanged attachment vertices with full 3D rank; rigid identity-fit residual 1.53e-14 mm; see docs/assets/softpalate-frame-anchors.json.','raw_airway_shared_frame_evidence':'face and jawTongue raw badinairway.obj SHA256 both 978696d93fcaf22c501c25c6ed7be026d7a5e12150a71ddcb188b301f94dd7cd; 39394 indexed vertices identical. Reference airway meshes omitted from compact runtime-build subset.'},
 'provenance_limits':['Same-source model assembly is not proof of a single donor. Teeth and soft-palate donor identities are unknown.','Source code co-loads dental/tongue geometry, but this is compatibility evidence only, not measured anatomical registration.','BadinFaceDemo default FEM prefix is badinface_oop_csa_midsagittal. face.node/face.elem are a different acquired alternative, included for explicit source-derived context preparation.','softpalate up/down are native source poses, not automatically contact-safe with our assembled tongue.','No acquired nasal cavity mesh is included; any generated nasal lining must remain explicitly authored and unmeasured.','This bundle preserves upstream files byte-for-byte; project-specific edits belong in build scripts/derived assets.'],
 'attribution_from_upstream_getAbout':'Ian Stavness, John E Lloyd, Yohan Payan, and Sidney Fels. Coupled Hard-Soft Tissue Simulation with Contact and Constraints Applied to Jaw-Tongue-Hyoid Dynamics. International Journal for Numerical Methods in Biomedical Engineering, 27:367-390, 2011. Cited by BadinJawHyoidTongue.getAbout; does not establish provenance of each individual mesh.',
 'files':files,'total_source_bytes':sum(f['bytes']for f in files)
}
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'verified_files':len(files),'total_source_bytes':manifest['total_source_bytes'],'upstream_commit':commit,'snapshot':str(DEST)},indent=2))
