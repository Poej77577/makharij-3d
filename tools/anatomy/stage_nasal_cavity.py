"""Stage the actual checked hollow nasal wall; analysis air stays out of runtime."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
folder = ROOT/'artifacts/method-evidence/nasal-cavity'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m = json.loads((folder/'nasal-manifest.json').read_text())
qa = json.loads((folder/'qa/nasal-airway.json').read_text())
face = json.loads((ROOT/'public/models/face-context.manifest.json').read_text())
oral = json.loads((ROOT/'public/models/oral-study.manifest.json').read_text())
assert qa['passed'], 'Actual nasal wall / open-air continuity review must pass'
assert qa['topologyPass'] and qa['wallGenus'] == 2 and qa['airGenus'] == 0, 'Unexpected extra openings'
assert digest(folder/'nasal-cavity.glb') == m['glbSha256'] == qa['assetSha256']
assert digest(folder/'nasal-airspace.analysis.glb') == qa['airAssetSha256']
assert m['faceSourceGlbSha256'] == face['glbSha256'] == qa['faceAssetSha256']
assert m['oralSourceGlbSha256'] == oral['glbSha256']
assert all('AIR' not in part for part in m['parts']), 'Negative air is not runtime positive tissue'
dest = ROOT/'public/models'
shutil.copyfile(folder/'nasal-cavity.glb', dest/'nasal-cavity.glb')
shutil.copyfile(folder/'nasal-manifest.json', dest/'nasal-cavity.manifest.json')
shutil.copyfile(folder/'NOTICE.md', dest/'nasal-cavity.NOTICE.md')
print('Staged checked nasal wall with open bilateral inlets and posterior outlet')
