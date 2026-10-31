import {sampleRa,raDuration,raKeys} from './ra-prototype';
import {AnatomyInspector,partLabels} from './viewer';
import './styles.css';
const root=document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML=`<header><h1>مخارج · فحص الأصل</h1><p class="gate" role="alert">عارض فحص أصل — بوابة التشريح لم تجتز بعد</p></header>
<main><p>هذا عارض تقني للهندسة المكتسبة والمعدّلة. يعرض تجربة حركة طرفية واحدة للراء قيد المراجعة، ولا يمنح اعتمادًا تشريحيًا أو تجويديًا. الشفافية والخامات من ملف الأصل؛ أداة القطع تغيّر الرؤية فقط.</p>
<div class="toolbar"><button id="swap" disabled>تبديل العرضين</button><button id="reset" disabled>استعادة الكاميرتين</button><label><input id="clip" type="checkbox" checked disabled> مقطع جانبي Z=0</label><label><input id="front-full" type="checkbox" disabled> إطار أمامي كامل</label><label><input id="labels" type="checkbox" disabled> أسماء الأجزاء عند مراكزها</label><button id="fullscreen">ملء الشاشة</button></div>
<section id="stage"><canvas aria-label="فحص نموذج ثلاثي الأبعاد فعلي بعرضين" id="canvas"></canvas><div id="labels-layer" aria-hidden="true"></div><span id="primary-label" class="view-label primary-label">مقطع جانبي — الهندسة الحجمية</span><span id="secondary-label" class="view-label secondary-label">أمامي — الشفتان وتيجان الأسنان</span><p class="camera-hint">اسحب للدوران · عجلة للتقريب · زر أيمن للتحريك · بإصبعين على اللمس</p></section>
<div class="motion-controls"><strong>تجربة الراء التقنية</strong><button id="motionPlay" disabled>تشغيل الراء</button><button id="motionReset" disabled>إعادة</button><label>الزمن <input id="motionTime" aria-label="زمن تجربة الراء" type="range" min="0" max="1" step="0.001" value="0" disabled></label><label>السرعة <select id="motionSpeed" disabled><option value="0.25">0.25×</option><option value="0.5" selected>0.5×</option><option value="1">1×</option></select></label><span id="motionPhase" role="status">راحة</span></div><p id="status" role="status">جارٍ تحميل GLB الفعلي…</p>
<div class="inspect-controls"><label>جزء الفحص <select id="part" disabled></select></label><button id="focus" disabled>تركيز الكاميرتين</button><button id="highlight" disabled>تظليل الجزء المختار</button><label><input id="skin" type="checkbox" checked disabled> نسيج الوجه والشفتين</label><label><input id="nose" type="checkbox" checked disabled> إعادة البناء الأنفي</label></div>
<details><summary>حدود هذا الأصل والعارض</summary><ul><li>المصدر Badin/ArtiSynth، مع تعديلات موثقة في ملفات المصدر. الحنك الرخو من أصل بحثي بمواءمة موثقة وحدودها تحتاج مراجعة.</li><li>البطانة الأنفية مؤلفة وغير مقاسة؛ ليست تجويفًا أنفيًا مكتسبًا. لا توجد محاكاة للهواء أو الرنين. التخطيط الليفي على سطح قطع اللسان توضيحي، وليس بيانات عضلية مكتسبة.</li><li>الإطار الأمامي الافتراضي يقتصر على الشفتين والتيجان؛ فعّل «إطار أمامي كامل» لرؤية حدود الأصل وحوافه المقطوعة. الخطأ الهندسي قد يظهر هنا، ولا تخفيه نتيجة تحميل ناجحة. التسميات هنا مراكز أجزاء فعلية، وليست تحديدًا لمناطق تماس.</li><li>تجربة الراء تختبر تماس الطرف تقنيًا؛ التفخيم والترقيق لم يعايرا، ولا تمثل تلاوة معتمدة. بقية الحركات لم تجهز بعد. لا توجد تسجيلات صوتية معتمدة ومرخصة.</li><li>صور viewport صغير لا تعني فحص هاتف فعلي أو أداء عتاده.</li></ul></details>
<p class="source">الأصل التقني: <a href="/models/makharij-ra-prototype.glb" download>تنزيل GLB المفحوص بصريًا</a> · الإطار: متر، X أمامي، Y علوي، Z جانبي. فحص الصورة لا يثبت اجتياز اختبارات هندسية.</p></main>`;
const el=<T extends HTMLElement>(id:string)=>document.getElementById(id) as T;
let viewer:AnatomyInspector;
try{
 viewer=new AnatomyInspector(el('stage'),el('canvas'),el('labels-layer'));
 viewer.load('/models/makharij-ra-prototype.glb').then(info=>{
  viewer.validateMorphTargets(raKeys);
  el('status').textContent=`حُمّل الأصل: ${info.parts.length} جزءًا، ${Math.round(info.triangles).toLocaleString('ar')} مثلثًا. الأبعاد ${Object.values(info.boundsMeters).map(x=>(x*1000).toFixed(1)).join(' × ')} مم. التحميل ليس اجتيازًا لبوابة التشريح.`;
  document.querySelectorAll<HTMLButtonElement|HTMLInputElement|HTMLSelectElement>('button:disabled,input:disabled,select:disabled').forEach(e=>e.disabled=false);
  const select=el<HTMLSelectElement>('part');for(const name of info.parts){const o=document.createElement('option');o.value=name;o.textContent=partLabels[name]??name;select.appendChild(o)}
  el('swap').onclick=()=>{const swapped=viewer.swap();const front=el<HTMLInputElement>('front-full').checked?'أمامي — كامل':'أمامي — الشفتان وتيجان الأسنان';el('primary-label').textContent=swapped?front:'مقطع جانبي — الهندسة الحجمية';el('secondary-label').textContent=swapped?'مقطع جانبي — الهندسة الحجمية':front};
  el<HTMLInputElement>('front-full').onchange=e=>{const full=(e.target as HTMLInputElement).checked;viewer.setFrontFullFrame(full);const label=el('primary-label').textContent?.startsWith('أمامي')?el('primary-label'):el('secondary-label');label.textContent=full?'أمامي — كامل':'أمامي — الشفتان وتيجان الأسنان'};
  el('reset').onclick=()=>viewer.reset();
  el<HTMLInputElement>('clip').onchange=e=>viewer.setClipping((e.target as HTMLInputElement).checked);
  el<HTMLInputElement>('labels').onchange=e=>viewer.setLabels((e.target as HTMLInputElement).checked);
  el<HTMLInputElement>('skin').onchange=e=>viewer.setHidden('LIP_CONTEXT',!(e.target as HTMLInputElement).checked);
  el<HTMLInputElement>('nose').onchange=e=>viewer.setNasalVisible((e.target as HTMLInputElement).checked);
  el('focus').onclick=()=>viewer.focus(select.value);el('highlight').onclick=()=>viewer.highlight(select.value);
  let t=0,running=false,speed=.5,last=performance.now();
  const sync=()=>{const frame=sampleRa(t);el<HTMLInputElement>('motionTime').value=String(t);el('motionPhase').textContent=frame.phase;el<HTMLButtonElement>('motionPlay').textContent=running?'إيقاف':'تشغيل الراء';return frame};
  viewer.setMotionDriver(now=>{if(running)t=Math.min(1,t+Math.min((now-last)/1000,.2)*speed/raDuration);last=now;if(t>=1)running=false;viewer.applyMotionWeights(sync().weights,false);});
  el('motionPlay').onclick=()=>{if(t>=1)t=0;running=!running;last=performance.now();sync()};
  el('motionReset').onclick=()=>{running=false;t=0;viewer.applyMotionWeights(sync().weights)};
  el<HTMLInputElement>('motionTime').oninput=e=>{running=false;t=Number((e.target as HTMLInputElement).value);viewer.applyMotionWeights(sync().weights)};
  el<HTMLSelectElement>('motionSpeed').onchange=e=>{speed=Number((e.target as HTMLSelectElement).value)};

 }).catch(error=>{el('status').textContent=`فشل تحميل/عقد الأصل: ${String(error)}. لا يوجد نموذج بديل.`;el('status').className='error';});
 el('fullscreen').onclick=()=>el('stage').requestFullscreen().catch(()=>{el('status').textContent='ملء الشاشة غير متاح في هذا السياق.'});
 window.addEventListener('pagehide',()=>viewer.dispose(),{once:true});
}catch(error){el('status').textContent=`تعذر تهيئة WebGL: ${String(error)}. لا يوجد نموذج بديل.`;el('status').className='error';}
