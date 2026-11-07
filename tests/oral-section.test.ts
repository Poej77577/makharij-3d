import {describe, expect, it} from 'vitest';
import * as THREE from 'three';
import {sectionCap} from '../src/oral-section';

function area(geometry: THREE.BufferGeometry) {
  const p = geometry.getAttribute('position');
  let result = 0;
  for (let i = 0; i < p.count; i += 3) {
    result += Math.abs((p.getX(i + 1) - p.getX(i)) * (p.getY(i + 2) - p.getY(i)) -
      (p.getX(i + 2) - p.getX(i)) * (p.getY(i + 1) - p.getY(i))) / 2;
  }
  return result;
}

describe('actual deformed tissue sections', () => {
  it('preserves the analytical area of a rigidly transformed cube section', () => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2));
    mesh.position.set(.3, -.2, 0); mesh.rotation.z = .31; mesh.updateMatrixWorld(true);
    const cap = sectionCap(mesh, .15);
    expect(cap.openChains).toBe(0); expect(cap.loops).toBe(1);
    expect(area(cap.geometry)).toBeCloseTo(4, 5);
    const positions = cap.geometry.getAttribute('position');
    expect(positions.getZ(0)).toBeCloseTo(.150001, 7);
  });
  it('leaves a nested airspace empty', () => {
    const outer = new THREE.BoxGeometry(4, 4, 4).toNonIndexed().getAttribute('position');
    const inner = new THREE.BoxGeometry(2, 2, 2).toNonIndexed().getAttribute('position');
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute([...outer.array, ...inner.array], 3));
    const mesh = new THREE.Mesh(geometry); mesh.updateMatrixWorld(true);
    const cap = sectionCap(mesh, .15);
    expect(cap.openChains).toBe(0); expect(cap.loops).toBe(2);
    expect(area(cap.geometry)).toBeCloseTo(12, 5);
  });
  it('follows morph geometry and returns to the original section', () => {
    const geometry = new THREE.BoxGeometry(2, 2, 2);
    const base = geometry.getAttribute('position');
    const values = new Float32Array(base.count * 3);
    for (let i = 0; i < base.count; i++) values[i * 3 + 1] = .5 * base.getY(i);
    geometry.morphTargetsRelative = true;
    geometry.morphAttributes.position = [new THREE.Float32BufferAttribute(values, 3)];
    const mesh = new THREE.Mesh(geometry); mesh.updateMorphTargets(); mesh.updateMatrixWorld(true);
    mesh.morphTargetInfluences![0] = 1;
    expect(area(sectionCap(mesh, .15).geometry)).toBeCloseTo(6, 5);
    mesh.morphTargetInfluences![0] = 0;
    expect(area(sectionCap(mesh, .15).geometry)).toBeCloseTo(4, 5);
  });
});
