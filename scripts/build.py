"""Execute lessons, build Book/Lite and assemble one prefixed Pages artifact."""
from __future__ import annotations
import argparse, hashlib, html, importlib.metadata, json, os, shutil, subprocess, sys, urllib.request, zipfile, io
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
THEME_COMMIT='23f2df5493e23dfb1d9433c8aa64c87beb4232a3'
EXCLUDED_BOOK_PAYLOADS={
    'build/_shared/plotly-PQJCFEUX.js': '0880d21844a366d8906d5252ee70c205b209cbfad1bce3c18a392e7879f488d8',
}

def exclude_optional_payloads(book):
    """Omit unused optional code whose nested permissions are unresolved."""
    excluded=[]
    for relative, expected in EXCLUDED_BOOK_PAYLOADS.items():
        target=(book/relative).resolve()
        assert book.resolve() in target.parents
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual==expected, f'Pinned optional payload changed: {relative}'
        excluded.append({'path':'book/'+relative,'sha256':actual,'distributed':False,
          'reason':'Unused optional Plotly payload omitted because a legacy parser dependency has unresolved locked-version permission evidence. All project figures use Matplotlib or original SVG.'})
        target.unlink()
    return excluded
def prepare_theme():
    target=ROOT/'_build/pinned-book-theme'
    marker=target/'.onehealth-commit'
    if marker.exists() and marker.read_text()==THEME_COMMIT:return
    url=f'https://github.com/myst-templates/book-theme/archive/{THEME_COMMIT}.zip'
    print('Fetching pinned MIT Book theme '+THEME_COMMIT,flush=True)
    with urllib.request.urlopen(url,timeout=120) as response:archive=zipfile.ZipFile(io.BytesIO(response.read()))
    target.mkdir(parents=True,exist_ok=True)
    for info in archive.infolist():
        parts=Path(info.filename).parts[1:]
        if not parts or info.is_dir():continue
        out=target.joinpath(*parts).resolve();assert target.resolve() in out.parents
        out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(archive.read(info))
    marker.write_text(THEME_COMMIT)
def run(args,env=None):
    print('Running: '+' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=ROOT,env=env,check=True)

def configure_lite(lite):
    """Apply project branding after Lite's cached copy/patch tasks finish."""
    source=json.loads((ROOT/'jupyter-lite.json').read_text())['jupyter-config-data']
    for relative in ('jupyter-lite.json','lab/jupyter-lite.json'):
        path=lite/relative
        config=json.loads(path.read_text())
        data=config.setdefault('jupyter-config-data',{})
        for key,value in source.items():
            data[key]=list(dict.fromkeys([*data.get(key,[]),*value])) if key=='disabledExtensions' else value
        path.write_text(json.dumps(config,indent=2),encoding='utf-8')
def licenses(site, excluded):
    target=site/'notices';shutil.copytree(ROOT/'notices',target,dirs_exist_ok=True)
    inventory=[]
    for dist in importlib.metadata.distributions():
        name=dist.metadata.get('Name','unknown');version=dist.version;found=[]
        for file in dist.files or []:
            parts=[p.lower() for p in file.parts]
            if any('dist-info' in p for p in parts) and any(p.startswith(('license','copying','notice')) for p in parts):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    out=target/'python'/f'{name}-{version}'/Path(*file.parts[1:]);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out);found.append(str(out.relative_to(target)))
        inventory.append({'name':name,'version':version,'license_files':found,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License')})
    (target/'python-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    (target/'excluded-components.json').write_text(json.dumps(excluded,indent=2),encoding='utf-8')
    # Preserve license/notices emitted by Book/theme and Lite distributions.
    bundled=[]
    for base in (ROOT/'_build',site/'lite'):
        if not base.exists():continue
        for source in base.rglob('*'):
            if source.is_file() and any(t in source.name.lower() for t in ('license','notice','copying')):
                if target in source.parents:continue
                rel=source.relative_to(base);out=target/'built-components'/base.name/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out);bundled.append(str(out.relative_to(target)))
    entries=sorted(str(p.relative_to(target)).replace('\\','/') for p in target.rglob('*') if p.is_file())
    body=''.join(f'<li><a href="{html.escape(p)}">{html.escape(p)}</a></li>' for p in entries)
    (target/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Software notices · OneHealth</title><h1>Software licenses and notices</h1><p>Open-source infrastructure retains its own terms. No agency endorsement.</p><ul>'+body+'</ul></html>',encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',default='/JupyterLite-OneHealth');p.add_argument('--skip-execution',action='store_true',help='Use previously executed notebook outputs for an iteration.');a=p.parse_args()
    prefix='/'+a.base_url.strip('/') if a.base_url.strip('/') else ''
    env=os.environ.copy();env['PYTHONUTF8']='1';env['BASE_URL']=prefix+'/book';env['MPLBACKEND']='Agg'
    env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env.get('PATH','')
    run([sys.executable,'scripts/check_data.py'],env)
    if not a.skip_execution:run([sys.executable,'scripts/check_notebooks.py','--execute','--write'],env)
    prepare_theme()
    # This only removes the checked, fixed artifact path inside this repository.
    site=(ROOT/'_site').resolve();assert site.parent==ROOT.resolve()
    if site.exists():shutil.rmtree(site)
    site.mkdir()
    run([sys.executable,'-m','jupyter_book','build','--html','--strict','--ci'],env)
    shutil.copytree(ROOT/'_build/html',site/'book')
    excluded=exclude_optional_payloads(site/'book')
    run([sys.executable,'-m','jupyter','lite','build','--force','--contents','content','--output-dir',str(site/'lite'),'--no-sourcemaps','--no-unused-shared-packages'],env)
    configure_lite(site/'lite')
    for name in ('index.html','styles.css','explorer.js','model.mjs','live.mjs'):shutil.copyfile(ROOT/'web'/name,site/name)
    shutil.copytree(ROOT/'web/vendor',site/'vendor')
    for route in ('profile','2d','3d','scene','charts','lab'):
        target=site/'explorer'/route;target.mkdir(parents=True);shutil.copyfile(ROOT/'web/explorer.html',target/'index.html')
    shutil.copytree(ROOT/'assets',site/'assets');shutil.copytree(ROOT/'content/data',site/'data')
    notebooks=site/'notebooks';notebooks.mkdir()
    for source in (ROOT/'content').glob('*.ipynb'):shutil.copyfile(source,notebooks/source.name)
    licenses(site, excluded)
    (site/'.nojekyll').touch()
    (site/'build-info.json').write_text(json.dumps({'base_url':prefix,'book_base_url':prefix+'/book','notebooks':11,'data':'real federal public-domain observations'},indent=2))
    run([sys.executable,'scripts/check_site.py','--base-url',prefix],env)
    print(f'Built {site}. Public deployment has not been verified by this command.')
if __name__=='__main__':main()
