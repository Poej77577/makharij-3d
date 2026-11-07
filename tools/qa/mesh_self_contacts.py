"""FCL triangle contacts with explicit adjacency exclusion and saturation guard."""
import fcl
import numpy as np

def self_contact_report(name, mesh, limit=300000):
    p, faces = mesh.vertices, mesh.faces.astype(np.int32)
    tree = fcl.BVHModel()
    tree.beginModel(len(p), len(faces))
    tree.addSubModel(p, faces)
    tree.endModel()
    ob = fcl.CollisionObject(tree)
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
    return {'name': name, 'fclTriangleContacts': len(result.contacts), 'nonadjacentIntersectingTrianglePairs': len(bad),
            'truncated': len(result.contacts) >= limit, 'examples': examples}
