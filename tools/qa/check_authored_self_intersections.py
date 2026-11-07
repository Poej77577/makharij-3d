"""Independent FCL nonadjacent self-intersection check of authored nasal tissue."""
import json
import numpy as np
import fcl
from delivered_character import load_verified_character, FOLDER

manifest, data, meshes = load_verified_character()
records, failures = [], []
for name in [n for n in meshes if n.startswith('NASAL_')]:
    mesh = meshes[name]
    p, faces = mesh.vertices, mesh.faces.astype(np.int32)
    tree = fcl.BVHModel()
    tree.beginModel(len(p), len(faces))
    tree.addSubModel(p, faces)
    tree.endModel()
    ob = fcl.CollisionObject(tree)
    limit = 300000
    result = fcl.CollisionResult()
    fcl.collide(ob, ob, fcl.CollisionRequest(num_max_contacts=limit, enable_contact=True), result)
    bad, examples = set(), []
    for contact in result.contacts:
        a, b = contact.b1, contact.b2
        if a == b or len(set(faces[a]) & set(faces[b])):
            continue
        key = tuple(sorted((a, b)))
        if key not in bad and len(examples) < 8:
            examples.append({'triangles': list(key), 'point_m': contact.pos.tolist()})
        bad.add(key)
    truncated = len(result.contacts) >= limit
    record = {'name': name, 'fclTriangleContacts': len(result.contacts), 'nonadjacentIntersectingTrianglePairs': len(bad),
              'truncated': truncated, 'examples': examples}
    records.append(record)
    if truncated or bad:
        failures.append(record)
report = {'assetSha256': manifest['glbSha256'], 'parts': records, 'passed': not failures,
          'scope': 'FCL triangle self-contacts excluding all pairs with shared geometric vertices; actual delivered authored nasal tissues only. No expert approval.'}
(FOLDER / 'authored-self-intersections.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
if failures:
    raise SystemExit('FAIL: authored nasal tissue self-intersections or incomplete contact enumeration')
