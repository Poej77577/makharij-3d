"""Bounded geometric proof of two nasal inlets reaching one common outlet.

Actual exported positive mucosa, closed negative air envelope, and external
head TRIANGLE SURFACE are distinct inputs. Guide curves are suggestions only:
closed-air membership and swept finite-radius FCL capsules must validate them.
No head containment, flow simulation, clinical or full-airway anatomy claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import fcl
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from oral_contacts import bounded_rows, collision_object, mesh_from

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RADIUS = .00025

EXPORTER = r'''
import bpy,json,sys
from pathlib import Path
import numpy as np
c=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
chosen={}
for role,filename in [('wall','wall.glb'),('air','air.glb'),('face','face.glb')]:
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(Path(c['cache'])/filename))
    arrived=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
    if role=='wall':
        if not arrived or any(not o.name.startswith('NASAL_MUCOSA') and not o.name.startswith('NASAL_SEPTUM') for o in arrived):
            raise RuntimeError('Runtime GLB must contain positive nasal wall parts only')
        for i,o in enumerate(sorted(arrived,key=lambda o:o.name)):
            chosen['WALL'+str(i)]=o
    else:
        name='NASAL_AIR_NEGATIVE' if role=='air' else 'HEAD_EXTERNAL'
        selected=[o for o in arrived if o.name==name]
        if len(selected)!=1 or (role=='air' and len(arrived)!=1):
            raise RuntimeError('Expected actual '+name+' in '+role+' GLB')
        chosen[role.upper()]=selected[0]
for o in bpy.context.scene.objects:
    o.animation_data_clear()
    if o.type=='MESH' and o.data.shape_keys:
        o.data.shape_keys.animation_data_clear()
        for key in o.data.shape_keys.key_blocks[1:]:key.value=0
        o.data.shape_keys.update_tag()
bpy.context.view_layer.update()
arrays={}
for key,original in chosen.items():
    o=original.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m=o.to_mesh();m.calc_loop_triangles()
    points=[o.matrix_world@v.co for v in m.vertices]
    arrays[key+'_vertices']=np.array([(-p.y,p.z,-p.x) for p in points],dtype=np.float64)
    arrays[key+'_faces']=np.array([t.vertices for t in m.loop_triangles],dtype=np.int32)
    o.to_mesh_clear()
np.savez_compressed(Path(c['cache'])/'geometry.npz',**arrays)
Path(c['cache'],'parts.json').write_text(json.dumps({k:o.name for k,o in chosen.items()},indent=2)+'\n')
'''


def mm_mesh(mesh):
    return trimesh.Trimesh(mesh.vertices*1000, mesh.faces, process=False)


def contains_closed(mesh, points):
    if not mesh.is_volume:
        raise ValueError('Containment requires a closed, consistently wound positive volume')
    numerical = mm_mesh(mesh)
    points = np.asarray(points, dtype=float).reshape((-1, 3))
    result = []
    for start in range(0, len(points), 128):
        result.extend(numerical.contains(points[start:start+128]*1000))
    return np.array(result, dtype=bool)


def nearest_mm(mesh, points):
    numerical = mm_mesh(mesh)
    points = np.asarray(points, dtype=float).reshape((-1, 3))
    distances = []
    for start in range(0, len(points), 128):
        distances.extend(numerical.nearest.on_surface(points[start:start+128]*1000)[1]/1000)
    return np.array(distances)


def capsule(a, b, radius):
    delta = b-a
    length = float(np.linalg.norm(delta))
    if length <= 1e-12:
        return fcl.CollisionObject(fcl.Sphere(radius), fcl.Transform(a))
    rotation = trimesh.geometry.align_vectors([0, 0, 1], delta/length)[:3, :3]
    return fcl.CollisionObject(fcl.Capsule(radius, length), fcl.Transform(rotation, (a+b)/2))


def stroke_clearance(points, obstacles, radius):
    """Prove a continuous swept ball of radius r avoids triangle obstacles.

    A positive surface separation d gives a conservative centreline clearance
    r+d along this chosen polyline, not the maximum possible lumen radius.
    """
    minimum, limiting, failures = None, None, []
    by_obstacle, blocked_obstacles = {}, set()
    for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
        probe = capsule(a, b, radius)
        for name, surface in obstacles.items():
            contact = fcl.CollisionResult()
            fcl.collide(probe, surface, fcl.CollisionRequest(num_max_contacts=4, enable_contact=True), contact)
            if contact.is_collision:
                blocked_obstacles.add(name)
                failures.append({'segment': i, 'obstacle': name, 'from_m': a.tolist(), 'to_m': b.tolist(),
                                 'fclContactPositions_m': [np.array(v.pos).tolist() for v in contact.contacts]})
                continue
            result = fcl.DistanceResult()
            distance = fcl.distance(probe, surface, fcl.DistanceRequest(enable_nearest_points=True), result)
            if distance < 0 or not np.isfinite(distance):
                blocked_obstacles.add(name)
                failures.append({'segment': i, 'obstacle': name, 'invalidFclDistance': float(distance)})
                continue
            clearance = radius+float(distance)
            by_obstacle[name] = min(clearance, by_obstacle.get(name, clearance))
            if minimum is None or clearance < minimum:
                minimum = clearance
                limiting = {'segment': i, 'obstacle': name,
                            'nearestCapsuleAndSurfacePoints_m': np.array(result.nearest_points).tolist()}
    physical = [name for name in obstacles if name != 'NEGATIVE_AIR_BOUNDARY_ONLY']
    physical_minimum = min((by_obstacle[name] for name in physical if name in by_obstacle), default=None)
    if any(name in blocked_obstacles for name in physical):
        physical_minimum = None
    return {'clearAtProbeRadius': not failures and minimum is not None,
            'probeRadius_m': radius, 'segmentsChecked': len(points)-1,
            'minimumTestedCenterlineClearance_m': minimum if not failures else None,
            'minimumWallOrContextCenterlineClearance_m': physical_minimum,
            'minimumCenterlineClearanceByObstacle_m': {name: value if name not in blocked_obstacles else None for name, value in by_obstacle.items()},
            'limitingSurface': limiting, 'collisionCount': len(failures), 'failures': failures[:12],
            'fclPenetrationDepthUsed': False}


def trim_polyline(points, amount):
    points = np.asarray(points, dtype=float)
    points = points[np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-12]]
    if len(points) < 2:
        raise ValueError('Guide path has fewer than two distinct points')
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    arc = np.r_[0., np.cumsum(lengths)]
    if arc[-1] <= 2*amount:
        raise ValueError('Guide path too short to trim analysis end caps')
    def at(distance):
        index = min(int(np.searchsorted(arc, distance, side='right'))-1, len(lengths)-1)
        return points[index]+(points[index+1]-points[index])*(distance-arc[index])/lengths[index]
    return np.vstack([at(amount), points[(arc > amount) & (arc < arc[-1]-amount)], at(arc[-1]-amount)])


def validate_contract(ports, paths):
    ids = [p['id'] for p in ports]
    if len(ids) != 3 or len(set(ids)) != 3 or sorted(p['role'] for p in ports) != ['inlet', 'inlet', 'outlet']:
        raise ValueError('Exactly two distinct inlet ports and one outlet are required')
    for port in ports:
        center, normal, ring = np.array(port['center_m']), np.array(port['inward_normal']), np.array(port['ring_vertex_positions_m'])
        if center.shape != (3,) or normal.shape != (3,) or ring.ndim != 2 or ring.shape[1] != 3 or len(ring) < 3:
            raise ValueError('Invalid finite port geometry')
        if not np.isfinite(np.r_[center, normal, ring.ravel()]).all() or abs(np.linalg.norm(normal)-1) > .001:
            raise ValueError('Ports require finite points and unit inward normals')
    inlet_ids = {p['id'] for p in ports if p['role'] == 'inlet'}
    outlet_id = next(p['id'] for p in ports if p['role'] == 'outlet')
    if len(paths) != 2 or {p['inlet'] for p in paths} != inlet_ids or any(p['outlet'] != outlet_id for p in paths):
        raise ValueError('Both inlet guides must reach the same sole outlet')
    by_id = {p['id']: p for p in ports}
    for path in paths:
        points = np.asarray(path['points_m'], dtype=float)
        if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or len(points) > 250 or not np.isfinite(points).all():
            raise ValueError('Each guide needs 2..250 finite 3D points')
        if np.linalg.norm(points[0]-by_id[path['inlet']]['center_m']) > 1e-5 or np.linalg.norm(points[-1]-by_id[outlet_id]['center_m']) > 1e-5:
            raise ValueError('Guide endpoints must match actual port centres within 0.01 mm')


def topology(mesh):
    components = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(mesh.faces)), min_len=1)
    euler = int(len(np.unique(mesh.faces))-len(mesh.edges_unique)+len(mesh.faces))
    genus = len(components)-euler/2
    return {'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
            'closedPositiveVolume': bool(mesh.is_volume), 'watertight': bool(mesh.is_watertight),
            'windingConsistent': bool(mesh.is_winding_consistent),
            'connectedComponents': len(components), 'eulerCharacteristic': euler,
            'genus': int(round(genus)) if mesh.is_watertight and mesh.is_winding_consistent and abs(genus-round(genus)) < 1e-8 else None,
            'volume_m3': float(mesh.volume) if mesh.is_volume else None}


def expected_topology(walls, air):
    wall = trimesh.util.concatenate(list(walls.values()))
    wall.merge_vertices(digits_vertex=10, merge_tex=True, merge_norm=True)
    wt, at = topology(wall), topology(air)
    passed = (wt['closedPositiveVolume'] and at['closedPositiveVolume']
              and wt['connectedComponents'] == at['connectedComponents'] == 1
              and wt['genus'] == 2 and at['genus'] == 0)
    return {'topologyPass': bool(passed), 'expectedWallGenus': 2, 'expectedAirGenus': 0,
            'wallGenus': wt['genus'], 'airGenus': at['genus'],
            'wallConnectedComponents': wt['connectedComponents'], 'airConnectedComponents': at['connectedComponents'],
            'wallWatertight': wt['watertight'], 'airWatertight': at['watertight'],
            'wallWindingConsistent': wt['windingConsistent'], 'airWindingConsistent': at['windingConsistent'],
            'wallEulerCharacteristic': wt['eulerCharacteristic'], 'airEulerCharacteristic': at['eulerCharacteristic']}


def evaluate(walls, air, contexts, ports, paths, radius=DEFAULT_RADIUS, coverage_samples=1024, require_airway_topology=True):
    validate_contract(ports, paths)
    statuses = {name: topology(mesh) for name, mesh in walls.items()}
    air_status = topology(air)
    topology_contract = expected_topology(walls, air)
    connected = trimesh.graph.connected_components(air.face_adjacency, nodes=np.arange(len(air.faces)), min_len=1)
    volume_contract = air.is_volume and len(connected) == 1 and all(m.is_volume for m in walls.values())
    if not volume_contract or require_airway_topology and not topology_contract['topologyPass']:
        return {'passed': False, 'volumeContractPass': bool(volume_contract), 'wallTopology': statuses,
                'airTopology': air_status, 'negativeAirConnectedComponents': len(connected),
                'strictAirwayTopologyRequired': require_airway_topology, **topology_contract,
                'reason': 'Actual air must be one genus-0 closed volume; runtime wall must be one genus-2 closed volume for the three-port shell. Both must be watertight and consistently wound.'}
    tissue_objects = {**{name: collision_object(mesh) for name, mesh in walls.items()},
                      **{name: collision_object(mesh) for name, mesh in contexts.items()}}
    all_objects = {**tissue_objects, 'NEGATIVE_AIR_BOUNDARY_ONLY': collision_object(air)}
    wall_union_surface = trimesh.util.concatenate(list(walls.values()))
    head = contexts.get('HEAD_EXTERNAL_SURFACE_ONLY')
    head_boundary_tree = None
    if head is not None:
        counts = np.bincount(head.edges_unique_inverse, minlength=len(head.edges_unique))
        boundary_vertices = np.unique(head.edges_unique[counts == 1])
        if len(boundary_vertices):
            head_boundary_tree = cKDTree(head.vertices[boundary_vertices])
    port_rows, per_inlet = [], []
    trim = max(.001, radius*3)
    by_id = {p['id']: p for p in ports}
    bridge_endpoints = {}
    for path in paths:
        points = np.asarray(path['points_m'], dtype=float)
        trimmed = trim_polyline(points, trim)
        bridge_endpoints[path['inlet']] = trimmed[0]
        # Different outgoing tangent samples are both covered by this port's
        # tested branches; the common endpoint is the exact same centre.
        bridge_endpoints.setdefault(path['outlet'], trimmed[-1])
        samples = np.vstack([trimmed, (trimmed[:-1]+trimmed[1:])/2])
        inside = contains_closed(air, samples)
        wall_inside = {name: int(contains_closed(mesh, samples).sum()) for name, mesh in walls.items()}
        proof = stroke_clearance(trimmed, all_objects, radius)
        proof['allTestedCentersInsideNegativeAir'] = bool(inside.all())
        proof['testedCenterSamples'] = len(samples)
        proof['centerSamplesInsidePositiveWall'] = wall_inside
        proof['passed'] = proof['clearAtProbeRadius'] and inside.all() and not any(wall_inside.values())
        proof['inlet'] = path['inlet']; proof['outlet'] = path['outlet']
        proof['trimmedPath_m'] = trimmed.tolist()
        # Include each guide's outlet tangent, so a second guide cannot reach
        # the shared cap through an untested corner.
        center = np.array(by_id[path['outlet']]['center_m'], dtype=float)
        proof['outletBridgeToCommonCenter'] = stroke_clearance(np.vstack([trimmed[-1], center]), tissue_objects, radius)
        proof['passed'] = bool(proof['passed'] and proof['outletBridgeToCommonCenter']['clearAtProbeRadius'])
        per_inlet.append(proof)
    for port in ports:
        center = np.array(port['center_m'], dtype=float)
        normal = np.array(port['inward_normal'], dtype=float)
        outside = center-normal*.0015
        bridge = np.vstack([outside, center, bridge_endpoints[port['id']]])
        proof = stroke_clearance(bridge, tissue_objects, radius)
        ring_distances = nearest_mm(wall_union_surface, port['ring_vertex_positions_m'])
        normal_inside = bool(contains_closed(air, [center+normal*trim])[0])
        outside_air = not bool(contains_closed(air, [outside])[0])
        cap_distance = float(nearest_mm(air, [center])[0])
        face_boundary_distance = None
        if port['role'] == 'inlet' and head is not None:
            face_boundary_distance = float(head_boundary_tree.query(port['ring_vertex_positions_m'])[0].max()) if head_boundary_tree is not None else None
        proof.update({'id': port['id'], 'role': port['role'], 'center_m': center.tolist(),
                      'inwardNormalPointsInsideActualAir': normal_inside,
                      'outsideProbeOutsideActualAir': outside_air,
                      'portCenterDistanceToClosedAirBoundary_m': cap_distance,
                      'ringMaximumDistanceToPositiveWall_m': float(ring_distances.max()),
                      'ringWallBindingTolerance_m': .00035,
                      'inletRingMaximumDistanceToActualHeadBoundary_m': face_boundary_distance,
                      'inletFaceBoundaryBindingTestRun': port['role'] == 'inlet' and head is not None,
                      'analysisAirCapExcludedFromOpeningTest': True})
        face_ring_ok = head is None or port['role'] != 'inlet' or face_boundary_distance is not None and face_boundary_distance <= .00035
        proof['passed'] = bool(proof['clearAtProbeRadius'] and normal_inside and outside_air and cap_distance <= .00035 and ring_distances.max() <= .00035 and face_ring_ok)
        port_rows.append(proof)
    # Distinguish the negative envelope from an arbitrary labelled air solid:
    # its sampled boundary must meet positive mucosa except at the three
    # measured port regions. This is sampled coverage, not a micro-leak audit.
    probes = bounded_rows(air.triangles_center, coverage_samples)
    distances = nearest_mm(wall_union_surface, probes)
    in_port = np.zeros(len(probes), dtype=bool)
    for port in ports:
        center, normal = np.array(port['center_m']), np.array(port['inward_normal'])
        ring = np.array(port['ring_vertex_positions_m'])-center
        axial_ring = ring@normal
        radial_ring = np.linalg.norm(ring-axial_ring[:, None]*normal, axis=1)
        delta = probes-center; axial = delta@normal
        radial = np.linalg.norm(delta-axial[:, None]*normal, axis=1)
        in_port |= (np.abs(axial) <= np.abs(axial_ring).max()+.0005) & (radial <= radial_ring.max()+.0005)
    uncovered = (distances > .0004) & ~in_port
    coverage = {'samples': len(probes), 'wallCoverageTolerance_m': .0004,
                'unexpectedUncoveredBoundarySamples': int(uncovered.sum()),
                'uncoveredWitnesses_m': bounded_rows(probes[uncovered], 12).tolist(),
                'passed': not bool(uncovered.any())}
    passed = all(p['passed'] for p in per_inlet+port_rows) and coverage['passed']
    strokes = per_inlet+port_rows+[p['outletBridgeToCommonCenter'] for p in per_inlet]
    physical_minimum = min((p['minimumWallOrContextCenterlineClearance_m'] for p in strokes if p['minimumWallOrContextCenterlineClearance_m'] is not None), default=None)
    return {'passed': bool(passed), 'volumeContractPass': True, 'wallTopology': statuses,
            'airTopology': air_status, 'negativeAirConnectedComponents': len(connected),
            'strictAirwayTopologyRequired': require_airway_topology, **topology_contract,
            'ports': port_rows, 'perInlet': per_inlet, 'sampledAirBoundaryWallCoverage': coverage,
            'twoInletsReachCommonOutletAtProbeRadius': all(p['passed'] for p in per_inlet),
            'allThreePortsGeometricallyOpenAtProbeRadius': all(p['passed'] for p in port_rows),
            'certifiedPositiveCorridorRadius_m': radius if passed else None,
            'minimumWallOrContextCenterlineClearance_m': physical_minimum if passed else None,
            'commonPosteriorOutlet': next(p['id'] for p in ports if p['role'] == 'outlet'),
            'probeRadius_m': radius, 'externalHeadContainmentRun': False,
            'negativeAirIsRuntimeTissue': False, 'anatomyAccepted': False,
            'scope': 'Two provided guide paths validated against actual surfaces using finite-radius swept capsules; three explicit opening bridges; closed-air membership; sampled air-boundary wall coverage. This proves selected geometric corridors at the tested radius, not optimal cross-sectional area, all alternate paths, micro-leaks, motion, CFD, clinical or full nasal anatomy.'}


def fixture_air():
    """Exact rectilinear bifurcating solid; front septum ends at x=0."""
    xs, ys, zs = np.array([-20, 0, 30]), np.array([-5, 5]), np.array([-12, -1, 1, 12])
    occupied = {(0, 0, k) for k in range(3)} | {(1, 0, 0), (1, 0, 2)}
    vertices, faces, index = [], [], {}
    quads = [((-1,0,0),[(0,0,0),(0,0,1),(0,1,1),(0,1,0)]),
             ((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
             ((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
             ((0,1,0),[(0,1,0),(0,1,1),(1,1,1),(1,1,0)]),
             ((0,0,-1),[(0,0,0),(0,1,0),(1,1,0),(1,0,0)]),
             ((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)])]
    for i,j,k in sorted(occupied):
        for direction, corners in quads:
            if (i+direction[0], j+direction[1], k+direction[2]) in occupied:
                continue
            ids=[]
            for di,dj,dk in corners:
                key=(i+di,j+dj,k+dk)
                if key not in index:
                    index[key]=len(vertices);vertices.append([xs[key[0]],ys[key[1]],zs[key[2]]])
                ids.append(index[key])
            faces.extend([[ids[0],ids[1],ids[2]],[ids[0],ids[2],ids[3]]])
    return trimesh.Trimesh(np.array(vertices)/1000, faces, process=False)


def fixture_box(lo, hi):
    lo, hi = np.array(lo)/1000, np.array(hi)/1000
    mesh = trimesh.creation.box(extents=hi-lo)
    mesh.apply_translation((hi+lo)/2)
    return mesh


def fixture_inputs():
    walls={'TOP':fixture_box([-20,5,-14],[30,7,14]), 'BOTTOM':fixture_box([-20,-7,-14],[30,-5,14]),
           'SIDE_L':fixture_box([-20,-5,-14],[30,5,-12]), 'SIDE_R':fixture_box([-20,-5,12],[30,5,14]),
           'SEPTUM':fixture_box([0,-5,-1],[30,5,1])}
    ports=[]
    for name, z, z0, z1 in [('L',-6,-12,-1),('R',6,1,12)]:
        ports.append({'id':name,'role':'inlet','center_m':[.03,0,z/1000],'inward_normal':[-1,0,0],
                      'ring_vertex_positions_m':(np.array([[30,-5,z0],[30,5,z0],[30,5,z1],[30,-5,z1]])/1000).tolist()})
    ports.append({'id':'POSTERIOR','role':'outlet','center_m':[-.02,0,0],'inward_normal':[1,0,0],
                  'ring_vertex_positions_m':(np.array([[-20,-5,-12],[-20,5,-12],[-20,5,12],[-20,-5,12]])/1000).tolist()})
    paths=[{'inlet':name,'outlet':'POSTERIOR','points_m':(np.array([[30,0,z],[25,0,z],[5,0,z],[-5,0,z/2],[-15,0,z/6],[-20,0,0]])/1000).tolist()} for name,z in [('L',-6),('R',6)]]
    return walls, fixture_air(), ports, paths


def analytical_fixtures():
    walls,air,ports,paths=fixture_inputs()
    # These deliberately separate rectangular wall pieces exercise corridor
    # logic, not the monolithic three-port runtime shell topology contract.
    open_result=evaluate(walls,air,{},ports,paths,require_airway_topology=False)
    blocked=evaluate({**walls,'ACTUAL_LEFT_BRANCH_BLOCK':fixture_box([12,-5,-12],[13,5,-1])},air,{},ports,paths,require_airway_topology=False)
    cap=trimesh.Trimesh(np.array([[30,-5,-12],[30,5,-12],[30,5,-1],[30,-5,-1]])/1000,[[0,1,2],[0,2,3]],process=False)
    capped=evaluate(walls,air,{'OPEN_HEAD_SURFACE_CAP':cap},ports,paths,require_airway_topology=False)
    assert open_result['passed'], open_result
    assert not blocked['passed'] and not next(v for v in blocked['perInlet'] if v['inlet']=='L')['passed']
    assert next(v for v in blocked['perInlet'] if v['inlet']=='R')['passed']
    left_blocked = next(v for v in blocked['perInlet'] if v['inlet']=='L')
    assert left_blocked['centerSamplesInsidePositiveWall']['ACTUAL_LEFT_BRANCH_BLOCK'] == 0
    assert left_blocked['collisionCount'] > 0  # Obstruction lies between sampled guide centres.
    assert not cap.is_watertight and not capped['passed'] and not next(v for v in capped['ports'] if v['id']=='L')['passed']
    box = topology(trimesh.creation.box())
    torus = topology(trimesh.creation.torus(major_radius=.01, minor_radius=.002, major_sections=24, minor_sections=8))
    assert box['eulerCharacteristic'] == 2 and box['genus'] == 0 and box['connectedComponents'] == 1
    assert torus['eulerCharacteristic'] == 0 and torus['genus'] == 1 and torus['connectedComponents'] == 1
    return {'passed':True,'fixtureUnits':'metres; exact rectilinear two-inlet/common-outlet solids',
            'topologyFixtures': {'closedBox': box, 'closedTorus': torus},
            'openBilateralChannel':open_result,'leftBranchSolidBlock':blocked,
            'leftPortOpenTriangleSurfaceCap':capped,
            'assertions':'Open channel passes; actual one-branch tissue obstruction fails only that guided branch; open two-triangle cap blocks inlet without any head-volume operation.',
            'clinicalOrCFDValidation':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,default=ROOT/'artifacts/method-evidence/nasal-cavity')
    p.add_argument('--face-folder',type=Path,default=ROOT/'artifacts/method-evidence/face-context')
    p.add_argument('--manifest',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--probe-radius',type=float,default=DEFAULT_RADIUS)
    p.add_argument('--gate',action='store_true')
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    out=(a.out or a.folder/'qa').resolve();out.mkdir(parents=True,exist_ok=True)
    if a.self_test:
        report=analytical_fixtures()
        report['toolSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        report['helperSha256']=hashlib.sha256(Path(__file__).with_name('oral_contacts.py').read_bytes()).hexdigest()
        (out/'analytical-fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'passed':report['passed'],'report':str(out/'analytical-fixtures.json')}));return
    if not .00001<=a.probe_radius<=.002:
        raise ValueError('Probe radius must be finite and between 0.01 and 2 mm')
    manifest_path=a.manifest or a.folder/'nasal-manifest.json'
    manifest_bytes=manifest_path.read_bytes();manifest=json.loads(manifest_bytes)
    if manifest.get('gltfToProject')!=[[0,0,1],[0,1,0],[-1,0,0]]:
        raise ValueError('Unsupported canonical coordinate contract')
    sources={'wall':a.folder/'nasal-cavity.glb','air':a.folder/'nasal-airspace.analysis.glb','face':a.face_folder/'face-context.glb'}
    hashes={role:hashlib.sha256(path.read_bytes()).hexdigest() for role,path in sources.items()}
    if manifest.get('glbSha256') and manifest['glbSha256']!=hashes['wall']:
        raise ValueError('Runtime GLB/manifest mismatch')
    if manifest.get('analysisGlbSha256')!=hashes['air']:
        raise ValueError('Analysis negative-air GLB/manifest mismatch')
    if manifest.get('faceSourceGlbSha256')!=hashes['face']:
        raise ValueError('Nasal geometry was constructed against another external face')
    face_manifest=json.loads((a.face_folder/'face-manifest.json').read_text())
    if face_manifest['glbSha256']!=hashes['face']:
        raise ValueError('Face GLB/manifest mismatch')
    if face_manifest.get('gltfToProject')!=manifest['gltfToProject']:
        raise ValueError('Face and nasal assets do not share the canonical frame contract')
    cache_id=hashlib.sha256(json.dumps([hashes,EXPORTER],sort_keys=True).encode()).hexdigest()
    cache=Path('/workspace/research/nasal-airway-qa')/cache_id[:20];cache.mkdir(parents=True,exist_ok=True)
    for role,source in sources.items():
        frozen=cache/(role+'.glb')
        if not frozen.exists():shutil.copyfile(source,frozen)
        if hashlib.sha256(frozen.read_bytes()).hexdigest()!=hashes[role]:raise ValueError('Frozen GLB identity mismatch')
    config=cache/'export.json';config.write_text(json.dumps({'cache':str(cache)},indent=2))
    exporter=cache/'export.py';exporter.write_text(EXPORTER)
    if not (cache/'geometry.npz').exists():
        with (cache/'blender-export.log').open('w') as log:
            subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(exporter),'--',str(config)],check=True,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    parts=json.loads((cache/'parts.json').read_text())
    with np.load(cache/'geometry.npz') as data:
        meshes={name:mesh_from(data,name) for name in parts}
    walls={parts[k]:m for k,m in meshes.items() if k.startswith('WALL')}
    report=evaluate(walls,meshes['AIR'],{'HEAD_EXTERNAL_SURFACE_ONLY':meshes['FACE']},manifest['ports'],manifest['guide_paths'],a.probe_radius)
    report.update({'assetSha256':hashes['wall'],'airAssetSha256':hashes['air'],'faceAssetSha256':hashes['face'],
                   'manifestSha256':hashlib.sha256(manifest_bytes).hexdigest(),
                   'toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'helperSha256':hashlib.sha256(Path(__file__).with_name('oral_contacts.py').read_bytes()).hexdigest(),
                   'evaluatedGeometrySha256':hashlib.sha256((cache/'geometry.npz').read_bytes()).hexdigest(),
                   'frame':'+X anterior,+Y superior,+Z subject right; metres',
                   'evaluatedBy':'Blender actual GLB importer; evaluated rest world matrices; explicit zero morphs; no external head volume',
                   'wallParts':list(walls),'runtimeNegativeAirMeshFound':False,
                   'sourceAttribution':manifest.get('attribution',face_manifest.get('attribution','See source NOTICE.md'))})
    previous=out/'nasal-airway.json'
    if previous.exists():
        old=json.loads(previous.read_text())
        if any(old.get(k)!=report[k] for k in ['assetSha256','airAssetSha256','faceAssetSha256']):
            archive=out/'history'/hashlib.sha256(previous.read_bytes()).hexdigest()[:16]
            archive.mkdir(parents=True,exist_ok=True);shutil.copyfile(previous,archive/'nasal-airway.json')
    previous.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'assetSha256':hashes['wall'],'airAssetSha256':hashes['air'],'faceAssetSha256':hashes['face'],'report':str(previous)}))
    if a.gate and not report['passed']:raise SystemExit('Selected nasal airway geometry gate needs review')


if __name__=='__main__':main()
