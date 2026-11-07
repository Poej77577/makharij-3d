"""Author a lower-airway negative-space continuation between research anchors.

This is a reconstructed cavity, not acquired lower-airway segmentation. Its
upper contour comes from the actual TetGen airspace; its tilted laryngeal
contour comes from the actual cricoid ring opening, never a primitive organ.
"""
import json
from pathlib import Path
import sys
import numpy as np
import trimesh
from shapely.geometry import Polygon
from mesh_sources import ROOT, file_sha
from surface_fits import fit_throat_context

sys.path.insert(0, str(ROOT / 'tools/qa'))
from section_geometry import closed_polygons

out = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
air_path = out / 'research-airspace-helper.json'
vkh_path = ROOT / 'artifacts/milestone-evidence/M1/vkh-upper-airway/source-meshes.json'
fit_path = ROOT / 'assets/calibration/character-fit.json'
air = json.loads(air_path.read_text())
vkh = json.loads(vkh_path.read_text())['parts']['Cricoid']
fit = json.loads(fit_path.read_text())
t = np.array(fit['transforms']['vkh_context']['matrix'])[:3, 3]
cartilage = trimesh.Trimesh(fit_throat_context(np.array(vkh['positions']).reshape(-1, 3) + t), vkh['faces'], process=False)
space = trimesh.Trimesh(np.array(air['positions']).reshape(-1, 3), np.array(air['indices']).reshape(-1, 3), process=False)
assert space.is_watertight and cartilage.is_watertight

def sample(ring, n=96):
    return np.array([[p.x, p.y] for p in [ring.interpolate(ring.length * i / n) for i in range(n)]])

y = float(space.bounds[0, 1] + .0023)
segments = trimesh.intersections.mesh_plane(space, [0, 1, 0], [0, y, 0])
polygons, _ = closed_polygons(segments[:, :, [0, 2]])
source_upper_poly = max(polygons, key=lambda p: p.area)
upper_poly = source_upper_poly.convex_hull
q = sample(upper_poly.exterior)
q = q.mean(0) + (q - q.mean(0)) * 1.03
upper = np.c_[q[:, 0], np.full(len(q), y), q[:, 1]]
values, axes = np.linalg.eigh(np.cov(cartilage.vertices.T))
normal = axes[:, 0]
if normal[1] < 0:
    normal *= -1
basis = np.linalg.svd(np.array([normal]))[2][1:]
origin = cartilage.center_mass
segments = trimesh.intersections.mesh_plane(cartilage, normal, origin)
polygons, _ = closed_polygons((segments - origin) @ basis.T)
holes = [Polygon(ring) for poly in polygons for ring in poly.interiors]
assert holes, 'No actual cricoid opening was identified; do not invent one'
hole = max(holes, key=lambda p: p.area)
lower = sample(hole.exterior) @ basis + origin
# A documented 8% radial inset keeps the helper inside the observed opening.
center = lower.mean(0)
lower = center + (lower - center) * .92

def oriented(ring):
    a = ring - ring.mean(0)
    n = np.cross(a, np.roll(a, -1, axis=0)).sum(0)
    return ring if n[1] > 0 else ring[::-1]
upper, lower = oriented(upper), oriented(lower)
uc, lc = upper - upper.mean(0), lower - lower.mean(0)
offset = min(range(len(lower)), key=lambda k: ((uc - np.roll(lc, k, axis=0)) ** 2).sum())
lower = np.roll(lower, offset, axis=0)
rings = []
entry = lower + normal * .008
exit_ = lower - normal * .008
for s in np.linspace(0, 1, 12, endpoint=False):
    rings.append(upper * (1 - s) + entry * s)
for s in np.linspace(0, 1, 7, endpoint=False):
    rings.append(entry * (1 - s) + exit_ * s)
end = exit_.copy()
end[:, 1] = -.139
end[:, 0] -= .004
for s in np.linspace(0, 1, 20):
    rings.append(exit_ * (1 - s) + end * s)
vertices = np.vstack(rings)
faces = []
n = len(upper)
for i in range(len(rings) - 1):
    for j in range(n):
        a, b, c, d = i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j
        faces.extend([[a, b, c], [a, c, d]])
for end_index, reverse in [(0, True), (len(rings) - 1, False)]:
    # The first contour may be concave: use actual polygon triangulation,
    # never a centroid fan across an unverified airway contour.
    ring = rings[end_index]
    polygon = Polygon(ring[:, [0, 2]])
    assert polygon.is_valid
    center_2d = ring[:, [0, 2]].mean(0)
    star_shaped = all(polygon.buffer(1e-12).covers(Polygon([center_2d, ring[j, [0, 2]], ring[(j + 1) % n, [0, 2]]])) for j in range(n))
    if star_shaped:
        # Use a fan only after proving every triangle lies in the actual cap
        # polygon. This retains collinear boundary samples without zero-area
        # Earcut slivers; no fan is allowed across an unverified concavity.
        center_id = len(vertices)
        vertices = np.vstack([vertices, ring.mean(0)])
        for j in range(n):
            faces.append([center_id, end_index * n + j, end_index * n + (j + 1) % n])
        continue
    points, triangles = trimesh.creation.triangulate_polygon(polygon, engine='earcut')
    ids = [int(np.linalg.norm(ring[:, [0, 2]] - p, axis=1).argmin()) for p in points]
    for a, b, c in triangles:
        tri = [end_index * n + ids[a], end_index * n + ids[b], end_index * n + ids[c]]
        # Orient caps opposite the existing border direction below.
        faces.append(tri)
mesh = trimesh.Trimesh(vertices, faces, process=False)
trimesh.repair.fix_winding(mesh)
if mesh.volume < 0:
    mesh.invert()
assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0
record = {'positions': mesh.vertices.ravel().tolist(), 'indices': mesh.faces.ravel().tolist(),
          'role': 'Authored lower-airway negative-space helper, never a displayed organ',
          'clinicalOrExpertApproval': False, 'anchorMethod': 'Convex envelope of actual research upper-airway section with3% authoring expansion, PCA-plane cricoid inner contour with8% radial inset; interpolated continuation to open neck-context crop',
          'sourceUpperSectionArea_m2': source_upper_poly.area, 'upperEnvelopeArea_m2': upper_poly.area * 1.03 ** 2,
          'upperSectionY_m': y, 'cricoidPlaneOrigin_m': origin.tolist(), 'cricoidPlaneNormal': normal.tolist(),
          'cricoidOpeningArea_m2': hole.area, 'volume_m3': float(mesh.volume), 'rings': len(rings),
          'inputs': {str(path.relative_to(ROOT)): file_sha(path) for path in [air_path, vkh_path, fit_path, Path(__file__), ROOT / 'tools/anatomy/surface_fits.py']},
          'limits': ['Not acquired tracheal segmentation', 'Epiglottis and vocal folds are not supplied', 'Patency and tissue clearance require independent checks after fitting']}
(out / 'lower-airway-helper.json').write_text(json.dumps(record, separators=(',', ':')) + '\n')
print(json.dumps({k: record[k] for k in ['role', 'cricoidOpeningArea_m2', 'rings', 'volume_m3']}, indent=2))
