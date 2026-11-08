"""Four isolated actual-GLB tongue self-contact checks; no anatomy acceptance.

Run with .venv-qa/bin/python. The explicit expected SHA and manifest SHA must
both match the current bytes. Reimport GLB in script-disabled Blender, evaluate
rest and three tongue endpoints at jaw=0, then use the existing reviewed FCL
self-contact helper. Coincident UV/normal seam positions are welded at 1e-10m;
all shared-vertex triangle pairs are excluded. Adjacent folds and untested
combined/intermediate controls remain outside this bounded test.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import trimesh

from mesh_self_contacts import self_contact_report

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ('rest', {}),
    ('TIP_ELEVATE_1', {'TIP_ELEVATE': 1}),
    ('DORSUM_ELEVATE_1', {'DORSUM_ELEVATE': 1}),
    ('ROOT_RETRACT_1', {'ROOT_RETRACT': 1}),
)
EXPORTER = r'''
from pathlib import Path
import hashlib,json,sys
import bpy,numpy as np
c=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
a=Path(c['asset'])
if hashlib.sha256(a.read_bytes()).hexdigest()!=c['expectedSha256']:
    raise RuntimeError('GLB changed before reimport')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(a))
for ob in bpy.context.scene.objects:
    if ob.type=='MESH' and ob.data.shape_keys:
        ob.data.shape_keys.animation_data_clear()
jaw=bpy.data.objects[c['manifest']['jawBinding']['node']]
jaw.animation_data_clear();jaw.rotation_mode='XYZ';jaw.rotation_euler.x=0
ob=bpy.data.objects['TONGUE']
keys=ob.data.shape_keys
if keys is None or not {'TIP_ELEVATE','DORSUM_ELEVATE','ROOT_RETRACT'}.issubset(keys.key_blocks.keys()):
    raise RuntimeError('Actual GLB lacks required tongue morphs')
rows=[]
for i,(label,values)in enumerate(c['cases']):
    for mesh in bpy.context.scene.objects:
        if mesh.type!='MESH' or not mesh.data.shape_keys:continue
        for k in mesh.data.shape_keys.key_blocks[1:]:
            pair=c['manifest']['correctives'].get(k.name)
            k.value=values.get(pair[0],0)*values.get(pair[1],0) if pair else values.get(k.name,0)
        mesh.data.shape_keys.update_tag()
    jaw.rotation_euler.x=0
    bpy.context.view_layer.update()
    e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles()
    world=[e.matrix_world@v.co for v in m.vertices]
    points=np.array([(-v.y,v.z,-v.x)for v in world],dtype=np.float64)
    faces=np.array([t.vertices for t in m.loop_triangles],dtype=np.int32)
    e.to_mesh_clear()
    p=Path(c['output'])/('pose-%02d.npz'%i)
    np.savez_compressed(p,vertices=points,faces=faces)
    rows.append({'case':label,'controls':values,'jawOpen':0,'file':str(p)})
if hashlib.sha256(a.read_bytes()).hexdigest()!=c['expectedSha256']:
    raise RuntimeError('GLB changed during pose export')
Path(c['output'],'poses.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'actualGlbPoses':len(rows),'assetSha256':c['expectedSha256']}))
'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_identity(asset: Path, manifest: dict, expected: str) -> str:
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Expected SHA256 must contain 64 lowercase hexadecimal characters')
    actual = sha(asset)
    if actual != expected or manifest.get('glbSha256') != expected:
        raise ValueError('Asset identity mismatch: bytes=' + actual + ', manifest=' +
                         str(manifest.get('glbSha256')) + ', expected=' + expected)
    return actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=ROOT/'artifacts/method-evidence/oral-sculpt')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--contact-limit', type=int, default=2_000_000)
    parser.add_argument('--maximum-contact-limit', type=int, default=4_000_000)
    args = parser.parse_args()
    if not 0 < args.contact_limit <= args.maximum_contact_limit:
        parser.error('Require 0 < contact limit <= maximum contact limit')
    folder = args.folder.resolve()
    asset, manifest_path = folder/'oral-unit.glb', folder/'oral-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    identity = check_identity(asset, manifest, args.expected_sha256)
    out = (args.out or folder/'self-contact-review').resolve()
    out.mkdir(parents=True, exist_ok=True)
    blender = shutil.which('blender')
    if not blender:
        raise RuntimeError('Blender executable not found')
    exporter = out/'export-actual-glb-poses.py'
    exporter.write_text(EXPORTER)
    config = {'asset':str(asset), 'expectedSha256':identity, 'manifest':manifest,
              'cases':CASES, 'output':str(out)}
    config_path = out/'export-config.json'
    config_path.write_text(json.dumps(config, indent=2)+'\n')
    with (out/'export.log').open('w') as log:
        subprocess.run([blender, '--background', '--factory-startup', '--disable-autoexec',
                        '--threads', '2', '--python-exit-code', '1', '--python', str(exporter),
                        '--', str(config_path)], check=True, stdout=log, stderr=subprocess.STDOUT)
    poses = json.loads((out/'poses.json').read_text())
    if [(x['case'], x['controls']) for x in poses] != list(CASES):
        raise RuntimeError('Exported pose inventory differs from the four explicit cases')
    records = []
    for pose in poses:
        with np.load(pose['file']) as arrays:
            vertices, faces = arrays['vertices'], arrays['faces']
        if (not len(vertices) or not len(faces) or not np.isfinite(vertices).all() or
                faces.min() < 0 or faces.max() >= len(vertices)):
            raise RuntimeError('Invalid actual tongue geometry in '+pose['case'])
        mesh = trimesh.Trimesh(vertices, faces, process=False)
        mesh.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
        limit = args.contact_limit
        attempts = []
        while True:
            result = self_contact_report('TONGUE', mesh, limit=limit)
            attempts.append({'limit':limit, 'contacts':result['fclTriangleContacts'],
                             'saturated':result['truncated']})
            if not result['truncated'] or limit >= args.maximum_contact_limit:
                break
            limit = min(2*limit, args.maximum_contact_limit)
        result.update({'case':pose['case'], 'controls':pose['controls'], 'jawOpen':0,
                       'poseFileSha256':sha(Path(pose['file'])), 'enumerationAttempts':attempts,
                       'triangles':len(mesh.faces), 'geometricVertices':len(mesh.vertices),
                       'watertight':bool(mesh.is_watertight),
                       'windingConsistent':bool(mesh.is_winding_consistent),
                       'volume_m3':float(mesh.volume),
                       'minimumTriangleArea_m2':float(mesh.area_faces.min())})
        result['passed'] = (not result['truncated'] and not result['nonadjacentIntersectingTrianglePairs']
                            and result['watertight'] and result['windingConsistent']
                            and result['volume_m3'] > 0 and result['minimumTriangleArea_m2'] > 1e-15)
        records.append(result)
        (out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')
        print(json.dumps({'case':pose['case'], 'selfIntersections':result['nonadjacentIntersectingTrianglePairs'],
                          'contacts':result['fclTriangleContacts'], 'saturated':result['truncated'],
                          'passed':result['passed']}), flush=True)
        del mesh, vertices, faces
        gc.collect()
    check_identity(asset, json.loads(manifest_path.read_text()), identity)
    report = {'asset':str(asset), 'assetSha256':identity, 'manifestSha256':sha(manifest_path),
              'scriptSha256':sha(Path(__file__)),
              'reviewedSelfContactHelperSha256':sha(Path(__file__).with_name('mesh_self_contacts.py')),
              'poseExporterSha256':sha(exporter), 'cases':records,
              'passed':all(x['passed'] for x in records),
              'method':'Actual imported GLB morph evaluation; geometric seam welding at 1e-10m; existing FCL self-contact helper excludes all shared-vertex triangle pairs; explicit saturation guard.',
              'scope':'Rest and three isolated tongue endpoints at jaw=0 only. No intermediate/combined controls, adjacent-fold/strain, contact biomechanics, phoneme or clinical/anatomical acceptance.'}
    (out/'self-contacts.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'assetSha256':identity, 'cases':len(records), 'passed':report['passed']}), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
