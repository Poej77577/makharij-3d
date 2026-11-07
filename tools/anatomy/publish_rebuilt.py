"""Stage the verified resting model and matching sections for local review."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'artifacts/milestone-evidence/M2/realistic-rebuild'
target = ROOT / 'public/models'
report = json.loads((source / 'anatomy-verification.json').read_text())
manifest = json.loads((source / 'atlas-study.manifest.json').read_text())
assert report['staticGeometryPassed'], 'Fix actual static geometry before publishing the review model'
assert report['assetSha256'] == manifest['glbSha256'] == hashlib.sha256((source / 'atlas-study.glb').read_bytes()).hexdigest()
target.mkdir(parents=True, exist_ok=True)
for original, name in [('atlas-study.glb', 'makharij-realistic.glb'), ('atlas-sections.json', 'makharij-sections.json'), ('atlas-nasal-sections.json', 'makharij-nasal-sections.json')]:
    temporary = target / (name + '.tmp')
    shutil.copyfile(source / original, temporary)
    temporary.replace(target / name)
notice = (ROOT / 'assets/source/z-anatomy/NOTICE.md').read_text()
notice += '\n## MAKHARIJ rebuild modifications\n\n'
notice += 'Rebuilt tongue surface/root envelope, shallow dorsal sulcus, soft-palate tissue thickness, selected source topology repairs, hollow proximal tracheal context, source-guided negative oral/pharyngeal/nasal cavities, fitted connected lip vestibule, rigid dental placement into a CC0 MakeHuman head, and authored materials/normal map. Parameters and source identities are recorded in the editable reconstruction manifest. The two computed sagittal sections expose oral and nasal regions at different planes of the same actual model. This is a resting model for visual review; articulation and expert approval remain pending.\n\n'
notice += 'MakeHuman head, source facial targets, eyes and eye texture: CC0 1.0, https://github.com/makehumancommunity/makehuman ; original asset notices retained in assets/source/makehuman. No MakeHuman application program code is redistributed in this model.\n'
(target / 'makharij-realistic.NOTICE.md').write_text(notice)
manifest.update({'reviewPage': '/anatomy.html', 'isAcceptedAnatomy': False, 'rigReady': False,
    'visualReview': report.get('visualReview', 'pending'),
    'staticGeometryPassed': True, 'modelDataLicense': 'CC-BY-SA-4.0',
    'attributionNotice': '/models/makharij-realistic.NOTICE.md'})
(target / 'makharij-realistic.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('STAGED_REBUILT_ANATOMY', manifest['glbSha256'])
