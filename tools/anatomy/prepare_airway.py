"""Extract the actually loaded VKH WA airspace; never use the unrelated OBJ."""
import json
import numpy as np
from mesh_sources import ROOT, load_tetgen_boundary, canonical_vkh, file_sha
from surface_fits import fit_throat_context

source = ROOT / 'assets/source/vkh-upper-airway/src/artisynth/models/vkhUpperAirway/geometry/fem'
nodes, cells = source / 'Airway-final2.1.node', source / 'Airway-final2.1.ele'
data = load_tetgen_boundary(nodes, cells)
fit = json.loads((ROOT / 'assets/calibration/character-fit.json').read_text())
t = np.array(fit['transforms']['vkh_context']['matrix'])[:3, 3]
p = fit_throat_context(canonical_vkh(data['points']) + t)
out = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
out.mkdir(parents=True, exist_ok=True)
record = {'positions': p.ravel().tolist(), 'indices': data['faces'].ravel().tolist(),
          'sourceNodeIds': data['sourceNodeIds'].tolist(), 'sourceCells': data['cells'],
          'skippedDegenerateCells': data['skippedDegenerateCells'],
          'sources': {str(path.relative_to(ROOT)): file_sha(path) for path in [nodes, cells]},
          'source': 'Research TetGen airspace actually loaded by VKHUpperAirwayWA and femList_Airway.txt',
          'role': 'Negative-space reference only; not a visible tissue or full lower airway',
          'status': 'Character-fit review pending; not clinical registration'}
(out / 'research-airspace-helper.json').write_text(json.dumps(record, separators=(',', ':')) + '\n')
print(json.dumps({'cells': data['cells'], 'surfaceTriangles': len(data['faces']), 'bounds_m': [p.min(0).tolist(), p.max(0).tolist()]}, indent=2))
