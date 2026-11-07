"""Inspect actual exported atlas surfaces and derive only justified sections."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh
from section_geometry import closed_polygons
from shapely.ops import unary_union

p = argparse.ArgumentParser()
p.add_argument('--folder', required=True)
p.add_argument('--plane', type=float, default=.000001)
p.add_argument('--out-name', default='atlas-sections.json')
args = p.parse_args()
folder = Path(args.folder)
source = json.loads((folder / 'atlas-meshes.json').read_text())['parts']
manifest = json.loads((folder / 'atlas-study.manifest.json').read_text())
assert hashlib.sha256((folder / 'atlas-study.glb').read_bytes()).hexdigest() == manifest['glbSha256']
scene = trimesh.load_scene(folder / 'atlas-study.glb', process=False)
caps, checks, failures = {}, {}, []
all_regions = {}
grouped = {}
for node in scene.graph.nodes_geometry:
    transform, geometry = scene.graph[node]
    mesh = scene.geometry[geometry].copy()
    mesh.apply_transform(transform)
    name = node
    while name not in source:
        name = scene.graph.transforms.parents.get(name)
        assert name and name != 'world', node
    grouped.setdefault(name, []).append(mesh)
assert set(grouped) == set(source), 'Missing or extra delivered anatomy'
for node, primitives in grouped.items():
    mesh = trimesh.util.concatenate(primitives)
    original = source[node]
    q = np.array(original['positions']).reshape(-1, 3)
    error = float(cKDTree(q).query(mesh.vertices)[0].max())
    assert error < 1e-6, node
    assert len(mesh.faces) == len(original['indices']) // 3, node
    # UV islands and material primitives duplicate real shared vertices in GLB.
    # Topology is evaluated by position, independently of texture/normal seams.
    mesh.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
    valid_volume = bool(mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0)
    record = {'sourceObjectName': original['source']['sourceObjectName'], 'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
              'closedOutwardVolume': valid_volume, 'windingConsistent': bool(mesh.is_winding_consistent),
              'volume_m3': float(mesh.volume), 'positionMaxError_m': error, 'minimumArea_m2': float(mesh.area_faces.min()),
              'bounds_m': mesh.bounds.tolist()}
    checks[node] = record
    if not valid_volume:
        continue
    segments = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], [0, 0, args.plane])
    if not len(segments):
        continue
    try:
        polygons, contour_check = closed_polygons(segments[:, :, :2])
        regions = []
        for poly in polygons:
            r = poly.representative_point()
            if mesh.contains([[r.x, r.y, args.plane]])[0]:
                regions.append(poly)
        all_regions[node] = unary_union(regions)
        record['section'] = {'regions': len(regions), **contour_check}
    except (AssertionError, ValueError) as error:
        failures.append({'part': node, 'error': str(error)})

# Source envelopes intentionally nest muscle regions. Compose their exact
# cross-sections without coincident cap triangles or borrowed organ outlines.
# This is a rendering partition, not a claim that all original surfaces have
# been clinically segmented into disjoint tissue layers.
def priority(name):
    if name == 'HEAD_SKIN': return 9, name
    if name == 'ATLAS_TONGUE': return 8, name
    if any(s in name for s in ['INCISOR', 'CANINE', 'MOLAR', 'PREMOLAR']): return 0, name
    if any(s in name for s in ['BONE', 'MANDIBLE', 'MAXILLA', 'VOMER']): return 1, name
    if 'CARTILAGE' in name: return 2, name
    if 'GENIOGLOSSUS' in name: return 3, name
    if 'HYOGLOSSUS' in name: return 4, name
    if 'MUSCLE' in name or 'CONSTRICTOR' in name: return 5, name
    return 6, name
occupied = unary_union([])
overlaps = {}
for name in sorted(all_regions, key=priority):
    original = all_regions[name]
    overlaps[name] = float(original.intersection(occupied).area)
    all_regions[name] = original.difference(occupied)
    occupied = occupied.union(original)
for node, region in all_regions.items():
    try:
        def polygon_parts(value):
            if value.is_empty or value.area == 0: return []
            if value.geom_type == 'Polygon': return [value]
            return [p for child in value.geoms for p in polygon_parts(child)]
        regions = polygon_parts(region)
        points, faces = [], []
        for region in regions:
            v, f = trimesh.creation.triangulate_polygon(region, engine='earcut')
            assert abs(trimesh.Trimesh(np.c_[v, np.zeros(len(v))], f, process=False).area - region.area) < 1e-10
            start = len(points)
            points.extend(np.c_[v, np.full(len(v), args.plane)].tolist())
            for a, b, c in f:
                ab, ac = v[b] - v[a], v[c] - v[a]
                if ab[0] * ac[1] - ab[1] * ac[0] > 0:
                    b, c = c, b
                faces.append([start + int(a), start + int(b), start + int(c)])
        if faces:
            caps[node] = {'points': points, 'faces': faces}
        checks[node]['section']['triangles'] = len(faces)
    except (AssertionError, ValueError) as error:
        failures.append({'part': node, 'error': str(error)})
report = {'assetSha256': manifest['glbSha256'], 'parts': checks, 'planeZ_m': args.plane, 'caps': caps,
          'nestedRegionOverlapArea_m2': overlaps, 'capComposition': 'Disjoint exact tissue-section partition by recorded anatomical priority; no coincident cap triangles',
          'sectionFailures': failures, 'isAcceptedAnatomy': False,
          'scope': 'Actual GLB source identity and static volume/section diagnostics; open source tissues remain uncapped; no visual/expert approval'}
(folder / args.out_name).write_text(json.dumps(report, separators=(',', ':')) + '\n')
print(json.dumps({'parts': len(checks), 'closedVolumes': sum(c['closedOutwardVolume'] for c in checks.values()), 'sections': len(caps),
                  'sectionFailures': failures, 'tongue': checks.get('ATLAS_TONGUE')}, indent=2))
