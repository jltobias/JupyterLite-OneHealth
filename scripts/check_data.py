"""Check provenance bytes, masks/calibration and measured-data invariants."""
import csv, hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'content/data'
def main():
 m=json.loads((DATA/'manifest.json').read_text())
 for name,info in m['files'].items(): assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==info['sha256'],name
 for info in m['source_files'].values(): assert hashlib.sha256((DATA/info['path']).read_bytes()).hexdigest()==info['sha256'],info['path']
 rows=list(csv.DictReader((DATA/'pixels.csv').open(newline='')))
 assert len(rows)==m['sample_count'] and len(rows)>1000
 for r in rows:
    d={k:float(v) if v else None for k,v in r.items() if k!='id'}
    clear=(int(d['qa_pixel_dn'])&63)==0 and d['qa_radsat_dn']==0
    optical=clear and all(d[k+'_dn']>0 for k in ('blue','green','red','nir08'))
    assert bool(d['valid'])==optical
    for k in ('blue','green','red','nir08'):
      assert (d[k] is not None)==optical
      if optical: assert abs(d[k]-(d[k+'_dn']*.0000275-.2))<1e-6
    thermal=clear and d['lwir11_dn']>0
    assert (d['temperature_c'] is not None)==thermal
    if thermal: assert abs(d['temperature_c']-(d['lwir11_dn']*.00341802+149-273.15))<1e-6
    if optical:
      for key,a,b in [('ndvi','nir08','red'),('ndwi','green','nir08')]:
        if abs(d[a]+d[b])>1e-12: assert abs(d[key]-(d[a]-d[b])/(d[a]+d[b]))<1e-5
    assert m['bbox'][0]<=d['lon']<=m['bbox'][2] and m['bbox'][1]<=d['lat']<=m['bbox'][3]
 t=json.loads((DATA/'tracts.geojson').read_text());assert sum(int(f['properties']['POP100']) for f in t['features'])==764468
 assert len(t['features'])==166
 # The explorer consumes this package rather than the separately checked files.
 package=json.loads((DATA/'profile-package.json').read_text())
 assert package['manifest']==m,'Explorer manifest differs from the audited manifest'
 assert package['tracts']==t,'Explorer Census features differ from audited GeoJSON'
 typed=[{k:(v if k=='id' else float(v) if v else None) for k,v in r.items()} for r in rows]
 assert package['pixels']==typed,'Explorer measurements differ from audited CSV'
 # The snapshot must not contain expiring access tokens.
 for f in DATA.glob('*.json'): assert 'sig=' not in f.read_text(),f
 print(f'Checked hashes, actual DN scales/QA and Census counts: {len(rows)} samples / 166 tracts.')
if __name__=='__main__':main()
