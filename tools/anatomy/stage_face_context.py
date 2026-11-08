"""Stage checked external face context with its associated oral-unit identity."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
folder = ROOT/'artifacts/method-evidence/face-context'
manifest = json.loads((folder/'face-manifest.json').read_text())
review = json.loads((folder/'technical-review.json').read_text())
oral = json.loads((ROOT/'public/models/oral-study.manifest.json').read_text())
assert review['technicalPass']
assert manifest['glbSha256'] == review['glbSha256'] == hashlib.sha256((folder/'face-context.glb').read_bytes()).hexdigest()
assert manifest['oralSourceGlbSha256'] == oral['glbSha256'], 'Rebuild the face master around the current oral input'
contact_reports = []
for path in (folder/'contact-review').rglob('face-contacts.json'):
    record = json.loads(path.read_text())
    if (record.get('faceAssetSha256') == manifest['glbSha256'] and
            record.get('oralAssetSha256') == oral['glbSha256'] and
            record.get('selectedHeadDentalSurfacePass') and
            record.get('cases') == 10 and record.get('pairsChecked') == 20 and
            len(record.get('records', [])) == 20):
        contact_reports.append((path, record))
assert contact_reports, 'Run assets:face:contacts on the current face/oral pair before staging it'
contact_path, contact = contact_reports[-1]
destination = ROOT/'public/models'
shutil.copyfile(folder/'face-context.glb', destination/'face-context.glb')
runtime = {key: manifest[key] for key in
    ['status', 'visualReview', 'expertAcceptance', 'contextSurfaceOnly', 'fullInternalHeadComplete',
     'clinicalAccuracyClaim', 'parts', 'glbSha256', 'oralSourceGlbSha256', 'controls',
     'gltfToProject', 'excludeFromTissueSectionCaps', 'limitations', 'originalAssetLicense']}
runtime['selectedHeadDentalSurfaceReview'] = {
    'faceAssetSha256': contact['faceAssetSha256'], 'oralAssetSha256': contact['oralAssetSha256'],
    'cases': contact['cases'], 'pairsChecked': contact['pairsChecked'],
    'surfaceCrossings': sum(row['surfaceCrossing'] for row in contact['records']),
    'minimumSurfaceDistance_m': min(row['minimumSurfaceDistance_m'] for row in contact['records']),
    'headSurfaceIntentionallyOpen': True, 'insideOrVolumeTestsRun': False,
    'scope': contact['scope'], 'report': str(contact_path.relative_to(ROOT))}
(destination/'face-context.manifest.json').write_text(json.dumps(runtime, indent=2)+'\n')
shutil.copyfile(folder/'NOTICE.md', destination/'face-context.NOTICE.md')
print('Staged checked external face surface; no complete cranial-anatomy acceptance')
