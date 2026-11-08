"""Actual nasal GLB in Chromium, cutaway/empty-lumen view and mobile layout."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/method-evidence/nasal-cavity/browser'
OUT.mkdir(exist_ok=True, parents=True)
URL = os.environ.get('MAKHARIJ_ORAL_TEST_URL', 'http://127.0.0.1:4174')
m = json.loads((ROOT/'public/models/nasal-cavity.manifest.json').read_text())
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1365,'height':1024})
    page.on('pageerror', lambda e:errors.append(str(e)))
    page.goto(URL, wait_until='networkidle')
    page.wait_for_function('window.__oralStudy?.ready',timeout=90000)
    page.get_by_role('button',name='الخيشوم',exact=True).click()
    page.wait_for_timeout(500)
    state = page.evaluate('window.__oralStudy.snapshot()')
    assert state['mode']=='nasal' and state['nasalVisible']
    assert state['nasalSha256']==m['glbSha256']
    assert set(state['nasalParts'])==set(m['parts'])
    assert not any('AIR' in name for name in state['nasalParts'])
    assert hashlib.sha256(page.request.get(URL+'/models/nasal-cavity.glb').body()).hexdigest()==m['glbSha256']
    assert page.locator('#controls').is_hidden()
    page.screenshot(path=str(OUT/'nasal-desktop.png'),full_page=True)
    section = page.locator('#oral-stage').screenshot(path=str(OUT/'nasal-section.png'))
    page.locator('#nasal-paths').uncheck();page.wait_for_timeout(150)
    assert not page.evaluate('window.__oralStudy.snapshot().nasalPaths')
    page.locator('#oral-stage').screenshot(path=str(OUT/'nasal-empty.png'))
    page.locator('#nasal-cut').uncheck();page.wait_for_timeout(200)
    full = page.locator('#oral-stage').screenshot(path=str(OUT/'nasal-full.png'))
    assert full != section
    assert not page.evaluate('window.__oralStudy.snapshot().nasalSection')
    page.locator('[data-camera="front"]').click();page.wait_for_timeout(200)
    page.locator('#oral-stage').screenshot(path=str(OUT/'nasal-inlets.png'))
    page.get_by_role('button',name='الوجه',exact=True).click()
    assert not page.evaluate('window.__oralStudy.snapshot().nasalVisible')
    mobile = browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    mobile.goto(URL,wait_until='networkidle');mobile.wait_for_function('window.__oralStudy?.ready',timeout=90000)
    mobile.get_by_role('button',name='الخيشوم',exact=True).tap();mobile.wait_for_timeout(300)
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    mobile.screenshot(path=str(OUT/'nasal-mobile.png'),full_page=True)
    assert not errors, errors
    (OUT/'browser-review.json').write_text(json.dumps({'passed':True,'assetSha256':m['glbSha256'],
        'runtimePositiveWallOnly':True,'cutawayToggle':True,'guideToggle':True,'mobileWidth':390,
        'pageErrors':errors,'scope':'Actual browser wall rendering and controls; geometry/continuity evaluated separately'},indent=2)+'\n')
    browser.close()
print('PASS: actual nasal wall, cutaway, guide toggle and mobile layout')
