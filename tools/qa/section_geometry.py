"""Closed-section polygonization with explicit numerical-contour validation."""
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString
from shapely.ops import polygonize_full, unary_union

def closed_polygons(segments_2d, tolerance=1e-8):
    segments = np.asarray(segments_2d)
    if not len(segments):
        return [], {'segments': 0, 'maximumEndpointWeld_m': 0}
    q = segments.reshape(-1, 2)
    parent = np.arange(len(q))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in cKDTree(q).query_pairs(tolerance):
        parent[root(a)] = root(b)
    groups = {}
    for i in range(len(q)):
        groups.setdefault(root(i), []).append(i)
    welded = q.copy()
    for ids in groups.values():
        welded[ids] = q[ids].mean(axis=0)
    error = float(np.linalg.norm(welded - q, axis=1).max())
    assert error <= tolerance, 'Section endpoint weld exceeds explicit numerical tolerance'
    lines = [LineString(s) for s in welded.reshape(-1, 2, 2) if np.linalg.norm(s[1] - s[0]) > 1e-10]
    polygons, cuts, dangles, invalid = polygonize_full(unary_union(lines))
    assert cuts.is_empty and dangles.is_empty and invalid.is_empty, 'Closed-volume section has unclosed/invalid contours'
    return list(polygons.geoms), {'segments': len(lines), 'maximumEndpointWeld_m': error}
