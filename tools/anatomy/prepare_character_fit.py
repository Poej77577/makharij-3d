"""Documented artist placement from real source geometry, not clinical registration.
No rotation/scale is silently fitted; existing research proportions are retained.
"""
from pathlib import Path
import json
import numpy as np
from mesh_sources import ROOT, makehuman_head_data, canonical_vkh, load_obj, file_sha

out = ROOT / 'assets/calibration'
out.mkdir(parents=True, exist_ok=True)
head = makehuman_head_data(.24)
target_upper = head['fittingReferences']['helper-upper-teeth']
target_mid = target_upper[abs(target_upper[:, 2]) < .003]
target_low = target_mid[target_mid[:, 1] < target_mid[:, 1].min() + .001]
target_anchor = target_low[target_low[:, 0].argmax()]
legacy_path = ROOT / 'assets/anatomy/rest-meshes.json'
legacy = json.loads(legacy_path.read_text())
p = np.array(legacy['parts']['UPPER_TEETH']['positions']).reshape(-1, 3)
q = p[(abs(p[:, 2]) < .003) & (p[:, 0] > .08)]
q = q[q[:, 1] < q[:, 1].min() + .0015]
legacy_anchor = q[q[:, 0].argmax()]
research_path = ROOT / 'assets/source/vkh-upper-airway/src/artisynth/models/vkhUpperAirway/geometry/rigidBodies/Maxilla.obj'
r = canonical_vkh(load_obj(research_path)['points'])
q = r[(abs(r[:, 2]) < .003) & (r[:, 0] > .055)]
q = q[q[:, 1] < q[:, 1].min() + .0015]
research_anchor = q[q[:, 0].argmax()]
transforms = {}
for name, anchor in [('badin_oral', legacy_anchor), ('vkh_context', research_anchor)]:
    matrix = np.eye(4)
    matrix[:3, 3] = target_anchor - anchor
    transforms[name] = {'matrix': matrix.tolist(), 'sourceAnchor_m': anchor.tolist(), 'targetAnchor_m': target_anchor.tolist(), 'uniformScale': 1, 'rotationChanged': False}
report = {
    'version': 1,
    'headPose': {'preset': 'adult source macros', 'mouthOpenAuthoringWeight': .24, 'clinicalRange': False},
    'frame': {'units': 'm', 'anterior': '+X', 'superior': '+Y', 'right': '+Z'},
    'placementMethod': 'Translation-only authoring fit at a source anterior dental edge and matching character fitting-reference edge. No patient registration or donor identity is established.',
    'targetReferenceRole': 'invisible source fitting cage, not displayed anatomy or a clinical measurement',
    'legacyRestSha256': file_sha(legacy_path),
    'researchMaxillaSha256': file_sha(research_path),
    'transforms': transforms,
    'requires': ['actual cross-section review', 'independent clearance/attachment checks', 'oral mucosa fitting', 'expert anatomical review'],
    'status': 'M2 working placement, not accepted anatomy',
}
(out / 'character-fit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'calibration': str((out / 'character-fit.json').relative_to(ROOT)), 'status': report['status'],
                  'translations_m': {name: value['matrix'][:3] for name, value in transforms.items()}}, indent=2))
