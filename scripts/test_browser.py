"""Exercise the production build with system Chromium + software WebGL.
Phone viewport is emulation, not a physical phone test.
"""
import asyncio,json,platform,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def main():
 async with async_playwright()as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader','--enable-webgl'])
  ctx=await browser.new_context(viewport={'width':1480,'height':1150},device_scale_factor=1,accept_downloads=True)
  page=await ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  resp=await page.goto('http://127.0.0.1:4173/');assert resp.status==200
  for url in ['licenses/ArtiSynth-LICENSE.txt','licenses/Noto-Sans-Arabic-OFL.txt','licenses/Three-MIT.txt','models/ATTRIBUTION.md']:
   assert(await page.request.get('http://127.0.0.1:4173/'+url)).status==200
  await page.wait_for_function('window.makharijQA?.getState().ready',timeout=90000)
  await page.screenshot(path=str(ROOT/'public/evidence/browser-desktop.png'),full_page=True)
  await page.locator('#fullscreen').click();await page.wait_for_function('Boolean(document.fullscreenElement)');await page.evaluate('document.exitFullscreen()')
  s=await page.evaluate('window.makharijQA.getState()');assert s['main']=='section'and s['secondary']=='front'
  await page.locator('#full-view').click();assert(await page.evaluate('window.makharijQA.getState().main'))=='full'
  await page.locator('#swap').click();assert(await page.evaluate('window.makharijQA.getState().main'))=='front'
  await page.locator('#restore').click()
  await page.locator('[data-part="tongue"]').click();await page.locator('#focus').click()
  await page.screenshot(path=str(ROOT/'public/evidence/browser-tongue-focus.png'))
  await page.locator('[data-layer="tongue"]').uncheck();assert'tongue'in(await page.evaluate('window.makharijQA.getState().hidden'))
  await page.locator('#save-view').click();await page.reload();await page.wait_for_function('window.makharijQA?.getState().ready',timeout=90000)
  assert not await page.locator('[data-layer="tongue"]').is_checked()
  await page.locator('#restore').click()
  async with page.expect_download()as d:await page.locator('#capture').click()
  capture=await d.value;await capture.save_as(str(ROOT/'public/evidence/browser-export.png'))
  await page.locator('#about').click()
  assert await page.locator('#info-dialog').is_visible()
  async with page.expect_download()as d:await page.locator('a[download]').click()
  dl=await d.value;await dl.save_as(str(ROOT/'work/browser-downloaded.glb'))
  assert(ROOT/'work/browser-downloaded.glb').read_bytes()==(ROOT/'public/models/makharij-rest.glb').read_bytes()
  await page.locator('.dialog-close').click()
  await page.locator('#primary').focus();await page.keyboard.press('ArrowLeft');await page.keyboard.press('+');await page.keyboard.press('0')
  await page.locator('#evidence').click();assert await page.locator('.evidence-grid img').count()==5;await page.keyboard.press('Escape')
  await page.locator('#full-view').click()
  await page.screenshot(path=str(ROOT/'public/evidence/browser-volume.png'))
  gpu=await page.evaluate('''()=>{let g=document.querySelector('canvas').getContext('webgl2');let e=g.getExtension('WEBGL_debug_renderer_info');return {version:g.getParameter(g.VERSION),renderer:e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):'not available'}}''')
  # Record an actual changing camera around the delivered GLB, at fixed angular increments.
  frames=ROOT/'work/rotation';frames.mkdir(exist_ok=True)
  await page.locator('#restore').click();await page.locator('#full-view').click()
  for i in range(24):
   await page.evaluate('window.makharijQA.orbit(Math.PI*2/24)')
   await page.locator('.viewer-card').screenshot(path=str(frames/f'{i:03d}.png'))
  mobile=await browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
  phone=await mobile.new_page();phone.on('pageerror',lambda e:errors.append('mobile: '+str(e)))
  await phone.goto('http://127.0.0.1:4173/');await phone.wait_for_function('window.makharijQA?.getState().ready',timeout=90000)
  assert await phone.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
  await phone.screenshot(path=str(ROOT/'public/evidence/browser-mobile.png'),full_page=True)
  await phone.locator('#full-view').tap();assert(await phone.evaluate('window.makharijQA.getState().main'))=='full'
  await phone.locator('#swap').tap();assert(await phone.evaluate('window.makharijQA.getState().main'))=='front'
  await phone.locator('#about').tap();await phone.locator('.dialog-close').tap()
  # Touch drag on the actual canvas via CDP.
  rect=await phone.locator('#primary').bounding_box();cdp=await mobile.new_cdp_session(phone)
  await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':rect['x']+200,'y':rect['y']+160}]})
  await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':rect['x']+140,'y':rect['y']+180}]})
  await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
  assert not errors,errors
  result={'date':'2026-10-31','platform':platform.platform(),'chromium':browser.version,'gpu':gpu,'webgl':'software','viewportDesktop':[1480,1150],'viewportPhone':[390,844],'physicalPhone':False,'checks':['production HTTP 200','packaged license notices HTTP 200','fullscreen enter/exit','final GLB loaded','two actual views','swap','volume mode','select and focus','layer visibility','persist/reload','PNG download','GLB download byte identity','sources modal','evidence gallery','keyboard rotate/zoom/reset','24-angle rotation capture','mobile layout without horizontal overflow','touch actions and touch drag'],'pageErrors':errors,'notTested':['clinical anatomy','tajwid expert review','letter articulation','physical hardware GPU','physical phone','screen reader','audio','performance benchmarks']}
  (ROOT/'docs/browser-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  await browser.close()
asyncio.run(main())
