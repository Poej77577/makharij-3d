"""Explicit artist reconstruction controls; no clinical calibration claim.

Every original exterior/rim vertex remains fixed during oral lining fitting.
The shared throat warp is a smooth shear with Jacobian determinant one; it
cannot invert a continuous volume. It is not a jaw or articulation control.
"""
import heapq
import numpy as np

def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def fit_oral_lining(points, faces, oral_face_ids, rim_ids):
    p = points.copy()
    ids = sorted({v for i in oral_face_ids for v in faces[i]})
    adjacent = {i: {} for i in ids}
    for fi in oral_face_ids:
        face = faces[fi]
        for a, b in zip(face, face[1:] + face[:1]):
            distance = float(np.linalg.norm(points[a] - points[b]))
            adjacent[a][b] = adjacent[b][a] = distance
    distance = {i: float('inf') for i in ids}
    queue = []
    for i in rim_ids:
        distance[i] = 0
        heapq.heappush(queue, (0, i))
    while queue:
        d, a = heapq.heappop(queue)
        if d > distance[a]:
            continue
        for b, edge in adjacent[a].items():
            if d + edge < distance[b]:
                distance[b] = d + edge
                heapq.heappush(queue, (d + edge, b))
    # Source midline controls follow the actual source oral bag. Targets fit
    # the placed crown/palatal envelope and a lower floor, not primitive organs.
    x = [.05, .064, .082, .095, .113, .124, .136, .144, .150, .152]
    roof_delta = [0, -.002, -.009, -.017, -.017, -.014, -.007, -.001, 0, 0]
    floor_delta = [-.004, -.016, -.016, -.014, -.010, -.007, -.005, -.003, 0, 0]
    for i in ids:
        q = points[i]
        falloff = float(smoothstep(distance[i] / .012))
        roof_weight = float(smoothstep((q[1] - .021) / .030))
        dy = np.interp(q[0], x, floor_delta) * (1 - roof_weight) + np.interp(q[0], x, roof_delta) * roof_weight
        p[i, 1] += falloff * dy
        width = np.interp(q[0], [.05, .07, .09, .11, .13, .145, .155], [0, .12, .24, .20, .10, 0, 0])
        p[i, 2] *= 1 + falloff * width
    delta = p - points
    assert np.array_equal(p[rim_ids], points[rim_ids]), 'Lip-rim continuity lost'
    unchanged = sorted(set(range(len(p))) - set(ids))
    assert np.array_equal(p[unchanged], points[unchanged]), 'Exterior changed by oral fit'
    return p, {'method': 'Source oral-bag geodesic rim falloff, roof/floor control curves and lateral mucosal expansion',
               'controlX_m': x, 'roofDeltaY_m': roof_delta, 'floorDeltaY_m': floor_delta,
               'rimVerticesFixed': len(rim_ids), 'externalVerticesUnchanged': True,
               'maximumVertexDisplacement_m': float(np.linalg.norm(delta, axis=1).max()),
               'clinicalMeasurement': False, 'posteriorAirwayConnection': 'pending'}

def fit_throat_context(points):
    p = points.copy()
    amount = .008 + .025 * (1 - smoothstep((p[:, 1] + .010) / .065))
    p[:, 0] -= amount
    return p

THROAT_FIT = {'method': 'Shared posterior shear of VKH context as a function of canonical superior coordinate',
              'deltaX_m': '-0.008 - 0.025 * (1 - smoothstep((Y + 0.010) / 0.065))',
              'continuousJacobianDeterminant': 1, 'clinicalMeasurement': False,
              'reason': 'Fit source pharyngeal/laryngeal context within the continuous character neck; preserve relative context placement'}
