"""Real browser interaction/export checks (Playwright is a verification dependency)."""
import argparse,csv,io,json,math,os,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8000/JupyterLite-OneHealth/');p.add_argument('--chrome',default=os.environ.get('CHROME_PATH'));p.add_argument('--live',action='store_true');a=p.parse_args()
 chrome=a.chrome or ('C:/Program Files/Google/Chrome/Application/chrome.exe' if os.name=='nt' else None)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=chrome,headless=True)
  page=browser.new_page(accept_downloads=True,viewport={'width':1360,'height':950});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  for route in ('profile','2d','3d','scene','charts','lab'):
   r=page.goto(a.url+'explorer/'+route+'/');assert r.status==200
   page.wait_for_function('window.oneHealth?.profile?.selected_samples > 1000')
   assert page.locator('#visual svg').count()==1
   assert page.locator('#rows tr').count()==50
   if route in ('3d','scene'):page.locator('#orbit-right').click()
  initial=page.evaluate('window.oneHealth.profile.selected_samples')
  for key,value in dict(west='-119.84',south='36.70',east='-119.74',north='36.82').items():page.locator('#'+key).fill(value)
  page.locator('#apply').click();assert page.evaluate('window.oneHealth.profile.selected_samples')<initial
  page.locator('#metric').select_option('temperature_c');assert page.evaluate('window.oneHealth.profile.metric')=='temperature_c'
  current=page.evaluate('window.oneHealth.profile.selected_samples')
  saved=page.evaluate('({bbox:window.oneHealth.profile.bbox,metric:window.oneHealth.profile.metric,scene:window.oneHealth.package.manifest.scene_id})')
  for view in ('2d','scene','charts','lab'):
   page.locator('[data-view="'+view+'"]').click()
   assert page.evaluate('({bbox:window.oneHealth.profile.bbox,metric:window.oneHealth.profile.metric,scene:window.oneHealth.package.manifest.scene_id})')==saved
  page.go_back();assert page.evaluate('window.oneHealth.profile.selected_samples')==current
  page.locator('#west').fill('-118');page.locator('#apply').click();assert 'previous valid profile' in page.locator('#status').inner_text().lower();assert page.evaluate('window.oneHealth.profile.selected_samples')==current
  with page.expect_download() as info:page.locator('#json').click()
  exported=json.loads(Path(info.value.path()).read_text());assert exported['summary']['selected_samples']==current and len(exported['pixels'])==current
  with page.expect_download() as info:page.locator('#csv').click()
  downloaded=list(csv.DictReader(io.StringIO(Path(info.value.path()).read_text())))
  actual=page.evaluate('window.oneHealth.profile.rows')
  assert len(downloaded)==len(actual)==current
  for exported_row,source_row in zip(downloaded,actual):
   assert exported_row.keys()==source_row.keys()
   for key,value in source_row.items():
    if value is None:assert exported_row[key]=='',(key,exported_row[key])
    elif isinstance(value,(int,float)):assert float(exported_row[key])==value,(key,value,exported_row[key])
    else:assert exported_row[key]==value,(key,value,exported_row[key])
  # Failed package import must preserve both current package identity and selected rows.
  identity=page.evaluate('window.oneHealth.package.manifest.scene_id')
  bad={'schema_version':1,'manifest':{},'pixels':[],'tracts':{}}
  page.locator('#package').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(bad).encode()})
  page.wait_for_function('document.querySelector("#status").textContent.includes("Import failed")')
  assert page.evaluate('window.oneHealth.package.manifest.scene_id')==identity
  assert page.evaluate('window.oneHealth.profile.selected_samples')==current
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  if a.live:
   page.locator('#reset').click();page.locator('#live').click()
   page.wait_for_function('window.oneHealth.package.manifest.title === "Live U.S. study-area observations"',timeout=600000)
   assert page.evaluate('window.oneHealth.profile.valid_samples')>100
   assert page.evaluate('window.oneHealth.package.manifest.hashes.pixels.length')==64
   rows=page.evaluate('window.oneHealth.package.pixels')
   for row in rows:
    clear=(int(row['qa_pixel_dn'])&63)==0 and row['qa_radsat_dn']==0
    optical=clear and all(row[k+'_dn']>0 for k in ('blue','green','red','nir08'))
    thermal=clear and row['lwir11_dn']>0
    assert bool(row['valid'])==optical and bool(row['thermal_valid'])==thermal
    for key in ('blue','green','red','nir08'):
     expected=row[key+'_dn']*.0000275-.2 if optical else None
     assert row[key] is None if expected is None else math.isclose(row[key],expected,abs_tol=1e-10)
    expected=row['lwir11_dn']*.00341802+149-273.15 if thermal else None
    assert row['temperature_c'] is None if expected is None else math.isclose(row['temperature_c'],expected,abs_tol=1e-10)
    for key,a,b in [('ndvi','nir08','red'),('ndwi','green','nir08')]:
     expected=(row[a]-row[b])/(row[a]+row[b]) if optical and abs(row[a]+row[b])>1e-12 else None
     assert row[key] is None if expected is None else math.isclose(row[key],expected,abs_tol=1e-10)
   print('Live acquisition and exported canonical evidence hashes passed.',flush=True)
  assert not errors,errors
  browser.close()
 print('Browser routes, real-data controls, bounds errors, transactional import, exports, orbit and mobile layout passed.')
if __name__=='__main__':main()
