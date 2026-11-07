"""Fail if review evidence, source, delivered model or browser files are stale."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
folder = ROOT / 'artifacts/milestone-evidence/M2/realistic-rebuild'
public = ROOT / 'public/models'
def read(name): return json.loads((folder / name).read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = read('atlas-study.manifest.json')
asset_sha = sha(folder / 'atlas-study.glb')
blend_sha = sha(folder / 'atlas-study.blend')
assert asset_sha == manifest['glbSha256'] and blend_sha == manifest['blendSha256']
assert sha(public / 'makharij-realistic.glb') == asset_sha
assert json.loads((public / 'makharij-realistic.manifest.json').read_text())['glbSha256'] == asset_sha
for local, delivered in [('atlas-sections.json', 'makharij-sections.json'), ('atlas-nasal-sections.json', 'makharij-nasal-sections.json')]:
    assert read(local)['assetSha256'] == asset_sha
    assert sha(folder / local) == sha(public / delivered), 'Stale published section file'
geometry, captures, browser = read('anatomy-verification.json'), read('atlas-captures.json'), read('browser-verification.json')
assert all(report['assetSha256'] == asset_sha for report in [geometry, captures, browser])
assert geometry['staticGeometryPassed'] and not geometry['geometryFailures']
expected = {'atlas-three-quarter', 'atlas-sagittal', 'atlas-mouth', 'atlas-nose', 'atlas-tongue'}
assert set(captures['views']) == expected, 'Missing actual resting-anatomy view'
for name, expected_sha in captures['views'].items():
    assert sha(folder / (name + '.png')) == expected_sha, 'Stale native render: ' + name
assert browser['actualProductionPage'] and browser['actualPointerRotation'] and not browser['pageErrors']
assert browser['rendererInstances'] == 1 and browser['cameraRotationViews'] == 8
for i, expected_sha in enumerate(browser['rotationFrameSha256']):
    assert sha(folder / f'rotation-{i:02}.png') == expected_sha
assert len(set(browser['rotationFrameSha256'])) == 8
report = {'assetSha256': asset_sha, 'sourceBlendSha256': blend_sha, 'nativeViews': len(expected),
    'actualBrowserCameraViews': 8, 'actualPointerRotation': True, 'matchingPublishedSections': True,
    'staticGeometryPassed': True, 'passed': True, 'isAcceptedAnatomy': False, 'visualReview': geometry.get('visualReview', 'pending'),
    'scope': 'Independent byte-identity audit of the retained study across source, actual delivery, native captures, browser evidence and published review files; this does not override the recorded visual rejection or establish expert acceptance'}
(folder / 'evidence-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
