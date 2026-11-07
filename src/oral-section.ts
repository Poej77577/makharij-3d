import * as THREE from 'three';

/** Real sections of current morph positions; no rest-pose cap is reused. */
export function sectionCap(mesh: THREE.Mesh, planeZ: number) {
  const geometry = mesh.geometry;
  const position = geometry.getAttribute('position');
  const index = geometry.index;
  const points: THREE.Vector3[] = [];
  for (let i = 0; i < position.count; i++) {
    points.push(mesh.getVertexPosition(i, new THREE.Vector3()).applyMatrix4(mesh.matrixWorld));
  }
  const graph = new Map<string, Set<string>>();
  const coordinates = new Map<string, THREE.Vector2>();
  const id = (point: THREE.Vector3) => `${Math.round(point.x / 1e-7)},${Math.round(point.y / 1e-7)}`;
  function connect(a: THREE.Vector3, b: THREE.Vector3) {
    const ka = id(a), kb = id(b);
    if (ka === kb) return;
    coordinates.set(ka, new THREE.Vector2(a.x, a.y));
    coordinates.set(kb, new THREE.Vector2(b.x, b.y));
    if (!graph.has(ka)) graph.set(ka, new Set());
    if (!graph.has(kb)) graph.set(kb, new Set());
    graph.get(ka)!.add(kb); graph.get(kb)!.add(ka);
  }
  const count = index?.count ?? position.count;
  for (let i = 0; i < count; i += 3) {
    const tri = [0, 1, 2].map(j => points[index ? index.getX(i + j) : i + j]);
    const hits: THREE.Vector3[] = [];
    for (let j = 0; j < 3; j++) {
      const a = tri[j], b = tri[(j + 1) % 3];
      const da = a.z - planeZ, db = b.z - planeZ;
      if ((da < 0 && db > 0) || (da > 0 && db < 0)) hits.push(a.clone().lerp(b, da / (da - db)));
    }
    if (hits.length === 2) connect(hits[0], hits[1]);
  }
  const visited = new Set<string>();
  const loops: THREE.Vector2[][] = [];
  let openChains = 0;
  for (const start of graph.keys()) {
    if (visited.has(start)) continue;
    const loop: THREE.Vector2[] = [];
    let current = start, previous = '';
    let closed = false;
    for (let step = 0; step <= graph.size; step++) {
      if (visited.has(current)) { closed = current === start; break; }
      visited.add(current); loop.push(coordinates.get(current)!);
      const next = [...graph.get(current)!].find(key => key !== previous);
      if (!next) break;
      previous = current; current = next;
    }
    if (closed && loop.length > 2) loops.push(loop); else openChains++;
  }
  loops.sort((a, b) => Math.abs(THREE.ShapeUtils.area(b)) - Math.abs(THREE.ShapeUtils.area(a)));
  function contains(loop: THREE.Vector2[], point: THREE.Vector2) {
    let inside = false;
    for (let i = 0, j = loop.length - 1; i < loop.length; j = i++) {
      const a = loop[i], b = loop[j];
      if ((a.y > point.y) !== (b.y > point.y) && point.x < (b.x - a.x) * (point.y - a.y) / (b.y - a.y) + a.x) inside = !inside;
    }
    return inside;
  }
  const parents = loops.map((loop, i) => {
    for (let j = i - 1; j >= 0; j--) if (contains(loops[j], loop[0])) return j;
    return -1;
  });
  const depth = (i: number): number => parents[i] < 0 ? 0 : 1 + depth(parents[i]);
  const vertices: number[] = [];
  loops.forEach((outer, i) => {
    if (depth(i) % 2) return;
    const holes = loops.filter((_, j) => parents[j] === i && depth(j) % 2 === 1);
    const all = [...outer, ...holes.flat()];
    for (const triangle of THREE.ShapeUtils.triangulateShape(outer, holes)) {
      for (const idx of triangle) vertices.push(all[idx].x, all[idx].y, planeZ + 1e-6);
    }
  });
  const cap = new THREE.BufferGeometry();
  cap.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  cap.computeVertexNormals();
  return {geometry: cap, loops: loops.length, openChains};
}
