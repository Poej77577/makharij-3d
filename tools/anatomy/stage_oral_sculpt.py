"""Stage only the experimental oral review page's checked assets, never approve anatomy."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
source = ROOT/'artifacts/method-evidence/oral-sculpt'
destination = ROOT/'public/models'
manifest = json.loads((source/'oral-manifest.json').read_text())
review = json.loads((source/'technical-review.json').read_text())
assert review['technicalPass'] and review['glbSha256'] == manifest['glbSha256']
assert hashlib.sha256((source/'oral-unit.glb').read_bytes()).hexdigest() == manifest['glbSha256']
assert not manifest['productionSelected'] and manifest['clinicalAccuracyClaim'] is False
destination.mkdir(exist_ok=True, parents=True)
shutil.copyfile(source/'oral-unit.glb', destination/'oral-study.glb')
(destination/'oral-study.manifest.json').write_text(json.dumps({
    key: manifest[key] for key in ['status', 'visualReview', 'expertAcceptance', 'clinicalAccuracyClaim',
                                  'productionSelected', 'glbSha256', 'gltfToProject', 'parts',
                                  'jawBinding', 'correctives', 'attribution', 'limitations']
}, indent=2, ensure_ascii=False)+'\n')
shutil.copyfile(source/'NOTICE.md', destination/'oral-study.NOTICE.md')
print('Staged checked experimental oral study; no clinical or teaching acceptance granted')
