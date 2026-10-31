from playwright.sync_api import sync_playwright
from pathlib import Path
import hashlib,json
from urllib.parse import urljoin
root=Path(__file__).resolve().parents[2];out=root/'research/qa/ra-runtime-v10-refined';out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1150},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:4173',wait_until='networkidle');page.wait_for_function("!document.querySelector('#motionPlay').disabled")
 source=page.request.get('http://127.0.0.1:4173/models/makharij-ra-prototype.glb').body();assert hashlib.sha256(source).hexdigest()==hashlib.sha256((root/'assets/anatomy/makharij-ra-prototype.glb').read_bytes()).hexdigest()
 def scrub(t):
  page.locator('#motionTime').fill(str(t));page.wait_for_timeout(900);return page.locator('canvas').evaluate('(c)=>c.toDataURL()')
 rest=scrub(0);page.screenshot(path=str(out/'rest.png'),full_page=True)
 peak=scrub(.41);assert rest!=peak;assert 'تحقيق' in page.locator('#motionPhase').inner_text();page.screenshot(path=str(out/'ra-contact.png'),full_page=True)
 back=scrub(1);assert back==rest,'Returned rendered pose differs from rest';page.locator('#motionReset').click()
 page.locator('#motionSpeed').select_option('0.25')
 page.evaluate('''()=>{const c=document.querySelector('canvas');const types=['video/webm;codecs=vp9','video/webm;codecs=vp8'];const mime=types.find(t=>MediaRecorder.isTypeSupported(t));if(!mime)throw Error('No video codec');const stream=c.captureStream(20);const rec=new MediaRecorder(stream,{mimeType:mime});const parts=[];rec.ondataavailable=e=>{if(e.data.size)parts.push(e.data)};rec.onstop=()=>{const u=URL.createObjectURL(new Blob(parts,{type:mime}));const a=document.createElement('a');a.href=u;a.download='ra-reference-prototype.webm';a.click();stream.getTracks().forEach(t=>t.stop())};window._raRecorder=rec;rec.start(100)}''')
 page.locator('#motionPlay').click();page.wait_for_function("Number(document.querySelector('#motionTime').value)>=1",timeout=35000);page.wait_for_timeout(400)
 with page.expect_download(timeout=10000) as pending:page.evaluate('window._raRecorder.stop()')
 pending.value.save_as(str(out/'ra-reference-prototype.webm'))
 assert not errors,errors
 result={'pageErrors':errors,'assetSha256':hashlib.sha256(source).hexdigest(),'renderBundleSha256':hashlib.sha256(page.request.get(urljoin(page.url,page.locator('script[type=module]').get_attribute('src'))).body()).hexdigest(),'actualCanvasRestPeakDiffer':True,'actualCanvasReturnMatchesRest':True,'recordedFullCycle':True,'recordedPlaybackSpeed':.25,'videoBytes':(out/'ra-reference-prototype.webm').stat().st_size,'renderer':'Chromium SwiftShader software; no hardware phone performance claim','scope':'Ra technical prototype only; anatomy/tajwid qualification and other letters pending'}
 (out/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));print(json.dumps(result,ensure_ascii=False));b.close()
