"""Render the actual combined native scene with the pinned Blender review skill.

The external head remains an open surface. No section or cranial cap is made.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--folder', default='artifacts/method-evidence/face-context')
p.add_argument('--res', type=int, default=900)
p.add_argument('--labels', nargs='+')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
folder = ROOT/a.folder
manifest = json.loads((folder/'face-manifest.json').read_text())
master = folder/'face-context.blend'
assert hashlib.sha256(master.read_bytes()).hexdigest() == manifest['blendSha256']
skill = ROOT/'.agents/skills/blender-image-to-3d/scripts/review_render.py'
spec = importlib.util.spec_from_file_location('face_review_skill', skill)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
parts = ['HEAD_EXTERNAL', 'FACE_EYES', 'TONGUE', 'ORAL_FLOOR', 'LINGUAL_FRENULUM',
         'PALATE', 'UPPER_DENTITION', 'LOWER_DENTITION', 'UPPER_GINGIVA', 'LOWER_GINGIVA']
records = []
for label, control, frame in [('rest', None, 1), ('jaw', 'JAW_OPEN', 169),
                              ('press', 'LIP_PRESS', 265), ('round', 'LIP_ROUND', 313),
                              ('protrude', 'LIP_PROTRUDE', 361)]:
    if a.labels and label not in a.labels:
        continue
    out = folder/'review'/label
    out.mkdir(exist_ok=True, parents=True)
    for previous in out.glob('material_*.png'):
        previous.unlink()  # Only this tool's prior generated images for this pose.
    fit = ['HEAD_EXTERNAL'] if label == 'rest' else ['UPPER_DENTITION', 'LOWER_DENTITION']
    argv = ['--blend', str(master), '--out', str(out), '--only', ','.join(parts),
            '--fit', ','.join(fit), '--views', 'front,side,threequarter' if label == 'rest' else 'threequarter',
            '--mode', 'material', '--engine', 'cycles', '--frame', str(frame),
            '--res', str(a.res), '--samples', '32']
    renderer.main(renderer.parse(argv))
    records.append({'label': label, 'nativeFrame': frame, 'controls': {control: 1} if control else {},
                    'images': {str(path.relative_to(folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in out.glob('*.png')}})
(folder/'review-material.json').write_text(json.dumps({
    'blendSha256': manifest['blendSha256'], 'faceGlbSha256': manifest['glbSha256'],
    'oralGlbSha256': manifest['oralSourceGlbSha256'],
    'skillSha256': hashlib.sha256(skill.read_bytes()).hexdigest(),
    'scope': 'Actual combined native surfaces, original facial morphs and one shared jaw state; no cranial sections',
    'records': records, 'clinicalAcceptance': 'pending'
}, indent=2)+'\n')
