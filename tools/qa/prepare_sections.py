"""Compute section caps from actual closed tissue triangles, preserving holes.

Separate QA Python handles native geometry libraries; Blender consumes plain
JSON. Open context surfaces are never passed to containment or filled as solid.
"""
import json
from pathlib import Path
import numpy as np
import trimesh
from section_geometry import closed_polygons
from delivered_character import load_verified_character
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
manifest, data, delivered = load_verified_character()
caps, checks, regions = {}, {}, {}
plane_z = 1e-6  # Avoid slicing exactly through original midline edges/vertices.
for name, part in data['parts'].items():
    if not part['closedTissueVolumeClaimed']:
        continue
    mesh = delivered[name]
    assert mesh.is_watertight and mesh.is_winding_consistent, name
    segments = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, plane_z])
    if not len(segments):
        continue
    polygons, contour_check = closed_polygons(segments[:, :, :2])
    assert polygons, f'{name}: no closed section contour'
    accepted = []
    for poly in polygons:
        q = poly.representative_point()
        if mesh.contains([[q.x, q.y, plane_z]])[0]:
            accepted.append(poly)
    assert accepted, f'{name}: no section polygon inside actual tissue'
    regions[name] = unary_union(accepted)
    checks[name] = {'contours': len(polygons), 'insideTissueRegions': len(accepted), **contour_check}

# Generic head context encloses separately represented research tissues. Give
# their actual sections precedence, so coplanar overlapping context cannot
# conceal an organ. This is set subtraction of the verified volume sections,
# not a painted 2-D anatomy substitute or a fabricated tissue surface.
if 'HEAD_SKIN' in regions:
    regions['HEAD_SKIN'] = regions['HEAD_SKIN'].difference(unary_union([p for name, p in regions.items() if name != 'HEAD_SKIN']))
for name, region in regions.items():
    accepted = list(region.geoms) if region.geom_type == 'MultiPolygon' else [region]
    points, faces = [], []
    for polygon in accepted:
        q, t = trimesh.creation.triangulate_polygon(polygon, engine='earcut')
        assert abs(trimesh.Trimesh(np.c_[q, np.zeros(len(q))], t, process=False).area - polygon.area) < 1e-10, name
        base = len(points)
        points.extend(np.c_[q, np.full(len(q), plane_z)].tolist())
        # Render the retained +Z half, whose section normal points toward -Z.
        for a, b, c in t:
            ab, ac = q[b] - q[a], q[c] - q[a]
            if ab[0] * ac[1] - ab[1] * ac[0] > 0:
                b, c = c, b
            faces.append([base + int(a), base + int(b), base + int(c)])
    caps[name] = {'points': points, 'faces': faces}
    checks[name].update({'triangles': len(faces),
                    'area_m2': sum(poly.area for poly in accepted), 'holesPreserved': sum(len(poly.interiors) for poly in accepted)}
                         )
record = {'assetSha256': manifest['glbSha256'], 'planeZ_m': plane_z, 'intersectionWeldTolerance_m': 1e-8,
          'caps': caps, 'checks': checks, 'scope': 'Computed actual GLB closed-volume sections. Generic head-context section excludes separately represented tissue sections. Intentionally open surfaces are not capped.'}
(out / 'computed-sections.json').write_text(json.dumps(record, separators=(',', ':')) + '\n')
print(json.dumps({'closedTissueSections': checks, 'openContextCapped': False}, indent=2))
