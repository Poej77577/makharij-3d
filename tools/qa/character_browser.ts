/** Static M2 review harness. No production UI or articulation readiness claim. */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const WIDTH = 1280, HEIGHT = 860;
const canvas = document.querySelector('canvas')!;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(WIDTH, HEIGHT, false);
renderer.setClearColor(0xe3e5e4);
renderer.localClippingEnabled = true;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x66635e, 2));
for (const [position, intensity] of [ [[.5, .5, -.5], 2.2], [[.1, .1, .5], .8] ] as const) {
  const light = new THREE.DirectionalLight(0xffffff, intensity);
  light.position.set(...position);
  scene.add(light);
}
const model = (await new GLTFLoader().loadAsync('/__character.glb')).scene;
scene.add(model);
const section = await (await fetch('/__sections.json')).json();
const caps = new THREE.Group();
scene.add(caps);
let meshCount = 0, triangleCount = 0;
const clip = new THREE.Plane(new THREE.Vector3(0, 0, 1), -section.planeZ_m);
const materials: THREE.Material[] = [];
model.traverse(object => {
  if (!(object instanceof THREE.Mesh)) return;
  meshCount++;
  triangleCount += object.geometry.index ? object.geometry.index.count / 3 : object.geometry.attributes.position.count / 3;
  for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
    materials.push(material);
    material.side = THREE.DoubleSide;
  }
});
for (const [name, value] of Object.entries(section.caps) as [string, { points: number[][]; faces: number[][] }][]) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(value.points.flat(), 3));
  geometry.setIndex(value.faces.flat());
  geometry.computeVertexNormals();
  const source = model.getObjectByName(name) as THREE.Mesh;
  let material: THREE.MeshStandardMaterial;
  if (source && source.material) {
    material = (Array.isArray(source.material) ? source.material[0] : source.material).clone() as THREE.MeshStandardMaterial;
  } else material = new THREE.MeshStandardMaterial({ color: 0xb77969 });
  if (name === 'HEAD_SKIN') material.color.setRGB(.48, .29, .205);
  material.side = THREE.DoubleSide;
  material.roughness = .68;
  const cap = new THREE.Mesh(geometry, material);
  cap.name = name + ' computed volume section';
  caps.add(cap);
}
function camera(scale: number, center: THREE.Vector3) {
  const aspect = (WIDTH / 2) / HEIGHT;
  const camera = new THREE.OrthographicCamera(-scale * aspect / 2, scale * aspect / 2, scale / 2, -scale / 2, .01, 5);
  camera.up.set(0, 1, 0);
  camera.userData.center = center;
  return camera;
}
const external = camera(.40, new THREE.Vector3(.065, .05, 0));
const sagittal = camera(.29, new THREE.Vector3(.09, .03, 0));
sagittal.position.set(.09, .03, -.8);
sagittal.lookAt(sagittal.userData.center);
function render(yaw = Math.PI / 4) {
  external.position.copy(external.userData.center).add(new THREE.Vector3(Math.cos(yaw) * .8, .02, -Math.sin(yaw) * .8));
  external.lookAt(external.userData.center);
  renderer.setScissorTest(false);
  renderer.clear();
  renderer.setScissorTest(true);
  caps.visible = false;
  for (const material of materials) material.clippingPlanes = [];
  renderer.setViewport(0, 0, WIDTH / 2, HEIGHT);
  renderer.setScissor(0, 0, WIDTH / 2, HEIGHT);
  renderer.render(scene, external);
  caps.visible = true;
  for (const material of materials) material.clippingPlanes = [clip];
  renderer.setViewport(WIDTH / 2, 0, WIDTH / 2, HEIGHT);
  renderer.setScissor(WIDTH / 2, 0, WIDTH / 2, HEIGHT);
  renderer.render(scene, sagittal);
  renderer.setScissorTest(false);
  return { meshCount, triangleCount, sectionCaps: caps.children.length, rendererInstances: 1 };
}
const bounds = new THREE.Box3().setFromObject(model);
render();
Object.assign(window, { characterReview: { render, bounds: [bounds.min.toArray(), bounds.max.toArray()], meshCount, triangleCount, assetSha256: section.assetSha256 } });
