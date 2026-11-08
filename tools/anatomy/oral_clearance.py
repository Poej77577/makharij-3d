"""Bounded authoring fit to the actual lower gingival cavity, in project metres.

This is a geometric rest/endpoint fit, not a real-time collision solver or tissue
simulation. No FCL penetration depth, solid containment or clinical fit is used.
Actual exported triangle surfaces must be checked independently after fitting.
"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


def lower_gingival_source(part):
    points = [part['positions'][i:i+3] for i in range(0, len(part['positions']), 3)]
    faces = [part['indices'][i:i+3] for i in range(0, len(part['indices']), 3)]
    parent = list(range(len(points)))

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for face in faces:
        for v in face[1:]:
            parent[find(v)] = find(face[0])
    groups = {}
    for face in faces:
        groups.setdefault(find(face[0]), []).append(face)
    lower = []
    for group in groups.values():
        ids = {v for face in group for v in face}
        if sum(points[v][1] for v in ids)/len(ids) <= .004:
            lower.extend(group)
    if not lower:
        raise RuntimeError('Missing connected lower gingival source')
    return points, lower


class LingualGingivalFit:
    def __init__(self, points, faces, margin_m=.0008):
        ps = [Vector(p) for p in points]
        signed = sum(ps[f[0]].dot(ps[f[1]].cross(ps[f[2]])) for f in faces)/6
        oriented = faces if signed > 0 else [tuple(reversed(f)) for f in faces]
        self.bvh = BVHTree.FromPolygons(ps, oriented)
        self.source_points, self.source_faces = ps, oriented
        self.vertex_normals = [Vector() for _ in ps]
        for face in oriented:
            a, b, c = [ps[i] for i in face]
            normal = (b-a).cross(c-a)
            for i in face:
                self.vertex_normals[i] += normal
        self.vertex_normals = [n.normalized() for n in self.vertex_normals]
        self.margin = margin_m
        self._adjacency = {}

    def fit(self, points, faces, eligible=None, smoothing_iterations=4):
        ps = [Vector(p) for p in points]
        required = []
        entries = 0
        excluded_surfaces = 0
        for i, p in enumerate(ps):
            if eligible is not None and not eligible[i]:
                required.append(Vector((0, 0, 0)))
                continue
            near, normal, face_index, distance = self.bvh.find_nearest(p)
            if near is None or distance > .004:
                required.append(Vector())
                continue
            face = self.source_faces[face_index]
            interpolated = barycentric_transform(near, *[self.source_points[j] for j in face],
                                                  *[self.vertex_normals[j] for j in face]).normalized()
            if interpolated.dot(normal) > 0:
                normal = interpolated
            # Only the real lingual/crest-facing source surface is eligible.
            # Correct along its local normal, rather than pinching the blade
            # against a slice of the curved arch with a long axial ray.
            toward_cavity = Vector((-.045, .020, 0))-near
            if normal.dot(toward_cavity) <= 0:
                excluded_surfaces += 1
                required.append(Vector())
                continue
            entries += 1
            signed_normal_distance = (p-near).dot(normal)
            d = self.margin-signed_normal_distance
            blend = .0003
            amount = 0. if d <= -blend else d if d >= blend else (d+blend)**2/(4*blend)
            required.append(normal*amount)
        key = (len(ps), len(faces))
        if key not in self._adjacency:
            neighbors = [set() for _ in ps]
            for face in faces:
                for j, first in enumerate(face):
                    second = face[(j+1) % len(face)]
                    neighbors[first].add(second)
                    neighbors[second].add(first)
            self._adjacency[key] = neighbors
        displacement = [v.copy() for v in required]
        for _ in range(smoothing_iterations):
            next_displacement = []
            for i, (d, near) in enumerate(zip(displacement, self._adjacency[key])):
                mean = sum((displacement[j] for j in near), Vector())/max(1, len(near))
                average = .5*d+.5*mean
                req = required[i]
                if req.length_squared:
                    direction = req.normalized()
                    average += direction*max(0., req.length-average.dot(direction))
                if eligible is not None and not eligible[i]:
                    average = Vector()
                next_displacement.append(average)
            displacement = next_displacement
        maximum = max((d.length for d in displacement), default=0.)
        if maximum > .004:
            index = max(range(len(displacement)), key=lambda i: displacement[i].length)
            raise RuntimeError('Lower gingival fit needs a shape revision; exceeds 4 mm: '+str({
                'required_mm': maximum*1000, 'point_mm': [v*1000 for v in ps[index]],
                'excluded_facing_away_surfaces': excluded_surfaces}))
        fitted = [p+d for p, d in zip(ps, displacement)]
        largest = max(range(len(ps)), key=lambda i: displacement[i].length)
        return fitted, {
            'method': 'Actual lower-gingival lingual/crest nearest surface normals; bounded local authoring fit',
            'margin_m': self.margin, 'changedVertices': sum(d.length > 1e-9 for d in displacement),
            'maximumDisplacement_m': maximum, 'eligibleNearSurfaceQueries': entries,
            'maximumDisplacementSourcePoint_m': list(ps[largest]),
            'maximumDisplacementVector_m': list(displacement[largest]),
            'sourceNormalInterpolation': 'Area-weighted source vertex normals, barycentric at the actual nearest triangle',
            'smoothingIterations': smoothing_iterations,
            'excludedFacingAwaySurfaces': excluded_surfaces,
            'notCertifiedByFit': ['triangle clearance', 'all combinations', 'biomechanics', 'clinical registration'],
        }
