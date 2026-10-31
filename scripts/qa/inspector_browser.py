#!/usr/bin/env python3
"""Exercise production technical inspector, not student articulation workflow.
Requires running build preview, Python Playwright, system Chromium. Software
rendering and emulated viewport checks do not establish physical device FPS.
"""
import argparse,hashlib,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:4173')
parser.add_argument('--out',type=Path,default=Path('research/qa/inspector'))
args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
result={'scope':'Production technical inspector only; no articulation, audio, hardware phone or anatomical approval','page_errors':[],'failed_requests':[],'checks':[]}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
 page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
 page.on('requestfailed',lambda r:result['failed_requests'].append({'url':r.url,'failure':r.failure}))
 page.goto(args.url,wait_until='networkidle');page.wait_for_function("document.querySelector('#swap') && !document.querySelector('#swap').disabled",timeout=60000);page.wait_for_timeout(2500)
 scripts=page.locator('script[src]').evaluate_all('(els)=>els.map(e=>e.src)')
 result['entry_scripts']=[{'url':url,'sha256':hashlib.sha256(page.request.get(url).body()).hexdigest()} for url in scripts]
 result['userAgent']=page.evaluate('navigator.userAgent');result['status']=page.locator('#status').inner_text()
 assert 'بوابة التشريح لم تجتز بعد' in page.locator('.gate').inner_text()
 assert page.locator('#part option').count()==12
 response=page.request.get(args.url+'/models/makharij-rest.glb');assert response.status==200
 result['loaded_asset_bytes']=len(response.body());result['loaded_asset_sha256']=hashlib.sha256(response.body()).hexdigest()
 def pixels():return page.locator('canvas').evaluate('(c)=>c.toDataURL()')
 def check(name,passed,detail=None):
  result['checks'].append({'name':name,'passed':bool(passed),'detail':detail})
  (args.out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  assert passed,name
 before=pixels();page.screenshot(path=str(args.out/'desktop-default.png'),full_page=True)
 page.locator('#swap').click();page.wait_for_function("document.querySelector('canvas').dataset.swapped==='true'");page.wait_for_timeout(800)
 check('swap changes actual canvas and view labels',pixels()!=before and 'أمامي' in page.locator('#primary-label').inner_text())
 page.locator('#swap').click();page.wait_for_function("document.querySelector('canvas').dataset.swapped==='false'");page.locator('#clip').uncheck();page.wait_for_function("document.querySelector('canvas').dataset.clipping==='false'")
 unclipped=pixels();page.locator('#clip').check();page.wait_for_function("document.querySelector('canvas').dataset.clipping==='true'")
 check('side cut changes rendered pixels',pixels()!=unclipped)
 before=pixels();page.locator('#front-full').check();page.wait_for_function("document.querySelector('canvas').dataset.frontFullFrame==='true'");check('front full framing changes rendered pixels',pixels()!=before);page.locator('#front-full').uncheck()
 page.locator('#labels').check();page.wait_for_timeout(1500)
 visible=page.locator('.anatomy-label:visible').count();check('actual part center labels visible',visible>0,visible)
 page.locator('#part').select_option('TONGUE');before=pixels();page.locator('#highlight').click();page.wait_for_timeout(1500)
 check('selected part highlight changes rendered pixels',pixels()!=before)
 before=pixels();page.locator('#focus').click();page.wait_for_timeout(1500)
 check('focus camera changes rendered pixels',pixels()!=before)
 page.locator('#reset').click();page.locator('#labels').uncheck();page.wait_for_timeout(1500)
 before=pixels();page.locator('#skin').uncheck();page.wait_for_timeout(1500)
 check('face context toggle changes rendered pixels',pixels()!=before)
 page.locator('#skin').check();page.wait_for_timeout(1500)
 pane=page.locator('.interaction-pane.primary').bounding_box();x=pane['x']+pane['width']*.45;y=pane['y']+pane['height']*.5
 before=pixels();page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+80,y+20,steps=8);page.mouse.up();page.wait_for_timeout(2000)
 check('drag orbit changes rendered pixels',pixels()!=before)
 before=pixels();page.mouse.wheel(0,-240);page.wait_for_timeout(2000)
 check('wheel zoom changes rendered pixels',pixels()!=before)
 for width,height,name in [(768,1024,'tablet-768'),(390,844,'responsive-390')]:
  page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(1500)
  check(name+' no horizontal document overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
  page.screenshot(path=str(args.out/(name+'.png')),full_page=True)
 check('no runtime page errors',not result['page_errors'],result['page_errors'])
 check('no failed resource requests',not result['failed_requests'],result['failed_requests'])
 b.close()
(args.out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
