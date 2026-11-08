"""Continuous oral-surface study with a separate B-spline deformation cage.

Different from the rejected station loft: no AP ring poles/caps, no piecewise
ellipse replacement, no atlas tongue, no volume Boolean or remeshing. A smooth
periodic sagittal sculpt drives six welded quad patches. All dimensions inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/anatomy'))
from oral_clearance import LingualGingivalFit, lower_gingival_source
from oral_roof_refinement import refine_gingival_ends, make_posterior_soft_palate
p = argparse.ArgumentParser()
p.add_argument('--out', default='artifacts/method-evidence/oral-sculpt')
p.add_argument('--geometry-only', action='store_true')
p.add_argument('--spec', default='data/anatomy/oral-sculpt.json')
a = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT = (ROOT/a.out).resolve()
OUT.mkdir(parents=True, exist_ok=True)
spec_path = (ROOT/a.spec).resolve()
spec = json.loads(spec_path.read_text())
src = ROOT/'assets/source/z-anatomy/reference-meshes.json'
source_data = json.loads(src.read_text())['parts']
gingival_fit = LingualGingivalFit(*lower_gingival_source(source_data['ATLAS_GINGIVA']),
                                margin_m=spec.get('gingivalClearanceMargin_mm', .8)*.001)
gingival_fit_records = {}
roof_authoring = {'gingivalRefinement': {}}
soft_grid = None
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.fps = 24


def smooth(x):
    x = max(0, min(1, x))
    return x*x*(3-2*x)


def native(v):
    x, y, z = v
    return Vector((-z, -x, y))


def project(v):
    return Vector((-v.y, v.z, -v.x))


def collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


LOW = collection('LOW')
RIG = collection('RIG_CTRL')
REF = collection('REFERENCE_CONTEXT')


def material(name, color, roughness=.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bs = mat.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = roughness
    return mat


CLAY = material('Review clay', (.43, .43, .42), .8)
TONGUE_MAT = material('Tongue mucosa', (.40, .095, .085), .46)
FLOOR_MAT = material('Oral mucosa', (.47, .16, .14), .53)
TEETH_MAT = material('Enamel', (.82, .78, .66), .31)
BONE_MAT = material('Bone reference', (.63, .53, .35), .76)


def mesh_object(name, coords, faces, col=LOW, mat=CLAY):
    me = bpy.data.meshes.new(name+'_surface')
    me.from_pydata([native(v) for v in coords], [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for face in me.polygons:
        face.use_smooth = True
    me.materials.append(mat)
    return ob


def subdivide(ob, levels):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sub = ob.modifiers.new('Fixed sculpt subdivision before cage binding', 'SUBSURF')
    sub.levels = sub.render_levels = levels
    bpy.ops.object.modifier_apply(modifier=sub.name)


# Periodic contour spline through explicit anatomical shape landmarks.
# Interpolate the curve itself, not a high-order radial fit: radial Fourier
# regression on uneven angular samples causes ringing between landmarks.
center = np.array(spec['sagittalCenter_mm'], dtype=float)*.001
outline = np.array(spec['sagittalOutline_mm'], dtype=float)*.001
samples = []
for i in range(len(outline)):
    p0, p1, p2, p3 = [outline[j % len(outline)] for j in (i-1, i, i+1, i+2)]
    for t in np.linspace(0, 1, 40, endpoint=False):
        samples.append(.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
samples = np.array(samples)
sample_angles = np.mod(np.arctan2(samples[:, 1]-center[1], samples[:, 0]-center[0]), 2*math.pi)
sample_radii = np.linalg.norm(samples-center, axis=1)


def sculpt_point(cube):
    x, y, z = cube
    # Six-patch sphere parameterisation avoids tip/root closure poles.
    sx = x*math.sqrt(max(0, 1-y*y/2-z*z/2+y*y*z*z/3))
    sy = y*math.sqrt(max(0, 1-z*z/2-x*x/2+z*z*x*x/3))
    sz = z*math.sqrt(max(0, 1-x*x/2-y*y/2+x*x*y*y/3))
    r2 = sx*sx+sy*sy
    boundary = float(np.interp(math.atan2(sy, sx), sample_angles, sample_radii, period=2*math.pi))
    # At the lateral centre use an isotropic tangent disk, not a radial pinch.
    tangent_radius = spec.get('lateralTangentRadius_mm', 24)*.001
    radius = tangent_radius + r2*(boundary-tangent_radius)
    px, py = center + np.array([sx, sy])*radius
    width = spec['transverseHalfWidth_mm']*.001
    width *= (.83+.17*smooth((-px-.018)/.035))
    width *= (1-.13*smooth((-py-.018)/.012))
    width *= 1+spec.get('anteriorWidthFlare', 0)*smooth((px+.039)/.026)
    pz = sz*width
    # Inferred free-blade sculpt field on the same fixed quad patches. Advance
    # the anterior lateral blade to a broad rounded margin rather than leaving
    # the sphere parameterisation's pointed top silhouette. Basal tissue stays.
    blade = smooth((px+.051)/.027)*smooth((py+.024)/.014)
    lateral = smooth((abs(pz)/width-.15)/.65)
    px += spec.get('bladeLateralAdvance_mm', 0)*.001*blade*lateral
    shoulder = math.exp(-((abs(pz)-.008)/.006)**2)
    py += spec.get('bladeDorsalShoulder_mm', 0)*.001*blade*shoulder*smooth((py+.014)/.014)
    dorsal = smooth((py+.005)/.010)
    sulcus = .00055*math.exp(-(pz/.0032)**2)*math.exp(-((px+.038)/.024)**4)
    py -= dorsal*sulcus
    return (float(px), float(py), float(pz))


coords, faces, vertex_ids = [], [], {}
n = 18


def cube_vertex(values):
    key = tuple(values)
    if key not in vertex_ids:
        vertex_ids[key] = len(coords)
        coords.append(sculpt_point(tuple(v/n for v in values)))
    return vertex_ids[key]


for axis in range(3):
    others = [v for v in range(3) if v != axis]
    for side in (-n, n):
        grid = []
        for i in range(n+1):
            row = []
            for j in range(n+1):
                values = [0, 0, 0]
                values[axis] = side
                values[others[0]] = -n+2*i
                values[others[1]] = -n+2*j
                row.append(cube_vertex(values))
            grid.append(row)
        for i in range(n):
            for j in range(n):
                faces.append((grid[i][j], grid[i+1][j], grid[i+1][j+1], grid[i][j+1]))
tongue = mesh_object('TONGUE', coords, faces, mat=TONGUE_MAT)
tongue['source'] = 'Original six-patch anatomical surface; inferred dimensions'
tongue['review'] = 'experimental, not medically accepted'
subdivide(tongue, 2)
rest_coords = [project(v.co) for v in tongue.data.vertices]
if spec.get('fitLingualGingivalCavity', False):
    rest_coords, gingival_fit_records['rest'] = gingival_fit.fit(
        rest_coords, [list(face.vertices) for face in tongue.data.polygons],
        smoothing_iterations=spec.get('restClearanceSmoothingPasses', 32))
    for vertex, point in zip(tongue.data.vertices, rest_coords):
        vertex.co = native(point)
    tongue.data.update()

# A real closed mucosal annulus meets the actual root section. Its central
# opening is occupied by the tongue's basal body, not a plane through the tongue.
floor_y = spec['floorAttachmentHeight_mm']*.001


def attachment_height(point):
    theta = math.atan2(point[2], point[0]+.046)
    posterior = spec.get('floorAttachmentPosteriorOffset_mm', 9)*.001
    lateral = spec.get('floorAttachmentLateralOffset_mm', 3)*.001
    return floor_y+posterior*smooth((1-math.cos(theta))/2)+lateral*math.sin(theta)**2


bvh = BVHTree.FromPolygons(rest_coords, [list(p.vertices) for p in tongue.data.polygons])
origin = Vector((-.046, floor_y, 0))
segments, radial_steps = 128, 12
inner, outer = [], []
for j in range(segments):
    theta = 2*math.pi*j/segments
    direction = Vector((math.cos(theta), 0, math.sin(theta)))
    local_height = attachment_height(origin+direction*.02)
    local_origin = Vector((origin.x, local_height, 0))
    hit, normal, index, distance = bvh.ray_cast(local_origin, direction, .1)
    if hit is None:
        raise RuntimeError('Root/floor attachment section is not closed')
    inner.append(hit)
    # Outer boundary follows the oral arch; every value is an inferred fit.
    px = -.040+.034*math.cos(theta)
    pz = .027*math.sin(theta)*(1-.12*math.cos(theta))
    py = -.018-spec.get('floorOuterPosteriorDrop_mm', 6)*.001*(1-math.cos(theta))/2
    outer.append(Vector((px, py, pz)))
floor_coords = []
for lower in (False, True):
    for i in range(radial_steps+1):
        t = i/radial_steps
        blend = smooth(t)
        for j in range(segments):
            point = inner[j].lerp(outer[j], t)
            # A nonplanar mucosal saddle: lower beneath the free blade, higher
            # around the posterior/lateral root. Hermite falloff replaces the
            # horizontal belt; the inner outgoing slope forms a soft gutter.
            slope = -.007-.006*smooth((1-math.cos(2*math.pi*j/segments))/2)
            point.y = ((2*t**3-3*t*t+1)*inner[j].y+(t**3-2*t*t+t)*slope+
                       (-2*t**3+3*t*t)*outer[j].y)
            if lower:
                point.y -= spec['mucosalThickness_mm']*.001
            floor_coords.append(tuple(point))
layer = (radial_steps+1)*segments
floor_faces = []
for side in range(2):
    off = side*layer
    for i in range(radial_steps):
        for j in range(segments):
            k = (j+1)%segments
            face = (off+i*segments+j, off+(i+1)*segments+j, off+(i+1)*segments+k, off+i*segments+k)
            floor_faces.append(face if side == 0 else face[::-1])
for i in (0, radial_steps):
    for j in range(segments):
        k = (j+1)%segments
        floor_faces.append((i*segments+j, i*segments+k, layer+i*segments+k, layer+i*segments+j))
floor = mesh_object('ORAL_FLOOR', floor_coords, floor_faces, mat=FLOOR_MAT)
floor['source'] = 'Original closed mucosal surface; inner boundary sampled from actual tongue/root'

# A small, closed mucosal web joins the free ventrum to the floor. Its superior
# margin is sampled from the actual tongue, rather than floating above it.
web_vertices, web_faces = [], []
web_nx, web_ny = 18, 8
front_inner, front_outer = inner[0], outer[0]
web_start = front_inner.x+.001
web_end = max(point.x for point in rest_coords)-.004
if web_start >= web_end:
    raise RuntimeError('No free ventral span remains for the lingual frenulum')
for side in (-1, 1):
    for i in range(web_nx+1):
        x = web_start+(web_end-web_start)*i/web_nx
        hit, _, _, _ = bvh.ray_cast(Vector((x, -.060, 0)), Vector((0, 1, 0)), .1)
        if hit is None:
            raise RuntimeError('Frenulum ventral attachment not found')
        t = max(0, min(1, (x-front_inner.x)/(front_outer.x-front_inner.x)))
        low_y = ((2*t**3-3*t*t+1)*front_inner.y+(t**3-2*t*t+t)*(-.007)+
                 (-2*t**3+3*t*t)*front_outer.y)
        top_y = max(low_y+.0003, hit.y+.00015)
        for j in range(web_ny+1):
            v = j/web_ny
            web_vertices.append((x, low_y+(top_y-low_y)*v, side*.00027))
web_layer = (web_nx+1)*(web_ny+1)
for layer_id in range(2):
    for i in range(web_nx):
        for j in range(web_ny):
            q = layer_id*web_layer+i*(web_ny+1)+j
            web_faces.append((q, q+1, q+web_ny+2, q+web_ny+1))
web_edge = ([j for j in range(web_ny+1)]+[i*(web_ny+1)+web_ny for i in range(1, web_nx+1)]+
            [web_nx*(web_ny+1)+j for j in range(web_ny-1, -1, -1)]+[i*(web_ny+1) for i in range(web_nx-1, 0, -1)])
for k, idx in enumerate(web_edge):
    nxt = web_edge[(k+1)%len(web_edge)]
    web_faces.append((idx, nxt, web_layer+nxt, web_layer+idx))
frenulum = mesh_object('LINGUAL_FRENULUM', web_vertices, web_faces, mat=FLOOR_MAT)
frenulum['source'] = 'Inferred mucosal web, with actual floor/ventral attachment sampling'

# The hard-palatal vault is a thick curved surface. Its posterior edge shares
# coordinates with a deformable velum, so no pair of horizontal floating plates.
def palate_surface(x0, x1, name):
    nu, nv = 48, 32
    verts, polys = [], []
    for layer_id in range(2):
        for i in range(nu+1):
            whole_t = i/nu
            x = x0+(x1-x0)*whole_t
            soft = x < -.056
            t = (-x-.056)/.019 if soft else (-x-.009)/.047
            width = .017 if soft else .009+.010*math.sin(math.pi*t)**2+.008*smooth(t)
            for j in range(nv+1):
                v = 2*j/nv-1
                z = width*v
                y = (.020-.012*smooth(t) if soft else .013+.007*smooth(t))
                y += (.006 if soft else .010-.004*smooth(t))*(1-v*v)
                if soft:
                    # A central tissue extension, continuous with the velum.
                    uvular = math.exp(-(v/.17)**4)*smooth((t-.64)/.36)
                    y -= .009*uvular
                    x_local = x-.0025*uvular
                else:
                    x_local = x
                y += .0020*layer_id
                verts.append((x_local, y, z))
    count = (nu+1)*(nv+1)
    for layer_id in range(2):
        off = layer_id*count
        for i in range(nu):
            for j in range(nv):
                q = off+i*(nv+1)+j
                face = (q, q+1, q+nv+2, q+nv+1)
                polys.append(face if layer_id == 0 else face[::-1])
    perimeter = ([j for j in range(nv+1)] + [i*(nv+1)+nv for i in range(1, nu+1)] +
                 [nu*(nv+1)+j for j in range(nv-1, -1, -1)] + [i*(nv+1) for i in range(nu-1, 0, -1)])
    for k, idx in enumerate(perimeter):
        nxt = perimeter[(k+1)%len(perimeter)]
        polys.append((idx, nxt, count+nxt, count+idx))
    ob = mesh_object(name, verts, polys, mat=FLOOR_MAT)
    ob['source'] = 'Original inferred palatal tissue volume; not an acquired clinical surface'
    return ob


if not spec.get('useSourcePalatalMucosa', False):
    soft = palate_surface(-.009, -.075, 'PALATE')
    subdivide(soft, 1)
    soft['anatomical_regions'] = 'Hard palate anterior to X=-0.056m; soft palate/uvula posterior; shared continuous tissue mesh'

# Source dental context retains its native fit. Meshes are grouped by jaw and
# gingiva is split by actual connected components before any jaw articulation.
source_objects = []
for prefix, name in [('ATLAS_UPPER_', 'UPPER_DENTITION'), ('ATLAS_LOWER_', 'LOWER_DENTITION')]:
    verts, polys = [], []
    for key, part in source_data.items():
        if not key.startswith(prefix):
            continue
        offset = len(verts)
        pts, ids = part['positions'], part['indices']
        verts.extend([pts[i:i+3] for i in range(0, len(pts), 3)])
        polys.extend([tuple(v+offset for v in ids[i:i+3]) for i in range(0, len(ids), 3)])
    ob = mesh_object(name, verts, polys, mat=TEETH_MAT)
    ob['source'] = 'BodyParts3D / Z-Anatomy dental context, CC BY-SA 4.0'
    source_objects.append(ob)
part = source_data['ATLAS_GINGIVA']
gum_points = [part['positions'][i:i+3] for i in range(0, len(part['positions']), 3)]
gum_triangles = [part['indices'][i:i+3] for i in range(0, len(part['indices']), 3)]
parent = list(range(len(gum_points)))


def find(v):
    while parent[v] != v:
        parent[v] = parent[parent[v]]
        v = parent[v]
    return v


for tri in gum_triangles:
    for idx in tri[1:]:
        parent[find(idx)] = find(tri[0])
groups = {}
for tri in gum_triangles:
    groups.setdefault(find(tri[0]), []).append(tri)
gum_by_jaw = {'UPPER_GINGIVA': [], 'LOWER_GINGIVA': []}
for triangles in groups.values():
    ids = set(v for tri in triangles for v in tri)
    upper = sum(gum_points[v][1] for v in ids)/len(ids) > .004
    gum_by_jaw['UPPER_GINGIVA' if upper else 'LOWER_GINGIVA'].extend(triangles)
for name, triangles in gum_by_jaw.items():
    ids = sorted(set(v for tri in triangles for v in tri))
    index_map = {v: i for i, v in enumerate(ids)}
    points = [gum_points[v] for v in ids]
    faces = [tuple(index_map[v] for v in tri) for tri in triangles]
    if spec.get('refineGingivalEnds', False):
        dental = bpy.data.objects[name.replace('GINGIVA', 'DENTITION')]
        points, report = refine_gingival_ends(points, faces, [project(v.co) for v in dental.data.vertices],
                                            [list(face.vertices) for face in dental.data.polygons],
                                            'upper' if name.startswith('UPPER') else 'lower')
        roof_authoring['gingivalRefinement'][name] = report
    ob = mesh_object(name, points, faces, mat=FLOOR_MAT)
    attribute = ob.data.attributes.new('reference_vertex_id', 'INT', 'POINT')
    for value, source_id in zip(attribute.data, ids):
        value.value = source_id
    ob['source'] = 'BodyParts3D / Z-Anatomy; original connected gingival components grouped by jaw'
    ob['source_topology_retained'] = True
    ob['posterior_shape_refined'] = spec.get('refineGingivalEnds', False)
    source_objects.append(ob)
if spec.get('useSourcePalatalMucosa', False):
    upper = bpy.data.objects['UPPER_GINGIVA']
    roof_points, roof_faces, report = make_posterior_soft_palate(
        [project(v.co) for v in upper.data.vertices], [list(face.vertices) for face in upper.data.polygons])
    soft = mesh_object('PALATE', roof_points, roof_faces, mat=FLOOR_MAT)
    soft['source'] = 'Authored posterior soft-palate/uvular tissue fitted to real source palatal mucosa'
    soft['anatomical_regions'] = report['role']
    soft_grid = report['deformationGrid']
    roof_authoring['posteriorSoftPalate'] = report
for key in ['ATLAS_MANDIBLE', 'ATLAS_HYOID_BONE']:
    part = source_data[key]
    ref = mesh_object('REFERENCE_'+key, [part['positions'][i:i+3] for i in range(0, len(part['positions']), 3)],
                      [part['indices'][i:i+3] for i in range(0, len(part['indices']), 3)], col=REF, mat=BONE_MAT)
    ref.hide_render = True
    ref['source'] = 'BodyParts3D / Z-Anatomy reference; CC BY-SA 4.0'
REF.hide_render = True

# Editable B-spline cage. Its evaluated deformation is baked to delivery keys;
# Blender-only lattice support is never assumed in GLB or Three.js.
ld = bpy.data.lattices.new('TONGUE_BSPLINE_CAGE')
ld.points_u, ld.points_v, ld.points_w = 5, 14, 6
ld.interpolation_type_u = ld.interpolation_type_v = ld.interpolation_type_w = 'KEY_BSPLINE'
cage = bpy.data.objects.new(ld.name, ld)
RIG.objects.link(cage)
cage.location = native((-.042, -.009, 0))
# Changing lattice resolution changes the unscaled point extents in Blender.
# Fit the *measured* data bounds, not an assumed unit cube.
spans = [max(point.co_deform[i] for point in ld.points)-min(point.co_deform[i] for point in ld.points) for i in range(3)]
cage.scale = tuple(size/span for size, span in zip((.050, .080, .055), spans))
cage.hide_render = True
soft_targets = [tongue, frenulum]
modifiers = []
for ob in soft_targets:
    modifier = ob.modifiers.new('Authoring cage, baked for GLB', 'LATTICE')
    modifier.object = cage
    anchor = ob.vertex_groups.new(name='DEFORM_FREE_TISSUE')
    for vertex in ob.data.vertices:
        point = project(vertex.co)
        weight = smooth((point.y-attachment_height(point)-.002)/.014)
        anchor.add([vertex.index], weight, 'REPLACE')
    modifier.vertex_group = anchor.name
    modifiers.append(modifier)
cage_rest = [point.co_deform.copy() for point in ld.points]
bpy.context.view_layer.update()


def cage_pose(name):
    for point, base in zip(ld.points, cage_rest):
        v = project(cage.matrix_world@base)
        x, y, z = v
        if name == 'TIP_ELEVATE':
            weight = smooth((x+.040)/.030)
            angle = .62*weight
            pivot = Vector((-.033, -.012, z))
            dx, dy = x-pivot.x, y-pivot.y
            target = Vector((pivot.x+dx*math.cos(angle)-dy*math.sin(angle),
                             pivot.y+dx*math.sin(angle)+dy*math.cos(angle), z))
        elif name == 'DORSUM_ELEVATE':
            weight = math.exp(-((x+.043)/.018)**4)
            target = v+Vector((0, .007*weight, -.025*z*weight))
        else:
            weight = math.exp(-((x+.064)/.017)**4)
            target = v+Vector((-.0045*weight, -.001*weight, .02*z*weight))
        point.co_deform = cage.matrix_world.inverted()@native(target)
    ld.update_tag()
    bpy.context.view_layer.update()


motion = {}
baked = {ob.name: {} for ob in soft_targets}
volume_adjustments = {}
if not a.geometry_only:
    tongue.data.calc_loop_triangles()
    triangles = np.array([t.vertices for t in tongue.data.loop_triangles], dtype=np.int32)
    base = np.array([v.co[:] for v in tongue.data.vertices], dtype=np.float64)
    free_weights = np.array([smooth((p.y-attachment_height(p)-.002)/.014) for p in rest_coords])

    def volume(points):
        return float(np.einsum('ij,ij->i', points[triangles[:, 0]],
                               np.cross(points[triangles[:, 1]], points[triangles[:, 2]])).sum()/6)

    reference_volume = volume(base)
    for control in ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT']:
        cage_pose(control)
        for ob in soft_targets:
            evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            baked[ob.name][control] = [vertex.co.copy() for vertex in mesh.vertices]
            evaluated.to_mesh_clear()
            if ob == tongue:
                distances = [(p-v.co).length for p, v in zip(baked[ob.name][control], ob.data.vertices)]
                motion[control] = {'movedVertices': sum(v > 1e-7 for v in distances), 'maxDisplacement_m': max(distances)}
        # Geometric corrective, not a muscle simulation: preserve the closed
        # tongue's peak volume by redistributing free tissue laterally. The
        # floor attachment is pinned. Volume is affine in a single coordinate.
        posed = np.array([tuple(v) for v in baked[tongue.name][control]], dtype=np.float64)
        trial = posed.copy()
        trial[:, 0] *= 1+.01*free_weights  # native X is transverse
        before_volume, trial_volume = volume(posed), volume(trial)
        amount = .01*(reference_volume-before_volume)/(trial_volume-before_volume)
        if abs(amount) > .55:
            raise RuntimeError('Volume correction would distort the tissue excessively')
        volume_adjustments[control] = {'freeTransverseScaleDelta': amount,
                                       'uncorrectedVolumeChangeFraction': before_volume/reference_volume-1}
        for ob in soft_targets:
            for i, point in enumerate(baked[ob.name][control]):
                original = project(ob.data.vertices[i].co)
                weight = smooth((original.y-attachment_height(original)-.002)/.014)
                point.x *= 1+amount*weight
            if spec.get('fitLingualGingivalCavity', False):
                eligible = [smooth((p.y-attachment_height(p)-.002)/.014) > 1e-6
                            for p in (project(v.co) for v in ob.data.vertices)]
                fitted, record = gingival_fit.fit([project(p) for p in baked[ob.name][control]],
                                                  [list(face.vertices) for face in ob.data.polygons], eligible)
                baked[ob.name][control] = [native(p) for p in fitted]
                gingival_fit_records[control+'/'+ob.name] = record
        volume_adjustments[control]['afterGingivalFitVolumeChangeFraction'] = volume(
            np.array([tuple(v) for v in baked[tongue.name][control]], dtype=np.float64))/reference_volume-1
        distances = [(point-v.co).length for point, v in zip(baked[tongue.name][control], tongue.data.vertices)]
        motion[control]['maxDisplacement_m'] = max(distances)
    for point, base in zip(ld.points, cage_rest):
        point.co_deform = base
    for modifier in modifiers:
        modifier.show_viewport = modifier.show_render = False
    for ob in soft_targets:
        ob.shape_key_add(name='Basis')
        for control, points in baked[ob.name].items():
            key = ob.shape_key_add(name=control)
            for target, point in zip(key.data, points):
                target.co = point
    pivot = Vector(spec['jawPivot_mm'])*.001

    def jaw_point(point, amount=1):
        x, y, z = point
        angle = -math.radians(spec['jawOpen_degrees'])*amount
        dx, dy = x-pivot.x, y-pivot.y
        return Vector((pivot.x+dx*math.cos(angle)-dy*math.sin(angle),
                       pivot.y+dx*math.sin(angle)+dy*math.cos(angle), z))

    def jaw_weight(point):
        # Most of the tongue follows the jaw; a strongly pinned dorsum would
        # stretch its volume by ~20% at this diagnostic opening range.
        return 1-.12*smooth((point.y-attachment_height(point))/.025)

    for ob in [tongue, floor, frenulum]:
        if not ob.data.shape_keys:
            ob.shape_key_add(name='Basis')
        key = ob.shape_key_add(name='JAW_OPEN')
        for target, vertex in zip(key.data, ob.data.vertices):
            point = project(vertex.co)
            weight = jaw_weight(point) if ob in soft_targets else 1
            target.co = native(jaw_point(point, weight))
        if ob in soft_targets and spec.get('fitLingualGingivalCavity', False):
            eligible = [smooth((p.y-attachment_height(p)-.002)/.014) > 1e-6
                        for p in (project(v.co) for v in ob.data.vertices)]
            local = [jaw_point(project(v.co), -1) for v in key.data]
            fitted, record = gingival_fit.fit(local, [list(face.vertices) for face in ob.data.polygons], eligible)
            for target, point in zip(key.data, fitted):
                target.co = native(jaw_point(point))
            gingival_fit_records['JAW_OPEN/'+ob.name] = record
    # Teeth and gingiva use one actual rigid pivot, including intermediate
    # values; morph interpolation must not shrink a rigid dental arch.
    jaw_node = bpy.data.objects.new('JAW_PIVOT', None)
    RIG.objects.link(jaw_node)
    jaw_node.location = native(pivot)
    jaw_node.rotation_mode = 'XYZ'
    bpy.context.view_layer.update()
    for name in ['LOWER_DENTITION', 'LOWER_GINGIVA']:
        ob = bpy.data.objects[name]
        ob.parent = jaw_node
        ob.matrix_parent_inverse = jaw_node.matrix_world.inverted()
    jaw_driver = jaw_node.driver_add('rotation_euler', 0).driver
    jaw_driver.expression = 'jaw * '+str(math.radians(spec['jawOpen_degrees']))
    var = jaw_driver.variables.new()
    var.name = 'jaw'
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'KEY'
    var.targets[0].id = tongue.data.shape_keys
    var.targets[0].data_path = 'key_blocks["JAW_OPEN"].value'
    # Corrective deltas preserve the intended jaw transform of a tongue pose.
    # glTF carries the baked keys; the runtime uses jaw * tongue-control weights.
    for ob in soft_targets:
        keys = ob.data.shape_keys
        for control in ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT']:
            corrective = ob.shape_key_add(name='JAW_X_'+control)
            expected_points = []
            for i, vertex in enumerate(ob.data.vertices):
                base_point = project(vertex.co)
                deformed_point = project(keys.key_blocks[control].data[i].co)
                expected_points.append(jaw_point(deformed_point, jaw_weight(base_point)))
            if spec.get('fitLingualGingivalCavity', False):
                eligible = [smooth((p.y-attachment_height(p)-.002)/.014) > 1e-6
                            for p in (project(v.co) for v in ob.data.vertices)]
                fitted, record = gingival_fit.fit([jaw_point(p, -1) for p in expected_points],
                                                  [list(face.vertices) for face in ob.data.polygons], eligible)
                expected_points = [jaw_point(p) for p in fitted]
                gingival_fit_records['JAW_X_'+control+'/'+ob.name] = record
            for i, vertex in enumerate(ob.data.vertices):
                base = project(vertex.co)
                deformed = project(keys.key_blocks[control].data[i].co)
                expected = expected_points[i]
                additive = deformed + (project(keys.key_blocks['JAW_OPEN'].data[i].co)-base)
                corrective.data[i].co = native(base+expected-additive)
            driver = corrective.driver_add('value').driver
            driver.expression = 'jaw * tongue_control'
            for name, path in [('jaw', 'JAW_OPEN'), ('tongue_control', control)]:
                var = driver.variables.new()
                var.name = name
                var.type = 'SINGLE_PROP'
                var.targets[0].id_type = 'KEY'
                var.targets[0].id = keys
                var.targets[0].data_path = 'key_blocks["'+path+'"].value'
    soft.shape_key_add(name='Basis')
    key = soft.shape_key_add(name='VELUM_RAISE')
    for target, vertex in zip(key.data, soft.data.vertices):
        point = project(vertex.co)
        if soft_grid:
            u = (vertex.index % soft_grid['verticesPerLayer'])//(soft_grid['transverseSegments']+1)/soft_grid['longitudinalSegments']
            w = smooth((u-.15)/.85)
        else:
            w = smooth((-point.x-.056)/.019)
        target.co = native(point+Vector((-.0015*w, .009*w, 0)))
    controls = ['TIP_ELEVATE', 'DORSUM_ELEVATE', 'ROOT_RETRACT', 'JAW_OPEN', 'VELUM_RAISE']
    for ob in LOW.objects:
        if not ob.data.shape_keys:
            continue
        for control in controls:
            if control not in ob.data.shape_keys.key_blocks:
                continue
            key = ob.data.shape_keys.key_blocks[control]
            for frame in range(1, 242, 12):
                key.value = 0
                key.keyframe_insert('value', frame=frame)
            start = 1+48*controls.index(control)
            for offset, value in [(0, 0), (12, .5), (24, 1), (36, .5), (48, 0)]:
                key.value = value
                key.keyframe_insert('value', frame=start+offset)
        ob.data.shape_keys.animation_data.action.name = ob.name+'_DIAGNOSTICS'
        for curve in ob.data.shape_keys.animation_data.action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
scene.frame_end = 241
scene.frame_set(1)
if not a.geometry_only and any(v['maxDisplacement_m'] < .0005 for v in motion.values()):
    raise RuntimeError('A cage control did not produce meaningful surface deformation')
scene['status'] = 'Experimental oral sculpt, no medical or Arabic articulation acceptance'
scene['project_to_blender'] = '(-z, -x, y)'
blend = OUT/'oral-unit.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
bpy.ops.object.select_all(action='DESELECT')
for ob in LOW.objects:
    ob.select_set(True)
if not a.geometry_only:
    jaw_node.select_set(True)
glb = OUT/'oral-unit.glb'
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
                         export_extras=True, export_morph=True, export_animations=True,
                         export_yup=True, export_force_sampling=True, export_frame_range=True)
manifest = {'status': 'experimental-review-pending', 'productionSelected': False,
            'visualReview': 'pending', 'expertAcceptance': 'pending', 'clinicalAccuracyClaim': False,
            'method': spec['method'], 'dimensionsInferred': True,
            'authoringSkill': '.agents/skills/blender-image-to-3d/SKILL.md',
            'specSha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            'sourceContextSha256': hashlib.sha256(src.read_bytes()).hexdigest(),
            'authoringCodeSha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in [Path(__file__).resolve(), ROOT/'tools/anatomy/oral_clearance.py',
                                                ROOT/'tools/anatomy/oral_roof_refinement.py']},
            'blendSha256': hashlib.sha256(blend.read_bytes()).hexdigest(),
            'glbSha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
            'gltfToProject': [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
            'tongueVertices': len(tongue.data.vertices), 'motion': motion,
            'peakVolumeCorrectives': volume_adjustments,
            'lingualGingivalFit': gingival_fit_records,
            'oralRoofAuthoring': roof_authoring,
            'anatomicalRoles': {'PALATE': 'posterior soft palate and uvula only' if soft_grid else 'authored hard/soft palate and uvula',
                                'UPPER_GINGIVA': 'source gingiva including palatal mucosal surface; no hard-palatal bone claim'},
            'cage': {'type': 'B-spline lattice', 'resolution': [5, 14, 6], 'exportedAs': 'evaluated morph targets'},
            'correctives': {'JAW_X_TIP_ELEVATE': ['JAW_OPEN', 'TIP_ELEVATE'],
                            'JAW_X_DORSUM_ELEVATE': ['JAW_OPEN', 'DORSUM_ELEVATE'],
                            'JAW_X_ROOT_RETRACT': ['JAW_OPEN', 'ROOT_RETRACT']},
            'jawBinding': {'node': 'JAW_PIVOT', 'gltfAxis': 'X',
                           'angle_radians': math.radians(spec['jawOpen_degrees']),
                           'rigidParts': ['LOWER_DENTITION', 'LOWER_GINGIVA']},
            'floorAttachment': {'method': '128 actual BVH root hits at a nonplanar mucosal saddle',
                                'heightRange_m': [min(p.y for p in inner), max(p.y for p in inner)],
                                'innerSeamPoints_m': [list(p) for p in inner],
                                'floorIsClosedVolume': True, 'genialAndHyoidInsertionValidated': False},
            'frenulumAttachment': {'longitudinalSegments': web_nx, 'verticalSegments': web_ny,
                                   'floorVertices': [side*web_layer+i*(web_ny+1) for side in range(2) for i in range(web_nx+1)],
                                   'tongueVertices': [side*web_layer+i*(web_ny+1)+web_ny for side in range(2) for i in range(web_nx+1)],
                                   'intentionalTongueEmbedding_m': .00015,
                                   'scope': 'Both actual web margins; finite surface-distance samples, not all interface topology'},
            'parts': [ob.name for ob in LOW.objects],
            'limitations': ['Inferred art anatomy, not a scan', 'No contact-constrained biomechanics',
                            'No phoneme calibration or classroom approval', 'Floor/palatal relationships require visual review'],
            'attribution': 'BodyParts3D / DBCLS / Kousaku Okubo; Z-Anatomy / Gauthier Kervyn, CC BY-SA 4.0 dental/reference geometry; see assets/source/z-anatomy/NOTICE.md'}
(OUT/'oral-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({'blend': str(blend), 'tongueVertices': len(tongue.data.vertices), 'motion': motion}, indent=2))
