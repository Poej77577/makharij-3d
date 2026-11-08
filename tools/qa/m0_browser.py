"""Fresh-environment production smoke test of the preserved technical inspector.
This checks the legacy delivery only; it does not pass the new M1/M2 gates.
"""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/milestone-evidence/M0'
OUT.mkdir(parents=True, exist_ok=True)
url = os.environ.get('MAKHARIJ_TEST_URL', 'http://127.0.0.1:4173')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    response = page.goto(url + '/legacy.html', wait_until='networkidle')
    assert response and response.ok
    page.wait_for_function("!document.querySelector('#motionPlay').disabled")
    assert '13' in page.locator('#status').inner_text(), 'Preserved model inventory changed'
    data = page.request.get(url + '/models/makharij-ra-prototype.glb').body()
    assert hashlib.sha256(data).hexdigest() == hashlib.sha256((ROOT / 'assets/anatomy/makharij-ra-prototype.glb').read_bytes()).hexdigest()
    def scrub(t):
        page.locator('#motionTime').fill(str(t))
        page.wait_for_timeout(350)
        return page.locator('canvas').evaluate('(canvas)=>canvas.toDataURL()')
    rest = scrub(0)
    peak = scrub(.41)
    assert peak != rest
    assert scrub(1) == rest
    page.screenshot(path=str(OUT / 'preserved-inspector.png'), full_page=True)
    assert not errors, errors
    (OUT / 'browser-smoke.json').write_text(json.dumps({
        'httpStatus': response.status,
        'pagePath': '/legacy.html',
        'assetSha256': hashlib.sha256(data).hexdigest(),
        'actualPoseChange': True,
        'returnMatchesRest': True,
        'pageErrors': errors,
        'renderer': 'Chromium software SwiftShader; no physical-device performance claim',
        'scope': 'M0 functional readiness of preserved technical inspector. New external anatomy gate NOT passed.',
    }, indent=2) + '\n')
    browser.close()
print('PASS: production page, actual GLB identity, changed pose, return and no page errors')
