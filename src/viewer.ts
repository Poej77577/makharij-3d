import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';

type ViewName = 'side' | 'front';
export const partLabels: Record<string,string> = {
 LIP_CONTEXT:'الشفتان والوجه — نسيج متصل', TONGUE:'اللسان', UPPER_TEETH:'تيجان الأسنان العليا', LOWER_TEETH:'تيجان الأسنان السفلى',
 UPPER_LIP:'الشفة العليا', LOWER_LIP:'الشفة السفلى', HARD_PALATE:'الحنك الصلب',
 SOFT_PALATE:'الحنك الرخو — مواءمة بحثية', PHARYNX:'حدود البلعوم',
 FACE_CONTEXT:'سياق الوجه', NASAL_LINING:'بطانة أنفية مؤلفة غير مقاسة',
 NASAL_CONCHA_INFERIOR:'المحارة الأنفية السفلى — إعادة بناء', NASAL_CONCHA_MIDDLE:'المحارة الأنفية الوسطى — إعادة بناء', NASAL_CONCHA_SUPERIOR:'المحارة الأنفية العليا — إعادة بناء',
 GINGIVA_UPPER:'اللثة العليا', GINGIVA_LOWER:'اللثة السفلى',
};
const requiredParts=['TONGUE','UPPER_TEETH','LOWER_TEETH','LIP_CONTEXT','HARD_PALATE','PHARYNX','SOFT_PALATE'];
type Viewport = {x:number;y:number;width:number;height:number};

/** Actual GLB inspection renderer. No procedural fallback or mesh deformation. */
export class AnatomyInspector {
 readonly scene = new THREE.Scene();
 readonly renderer:THREE.WebGLRenderer;
 readonly cameras:Record<ViewName,THREE.OrthographicCamera>;
 readonly controls:Record<ViewName,OrbitControls>;
 readonly parts = new Map<string,THREE.Mesh>();
 private root?:THREE.Group;
 private bounds = new THREE.Box3();
 private center = new THREE.Vector3();
 private radius=.09;
 private resizeObserver:ResizeObserver;
 private frame=0;
 private swapped=false;
 private frontFullFrame=false;
 private frameSerial=0;
 private clipEnabled=true;
 private showLabels=false;
 private hidden = new Set<string>();
 private labelEls = new Map<string,HTMLElement>();
 private cutCaps = new Map<string,THREE.Group>();
 private motionDriver:((now:number)=>void)|null=null;
 private sideClip = new THREE.Plane(new THREE.Vector3(0,0,1),0);
 private selected?:THREE.Mesh;
 private emission?:THREE.Color;
 private clear=new THREE.Color(0x172329);
 private disposed=false;
 private panes:Record<'primary'|'secondary',HTMLDivElement>;
 private size = {width:1,height:1};
 constructor(private container:HTMLElement, private canvas:HTMLCanvasElement, private labelLayer:HTMLElement){
  this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true,stencil:true});
  this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  this.renderer.outputColorSpace=THREE.SRGBColorSpace;
  this.renderer.toneMapping=THREE.ACESFilmicToneMapping;
  this.renderer.toneMappingExposure=1.3;
  this.renderer.setScissorTest(true);
  this.scene.add(new THREE.HemisphereLight(0xe8f2ff,0x50403e,2.1));
  const light=new THREE.DirectionalLight(0xffffff,2.4);light.position.set(.08,.14,.2);this.scene.add(light);
  const fill=new THREE.DirectionalLight(0xffe3d7,1.4);fill.position.set(.15,.03,-.15);this.scene.add(fill);
  const back=new THREE.DirectionalLight(0xc5edee,1.1);back.position.set(-.1,.07,.03);this.scene.add(back);
  this.cameras={side:new THREE.OrthographicCamera(-1,1,1,-1,.0001,10),front:new THREE.OrthographicCamera(-1,1,1,-1,.0001,10)};
  const makePane=(className:string)=>{const el=document.createElement('div');el.className=className;el.style.touchAction='none';container.appendChild(el);return el};
  this.panes={primary:makePane('interaction-pane primary'),secondary:makePane('interaction-pane secondary')};
  this.controls={side:new OrbitControls(this.cameras.side,this.panes.primary),front:new OrbitControls(this.cameras.front,this.panes.secondary)};
  for(const control of Object.values(this.controls)){control.enableDamping=true;control.dampingFactor=.1;control.screenSpacePanning=true;control.minZoom=.3;control.maxZoom=12;control.zoomSpeed=.75;control.panSpeed=.7}
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);this.resize();
  const animate=()=>{if(this.disposed)return;for(const c of Object.values(this.controls))c.update();this.motionDriver?.(performance.now());this.render();this.frame=requestAnimationFrame(animate)};animate();
 }
 async load(url:string){
  const gltf=await new GLTFLoader().loadAsync(url);
  if(this.disposed){this.disposeObject(gltf.scene);throw new Error('أُغلق العارض قبل انتهاء التحميل.');}
  const found=new Map<string,THREE.Mesh>();
  gltf.scene.traverse(obj=>{if(obj instanceof THREE.Mesh){found.set(obj.name,obj);obj.frustumCulled=false;const materials=Array.isArray(obj.material)?obj.material:[obj.material];for(const m of materials){m.side=THREE.DoubleSide;}}});
  const missing=requiredParts.filter(name=>!found.has(name));
  if(missing.length){this.disposeObject(gltf.scene);throw new Error(`أجزاء مطلوبة مفقودة في GLB: ${missing.join(', ')}`)}
  if(this.root){this.scene.remove(this.root);this.disposeObject(this.root)}
  for(const el of this.labelEls.values())el.remove();this.labelEls.clear();this.parts.clear();
  this.root=gltf.scene;this.scene.add(this.root);for(const [name,mesh]of found){this.parts.set(name,mesh);const el=document.createElement('span');el.className='anatomy-label';el.textContent=partLabels[name]??name;this.labelLayer.appendChild(el);this.labelEls.set(name,el)}
  this.bounds.setFromObject(this.root);this.bounds.getCenter(this.center);this.radius=Math.max(this.bounds.getBoundingSphere(new THREE.Sphere()).radius,.001);
  const measured=this.bounds.getSize(new THREE.Vector3());
  if(!Number.isFinite(this.radius)||this.radius>1||this.radius<.005)throw new Error('أبعاد الأصل لا تتفق مع عقد المتر؛ أوقف التكامل وافحص المصدر.');
  this.createSectionCaps();this.reset();this.applyVisibility();this.render();
  return {parts:[...found.keys()],boundsMeters:{x:measured.x,y:measured.y,z:measured.z},triangles:[...found.values()].reduce((n,m)=>n+(m.geometry.index?.count??m.geometry.attributes.position.count)/3,0)};
 }
 /** Caps are computed only for source meshes checked closed and consistently wound.
  * Open scanned surfaces retain their real boundaries. Every stencil pair is
  * consumed and cleared independently, so tissues never borrow another outline.
  */
 private createSectionCaps(){
  this.cutCaps.clear();if(!this.root)return;
  const gl=this.renderer.getContext();if(gl.getParameter(gl.STENCIL_BITS)<1)return;
  const closedTissues:Record<string,number>={TONGUE:0xad7766,SOFT_PALATE:0xc58e86,NASAL_LINING:0xd6ad8e,NASAL_CONCHA_INFERIOR:0xc88d82,NASAL_CONCHA_MIDDLE:0xc88d82,NASAL_CONCHA_SUPERIOR:0xc88d82};
  let sequence=0;
  for(const [name,color]of Object.entries(closedTissues)){
   const source=this.parts.get(name);if(!source)continue;
   const group=new THREE.Group();group.name=`Computed section: ${name}`;
   const order=10+sequence++*3;
   const base=new THREE.MeshBasicMaterial({depthWrite:false,depthTest:false,colorWrite:false,stencilWrite:true,stencilFunc:THREE.AlwaysStencilFunc,clippingPlanes:[this.sideClip]});
   for(const [side,op]of [[THREE.BackSide,THREE.IncrementWrapStencilOp],[THREE.FrontSide,THREE.DecrementWrapStencilOp]] as const){
    const material=base.clone();material.side=side;material.stencilFail=op;material.stencilZFail=op;material.stencilZPass=op;
    const mesh=new THREE.Mesh(source.geometry,material);mesh.morphTargetInfluences=source.morphTargetInfluences;mesh.morphTargetDictionary=source.morphTargetDictionary;mesh.renderOrder=order;mesh.frustumCulled=false;mesh.matrix.copy(source.matrix);mesh.matrixAutoUpdate=false;group.add(mesh);
   }
   base.dispose();
   const stencil={side:THREE.DoubleSide,stencilWrite:true,stencilRef:0,stencilFunc:THREE.NotEqualStencilFunc,stencilFail:THREE.ReplaceStencilOp,stencilZFail:THREE.ReplaceStencilOp,stencilZPass:THREE.ReplaceStencilOp};
   const material=name==='TONGUE'?new THREE.ShaderMaterial({...stencil,
    vertexShader:'varying vec2 tissue; void main(){tissue=position.xy;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
    fragmentShader:'varying vec2 tissue;void main(){vec2 d=tissue-vec2(0.080,-0.040);float angle=atan(d.y,d.x);float fiber=pow(abs(sin(angle*85.0+length(d)*38.0)),18.0);vec3 color=mix(vec3(0.57,0.29,0.25),vec3(0.80,0.54,0.43),0.22+fiber*0.38);gl_FragColor=vec4(color,1.0);}'
   }):new THREE.MeshBasicMaterial({...stencil,color});
   const plane=new THREE.Mesh(new THREE.PlaneGeometry(.3,.3),material);plane.renderOrder=order+1;plane.frustumCulled=false;plane.onAfterRender=()=>this.renderer.clearStencil();group.add(plane);group.visible=false;this.root.add(group);this.cutCaps.set(name,group);
  }
 }
 private disposeObject(object:THREE.Object3D){object.traverse(o=>{if(o instanceof THREE.Mesh){o.geometry.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose()}})}
 private resize(){const r=this.container.getBoundingClientRect();this.size={width:Math.max(1,Math.round(r.width)),height:Math.max(1,Math.round(r.height))};this.renderer.setSize(this.size.width,this.size.height,false);this.updateProjection();this.layoutPanes();}
 private viewport(which:ViewName):Viewport{
  const main:ViewName=this.swapped?'front':'side';const {width,height}=this.size;const cut=Math.round(width*.72);const secondaryWidth=Math.max(1,width-cut-2);const secondaryHeight=Math.min(Math.round(secondaryWidth*.62),Math.round(height*.56));
  return which===main?{x:0,y:0,width:cut,height}:{x:cut+2,y:Math.round((height-secondaryHeight)/2),width:secondaryWidth,height:secondaryHeight};
 }
 private layoutPanes(){
  const secondary=this.viewport(this.swapped?'side':'front');const top=this.size.height-secondary.y-secondary.height;Object.assign(this.panes.secondary.style,{top:`${top}px`,height:`${secondary.height}px`,bottom:'auto'});
  const label=this.container.querySelector<HTMLElement>('.secondary-label');if(label)label.style.top=`${top+12}px`;
 }
 private framingBounds(name:ViewName){
  if(name==='side'||this.frontFullFrame)return this.bounds.clone();
  const box=new THREE.Box3();for(const partName of ['UPPER_TEETH','LOWER_TEETH']){const mesh=this.parts.get(partName);if(mesh)box.union(new THREE.Box3().setFromObject(mesh));}
  return box.isEmpty()?this.bounds.clone():box.expandByScalar(.008);
 }
 private updateProjection(){for(const name of ['side','front'] as ViewName[]){const camera=this.cameras[name];const v=this.viewport(name);const aspect=v.width/v.height;const size=this.framingBounds(name).getSize(new THREE.Vector3());const projectedWidth=name==='side'?size.x:size.z;const range=Math.max(size.y,projectedWidth/aspect,.02)*.56;camera.left=-range*aspect;camera.right=range*aspect;camera.top=range;camera.bottom=-range;camera.updateProjectionMatrix();}}
 reset(){
  this.cameras.side.up.set(0,1,0);this.cameras.side.position.copy(this.framingBounds('side').getCenter(new THREE.Vector3())).add(new THREE.Vector3(0,0,-this.radius*4));
  this.cameras.front.up.set(0,1,0);this.cameras.front.position.copy(this.framingBounds('front').getCenter(new THREE.Vector3())).add(new THREE.Vector3(this.radius*4,0,0));
  for(const name of ['side','front']as ViewName[]){const c=this.cameras[name];c.zoom=1;const center=this.framingBounds(name).getCenter(new THREE.Vector3());this.controls[name].target.copy(center);c.lookAt(center);this.controls[name].update();this.controls[name].saveState()}
  this.updateProjection();this.render();
 }
 swap(){this.swapped=!this.swapped;this.controls.side.disconnect();this.controls.front.disconnect();this.controls.side.connect(this.swapped?this.panes.secondary:this.panes.primary);this.controls.front.connect(this.swapped?this.panes.primary:this.panes.secondary);this.updateProjection();this.layoutPanes();this.render();return this.swapped;}
 setClipping(enabled:boolean){this.clipEnabled=enabled;this.render();}
 setLabels(enabled:boolean){this.showLabels=enabled;this.render();}
 setFrontFullFrame(enabled:boolean){this.frontFullFrame=enabled;this.reset();}
 setNasalVisible(show:boolean){for(const name of this.parts.keys())if(name.startsWith('NASAL_'))this.setHidden(name,!show);}
 setHidden(name:string,hidden:boolean){if(hidden)this.hidden.add(name);else this.hidden.delete(name);this.applyVisibility();this.render();}
 private applyVisibility(){for(const [name,part]of this.parts)part.visible=!this.hidden.has(name)}
 focus(name:string){const part=this.parts.get(name);if(!part)return;const box=new THREE.Box3().setFromObject(part);const target=box.getCenter(new THREE.Vector3());const r=box.getBoundingSphere(new THREE.Sphere()).radius;for(const n of ['side','front']as ViewName[]){this.controls[n].target.copy(target);this.cameras[n].zoom=THREE.MathUtils.clamp(this.radius/Math.max(r,.01)*.8,1,6);this.cameras[n].updateProjectionMatrix();this.controls[n].update()}this.render()}
 highlight(name:string){
  if(this.selected&&this.emission){for(const m of Array.isArray(this.selected.material)?this.selected.material:[this.selected.material])if('emissive'in m)(m as THREE.MeshStandardMaterial).emissive.copy(this.emission)}
  this.selected=this.parts.get(name);this.emission=undefined;if(!this.selected)return;for(const m of Array.isArray(this.selected.material)?this.selected.material:[this.selected.material])if('emissive'in m){this.emission=(m as THREE.MeshStandardMaterial).emissive.clone();(m as THREE.MeshStandardMaterial).emissive.setHex(0x3c1d05)}this.render();
 }

 /** The runtime accepts only morph keys present in the actual loaded asset. */
 availableMorphTargets():string[]{const keys=new Set<string>();for(const mesh of this.parts.values())for(const key of Object.keys(mesh.morphTargetDictionary??{}))keys.add(key);return [...keys];}
 validateMorphTargets(keys:string[]){const present=new Set(this.availableMorphTargets());const missing=keys.filter(key=>!present.has(key));if(missing.length)throw new Error(`أهداف تشوه غير موجودة في الأصل الفعلي: ${missing.join(', ')}`);}
 setMotionDriver(driver:((now:number)=>void)|null){this.motionDriver=driver;}
 applyMotionWeights(weights:Record<string,number>,renderNow=true){
  this.validateMorphTargets(Object.keys(weights).filter(key=>weights[key]!==0));
  for(const mesh of this.parts.values()){const influences=mesh.morphTargetInfluences;if(!influences)continue;influences.fill(0);for(const [key,weight]of Object.entries(weights)){const index=mesh.morphTargetDictionary?.[key];if(index!==undefined){if(!Number.isFinite(weight))throw new Error('وزن تشوه غير صالح.');influences[index]=weight;}}}
  if(renderNow)this.render();
 }
 private render(){
  this.renderer.setScissorTest(false);this.renderer.setClearColor(0x111b20);this.renderer.clear();this.renderer.setScissorTest(true);
  for(const name of ['side','front']as ViewName[]){const v=this.viewport(name);this.renderer.setViewport(v.x,v.y,v.width,v.height);this.renderer.setScissor(v.x,v.y,v.width,v.height);this.renderer.setClearColor(this.clear);this.renderer.clear();this.renderer.clippingPlanes=name==='side'&&this.clipEnabled?[this.sideClip]:[];for(const [part,group]of this.cutCaps)group.visible=name==='side'&&this.clipEnabled&&Boolean(this.parts.get(part)?.visible);this.renderer.render(this.scene,this.cameras[name]);}
  for(const group of this.cutCaps.values())group.visible=false;this.renderer.clippingPlanes=[];
  this.canvas.dataset.renderFrame=String(++this.frameSerial);this.canvas.dataset.clipping=String(this.clipEnabled);this.canvas.dataset.swapped=String(this.swapped);this.canvas.dataset.frontFullFrame=String(this.frontFullFrame);
  const viewport=this.viewport('side');
  for(const [name,el]of this.labelEls){const part=this.parts.get(name)!;if(!this.showLabels||!part.visible){el.hidden=true;continue}const center=new THREE.Box3().setFromObject(part).getCenter(new THREE.Vector3());center.project(this.cameras.side);el.hidden=center.z<-1||center.z>1||Math.abs(center.x)>1||Math.abs(center.y)>1;if(!el.hidden){el.style.left=`${viewport.x+(center.x*.5+.5)*viewport.width}px`;el.style.top=`${this.size.height-viewport.y-viewport.height+(-center.y*.5+.5)*viewport.height}px`;}}
 }
 dispose(){this.disposed=true;cancelAnimationFrame(this.frame);this.resizeObserver.disconnect();for(const c of Object.values(this.controls))c.dispose();if(this.root)this.disposeObject(this.root);this.renderer.dispose();for(const el of this.labelEls.values())el.remove();Object.values(this.panes).forEach(el=>el.remove());}
}
