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
contact_reports = []
for path in (source/'contact-review').rglob('contact-review.json'):
    record = json.loads(path.read_text())
    if (record.get('assetSha256') == manifest['glbSha256'] and record.get('selectedDentalClearancePass') and
            record.get('cases') == 18 and record.get('pairsChecked') == 36 and
            len(record.get('records', [])) == 36):
        contact_reports.append((path, record))
assert contact_reports, 'Run assets:oral:contacts on the current GLB before staging it'
contact_path, contact = contact_reports[-1]
destination.mkdir(exist_ok=True, parents=True)
shutil.copyfile(source/'oral-unit.glb', destination/'oral-study.glb')
runtime = {
    key: manifest[key] for key in ['status', 'visualReview', 'expertAcceptance', 'clinicalAccuracyClaim',
                                  'productionSelected', 'glbSha256', 'gltfToProject', 'parts',
                                  'jawBinding', 'correctives', 'attribution', 'limitations']
}
runtime['selectedDentalContactReview'] = {'cases': contact['cases'], 'pairsChecked': contact['pairsChecked'],
    'assetSha256': contact['assetSha256'], 'surfaceCrossings': sum(row['surfaceCrossing'] for row in contact['records']),
    'minimumSurfaceDistance_m': min(row['minimumSurfaceDistance_m'] for row in contact['records']),
    'scope': contact['scope'], 'report': str(contact_path.relative_to(ROOT))}
(destination/'oral-study.manifest.json').write_text(json.dumps(runtime, indent=2, ensure_ascii=False)+'\n')
shutil.copyfile(source/'NOTICE.md', destination/'oral-study.NOTICE.md')
print('Staged checked experimental oral study; no clinical or teaching acceptance granted')
