import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {sectionCap} from './oral-section';
import './oral-study.css';

const definitions = [
  ['TIP_ELEVATE', 'طرف اللسان'], ['DORSUM_ELEVATE', 'ظهر اللسان'],
  ['ROOT_RETRACT', 'سحب الجذر'], ['JAW_OPEN', 'فتح الفك'], ['VELUM_RAISE', 'رفع الحنك الرخو'],
] as const;
type Control = typeof definitions[number][0];
type Mode = 'floor' | 'whole' | 'section';
type Manifest = {glbSha256: string; parts: string[]; correctives: Record<string, [Control, Control]>;
  jawBinding: {node: string; angle_radians: number}; visualReview: string};
const state = Object.fromEntries(definitions.map(([key]) => [key, 0])) as Record<Control, number>;
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
<header><a class="brand" href="/anatomy.html"><span class="mark">م</span><span>مخارج<small>استكشاف أعضاء النطق</small></span></a><span class="status-badge">تجربة متحركة · قيد المراجعة</span></header>
<main><div class="intro"><p class="eyebrow">شاهد الحركة من الداخل</p><h1>اللسان والفم، بوضوح</h1><p>حرّك الأجزاء، دوّر النموذج، واستكشف المقطع الجانبي.</p></div>
<div class="workspace"><section class="viewer" aria-label="استكشاف الفم ثلاثي الأبعاد"><div class="view-tabs" aria-label="طريقة العرض"><button data-mode="floor" aria-pressed="true">اللسان والقاع</button><button data-mode="whole" aria-pressed="false">الفم</button><button data-mode="section" aria-pressed="false">المقطع الجانبي</button></div><div id="oral-stage"><canvas aria-label="نموذج الفم المتحرك، اسحب للدوران"></canvas><span class="stage-caption">اسحب للدوران · قرّب لاستكشاف التفاصيل</span><button id="camera-reset" class="camera-reset" aria-label="استعادة زاوية الرؤية">↺</button></div><div class="viewer-footer"><span id="load-status" role="status">جارٍ تحميل النموذج…</span><label class="clay-switch"><input id="clay" type="checkbox"> خامة محايدة</label></div></section>
<aside><div class="panel-heading"><span class="eyebrow">اكتشف بنفسك</span><h2>حركة الأعضاء</h2><p>ابدأ بعضو واحد، ثم جرّب دمج الحركات.</p></div><fieldset disabled id="controls"><legend class="sr-only">التحكم بالحركة</legend>${definitions.map(([key, label]) => `<label class="control-row" for="${key}"><span>${label}</span><output id="${key}-value">٠٪</output><input id="${key}" type="range" min="0" max="100" value="0" step="1" aria-label="${label}"></label>`).join('')}<div class="actions"><button id="play" class="primary">تشغيل الحركة</button><button id="rest">إعادة الوضع</button></div></fieldset><div class="anatomy-note"><strong id="part-name">اللسان</strong><p id="part-description">عضو عضلي تتغير هيئة طرفه وظهره وجذره أثناء النطق. اضغط على جزء من النموذج لاستكشافه.</p></div></aside></div>
<p class="review-note">هذه عينة تجريبية للفم. المراجعة التشريحية وضبط وضعيات الحروف لم يكتملا.</p><details><summary>عن هذه النسخة ومصادرها</summary><p>سطح اللسان والقاع والحنك إعادة تشكيل تعليمية بأبعاد مستنتجة. الأسنان واللثة من Z-Anatomy / BodyParts3D. لا يمثل النموذج تصويرًا طبيًا لشخص محدد.</p><p><a href="/models/oral-study.NOTICE.md">المصادر والترخيص</a> · <a href="/models/oral-study.glb" download>تنزيل النموذج التجريبي</a></p></details></main>`;

const stage = document.querySelector<HTMLDivElement>('#oral-stage')!;
const canvas = stage.querySelector('canvas')!;
const renderer = new THREE.WebGLRenderer({canvas, antialias: true, powerPreference: 'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.localClippingEnabled = true;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#e8ebe7');
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
scene.environment = pmrem.fromScene(room, .04).texture;
room.dispose(); pmrem.dispose();
scene.environmentIntensity = .55;
scene.add(new THREE.HemisphereLight(0xffffff, 0x6b7165, 1.15));
const light = new THREE.DirectionalLight(0xfff6ec, 2.2); light.position.set(.15, .2, -.15); scene.add(light);
const fill = new THREE.DirectionalLight(0xe3eeff, 1.3); fill.position.set(-.1, .1, .2); scene.add(fill);
const camera = new THREE.PerspectiveCamera(36, 1, .001, 10);
const orbit = new OrbitControls(camera, canvas);
orbit.enableDamping = true; orbit.dampingFactor = .12; orbit.minDistance = .055; orbit.maxDistance = .6;
const caps = new THREE.Group(); scene.add(caps);
const clipping = new THREE.Plane(new THREE.Vector3(0, 0, 1), -.00015);
const meshes: THREE.Mesh[] = [];
const originals = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
const roof = new Set(['PALATE', 'UPPER_DENTITION', 'UPPER_GINGIVA']);
const cutColors: Record<string, string> = {TONGUE: '#b76559', ORAL_FLOOR: '#c28676', LINGUAL_FRENULUM: '#c28676', PALATE: '#c28676', UPPER_GINGIVA: '#c28676', LOWER_GINGIVA: '#c28676', UPPER_DENTITION: '#e6dfcd', LOWER_DENTITION: '#e6dfcd'};
let manifest: Manifest, model: THREE.Group, jaw: THREE.Object3D | undefined;
let ready = false, mode: Mode = 'floor', clay = false, playing = false;
let scheduled = 0, geometryDirty = false, renderCount = 0, playStart = 0;
let capDiagnostics: Record<string, {loops: number; openChains: number}> = {};
const number = new Intl.NumberFormat('ar', {maximumFractionDigits: 0});

function draw() {
  if (scheduled) return;
  scheduled = requestAnimationFrame(time => {
    scheduled = 0;
    if (!ready) return;
    if (playing) {
      const t = ((time - playStart) / 2200) % definitions.length;
      definitions.forEach(([key], i) => state[key] = Math.floor(t) === i ? Math.sin(Math.PI * (t % 1)) ** 2 : 0);
      syncInputs(); applyState();
    }
    const moving = orbit.update();
    if (geometryDirty) updateCaps();
    renderer.render(scene, camera); renderCount++;
    if (playing || moving) draw();
  });
}
orbit.addEventListener('change', draw);
function syncInputs() {
  for (const [key] of definitions) {
    document.querySelector<HTMLInputElement>('#' + key)!.value = String(Math.round(state[key] * 100));
    document.querySelector('#' + key + '-value')!.textContent = number.format(state[key] * 100) + '٪';
  }
}
function applyState() {
  for (const mesh of meshes) {
    for (const [name, idx] of Object.entries(mesh.morphTargetDictionary ?? {})) {
      const correction = manifest.correctives[name];
      mesh.morphTargetInfluences![idx] = correction ? state[correction[0]] * state[correction[1]] : state[name as Control] ?? 0;
    }
  }
  if (jaw) jaw.rotation.x = state.JAW_OPEN * manifest.jawBinding.angle_radians;
  model.updateMatrixWorld(true); geometryDirty = true; draw();
}
function stop() { playing = false; document.querySelector('#play')!.textContent = 'تشغيل الحركة'; }
function resetCamera() {
  orbit.target.set(-.038, -.005, 0);
  camera.position.copy(orbit.target).add(mode === 'section' ? new THREE.Vector3(.006, .004, -.19) : new THREE.Vector3(.105, .112, -.11));
  camera.up.set(0, 1, 0); orbit.update(); draw();
}
function setMode(next: Mode) {
  mode = next;
  document.querySelectorAll<HTMLButtonElement>('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
  for (const mesh of meshes) {
    mesh.visible = mode !== 'floor' || !roof.has(mesh.name);
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      material.clippingPlanes = mode === 'section' ? [clipping] : [];
      material.needsUpdate = true;
    }
  }
  geometryDirty = true; resetCamera(); draw();
}
function updateCaps() {
  for (const child of [...caps.children]) {
    const mesh = child as THREE.Mesh;
    mesh.geometry.dispose(); (mesh.material as THREE.Material).dispose(); caps.remove(child);
  }
  capDiagnostics = {};
  if (mode === 'section') {
    for (const mesh of meshes.filter(mesh => mesh.visible)) {
      const cut = sectionCap(mesh, .00015);
      capDiagnostics[mesh.name] = {loops: cut.loops, openChains: cut.openChains};
      const source = (Array.isArray(mesh.material) ? mesh.material[0] : mesh.material) as THREE.MeshStandardMaterial;
      const material = new THREE.MeshStandardMaterial({color: clay ? source.color : cutColors[mesh.name] ?? source.color, roughness: .78, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1});
      const cap = new THREE.Mesh(cut.geometry, material); cap.name = mesh.name; caps.add(cap);
    }
  }
  geometryDirty = false;
}
function resize() {
  const {width, height} = stage.getBoundingClientRect();
  renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix(); draw();
}
new ResizeObserver(resize).observe(stage);
document.querySelectorAll<HTMLButtonElement>('[data-mode]').forEach(button => button.addEventListener('click', () => ready && setMode(button.dataset.mode as Mode)));
for (const [key] of definitions) document.querySelector<HTMLInputElement>('#' + key)!.addEventListener('input', event => {
  stop(); state[key] = Number((event.target as HTMLInputElement).value) / 100; syncInputs(); applyState();
});
document.querySelector('#rest')!.addEventListener('click', () => { stop(); definitions.forEach(([key]) => state[key] = 0); syncInputs(); applyState(); });
document.querySelector('#play')!.addEventListener('click', () => {
  playing = !playing; playStart = performance.now(); document.querySelector('#play')!.textContent = playing ? 'إيقاف الحركة' : 'تشغيل الحركة'; draw();
});
document.querySelector('#camera-reset')!.addEventListener('click', resetCamera);
document.querySelector<HTMLInputElement>('#clay')!.addEventListener('change', event => {
  clay = (event.target as HTMLInputElement).checked;
  for (const mesh of meshes) {
    if (clay) mesh.material = new THREE.MeshStandardMaterial({color: '#aaa99e', roughness: .83});
    else {
      if (mesh.material !== originals.get(mesh)) (mesh.material as THREE.Material).dispose();
      mesh.material = originals.get(mesh)!;
    }
  }
  setMode(mode);
});
const anatomy: Record<string, [string, string]> = {
  TONGUE: ['اللسان', 'يتصل طرف اللسان بنصله وظهره، ويمتد جذره نحو قاع الفم. جرّب رفع الطرف والظهر كلًا على حدة.'],
  ORAL_FLOOR: ['قاع الفم', 'تحيط أرضية الفم بقاعدة اللسان، وتبقى مقدمته حرة للحركة فوقها.'],
  LINGUAL_FRENULUM: ['لجام اللسان', 'طية مخاطية قصيرة تصل السطح البطني للسان بقاع الفم.'],
  PALATE: ['الحنك', 'يمتد الحنك الصلب في مقدمة سقف الفم، ويتصل به الحنك الرخو واللهاة خلفًا.'],
};
let pointerStart = new THREE.Vector2();
canvas.addEventListener('pointerdown', event => pointerStart.set(event.clientX, event.clientY));
canvas.addEventListener('pointerup', event => {
  if (!ready || pointerStart.distanceTo(new THREE.Vector2(event.clientX, event.clientY)) > 5) return;
  const box = canvas.getBoundingClientRect();
  const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2(2 * (event.clientX - box.left) / box.width - 1, 1 - 2 * (event.clientY - box.top) / box.height), camera);
  const hit = ray.intersectObjects(meshes.filter(mesh => mesh.visible)).find(hit => mode !== 'section' || hit.point.z >= .00015);
  if (!hit) return;
  const name = hit.object.name;
  const [label, text] = anatomy[name] ?? (name.includes('DENTITION') ? ['الأسنان', 'تساعد الأسنان وحوافها على تحديد مواضع تماس بعض الحروف. يتبع الصف السفلي حركة الفك.'] : ['اللثة', 'تحيط اللثة بأعناق الأسنان وتحدد حدود القوس السني.']);
  document.querySelector('#part-name')!.textContent = label; document.querySelector('#part-description')!.textContent = text;
});
Object.assign(window, {__oralStudy: {get ready() { return ready; }, snapshot() {
  model?.updateMatrixWorld(true);
  const probes: Record<string, number[][]> = {};
  for (const mesh of meshes) {
    const n = mesh.geometry.getAttribute('position').count;
    const indices = [0, n - 1];
    for (const target of mesh.geometry.morphAttributes.position ?? []) {
      let largest = -1, selected = 0;
      for (let i = 0; i < target.count; i++) {
        const length = target.getX(i) ** 2 + target.getY(i) ** 2 + target.getZ(i) ** 2;
        if (length > largest) { largest = length; selected = i; }
      }
      indices.push(selected);
    }
    probes[mesh.name] = indices.map(i => mesh.getVertexPosition(i, new THREE.Vector3()).applyMatrix4(mesh.matrixWorld).toArray());
  }
  const capSignatures = Object.fromEntries(caps.children.map(child => {
    const points = (child as THREE.Mesh).geometry.getAttribute('position');
    let sum = 0; for (let i = 0; i < points.count; i++) sum += (points.getX(i) + points.getY(i) * 3) * (i % 17 + 1);
    return [child.name, {triangles: points.count / 3, signature: sum}];
  }));
  return {ready, mode, clay, playing, state: {...state}, assetSha256: manifest?.glbSha256, parts: meshes.map(mesh => mesh.name), probes, capDiagnostics, capSignatures, camera: camera.position.toArray(), renderCount};
}}});

async function load() {
  try {
    const [meta, bytes] = await Promise.all([fetch('/models/oral-study.manifest.json').then(response => { if (!response.ok) throw new Error('manifest'); return response.json(); }), fetch('/models/oral-study.glb').then(response => { if (!response.ok) throw new Error('model'); return response.arrayBuffer(); })]);
    manifest = meta;
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(byte => byte.toString(16).padStart(2, '0')).join('');
    if (hash !== manifest.glbSha256) throw new Error('Model identity mismatch');
    const gltf = await new GLTFLoader().parseAsync(bytes, '/models/');
    model = gltf.scene; model.rotation.y = Math.PI / 2; scene.add(model);
    jaw = model.getObjectByName(manifest.jawBinding.node);
    model.traverse(object => {
      if (!(object as THREE.Mesh).isMesh) return;
      const mesh = object as THREE.Mesh;
      meshes.push(mesh); originals.set(mesh, mesh.material);
    });
    if (!jaw || meshes.length !== manifest.parts.length) throw new Error('Incomplete anatomical assembly');
    ready = true; (document.querySelector('#controls') as HTMLFieldSetElement).disabled = false;
    document.querySelector('#load-status')!.textContent = 'النموذج جاهز للاستكشاف';
    resize(); applyState(); setMode('floor');
  } catch (error) {
    document.querySelector('#load-status')!.textContent = 'تعذر تحميل النموذج. أعد تحميل الصفحة.';
    console.error(error);
  }
}
void load();
