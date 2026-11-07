"""Actual GLB load, two static viewports and camera-rotation evidence in Chromium.

The routed harness exists only in this test. It does not replace the preserved
production inspector or claim a new articulation/teacher interface is ready.
"""
import hashlib
import json
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/milestone-evidence/M2/character-assembly'
record = json.loads((OUT / 'assembly.manifest.json').read_text())
sections = json.loads((OUT / 'computed-sections.json').read_text())
assert sections['assetSha256'] == record['glbSha256']
blob = (OUT / 'character-assembly.glb').read_bytes()
assert hashlib.sha256(blob).hexdigest() == record['glbSha256']
bundle = Path('/workspace/artifacts/character-browser.js')
subprocess.run([str(ROOT / 'node_modules/.bin/esbuild'), str(ROOT / 'tools/qa/character_browser.ts'), '--bundle', '--format=esm', '--target=es2022', '--outfile=' + str(bundle)], check=True, capture_output=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                              args=['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    origin = 'http://127.0.0.1:4173'
    html = '''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><title>مراجعة تشريح مخارج — مسودة M2</title>
    <style>body{margin:0;background:#e3e5e4;font:16px sans-serif;color:#343c3e}p{height:40px;margin:0;text-align:center;line-height:40px}canvas{display:block;width:1280px;height:860px}</style>
    <p>مخارج — مسودة تشريح للمراجعة: الرأس الخارجي والمقطع الحجمي · التحريك والمراجعة العلمية قيد العمل</p>
    <canvas></canvas><script type="module" src="/__character.js"></script></html>'''
    page.route(origin + '/__review', lambda route: route.fulfill(body=html, content_type='text/html'))
    page.route(origin + '/favicon.ico', lambda route: route.fulfill(status=204))
    page.route(origin + '/__character.js', lambda route: route.fulfill(path=str(bundle), content_type='text/javascript'))
    page.route(origin + '/__character.glb', lambda route: route.fulfill(body=blob, content_type='model/gltf-binary'))
    page.route(origin + '/__sections.json', lambda route: route.fulfill(body=json.dumps(sections), content_type='application/json'))
    page.goto(origin + '/__review', wait_until='networkidle')
    page.wait_for_function('Boolean(window.characterReview)', timeout=45000)
    info = page.evaluate('({meshCount:characterReview.meshCount,triangleCount:characterReview.triangleCount,bounds:characterReview.bounds,assetSha256:characterReview.assetSha256})')
    assert info['meshCount'] >= 19 and info['triangleCount'] > 80000
    assert info['assetSha256'] == record['glbSha256']
    page.screenshot(path=str(OUT / 'browser-review.png'))
    frames = []
    for i in range(8):
        page.evaluate('(yaw)=>characterReview.render(yaw)', i * 3.141592653589793 / 4)
        page.wait_for_timeout(180)
        path = OUT / f'volume-rotation-{i:02}.png'
        page.screenshot(path=str(path), clip={'x': 0, 'y': 40, 'width': 640, 'height': 860})
        frames.append(path)
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in frames]
    assert len(set(hashes)) == 8, 'Camera rotation did not produce distinct real volume views'
    assert not errors, errors
    images = [Image.open(path).convert('RGB') for path in frames]
    images[0].save(OUT / 'volume-rotation.gif', save_all=True, append_images=images[1:], duration=400, loop=0)
    result = {**info, 'pageErrors': errors, 'cameraRotationViews': 8, 'singleRendererTwoViewports': True,
              'renderer': 'Chromium software SwiftShader; physical-device performance not measured',
              'scope': 'Static M2 review harness using actual GLB and independently computed sections; production UI and articulation not changed',
              'rotationFrameSha256': hashes}
    (OUT / 'browser-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    browser.close()
print(json.dumps({'actualGlbMeshes': info['meshCount'], 'actualGlbTriangles': info['triangleCount'], 'cameraRotationViews': 8, 'pageErrors': errors}, indent=2))
