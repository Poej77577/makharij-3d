"""Asset-format adapters. No upstream program logic or primitive anatomy.

Coordinates remain explicit; fitting helpers are metadata, never final organs.
"""
from collections import Counter
from pathlib import Path
import hashlib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

def load_obj(path):
    points, faces, uv, face_uv = [], [], [], []
    groups = {}
    group = ''
    for line in Path(path).read_text().splitlines():
        row = line.split()
        if not row:
            continue
        if row[0] == 'v':
            points.append(list(map(float, row[1:4])))
        elif row[0] == 'vt':
            uv.append(list(map(float, row[1:3])))
        elif row[0] == 'g':
            group = ' '.join(row[1:])
        elif row[0] == 'f':
            fields = [x.split('/') for x in row[1:]]
            groups.setdefault(group, []).append(len(faces))
            faces.append([int(x[0]) - 1 for x in fields])
            face_uv.append([int(x[1]) - 1 if len(x) > 1 and x[1] else -1 for x in fields])
    return {'points': np.asarray(points), 'faces': faces, 'uv': uv, 'face_uv': face_uv, 'groups': groups}

def group_vertices(obj, name):
    return sorted({i for f in obj['groups'][name] for i in obj['faces'][f]})

def apply_target(points, path, weight):
    for line in Path(path).read_text().splitlines():
        row = line.split()
        if row and not row[0].startswith('#'):
            index = int(row[0])
            if index < 0 or index >= len(points):
                raise ValueError('Target references a different base topology')
            points[index] += np.array(list(map(float, row[1:4]))) * weight

def makehuman_head_data(mouth_weight=.24):
    base = ROOT / 'assets/source/makehuman/makehuman/data'
    obj = load_obj(base / '3dobjs/base.obj')
    p = obj['points'].copy()
    for family in ['african', 'asian', 'caucasian']:
        apply_target(p, base / f'targets/macrodetails/{family}-male-young.target', 1 / 3)
    apply_target(p, base / 'targets/macrodetails/universal-male-young-averagemuscle-averageweight.target', 1)
    neutral = p.copy()
    for family in ['african', 'asian', 'caucasian']:
        apply_target(p, base / f'targets/expression/units/{family}/mouth-open.target', mouth_weight / 3)
    canonical = np.column_stack([p[:, 2] * .1, (p[:, 1] - 7) * .1, -p[:, 0] * .1])
    obj.update(rawPoints=p, neutralRawPoints=neutral, canonicalPoints=canonical)
    obj['landmarks'] = {name: canonical[group_vertices(obj, name)].mean(0) for name in obj['groups'] if name.startswith('joint-')}
    obj['fittingReferences'] = {name: canonical[group_vertices(obj, name)] for name in obj['groups'] if name.startswith('helper-')}
    return obj

def load_tetra_boundary(node_path, element_path):
    data = np.loadtxt(node_path)
    ids = data[:, 0].astype(int)
    index = {key: i for i, key in enumerate(ids)}
    points = data[:, 1:4]
    counts, oriented, tets = Counter(), {}, set()
    degenerates = 0
    for line in Path(element_path).read_text().splitlines():
        row = list(map(int, line.split()))
        if not row:
            continue
        nodes = list(dict.fromkeys(x for x in row[:8] if x > 0))
        if len(nodes) != 4:
            raise ValueError('This adapter accepts source four-node tetrahedra only')
        tet = tuple(index[n] for n in nodes)
        key = tuple(sorted(tet))
        if key in tets:
            raise ValueError('Duplicate source tetrahedron')
        tets.add(key)
        q = points[list(tet)]
        if abs(np.linalg.det(q[1:] - q[0])) < 1e-10:
            degenerates += 1
            continue
        for opposite in range(4):
            face = [tet[i] for i in range(4) if i != opposite]
            a, b, c = points[face]
            if np.dot(np.cross(b - a, c - a), points[tet[opposite]] - a) > 0:
                face[1], face[2] = face[2], face[1]
            fkey = tuple(sorted(face))
            counts[fkey] += 1
            oriented[fkey] = face
    if any(n > 2 for n in counts.values()):
        raise ValueError('Nonmanifold source tetrahedral incidence')
    faces = [oriented[k] for k, count in counts.items() if count == 1]
    used = sorted({i for face in faces for i in face})
    remap = {old: new for new, old in enumerate(used)}
    return {
        'points': points[used],
        'faces': np.array([[remap[i] for i in f] for f in faces]),
        'sourceNodeIds': ids[used],
        'cells': len(tets),
        'skippedDegenerateCells': degenerates,
    }

def canonical_vkh(points):
    """Source X lateral, Y anterior, Z superior; nominal native mm convention."""
    return np.column_stack([(points[:, 1] - 110) * .001, (points[:, 2] + 180) * .001, (points[:, 0] + 130) * .001])

def makehuman_eye_data(head):
    base = ROOT / 'assets/source/makehuman/makehuman/data/eyes'
    obj = load_obj(base / 'high-poly/high-poly.obj')
    p = head['rawPoints']
    scales, rows = {}, []
    reading = False
    for line in (base / 'high-poly/high-poly.mhclo').read_text().splitlines():
        t = line.split()
        if not t or t[0].startswith('#'):
            continue
        if t[0] in ['x_scale', 'y_scale', 'z_scale']:
            axis = 'xyz'.index(t[0][0])
            scales[axis] = abs(p[int(t[1]), axis] - p[int(t[2]), axis]) / float(t[3])
        elif t[0] == 'verts':
            reading = True
        elif reading and t[0].lstrip('-').isdigit():
            rows.append(t)
        elif reading:
            reading = False
    if len(rows) != len(obj['points']):
        raise ValueError('Eye binding topology does not match its original mesh')
    fitted = []
    for row in rows:
        if len(row) != 9:
            raise ValueError('Unsupported proxy binding')
        ids = list(map(int, row[:3]))
        weights = np.array(list(map(float, row[3:6])))
        offsets = np.array(list(map(float, row[6:9])))
        fitted.append(weights @ p[ids] + offsets * np.array([scales[i] for i in range(3)]))
    q = np.array(fitted)
    obj['canonicalPoints'] = np.column_stack([q[:, 2] * .1, (q[:, 1] - 7) * .1, -q[:, 0] * .1])
    return obj

def uv_islands(obj, face_ids):
    """UV-island topology, independent of anatomical naming or acceptance."""
    links, edges = [], {}
    for local, face in enumerate(face_ids):
        uv = obj['face_uv'][face]
        for i in range(len(uv)):
            edge = tuple(sorted((uv[i], uv[(i + 1) % len(uv)])))
            if edge in edges:
                links.append((local, edges[edge]))
            else:
                edges[edge] = local
    parent = list(range(len(face_ids)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in links:
        a, b = find(a), find(b)
        parent[a] = b
    groups = {}
    for i, source_id in enumerate(face_ids):
        groups.setdefault(find(i), []).append(source_id)
    return list(groups.values())

def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
