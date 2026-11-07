"""Check real artifact routes and portal/explorer internal references under a prefix."""
import argparse,json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote

ROOT=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in ('href','src') and v:self.links.append(v)
def main():
 p=argparse.ArgumentParser();p.add_argument('--base-url',default='/JupyterLite-OneHealth');a=p.parse_args();site=ROOT/'_site'
 expected=['index.html','book/index.html','book/methods/index.html','book/agency-perspectives/index.html','book/case-studies/index.html','book/credits/index.html','lite/lab/index.html','data/manifest.json','data/profile-package.json','notices/index.html','vendor/geotiff.js','vendor/proj4.js']+[f'explorer/{r}/index.html' for r in ('profile','2d','3d','scene','charts','lab')]
 for rel in expected:assert (site/rel).is_file(),f'Missing route: {rel}'
 assert not (site/'book/build/_shared/plotly-PQJCFEUX.js').exists(),'Excluded optional payload must not be published'
 for f in [site/'index.html',*list((site/'explorer').rglob('*.html'))]:
  parser=Links();parser.feed(f.read_text(encoding='utf-8'))
  for link in parser.links:
   u=urlsplit(link)
   if u.scheme or u.netloc or not u.path:continue
   path=unquote(u.path)
   if path.startswith('/'):
    assert path.startswith(a.base_url+'/'),f'Prefix missing: {link}'
    target=site/path[len(a.base_url)+1:]
   else:target=f.parent/path
   if target.is_dir():target=target/'index.html'
   assert target.is_file(),f'{f.relative_to(site)} -> missing {link}'
 m=json.loads((site/'data/manifest.json').read_text());assert m['scene_id']=='LC09_L2SP_042035_20240830_02_T1'
 assert len(list((site/'notebooks').glob('*.ipynb')))==11
 assert len(list((site/'notices/vendor').rglob('*')))>15
 for rel in ('jupyter-lite.json','lab/jupyter-lite.json'):
  config=json.loads((site/'lite'/rel).read_text())['jupyter-config-data']
  assert config['appName']=='OneHealth Python Lab'
  assert '@jupyterlab/apputils-extension:announcements' in config['disabledExtensions']
 print(f'Checked {len(expected)} required artifact routes and portal/explorer references under {a.base_url or "/"}.')
if __name__=='__main__':main()
