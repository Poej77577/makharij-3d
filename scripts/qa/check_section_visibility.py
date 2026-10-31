from playwright.sync_api import sync_playwright
from pathlib import Path
import json
root=Path(__file__).resolve().parents[2];out=root/'research/qa/ra-runtime-v10-refined';out.mkdir(exist_ok=True,parents=True)
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']);page=b.new_page(viewport={'width':1440,'height':1150});page.goto('http://127.0.0.1:4173',wait_until='networkidle');page.wait_for_function("!document.querySelector('#motionPlay').disabled")
 def snap():
  page.wait_for_timeout(600);return page.locator('canvas').evaluate('(c)=>c.toDataURL()')
 rest=snap();page.locator('#nose').uncheck();hidden=snap();assert hidden!=rest;page.screenshot(path=str(out/'nasal-hidden.png'),full_page=True);page.locator('#nose').check();assert snap()==rest
 page.locator('#clip').uncheck();assert snap()!=rest;page.screenshot(path=str(out/'full-volume.png'),full_page=True);page.locator('#clip').check();assert snap()==rest
 result={'nasalHideChangesActualCanvas':True,'nasalRestoreMatchesOriginal':True,'fullVolumeChangesActualCanvas':True,'sectionRestoreMatchesOriginal':True};(out/'section-visibility.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));b.close()
