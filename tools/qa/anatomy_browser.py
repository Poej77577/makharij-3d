"""Review the actual production anatomy page, asset identity and controls."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/milestone-evidence/M2/realistic-rebuild'
url = os.environ.get('MAKHARIJ_TEST_URL', 'http://127.0.0.1:4173')
manifest = json.loads((OUT / 'atlas-study.manifest.json').read_text())
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 1000}, device_scale_factor=1)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text + ' ' + str(m.location)) if m.type == 'error' else None)
    response = page.goto(url + '/anatomy.html', wait_until='networkidle')
    assert response and response.ok
    page.wait_for_function('Boolean(window.anatomyReview)', timeout=90000)
    info = page.evaluate('({assetSha256:anatomyReview.assetSha256,meshCount:anatomyReview.meshCount,triangles:anatomyReview.triangles,sectionCaps:anatomyReview.sectionCaps,rendererInstances:anatomyReview.rendererInstances})')
    assert info['assetSha256'] == manifest['glbSha256']
    assert info['meshCount'] >= len(manifest['parts']) and info['rendererInstances'] == 1
    ids = page.evaluate('({main:anatomyReview.sectionPartIds,nose:anatomyReview.nasalPartIds})')
    assert {'HEAD_SKIN', 'ATLAS_TONGUE', 'ATLAS_GENIOGLOSSUS_MUSCLE_R', 'ATLAS_SOFT_PALATE'} <= set(ids['main'])
    assert {'ATLAS_MUCOSA_OF_NASAL_CAVITY', 'ATLAS_INFERIOR_NASAL_CONCHA_BONE_R'} <= set(ids['nose'])
    blob = page.request.get(url + '/models/makharij-realistic.glb').body()
    assert hashlib.sha256(blob).hexdigest() == manifest['glbSha256']
    page.wait_for_timeout(400)
    page.screenshot(path=str(OUT / 'browser-review.png'), full_page=True)
    page.locator('#section').click()
    page.locator('#focus').select_option('mouth')
    assert abs(page.evaluate('anatomyReview.planeZ_m') - .00501) < 1e-9
    page.wait_for_timeout(300)
    before_drag = page.locator('canvas').evaluate('(c)=>c.toDataURL()')
    pane = page.locator('.section-pane').bounding_box()
    assert pane
    x, y = pane['x'] + pane['width'] / 2, pane['y'] + pane['height'] / 2
    page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x + 100, y + 30, steps=6); page.mouse.up()
    page.wait_for_timeout(400)
    assert page.locator('canvas').evaluate('(c)=>c.toDataURL()') != before_drag, 'Actual pointer drag failed to rotate the model'
    page.locator('#reset').click(); page.wait_for_timeout(300)
    page.locator('#review-stage').screenshot(path=str(OUT / 'browser-mouth.png'))
    page.locator('#focus').select_option('nose')
    assert abs(page.evaluate('anatomyReview.planeZ_m') - .00901) < 1e-9
    page.wait_for_timeout(300)
    page.locator('#review-stage').screenshot(path=str(OUT / 'browser-nose.png'))
    page.locator('#external').click()
    frames = []
    for i in range(8):
        page.evaluate('(yaw)=>anatomyReview.rotate(yaw)', i * 3.141592653589793 / 4)
        page.wait_for_timeout(200)
        path = OUT / f'rotation-{i:02}.png'
        page.locator('#review-stage').screenshot(path=str(path))
        frames.append(path)
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in frames]
    assert len(set(hashes)) == 8
    images = [Image.open(path).convert('RGB') for path in frames]
    images[0].save(OUT / 'rotation.gif', save_all=True, append_images=images[1:], duration=400, loop=0)
    page.close()
    mobile = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
    mobile.on('pageerror', lambda e: errors.append(str(e)))
    mobile.goto(url + '/anatomy.html', wait_until='networkidle')
    mobile.wait_for_function('Boolean(window.anatomyReview)', timeout=90000)
    assert mobile.locator('#section').get_attribute('aria-pressed') == 'true'
    assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    mobile.screenshot(path=str(OUT / 'browser-mobile.png'), full_page=True)
    assert not errors, errors
    result = {**info, 'pageErrors': errors, 'cameraRotationViews': 8, 'rotationFrameSha256': hashes,
        'actualProductionPage': True, 'actualPointerRotation': True, 'focusControlsExercised': ['mouth', 'nose'], 'mobileLayout': {'width': 390, 'horizontalOverflow': False},
        'renderer': 'Chromium software SwiftShader; no physical-device performance claim',
        'scope': 'Actual resting-model review page, GLB identity, matching tissue sections, controls and camera rotation; no articulation or scientific acceptance'}
    (OUT / 'browser-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    browser.close()
print(json.dumps({'productionReviewPage': True, **info, 'cameraRotationViews': 8, 'pageErrors': errors}, indent=2))
