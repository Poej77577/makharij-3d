import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {sectionCap} from './oral-section';
import {NasalView} from './nasal-view';
import './oral-study.css';

const oralDefinitions = [
  ['TIP_ELEVATE', 'طرف اللسان'], ['DORSUM_ELEVATE', 'ظهر اللسان'],
  ['ROOT_RETRACT', 'سحب الجذر'], ['JAW_OPEN', 'فتح الفك'], ['VELUM_RAISE', 'رفع الحنك الرخو'],
] as const;
const lipDefinitions = [
  ['LIP_PRESS', 'ضغط الشفتين'], ['LIP_ROUND', 'ضمّ الشفتين'], ['LIP_PROTRUDE', 'بروز الشفتين'],
] as const;
const definitions = [...oralDefinitions, ...lipDefinitions] as const;
type Control = typeof definitions[number][0];
type Mode = 'floor' | 'whole' | 'section' | 'face' | 'nasal';
type Manifest = {glbSha256: string; parts: string[]; correctives: Record<string, [Control, Control]>;
  jawBinding: {node: string; angle_radians: number}; visualReview: string; anatomicalRoles?: Record<string, string>};
type FaceManifest = {glbSha256: string; oralSourceGlbSha256: string; parts: string[]; contextSurfaceOnly: boolean};
const state = Object.fromEntries(definitions.map(([key]) => [key, 0])) as Record<Control, number>;
document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
<header><a class="brand" href="/mouth.html"><span class="mark">م</span><span>مخارج<small>استكشاف أعضاء النطق</small></span></a><span class="status-badge">تجربة متحركة · قيد المراجعة</span></header>
<main><div class="intro"><p class="eyebrow">شاهد الحركة من الداخل والخارج</p><h1>الفم والوجه، بوضوح</h1><p>استكشف اللسان، وحرّك الشفتين والفك، وقارن المنظور الداخلي والخارجي.</p></div>
<div class="workspace"><section class="viewer" aria-label="استكشاف الفم والوجه ثلاثي الأبعاد"><div class="view-tabs" aria-label="طريقة العرض"><button data-mode="face" aria-pressed="true">الوجه</button><button data-mode="floor" aria-pressed="false">اللسان والقاع</button><button data-mode="whole" aria-pressed="false">الفم</button><button data-mode="section" aria-pressed="false">المقطع الجانبي</button></div><div id="oral-stage"><canvas aria-label="نموذج الفم والوجه المتحرك، اسحب للدوران"></canvas><span class="stage-caption">اسحب للدوران · قرّب لاستكشاف التفاصيل</span><button id="camera-reset" class="camera-reset" aria-label="استعادة زاوية الرؤية">↺</button></div><div class="viewer-footer"><span id="load-status" role="status">جارٍ تحميل النموذج…</span><label class="clay-switch"><input id="clay" type="checkbox" disabled> خامة محايدة</label></div></section>
<aside><div class="panel-heading"><span class="eyebrow">اكتشف بنفسك</span><h2 id="control-heading">الشفتان والفك</h2><p>ابدأ بعضو واحد، ثم جرّب دمج الحركات.</p></div><fieldset disabled id="controls"><legend class="sr-only">التحكم بالحركة</legend>${definitions.map(([key, label]) => `<label class="control-row" data-control="${key}" for="${key}"><span>${label}</span><output id="${key}-value">٠٪</output><input id="${key}" type="range" min="0" max="100" value="0" step="1" aria-label="${label}"></label>`).join('')}<div class="actions"><button id="play" class="primary">تشغيل الحركة</button><button id="rest">إعادة الوضع</button></div></fieldset><div class="anatomy-note"><strong id="part-name">الوجه والشفتان</strong><p id="part-description">الشفتان متصلتان بجلد الوجه وتتحركان مع فتح الفك. انتقل إلى العرض الداخلي لمقارنة حركة اللسان والأسنان.</p></div></aside></div>
<p class="review-note">هذه عينة فم تجريبية مع سياق خارجي للوجه. بقية التشريح الداخلي والمراجعة العلمية وضبط الحروف قيد العمل.</p><details><summary>عن هذه النسخة ومصادرها</summary><p>سطح اللسان والقاع والحنك إعادة تشكيل تعليمية بأبعاد مستنتجة. الأسنان واللثة من Z-Anatomy / BodyParts3D؛ الوجه والعينان وحركات الشفتين من أصول MakeHuman المرخّصة CC0. عرض الوجه غلاف خارجي، ولا يمثل تشريح الرأس الداخلي أو تصويرًا لشخص محدد.</p><p><a href="/models/oral-study.NOTICE.md">مصادر الفم</a> · <a href="/models/face-context.NOTICE.md">مصادر الوجه</a> · <a href="/models/oral-study.glb" download>تنزيل الفم التجريبي</a> · <a href="/models/face-context.glb" download>تنزيل الوجه التجريبي</a></p></details></main>`;

const stage = document.querySelector<HTMLDivElement>('#oral-stage')!;
const canvas = stage.querySelector('canvas')!;
document.querySelector('h1')!.textContent = 'الفم والتجويف الأنفي، بوضوح';
document.querySelector('.intro > p:last-child')!.textContent = 'استكشف الفم والشفتين، وتتبّع الفراغ الأنفي حتى بداية الحلق.';
document.querySelector('.review-note')!.textContent = 'نموذج تجريبي للفم والممر الأنفي إلى البلعوم الأنفي. الأبعاد المؤلفة والمراجعة العلمية وضبط الحروف قيد العمل.';
document.querySelector('details')!.insertAdjacentHTML('beforeend','<p><a href="/models/nasal-cavity.NOTICE.md">مصدر التجويف الأنفي وحدود إعادة البناء</a></p>');
document.querySelector('.view-tabs')!.insertAdjacentHTML('beforeend', '<button data-mode="nasal" aria-pressed="false">الخيشوم</button>');
document.querySelector('#controls')!.insertAdjacentHTML('beforebegin', `<div id="nasal-tools" hidden><p>ممر فارغ من فتحتي الأنف إلى البلعوم الأنفي خلف الحنك.</p><label><input id="nasal-cut" type="checkbox" checked> مقطع يكشف التجويف</label><label><input id="nasal-paths" type="checkbox" checked> مسار توضيحي داخل الفراغ</label><p class="nasal-hint">عرض تشريحي تجريبي في الراحة؛ الخطوط دليل للمسار وليست محاكاة تدفق.</p></div>`);
stage.insertAdjacentHTML('afterend', `<div class="camera-tools" role="group" aria-label="أدوات العرض">
  <button data-camera="front">أمام</button><button data-camera="side">جانب</button>
  <button data-camera="detail">تفاصيل الفم</button>
  <button id="save-image" aria-label="حفظ صورة النموذج">حفظ صورة ↓</button></div>`);
document.querySelector('.actions')!.insertAdjacentHTML('afterend', `<label class="playback-rate">سرعة العرض
  <select id="playback-rate" aria-label="سرعة عرض الحركة"><option value="0.5">بطيئة · ½×</option><option value="1" selected>عادية · 1×</option><option value="1.5">سريعة · 1½×</option></select></label>`);
const renderer = new THREE.WebGLRenderer({canvas, antialias: true, powerPreference: 'high-performance'});
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.localClippingEnabled = true;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const nasal = new NasalView(scene);
scene.background = new THREE.Color('#e8ebe7');
const pmrem = new THREE.PMREMGenerator(renderer);
const room = new RoomEnvironment();
scene.environment = pmrem.fromScene(room, .04).texture;
room.dispose(); pmrem.dispose();
scene.environmentIntensity = .45;
scene.add(new THREE.HemisphereLight(0xffffff, 0x6b7165, .85));
const light = new THREE.DirectionalLight(0xfff6ec, 2.2); light.position.set(.15, .2, -.15); scene.add(light);
light.castShadow = true; light.shadow.mapSize.set(1024, 1024);
light.shadow.camera.near = .001; light.shadow.camera.far = 2;
light.shadow.bias = -.00003; light.shadow.normalBias = .0002;
scene.add(light.target);
const fill = new THREE.DirectionalLight(0xe3eeff, .8); fill.position.set(-.1, .1, .2); scene.add(fill);
const camera = new THREE.PerspectiveCamera(36, 1, .001, 10);
const orbit = new OrbitControls(camera, canvas);
orbit.enableDamping = true; orbit.dampingFactor = .12; orbit.minDistance = .055; orbit.maxDistance = .6;
const caps = new THREE.Group(); scene.add(caps);
const clipping = new THREE.Plane(new THREE.Vector3(0, 0, 1), -.00015);
const meshes: THREE.Mesh[] = [];
const faceMeshes: THREE.Mesh[] = [];
const originals = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
const roof = new Set(['PALATE', 'UPPER_DENTITION', 'UPPER_GINGIVA']);
const cutColors: Record<string, string> = {TONGUE: '#b76559', ORAL_FLOOR: '#c28676', LINGUAL_FRENULUM: '#c28676', PALATE: '#c28676', UPPER_GINGIVA: '#c28676', LOWER_GINGIVA: '#c28676', UPPER_DENTITION: '#e6dfcd', LOWER_DENTITION: '#e6dfcd'};
let manifest: Manifest, faceManifest: FaceManifest, model: THREE.Group, faceModel: THREE.Group, jaw: THREE.Object3D | undefined;
let ready = false, mode: Mode = 'face', clay = false, playing = false;
let scheduled = 0, geometryDirty = false, renderCount = 0, playStart = 0;
let playbackRate = 1;
let capDiagnostics: Record<string, {loops: number; openChains: number}> = {};
const number = new Intl.NumberFormat('ar', {maximumFractionDigits: 0});

function draw() {
  if (scheduled) return;
  scheduled = requestAnimationFrame(time => {
    scheduled = 0;
    if (!ready) return;
    if (playing) {
      const active: readonly (readonly [Control, string])[] = mode === 'face' ? [oralDefinitions[3], ...lipDefinitions] : oralDefinitions;
      const t = ((time - playStart) * playbackRate / 2200) % active.length;
      definitions.forEach(([key]) => state[key] = 0);
      active.forEach(([key], i) => state[key] = Math.floor(t) === i ? Math.sin(Math.PI * (t % 1)) ** 2 : 0);
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
  for (const mesh of [...meshes, ...faceMeshes, ...nasal.wallMeshes]) {
    for (const [name, idx] of Object.entries(mesh.morphTargetDictionary ?? {})) {
      const correction = manifest.correctives[name];
      mesh.morphTargetInfluences![idx] = correction ? state[correction[0]] * state[correction[1]] : state[name as Control] ?? 0;
    }
  }
  if (jaw) jaw.rotation.x = state.JAW_OPEN * manifest.jawBinding.angle_radians;
  model.updateMatrixWorld(true); faceModel.updateMatrixWorld(true); geometryDirty = true; draw();
}
function stop() { playing = false; document.querySelector('#play')!.textContent = 'تشغيل الحركة'; }
function focusCamera(view: 'front' | 'side' | 'detail') {
  if (!ready) return;
  const fit = mode === 'face' && view !== 'detail' ? faceModel : model;
  const box = mode === 'nasal' ? nasal.bounds() : new THREE.Box3().setFromObject(fit);
  const size = box.getSize(new THREE.Vector3());
  box.getCenter(orbit.target);
  const projectedWidth = view === 'front' ? size.z : size.x;
  const verticalSpan = Math.max(size.y, projectedWidth / camera.aspect);
  const distance = verticalSpan / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.35;
  const direction = view === 'front' ? new THREE.Vector3(1, mode === 'nasal' ? -.45 : .025, 0)
    : view === 'side' ? new THREE.Vector3(0, .025, -1) : new THREE.Vector3(1, .12, -.55);
  orbit.maxDistance = mode === 'face' ? 1.4 : .6;
  camera.position.copy(orbit.target).add(direction.normalize().multiplyScalar(Math.max(.09, distance)));
  camera.up.set(0, 1, 0); orbit.update(); draw();
}
function resetCamera() {
  if (mode === 'nasal') {
    const box = nasal.bounds(); const size = box.getSize(new THREE.Vector3()); box.getCenter(orbit.target);
    const distance = Math.max(size.y, size.x/camera.aspect)/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))*1.4;
    camera.position.copy(orbit.target).add(new THREE.Vector3(.12,.06,-1).normalize().multiplyScalar(Math.max(.15,distance)));
    orbit.maxDistance=.6; orbit.update(); draw(); return;
  }
  if (mode === 'face' && faceModel) {
    const box = new THREE.Box3().setFromObject(faceModel);
    const size = box.getSize(new THREE.Vector3());
    box.getCenter(orbit.target);
    const distance = Math.max(size.y, size.x) / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.16;
    orbit.maxDistance = 1.4;
    camera.position.copy(orbit.target).add(new THREE.Vector3(.85, .07, -.75).normalize().multiplyScalar(distance));
    camera.up.set(0, 1, 0); orbit.update(); draw(); return;
  }
  orbit.maxDistance = .6;
  orbit.target.set(-.038, -.005, 0);
  camera.position.copy(orbit.target).add(mode === 'section' ? new THREE.Vector3(.006, .004, -.19) : new THREE.Vector3(.105, .112, -.11));
  camera.up.set(0, 1, 0); orbit.update(); draw();
}
function setMode(next: Mode) {
  if (playing) stop();
  mode = next;
  if (mode === 'nasal') {definitions.forEach(([key])=>state[key]=0);syncInputs();applyState();}
  nasal.group.visible = mode === 'nasal';
  document.querySelector<HTMLElement>('#nasal-tools')!.hidden = mode !== 'nasal';
  document.querySelector<HTMLElement>('#controls')!.hidden = mode === 'nasal';
  document.querySelector<HTMLElement>('.playback-rate')!.hidden = mode === 'nasal';
  document.querySelectorAll<HTMLButtonElement>('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
  for (const mesh of meshes) {
    mesh.visible = mode !== 'floor' || !roof.has(mesh.name);
    if (mode === 'nasal') mesh.visible = mesh.name==='UPPER_GINGIVA' || mesh.name==='PALATE';
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      material.clippingPlanes = mode === 'section' ? [clipping] : [];
      material.clipShadows = true;
      material.needsUpdate = true;
    }
  }
  for (const mesh of faceMeshes) mesh.visible = mode === 'face';
  for (const row of document.querySelectorAll<HTMLElement>('[data-control]')) {
    const key = row.dataset.control!;
    row.hidden = mode === 'face' ? key !== 'JAW_OPEN' && !key.startsWith('LIP_') : key.startsWith('LIP_');
  }
  document.querySelector('#control-heading')!.textContent = mode === 'nasal' ? 'التجويف الأنفي' : mode === 'face' ? 'الشفتان والفك' : 'حركة الأعضاء';
  const description = mode === 'nasal' ? ['الخيشوم والبلعوم الأنفي','تدخل الفتحتان إلى ممرين يفصل بينهما الحاجز، ثم يلتقي المسار خلف الأنف عند بداية الحلق. شاهد الفراغ من خلال المقطع.'] : mode === 'face' ? anatomy.HEAD_EXTERNAL : anatomy.TONGUE;
  document.querySelector('#part-name')!.textContent = description[0];
  document.querySelector('#part-description')!.textContent = description[1];
  const center = mode === 'face' ? new THREE.Box3().setFromObject(faceModel).getCenter(new THREE.Vector3()) : new THREE.Vector3(-.04, -.005, 0);
  light.target.position.copy(center);
  light.position.copy(center).add(new THREE.Vector3(.4, .65, -.35));
  const extent = mode === 'face' ? .32 : .11;
  Object.assign(light.shadow.camera, {left: -extent, right: extent, top: extent, bottom: -extent});
  light.shadow.normalBias = mode === 'face' ? .0015 : .00045;
  light.shadow.bias = -.00012;
  light.shadow.camera.updateProjectionMatrix();
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
      cap.castShadow = true; cap.receiveShadow = true;
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
document.querySelector('#nasal-cut')!.addEventListener('change', event => {nasal.section=(event.target as HTMLInputElement).checked; nasal.update(); draw();});
document.querySelector('#nasal-paths')!.addEventListener('change', event => {nasal.paths=(event.target as HTMLInputElement).checked; nasal.update(); draw();});
document.querySelectorAll<HTMLButtonElement>('[data-camera]').forEach(button => button.addEventListener('click', () => {
  focusCamera(button.dataset.camera as 'front' | 'side' | 'detail');
}));
document.querySelector<HTMLSelectElement>('#playback-rate')!.addEventListener('change', event => {
  const next = Number((event.target as HTMLSelectElement).value);
  const time = performance.now();
  if (playing) playStart = time - (time - playStart) * playbackRate / next;
  playbackRate = next;
});
document.querySelector('#save-image')!.addEventListener('click', () => {
  if (!ready) return;
  if (geometryDirty) updateCaps();
  renderer.render(scene, camera);
  const picture = document.createElement('canvas');
  const scale = renderer.getPixelRatio();
  picture.width = canvas.width; picture.height = canvas.height + Math.ceil(104 * scale);
  const context = picture.getContext('2d')!;
  context.drawImage(canvas, 0, 0);
  context.fillStyle = '#f5f6f0'; context.fillRect(0, canvas.height, picture.width, picture.height - canvas.height);
  context.fillStyle = '#294c3b'; context.font = `${12 * scale}px Tahoma, Arial, sans-serif`;
  context.direction = 'rtl'; context.textAlign = 'right';
  context.fillText('مخارج · معاينة تعليمية تجريبية قيد المراجعة', picture.width - 14 * scale, canvas.height + 21 * scale, picture.width - 28 * scale);
  context.direction = 'ltr'; context.textAlign = 'left'; context.font = `${10 * scale}px Arial, sans-serif`;
  const credits = ['BodyParts3D / DBCLS / Kousaku Okubo — CC BY-SA 2.1 JP',
    'Z-Anatomy / Gauthier Kervyn — CC BY-SA 4.0',
    'MakeHuman — CC0; adapted model data: Makharij — CC BY-SA 4.0',
    'Sources and modifications: github.com/Poej77577/makharij-3d'];
  credits.forEach((line, index) => context.fillText(line, 14 * scale, canvas.height + (41 + 15 * index) * scale, picture.width - 28 * scale));
  const download = document.createElement('a');
  download.download = 'makharij-' + mode + '.png';
  download.href = picture.toDataURL('image/png');
  download.click();
});
document.querySelector<HTMLInputElement>('#clay')!.addEventListener('change', event => {
  clay = (event.target as HTMLInputElement).checked;
  nasal.setClay(clay);
  for (const mesh of [...meshes, ...faceMeshes]) {
    if (clay) mesh.material = new THREE.MeshStandardMaterial({color: '#aaa99e', roughness: .83});
    else {
      if (mesh.material !== originals.get(mesh)) (mesh.material as THREE.Material).dispose();
      mesh.material = originals.get(mesh)!;
    }
  }
  setMode(mode);
});
const anatomy: Record<string, [string, string]> = {
  NASAL_MUCOSA: ['جدار التجويف الأنفي', 'يحيط الجدار بممر فارغ يمتد من فتحتي الأنف إلى البلعوم الأنفي خلف الحنك. خطوط المسار توضيحية ويمكن إخفاؤها.'],
  HEAD_EXTERNAL: ['الوجه والشفتان', 'الشفتان جزء متصل بجلد الوجه. قارن فتح الفك وضم الشفتين وبروزهما، ثم انتقل إلى المقطع لمراجعة الداخل.'],
  FACE_EYES: ['العينان', 'العينان جزء من السياق الخارجي للوجه؛ تبقى الأجزاء الداخلية للفم متاحة في طرق العرض الأخرى.'],
  TONGUE: ['اللسان', 'يتصل طرف اللسان بنصله وظهره، ويمتد جذره نحو قاع الفم. جرّب رفع الطرف والظهر كلًا على حدة.'],
  ORAL_FLOOR: ['قاع الفم', 'تحيط أرضية الفم بقاعدة اللسان، وتبقى مقدمته حرة للحركة فوقها.'],
  LINGUAL_FRENULUM: ['لجام اللسان', 'طية مخاطية قصيرة تصل السطح البطني للسان بقاع الفم.'],
  PALATE: ['الحنك', 'يمتد الحنك في سقف الفم، ويتصل الجزء الرخو واللهاة خلفًا بالغشاء المخاطي الأمامي.'],
  UPPER_GINGIVA: ['اللثة العلوية والغشاء الحنكي', 'تُظهر هذه القطعة اللثة والسطح المخاطي لسقف الفم الأمامي. يرتبط به الجزء الرخو من الحنك خلفًا.'],
  LOWER_GINGIVA: ['اللثة السفلية', 'تحيط اللثة بأعناق الأسنان السفلية وتتحرك مع الفك. راقب العلاقة بين سطحها الداخلي وجانب اللسان.'],
};
let pointerStart = new THREE.Vector2();
canvas.addEventListener('pointerdown', event => pointerStart.set(event.clientX, event.clientY));
canvas.addEventListener('pointerup', event => {
  if (!ready || pointerStart.distanceTo(new THREE.Vector2(event.clientX, event.clientY)) > 5) return;
  const box = canvas.getBoundingClientRect();
  const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2(2 * (event.clientX - box.left) / box.width - 1, 1 - 2 * (event.clientY - box.top) / box.height), camera);
  const hit = ray.intersectObjects([...meshes, ...faceMeshes, ...(nasal.group.visible ? nasal.wallMeshes : [])].filter(mesh => mesh.visible)).find(hit => (mode !== 'section' || hit.point.z >= .00015) && (mode !== 'nasal' || !nasal.section || hit.point.z >= -nasal.cut.constant));
  if (!hit) return;
  const name = hit.object.name;
  const [label, text] = anatomy[name] ?? (name.includes('DENTITION') ? ['الأسنان', 'تساعد الأسنان وحوافها على تحديد مواضع تماس بعض الحروف. يتبع الصف السفلي حركة الفك.'] : ['اللثة', 'تحيط اللثة بأعناق الأسنان وتحدد حدود القوس السني.']);
  document.querySelector('#part-name')!.textContent = label; document.querySelector('#part-description')!.textContent = text;
});
Object.assign(window, {__oralStudy: {get ready() { return ready; }, snapshot() {
  model?.updateMatrixWorld(true);
  faceModel?.updateMatrixWorld(true);
  const probes: Record<string, number[][]> = {};
  for (const mesh of [...meshes, ...faceMeshes]) {
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
  return {ready, mode, clay, playing, playbackRate, state: {...state}, assetSha256: manifest?.glbSha256, faceSha256: faceManifest?.glbSha256,
    nasalSha256:nasal.manifest?.glbSha256, nasalVisible:nasal.group.visible, nasalSection:nasal.section,nasalPaths:nasal.paths,nasalParts:nasal.wallMeshes.map(m=>m.name),
    parts: meshes.map(mesh => mesh.name), contextParts: faceMeshes.map(mesh => mesh.name), faceVisible: faceMeshes.some(mesh => mesh.visible),
    probes, capDiagnostics, capSignatures, camera: camera.position.toArray(), renderCount};
}}});

async function load() {
  try {
    const [meta, bytes, faceMeta, faceBytes] = await Promise.all([
      fetch('/models/oral-study.manifest.json').then(response => { if (!response.ok) throw new Error('manifest'); return response.json(); }),
      fetch('/models/oral-study.glb').then(response => { if (!response.ok) throw new Error('model'); return response.arrayBuffer(); }),
      fetch('/models/face-context.manifest.json').then(response => { if (!response.ok) throw new Error('face manifest'); return response.json(); }),
      fetch('/models/face-context.glb').then(response => { if (!response.ok) throw new Error('face model'); return response.arrayBuffer(); }),
    ]);
    manifest = meta;
    if (manifest.anatomicalRoles?.PALATE === 'posterior soft palate and uvula only') {
      anatomy.PALATE = ['الحنك الرخو واللهاة', 'نسيج متحرك خلف السقف الأمامي للفم. جرّب رفعه، ولاحظ ثبات منطقة اتصاله بالغشاء الحنكي.'];
    }
    faceManifest = faceMeta;
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(byte => byte.toString(16).padStart(2, '0')).join('');
    if (hash !== manifest.glbSha256) throw new Error('Model identity mismatch');
    const faceHash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', faceBytes))].map(byte => byte.toString(16).padStart(2, '0')).join('');
    if (faceHash !== faceManifest.glbSha256 || faceManifest.oralSourceGlbSha256 !== manifest.glbSha256) throw new Error('Face/oral version mismatch');
    const gltf = await new GLTFLoader().parseAsync(bytes, '/models/');
    model = gltf.scene; model.rotation.y = Math.PI / 2; scene.add(model);
    jaw = model.getObjectByName(manifest.jawBinding.node);
    model.traverse(object => {
      if (!(object as THREE.Mesh).isMesh) return;
      const mesh = object as THREE.Mesh;
      mesh.castShadow = true; mesh.receiveShadow = true;
      meshes.push(mesh); originals.set(mesh, mesh.material);
    });
    const faceGltf = await new GLTFLoader().parseAsync(faceBytes, '/models/');
    faceModel = faceGltf.scene; faceModel.rotation.y = Math.PI / 2; scene.add(faceModel);
    faceModel.traverse(object => {
      if (!(object as THREE.Mesh).isMesh) return;
      const mesh = object as THREE.Mesh;
      mesh.castShadow = mesh.name !== 'FACE_EYES'; mesh.receiveShadow = true;
      faceMeshes.push(mesh); originals.set(mesh, mesh.material);
    });
    if (!jaw || meshes.length !== manifest.parts.length) throw new Error('Incomplete anatomical assembly');
    if (faceMeshes.length !== faceManifest.parts.length) throw new Error('Incomplete face context');
    await nasal.load(faceManifest.glbSha256, manifest.glbSha256, faceModel);
    ready = true; (document.querySelector('#controls') as HTMLFieldSetElement).disabled = false;
    document.querySelector<HTMLInputElement>('#clay')!.disabled = false;
    document.querySelector('#load-status')!.textContent = 'النموذج جاهز للاستكشاف';
    resize(); applyState(); setMode('face');
  } catch (error) {
    document.querySelector('#load-status')!.textContent = 'تعذر تحميل النموذج. أعد تحميل الصفحة.';
    console.error(error);
  }
}
void load();
