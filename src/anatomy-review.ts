import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import './anatomy-review.css';

type SectionData={assetSha256:string;planeZ_m:number;caps:Record<string,{points:number[][];faces:number[][]}>};
type AssetManifest={glbSha256:string;atlasPlacement:{translation_m:number[]};parts:Record<string,unknown>;visualReview?:'fail'|'pending'};
const root=document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML=`<header><div><h1>مخارج</h1><p>استكشف اللسان والفم والأنف والحلق في نموذج واحد</p></div><span class="badge">دراسة تشريحية محفوظة</span></header>
<main><div class="toolbar"><div class="buttons" aria-label="طريقة العرض"><button id="both" aria-pressed="true" disabled>عرضان معًا</button><button id="section" aria-pressed="false" disabled>المقطع الجانبي</button><button id="external" aria-pressed="false" disabled>الرأس الخارجي</button></div><div class="buttons"><button id="reset" disabled>استعادة المنظور</button><button id="fullscreen">ملء الشاشة</button></div></div>
<section id="review-stage" aria-label="استكشاف النموذج التشريحي"><canvas aria-label="نموذج تشريحي ثلاثي الأبعاد قابل للدوران"></canvas><div class="pane external-pane"></div><div class="pane section-pane"></div><span class="view-label external-label">الرأس الخارجي</span><span class="view-label section-label">مقطع عبر الفم والأنف والحلق</span><span class="hint">اسحب للدوران · عجلة للتقريب · بإصبعين على اللمس</span></section>
<div class="toolbar"><div class="focus"><label for="focus">استكشف</label><select id="focus" disabled><option value="whole">الفم والأنف والحلق</option><option value="mouth">اللسان والحنك</option><option value="nose">التجويف الأنفي</option><option value="throat">الحلق والحنجرة</option></select></div><p class="meta" id="load-status" role="status">جارٍ تحميل التشريح الجديد…</p></div>
<details><summary>عن النموذج ومصادره</summary><p>هذه دراسة محفوظة لوضع الراحة، مع لسان وجذر متصلين، ولثة وأسنان وحنك وتجويف أنفي وبنى الحلق. التحريك والمراجعة العلمية لم يكتملَا. تخطيط الألياف وتفاصيل سطح اللسان توضيحية، وليست صورًا مجهرية مقاسة. المقاطع محسوبة من أحجام الأنسجة الفعلية؛ يتغير مستوى القطع عند استكشاف الأنف لإظهار المحارات الأنفية.</p><p>المصدر التشريحي: <a href="https://github.com/Z-Anatomy/Models-of-human-anatomy">Z-Anatomy / BodyParts3D</a>؛ الرأس والعينان من MakeHuman. النموذج المعدّل مرخص CC BY-SA 4.0، ومكوّنات الرأس الأصلية CC0.</p><p><a href="/models/makharij-realistic.glb" download>تنزيل الدراسة المحفوظة GLB</a> · <a href="/models/makharij-realistic.NOTICE.md">المصادر والتعديلات والترخيص</a> · <a href="/">الدراسة التقنية السابقة</a></p></details>
<p class="credits">BodyParts3D — The Database Center for Life Science — CC BY-SA 2.1 Japan · Z-Anatomy — CC BY-SA 4.0</p></main>`;
const stage=document.querySelector<HTMLElement>('#review-stage')!;
const status=document.querySelector<HTMLElement>('#load-status')!;
const button=(id:string)=>document.getElementById(id) as HTMLButtonElement;
const select=document.querySelector<HTMLSelectElement>('#focus')!;
const canvas=stage.querySelector('canvas')!;
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
renderer.setClearColor(0xe1e5df);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=.9;
renderer.localClippingEnabled=true;
const scene=new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xfffdf5,0x69766a,2));
for(const [position,intensity] of [[[.5,.5,-.6],2.1],[[-.2,.2,.4],1.1]] as const){
 const light=new THREE.DirectionalLight(0xffffff,intensity);light.position.fromArray(position);scene.add(light);
}
const cameras={external:new THREE.OrthographicCamera(-1,1,1,-1,.001,5),section:new THREE.OrthographicCamera(-1,1,1,-1,.001,5)};
const controls={external:new OrbitControls(cameras.external,stage.querySelector<HTMLElement>('.external-pane')!),section:new OrbitControls(cameras.section,stage.querySelector<HTMLElement>('.section-pane')!)};
for(const c of Object.values(controls)){c.enableDamping=true;c.dampingFactor=.12;c.minZoom=.4;c.maxZoom=8;c.screenSpacePanning=true;}
let mode:'both'|'section'|'external'=innerWidth<650?'section':'both';
let ready=false,meshCount=0,triangles=0;
let width=1,height=1,translation=new THREE.Vector3();
const materials:THREE.Material[]=[];
const caps=new THREE.Group(),nasalCaps=new THREE.Group();scene.add(caps,nasalCaps);
let sectionPlanes={main:.00501,nose:.00901};
const clipping=new THREE.Plane(new THREE.Vector3(0,0,1),-.00301);
let assetSha='';
let requestedFrame=0;
function invalidate(){
 if(requestedFrame)return;
 requestedFrame=requestAnimationFrame(()=>{
  requestedFrame=0;if(!ready)return;
  let moving=false;for(const c of Object.values(controls))moving=c.update()||moving;
  render();if(moving)invalidate();
 });
}
for(const c of Object.values(controls))c.addEventListener('change',invalidate);

// Physical-coordinate illustrative tissue appearance shared by all section
// triangles, so fiber directions do not follow arbitrary triangulation edges.
function sectionMaterial(name:string,base:THREE.MeshStandardMaterial){
 const mat=new THREE.MeshStandardMaterial({color:base.color,roughness:.63,side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});
 let kind=0;
 if(name.includes('GENIOGLOSSUS'))kind=2;
 else if(name.includes('TONGUE'))kind=1;
 else if(name.includes('MUSCLE')||name.includes('CONSTRICTOR'))kind=3;
 else if(name==='HEAD_SKIN')kind=4;
 else if(['MANDIBLE','MAXILLA','PALATINE_BONE','HYOID_BONE'].some(s=>name.includes(s)))kind=5;
 mat.onBeforeCompile=shader=>{
  shader.uniforms.anatomicalOrigin={value:translation};
  shader.vertexShader='varying vec3 vTissuePosition;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvTissuePosition=(modelMatrix*vec4(position,1.)).xyz;');
  shader.fragmentShader=`varying vec3 vTissuePosition;uniform vec3 anatomicalOrigin;
  float tissueHash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
  float tissueNoise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(tissueHash(i),tissueHash(i+vec3(1,0,0)),f.x),mix(tissueHash(i+vec3(0,1,0)),tissueHash(i+vec3(1,1,0)),f.x),f.y),mix(mix(tissueHash(i+vec3(0,0,1)),tissueHash(i+vec3(1,0,1)),f.x),mix(tissueHash(i+vec3(0,1,1)),tissueHash(i+vec3(1,1,1)),f.x),f.y),f.z);}
  `+shader.fragmentShader;
  let expression='';
  if(kind>=1&&kind<=3){
   const phase=kind===2?'atan(p.y+.028,p.x+.014)*460.':kind===1?'(p.y+3.*pow(p.x+.040,2.))*13963.':'p.y*13963.';
   expression=`float phase=${phase};float lines=pow(.5+.5*sin(phase+n*2.1),10.);float t=.60*n+.40*lines;diffuseColor.rgb=mix(vec3(.22,.045,.031),vec3(.38,.115,.074),t);`;
  }else if(kind===4)expression='diffuseColor.rgb=mix(vec3(.41,.23,.11),vec3(.46,.26,.13),n);';
  else if(kind===5)expression='diffuseColor.rgb=mix(vec3(.43,.29,.14),vec3(.74,.55,.29),smoothstep(.28,.64,n));';
  if(expression)shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>\nvec3 p=vTissuePosition-anatomicalOrigin;float n=tissueNoise(p*${kind>=4?'1800.':'720.'});${expression}`);
 };
 mat.customProgramCacheKey=()=>`anatomy-section-${kind}`;
 return mat;
}
function setMode(value:typeof mode){
 mode=value;stage.classList.toggle('solo',mode!=='both');stage.classList.toggle('section-only',mode==='section');stage.classList.toggle('external-only',mode==='external');
 for(const key of ['both','section','external'] as const)button(key).setAttribute('aria-pressed',String(key===mode));
 resize();
}
function resize(){
 width=stage.clientWidth;height=stage.clientHeight;renderer.setSize(width,height,false);
 const aspects={external:width*(mode==='both'?.44:1)/height,section:width*(mode==='both'?.56:1)/height};
 for(const key of ['external','section'] as const){const camera=cameras[key];const scale=key==='external'?.40:select.value==='mouth'?.105:select.value==='nose'?.075:select.value==='throat'?.145:.235;camera.left=-scale*aspects[key]/2;camera.right=scale*aspects[key]/2;camera.top=scale/2;camera.bottom=-scale/2;camera.updateProjectionMatrix();}
 invalidate();
}
function reset(){
 controls.external.target.set(.04,.065,0);cameras.external.position.set(.59,.10,-.75);cameras.external.zoom=1;
 const centers:Record<string,number[]>={whole:[-.038,-.018,0],mouth:[-.036,.003,0],nose:[-.018,.047,0],throat:[-.078,-.067,0]};
 clipping.constant=-(select.value==='nose'?sectionPlanes.nose:sectionPlanes.main);
 stage.querySelector('.section-label')!.textContent=select.value==='nose'?'مقطع جانبي عبر المحارات الأنفية':'مقطع عبر الفم والأنف والحلق';
 const center=new THREE.Vector3(...centers[select.value]).add(translation);
 controls.section.target.copy(center);cameras.section.position.copy(center).add(new THREE.Vector3(0,0,-.8));cameras.section.zoom=1;
 for(const c of Object.values(controls))c.update();resize();
}
function render(){
 renderer.setScissorTest(false);renderer.clear();renderer.setScissorTest(true);
 if(mode!=='section'){
  caps.visible=false;nasalCaps.visible=false;for(const m of materials)m.clippingPlanes=[];
  const w=mode==='both'?Math.floor(width*.44):width;
  renderer.setViewport(0,0,w,height);renderer.setScissor(0,0,w,height);renderer.render(scene,cameras.external);
 }
 if(mode!=='external'){
  caps.visible=select.value!=='nose';nasalCaps.visible=select.value==='nose';for(const m of materials)m.clippingPlanes=[clipping];
  const x=mode==='both'?Math.floor(width*.44):0;
  renderer.setViewport(x,0,width-x,height);renderer.setScissor(x,0,width-x,height);renderer.render(scene,cameras.section);
 }
 renderer.setScissorTest(false);
}
new ResizeObserver(resize).observe(stage);
button('fullscreen').onclick=()=>{if(document.fullscreenElement)void document.exitFullscreen();else void stage.requestFullscreen();};
for(const key of ['both','section','external'] as const)button(key).onclick=()=>setMode(key);
button('reset').onclick=reset;select.onchange=reset;
setMode(mode);
async function load(){
 const [manifestResponse,sectionResponse,nasalResponse,response]=await Promise.all(['/models/makharij-realistic.manifest.json','/models/makharij-sections.json','/models/makharij-nasal-sections.json','/models/makharij-realistic.glb'].map(url=>fetch(url)));
 if(!manifestResponse.ok||!sectionResponse.ok||!nasalResponse.ok||!response.ok)throw new Error('تعذر تحميل ملفات التشريح. أعد المحاولة بعد اكتمال التصدير.');
 const manifest:AssetManifest=await manifestResponse.json(),section:SectionData=await sectionResponse.json(),nasal:SectionData=await nasalResponse.json();
 const bytes=await response.arrayBuffer();assetSha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');
 if(assetSha!==manifest.glbSha256||assetSha!==section.assetSha256||assetSha!==nasal.assetSha256)throw new Error('ملف النموذج والمقاطع من إصدارين مختلفين. يلزم إعادة التصدير.');
 sectionPlanes={main:section.planeZ_m,nose:nasal.planeZ_m};
 translation.fromArray(manifest.atlasPlacement.translation_m);clipping.constant=-section.planeZ_m;
 const gltf=await new GLTFLoader().parseAsync(bytes,'/models/');
 const model=gltf.scene;scene.add(model);
 model.traverse(ob=>{if(ob.userData.anatomicalRegionOf==='ATLAS_TONGUE')ob.visible=false;if(!(ob instanceof THREE.Mesh))return;meshCount++;triangles+=(ob.geometry.index?.count??ob.geometry.attributes.position.count)/3;for(const material of Array.isArray(ob.material)?ob.material:[ob.material]){material.side=THREE.DoubleSide;materials.push(material);}});
 for(const [dataset,group] of [[section,caps],[nasal,nasalCaps]] as const)for(const [name,data] of Object.entries(dataset.caps)){
  const part=model.getObjectByName(name);if(!part)throw new Error('جزء تشريحي مفقود: '+name);
  let source:THREE.MeshStandardMaterial|undefined;
  part.traverse(ob=>{if(!source&&ob instanceof THREE.Mesh)source=(Array.isArray(ob.material)?ob.material[0]:ob.material) as THREE.MeshStandardMaterial;});
  if(!source)throw new Error('نسيج تشريحي مفقود: '+name);
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(data.points.flat(),3));geometry.setIndex(data.faces.flat());geometry.computeVertexNormals();
  const cap=new THREE.Mesh(geometry,sectionMaterial(name,source));cap.name=name;group.add(cap);
 }
 ready=true;reset();document.querySelectorAll<HTMLButtonElement|HTMLSelectElement>('button:disabled,select:disabled').forEach(el=>el.disabled=false);
 if(manifest.visualReview==='fail'){
  document.querySelector('.badge')!.textContent='دراسة مرفوضة · محفوظة للمقارنة';
  status.textContent='رُفضت واقعية هذه الدراسة؛ يجري تغيير طريقة بناء الأصل التشريحي.';
 }else status.textContent='أُعيد بناء التشريح · وضع الراحة · المراجعة العلمية قيد العمل';
 Object.assign(window,{anatomyReview:{assetSha256:assetSha,meshCount,triangles,sectionCaps:caps.children.length,sectionPartIds:caps.children.map(p=>p.name),nasalPartIds:nasalCaps.children.map(p=>p.name),rendererInstances:1,get planeZ_m(){return -clipping.constant;},
   setMode,focus:(value:string)=>{select.value=value;reset();},rotate:(yaw:number)=>{cameras.external.position.copy(controls.external.target).add(new THREE.Vector3(Math.cos(yaw)*.8,.035,-Math.sin(yaw)*.8));controls.external.update();render();}}});
}
void load().catch(error=>{status.textContent=error instanceof Error?error.message:'تعذر فتح النموذج.';status.dataset.error='true';console.error(error);});
