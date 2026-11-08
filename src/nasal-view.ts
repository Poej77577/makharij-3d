import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {sectionCap} from './oral-section';

export type NasalManifest = {glbSha256: string; faceSourceGlbSha256: string; oralSourceGlbSha256: string;
  parts: string[]; recommendedSectionZ_m?: number; guidePaths_m: Record<string, number[][]>;
  ports: {name: string; center_m: number[]; inward_normal: number[]; ring_m: number[][]}[]};

export class NasalView {
  readonly group = new THREE.Group();
  readonly wallMeshes: THREE.Mesh[] = [];
  readonly guides = new THREE.Group();
  readonly cut = new THREE.Plane(new THREE.Vector3(0, 0, 1), -.005);
  manifest!: NasalManifest;
  private ghost?: THREE.Mesh;
  private caps = new THREE.Group();
  section = true;
  paths = true;
  private clay = false;
  setClay(value:boolean) {
    this.clay=value;
    for (const mesh of [...this.wallMeshes,...this.caps.children as THREE.Mesh[]]) (mesh.material as THREE.MeshStandardMaterial).color.set(value?'#aaa99e':'#bd776d');
  }

  constructor(scene: THREE.Scene) { scene.add(this.group); this.group.add(this.caps); this.group.visible = false; }

  async load(faceHash: string, oralHash: string, faceModel: THREE.Group) {
    const [metadata, response] = await Promise.all([fetch('/models/nasal-cavity.manifest.json'), fetch('/models/nasal-cavity.glb')]);
    if (!metadata.ok || !response.ok) throw new Error('Nasal assets unavailable');
    this.manifest = await metadata.json();
    const bytes = await response.arrayBuffer();
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');
    if (hash !== this.manifest.glbSha256 || faceHash !== this.manifest.faceSourceGlbSha256 || oralHash !== this.manifest.oralSourceGlbSha256) throw new Error('Nasal/face/oral version mismatch');
    const gltf = await new GLTFLoader().parseAsync(bytes, '/models/');
    gltf.scene.rotation.y = Math.PI / 2;
    this.group.add(gltf.scene);
    gltf.scene.traverse(object => {
      if (!(object as THREE.Mesh).isMesh) return;
      const mesh = object as THREE.Mesh;
      if (!this.manifest.parts.includes(mesh.name)) throw new Error('Unexpected nasal runtime mesh; negative air must stay analysis-only');
      const material = new THREE.MeshStandardMaterial({color: '#bd776d', roughness: .64, side: THREE.DoubleSide});
      material.clipShadows = true; mesh.material = material;
      mesh.castShadow = true; mesh.receiveShadow = true;
      this.wallMeshes.push(mesh);
    });
    if (this.wallMeshes.length !== this.manifest.parts.length) throw new Error('Incomplete nasal wall');
    this.cut.constant = -(this.manifest.recommendedSectionZ_m ?? .005);
    for (const [name,path] of Object.entries(this.manifest.guidePaths_m)) {
      const geometry = new THREE.BufferGeometry().setFromPoints(path.map(p => new THREE.Vector3(...p)));
      const line=new THREE.Line(geometry, new THREE.LineBasicMaterial({color: '#257f91', depthTest: true}));line.name=name;this.guides.add(line);
    }
    this.group.add(this.guides);
    faceModel.updateMatrixWorld(true);
    const head = faceModel.getObjectByName('HEAD_EXTERNAL') as THREE.Mesh;
    if (head) {
      this.ghost = new THREE.Mesh(head.geometry, new THREE.MeshBasicMaterial({color: '#b8b6a9', transparent: true, opacity: .11, depthWrite: false, side: THREE.DoubleSide}));
      this.ghost.matrixAutoUpdate = false; this.ghost.matrix.copy(head.matrixWorld);
      this.group.add(this.ghost);
    }
    this.update();
  }

  update() {
    for (const child of [...this.caps.children]) {
      const mesh = child as THREE.Mesh; mesh.geometry.dispose(); (mesh.material as THREE.Material).dispose(); this.caps.remove(mesh);
    }
    this.group.updateMatrixWorld(true);
    for (const mesh of this.wallMeshes) {const material=mesh.material as THREE.Material; material.clippingPlanes=this.section?[this.cut]:[];material.needsUpdate=true;}
    if (this.section) for (const mesh of this.wallMeshes) {
      const cut = sectionCap(mesh, -this.cut.constant);
      this.caps.add(new THREE.Mesh(cut.geometry, new THREE.MeshStandardMaterial({color:this.clay?'#aaa99e':'#bd776d', side:THREE.DoubleSide, roughness:.7, polygonOffset:true, polygonOffsetFactor:-1, polygonOffsetUnits:-1})));
    }
    if (this.ghost) {const material=this.ghost.material as THREE.Material;material.clippingPlanes=this.section?[this.cut]:[];material.needsUpdate=true;}
    this.guides.visible = this.paths;
    for (const line of this.guides.children) line.visible=!this.section || line.name==='right';
  }

  bounds() {
    this.group.updateMatrixWorld(true);
    const box = new THREE.Box3();
    for (const mesh of this.wallMeshes) box.union(new THREE.Box3().setFromObject(mesh));
    return box;
  }
}
