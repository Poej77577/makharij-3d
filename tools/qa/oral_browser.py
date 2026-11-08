"""Actual GLB control/cap/camera/mobile checks in Chromium; no anatomy approval."""
import hashlib
import json
import math
import os
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'artifacts/method-evidence/oral-sculpt/browser'
OUT.mkdir(exist_ok=True, parents=True)
URL = os.environ.get('MAKHARIJ_ORAL_TEST_URL', 'http://127.0.0.1:4174')
manifest = json.loads((ROOT/'public/models/oral-study.manifest.json').read_text())
face_manifest = json.loads((ROOT/'public/models/face-context.manifest.json').read_text())
errors = []


def snap(page):
    return page.evaluate('window.__oralStudy.snapshot()')


def control(page, key, value):
    before = snap(page)['renderCount']
    page.locator('#'+key).evaluate('(el,v)=>{el.value=String(v);el.dispatchEvent(new Event("input",{bubbles:true}));}', value)
    page.wait_for_function('(n)=>window.__oralStudy.snapshot().renderCount>n', arg=before)


def movement(a, b, name):
    return max(math.dist(p, q) for p, q in zip(a['probes'][name], b['probes'][name]))


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1365, 'height': 1024}, device_scale_factor=1)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    response = page.goto(URL+'/mouth.html', wait_until='networkidle')
    assert response and response.ok
    page.wait_for_function('window.__oralStudy?.ready', timeout=90000)
    page.wait_for_timeout(600)
    initial = snap(page)
    assert initial['assetSha256'] == manifest['glbSha256']
    assert set(initial['parts']) == set(manifest['parts'])
    assert initial['faceSha256'] == face_manifest['glbSha256']
    assert set(initial['contextParts']) == set(face_manifest['parts'])
    assert initial['mode'] == 'face' and initial['faceVisible']
    blob = page.request.get(URL+'/models/oral-study.glb').body()
    assert hashlib.sha256(blob).hexdigest() == manifest['glbSha256']
    face_blob = page.request.get(URL+'/models/face-context.glb').body()
    assert hashlib.sha256(face_blob).hexdigest() == face_manifest['glbSha256']
    page.screenshot(path=str(OUT/'desktop.png'), full_page=True)
    page.locator('#oral-stage').screenshot(path=str(OUT/'face.png'))
    face_movements = {}
    for key in ['LIP_PRESS', 'LIP_ROUND', 'LIP_PROTRUDE']:
        control(page, key, 100)
        current = snap(page)
        face_movements[key] = movement(initial, current, 'HEAD_EXTERNAL')
        assert face_movements[key] > .002, (key, face_movements[key])
        assert movement(initial, current, 'FACE_EYES') < 1e-7
        page.locator('#oral-stage').screenshot(path=str(OUT/('face-'+key.lower()+'.png')))
        page.locator('#rest').click()
        returned = snap(page)
        assert movement(initial, returned, 'HEAD_EXTERNAL') < 1e-7
    control(page, 'JAW_OPEN', 100)
    coupled_jaw = snap(page)
    assert movement(initial, coupled_jaw, 'HEAD_EXTERNAL') > .006
    assert movement(initial, coupled_jaw, 'LOWER_DENTITION') > .006
    assert movement(initial, coupled_jaw, 'FACE_EYES') < 1e-7
    page.locator('#oral-stage').screenshot(path=str(OUT/'face-open.png'))
    page.locator('#rest').click()
    control(page, 'JAW_OPEN', 55)
    control(page, 'LIP_ROUND', 65)
    page.locator('#oral-stage').screenshot(path=str(OUT/'face-combined.png'))
    face_frames = []
    for i, value in enumerate([0, 25, 50, 75, 100, 75, 50, 25, 0]):
        control(page, 'LIP_ROUND', value)
        path = OUT/f'face-motion-{i:02}.png'
        page.locator('#oral-stage').screenshot(path=str(path))
        face_frames.append(Image.open(path).convert('RGB'))
    face_frames[0].save(OUT/'lip-motion.gif', save_all=True, append_images=face_frames[1:], duration=180, loop=0)
    page.locator('#rest').click()
    page.get_by_role('button', name='اللسان والقاع', exact=True).click()
    page.wait_for_timeout(200)
    initial = snap(page)
    page.locator('#oral-stage').screenshot(path=str(OUT/'mouth.png'))
    movements = {}
    for key, threshold in [('TIP_ELEVATE', .005), ('DORSUM_ELEVATE', .003), ('ROOT_RETRACT', .001), ('JAW_OPEN', .004), ('VELUM_RAISE', .004)]:
        control(page, key, 100)
        current = snap(page)
        target = 'PALATE' if key == 'VELUM_RAISE' else 'LOWER_DENTITION' if key == 'JAW_OPEN' else 'TONGUE'
        movements[key] = movement(initial, current, target)
        assert movements[key] > threshold, (key, movements[key])
        page.locator('#rest').click()
    page.wait_for_timeout(200)
    assert movement(initial, snap(page), 'TONGUE') < 1e-7
    page.get_by_role('button', name='المقطع الجانبي', exact=True).click()
    page.wait_for_function('window.__oralStudy.snapshot().capSignatures.TONGUE?.triangles>0')
    rest_caps = snap(page)
    assert not rest_caps['faceVisible']
    assert 'HEAD_EXTERNAL' not in rest_caps['capDiagnostics'], 'Open context skin was incorrectly capped as cranial tissue'
    for name in ['TONGUE', 'ORAL_FLOOR', 'PALATE']:
        assert rest_caps['capDiagnostics'][name]['openChains'] == 0, rest_caps['capDiagnostics']
    control(page, 'JAW_OPEN', 65)
    control(page, 'TIP_ELEVATE', 80)
    combined = snap(page)
    assert combined['capSignatures']['TONGUE']['signature'] != rest_caps['capSignatures']['TONGUE']['signature']
    page.screenshot(path=str(OUT/'section.png'), full_page=True)
    page.locator('#oral-stage').screenshot(path=str(OUT/'section-detail.png'))
    # Actual browser-rendered morph frames, with caps rebuilt at each weight.
    frames = []
    for i, value in enumerate([0, 25, 50, 75, 100, 75, 50, 25, 0]):
        control(page, 'TIP_ELEVATE', value)
        path = OUT/f'motion-{i:02}.png'
        page.locator('#oral-stage').screenshot(path=str(path))
        frames.append(Image.open(path).convert('RGB'))
    frames[0].save(OUT/'tongue-motion.gif', save_all=True, append_images=frames[1:], duration=180, loop=0)
    page.locator('#rest').click()
    page.locator('#clay').check(); page.wait_for_timeout(150)
    assert snap(page)['clay']
    page.locator('#clay').uncheck()
    page.get_by_role('button', name='اللسان والقاع', exact=True).click()
    page.wait_for_timeout(300)
    before = page.locator('#oral-stage').screenshot()
    camera_before = snap(page)['camera']
    box = page.locator('#oral-stage').bounding_box()
    x, y = box['x']+box['width']/2, box['y']+box['height']/2
    page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x+80, y+30, steps=7); page.mouse.up()
    page.wait_for_timeout(400)
    assert math.dist(camera_before, snap(page)['camera']) > .001, 'Actual camera did not orbit'
    assert page.locator('#oral-stage').screenshot() != before, 'Composited model image did not change'
    page.locator('#camera-reset').click()
    page.locator('#play').click(); page.wait_for_timeout(700)
    assert snap(page)['playing']
    page.locator('#play').click(); page.locator('#rest').click()
    page.wait_for_timeout(900)
    idle_a = snap(page)['renderCount']; page.wait_for_timeout(350)
    idle_frames = snap(page)['renderCount']-idle_a
    assert idle_frames <= 2, idle_frames
    mobile = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
    mobile.on('pageerror', lambda error: errors.append(str(error)))
    mobile.goto(URL+'/mouth.html', wait_until='networkidle')
    mobile.wait_for_function('window.__oralStudy?.ready', timeout=90000)
    assert snap(mobile)['mode'] == 'face'
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    mobile.screenshot(path=str(OUT/'mobile-face.png'), full_page=True)
    mobile.get_by_role('button', name='المقطع الجانبي', exact=True).tap()
    mobile.wait_for_function('window.__oralStudy.snapshot().capSignatures.TONGUE?.triangles>0')
    mobile.screenshot(path=str(OUT/'mobile.png'), full_page=True)
    assert not errors, errors
    report = {'assetSha256': manifest['glbSha256'], 'faceSha256': face_manifest['glbSha256'],
              'meshCount': len(initial['parts']), 'faceContextMeshes': len(initial['contextParts']),
              'actualLipMovement_m': face_movements, 'coupledFaceJaw': True, 'contextSkinExcludedFromCaps': True,
              'faceEvidencePoses': {'face.png': {}, 'face-open.png': {'JAW_OPEN': 1},
                  'face-combined.png': {'JAW_OPEN': .55, 'LIP_ROUND': .65},
                  **{'face-'+key.lower()+'.png': {key: 1} for key in face_movements}},
              'actualSurfaceMovement_m': movements, 'dynamicCaps': True,
              'capDiagnostics': combined['capDiagnostics'], 'returnToRest': True,
              'pointerOrbit': True, 'clayToggle': True, 'animationPlayback': True,
              'idleRenderFramesIn350ms': idle_frames, 'mobileWidth': 390,
              'horizontalOverflow': False, 'pageErrors': errors,
              'scope': 'Actual experimental GLB in Chromium SwiftShader; no clinical acceptance or physical-phone benchmark'}
    (OUT/'browser-review.json').write_text(json.dumps(report, indent=2)+'\n')
    browser.close()
print(json.dumps({'pass': True, 'movements_m': movements, 'lipMovements_m': face_movements, 'pageErrors': errors}, indent=2))
