"""Acquire public-domain Landsat/Census evidence; normalize an inspectable snapshot.

No API credentials are required. Signed asset URLs exist in memory only.
Use --from-research tmp/eo-research for the already acquired Fresno native crops.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, shutil, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

BANDS = ('blue', 'green', 'red', 'nir08', 'lwir11', 'qa_pixel', 'qa_radsat')
CENSUS = 'https://tigerweb.geo.census.gov/arcgis/rest/services/Census2020/tigerWMS_Census2020/MapServer/6/query'
STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1'
DEFAULT_BBOX = [-119.90, 36.65, -119.65, 36.90]
RIGHTS = {
 'landsat': 'https://www.usgs.gov/faqs/are-landsat-data-cloud-still-considered-be-within-public-domain',
 'census': 'https://www.census.gov/newsroom/archives/2014-pr/cb14-208.html',
}

def retry_delay(value, attempt):
    if value is None: return 2**(attempt+1)
    try: delay=float(value)
    except ValueError:
        try: delay=(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError) as error:
            raise RuntimeError('Provider returned an invalid Retry-After delay; retry later.') from error
    if not math.isfinite(delay) or delay>30:
        raise RuntimeError('Provider requests a longer retry delay; retry later.')
    return max(1,delay)

def get_json(url, params=None):
    if params: url += '?' + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response: return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429,503) or attempt==2: raise
            time.sleep(retry_delay(error.headers.get('Retry-After'),attempt))

def validate_bbox(bbox):
    w,s,e,n = bbox
    if not all(math.isfinite(v) for v in bbox) or not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise ValueError('Use finite west < east and south < north in geographic degrees.')
    if e-w > .5 or n-s > .5: raise ValueError('Use an area at most 0.5 degrees wide and high.')
    if not (-180 <= w <= -60 and 15 <= s <= 75): raise ValueError('This public-domain population workflow supports U.S. study areas.')

def census_tracts(bbox):
    features, offset = [], 0
    params = dict(where='1=1', geometry=','.join(map(str,bbox)), geometryType='esriGeometryEnvelope', inSR=4326,
                  spatialRel='esriSpatialRelIntersects', outFields='GEOID,NAME,POP100,AREALAND', outSR=4326,
                  returnGeometry='true', f='geojson', orderByFields='GEOID', resultRecordCount=1000)
    while True:
        page = get_json(CENSUS, {**params, 'resultOffset': offset})
        if 'error' in page: raise RuntimeError(f'Census provider error: {page["error"]}')
        batch = page.get('features', [])
        features.extend(batch)
        more = page.get('exceededTransferLimit', page.get('properties',{}).get('exceededTransferLimit',False))
        if not more and len(batch) < 1000: break
        if not batch: raise RuntimeError('Census pagination stopped before all tracts were received.')
        offset += len(batch)
        if offset > 10000: raise RuntimeError('Too many tracts; select a smaller area.')
    if not features: raise RuntimeError('No 2020 U.S. Census tracts intersect this area.')
    unique = {f['properties']['GEOID']: f for f in features}
    return {'type':'FeatureCollection','features':list(unique.values())}, {'url':CENSUS, 'params':params, 'pagination':'ordered GEOID; offsets until complete'}

def acquire(bbox, output, dates):
    import rasterio
    from rasterio.windows import Window, from_bounds
    from rasterio.warp import transform_bounds
    tracts, query = census_tracts(bbox)
    search=dict(collections='landsat-c2-l2',bbox=','.join(map(str,bbox)),datetime=dates,limit=100)
    result = get_json(STAC+'/search',search)
    candidates = covering_candidates(result.get('features',[]),bbox)
    candidates.sort(key=lambda f:(f['properties'].get('eo:cloud_cover',100),f['id']))
    if not candidates: raise RuntimeError('No covering Landsat 8/9 Level-2 surface-temperature scene among the first 100 returned items in this date interval.')
    item = candidates[0]
    epsg = item['properties'].get('proj:epsg') or item['assets']['red'].get('proj:epsg')
    if not epsg: raise RuntimeError('Provider item lacks its projected CRS.')
    bounds = transform_bounds('EPSG:4326',f'EPSG:{epsg}',*bbox,densify_pts=21)
    raw = output/'native'; raw.mkdir(parents=True, exist_ok=True)
    assets = {}
    common = None
    token_cache = {}
    for band in BANDS:
        unsigned = item['assets'][band]['href']
        asset_url=urllib.parse.urlsplit(unsigned)
        token_key=asset_url.hostname.split('.')[0]+'/'+asset_url.path.split('/')[1]
        if token_key not in token_cache:
            token_cache[token_key]=get_json('https://planetarycomputer.microsoft.com/api/sas/v1/token/'+token_key)['token']
        signed=unsigned+'?'+token_cache[token_key]
        # rasterio/GDAL uses range reads; signed URLs are never serialized.
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.TIF'):
            with rasterio.open(signed) as src:
                if common is None:
                    win = from_bounds(*bounds,transform=src.transform)
                    left,top = math.floor(win.col_off),math.floor(win.row_off)
                    right,bottom = math.ceil(win.col_off+win.width),math.ceil(win.row_off+win.height)
                    if (right-left)*(bottom-top)>1000000: raise ValueError('Area exceeds one million native pixels; choose smaller bounds.')
                    if left<0 or top<0 or right>src.width or bottom>src.height: raise ValueError('Selected scene does not cover the full bbox; choose a different interval or smaller area.')
                    common=Window(left,top,right-left,bottom-top)
                data=src.read(1,window=common)
                profile=src.profile.copy(); profile.update(width=data.shape[1],height=data.shape[0],transform=src.window_transform(common),compress='deflate')
                path=raw/f'{band}.tif'
                with rasterio.open(path,'w',**profile) as dst: dst.write(data,1)
                assets[band]={'file':path.name,'source_asset':unsigned,'sha256':sha(path)}
    (output/'landsat-item.json').write_text(json.dumps(item,indent=2))
    meta={'item_id':item['id'],'acquisition_datetime':item['properties']['datetime'],'requested_bbox_wgs84':bbox,
          'source_crs':f'EPSG:{epsg}','assets':assets,'retrieved_at':datetime.now(timezone.utc).isoformat(),
          'stac_query':{'url':STAC+'/search','params':search,'selection':'Lowest scene cloud cover among up to 100 returned L2SP items with all required bands and a scene bbox covering the complete study area.'}}
    return raw, meta, tracts, query

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def covering_candidates(features,bbox):
    def covers(item):
        bounds=item.get('bbox',[])
        return len(bounds)==4 and bounds[0]<=bbox[0] and bounds[1]<=bbox[1] and bounds[2]>=bbox[2] and bounds[3]>=bbox[3]
    return [f for f in features if f['id'].startswith(('LC08_','LC09_')) and '_L2SP_' in f['id']
            and all(k in f['assets'] for k in BANDS) and covers(f)]

def normalize(raw, meta, tracts, query, output, research=False):
    import numpy as np
    import rasterio
    from pyproj import Transformer
    output.mkdir(parents=True,exist_ok=True)
    native = output/'native'; native.mkdir(exist_ok=True)
    arrays={}
    source_files={}
    for band in BANDS:
        source=raw/(meta['assets'][band]['file'])
        target=native/f'{band}.tif'
        if source.resolve()!=target.resolve(): shutil.copyfile(source,target)
        with rasterio.open(target) as ds:
            arrays[band]=ds.read(1)
            transform=ds.transform; crs=ds.crs; height,width=ds.height,ds.width
        source_files[band]={'path':f'native/{band}.tif','sha256':sha(target),'unsigned_asset':meta['assets'][band]['source_asset']}
    transformer=Transformer.from_crs(crs,'EPSG:4326',always_xy=True)
    bbox=meta['requested_bbox_wgs84']
    # Systematic nearest-native-pixel sampling, not averaged or invented pixels.
    stride=max(1,math.ceil(max(height,width)/96))
    rows=[]
    for r in range(min(stride//2,height//2),height,stride):
        for c in range(min(stride//2,width//2),width,stride):
            x,y=transform*(c+.5,r+.5); lon,lat=transformer.transform(x,y)
            if not (bbox[0]<=lon<=bbox[2] and bbox[1]<=lat<=bbox[3]): continue
            dn={b:int(a[r,c]) for b,a in arrays.items()}
            clear=(dn['qa_pixel']&63)==0 and dn['qa_radsat']==0
            optical=clear and all(dn[b]>0 for b in ('blue','green','red','nir08'))
            thermal=clear and dn['lwir11']>0
            vals={b:dn[b]*.0000275-.2 if optical else None for b in ('blue','green','red','nir08')}
            def ratio(a,b):
                return (a-b)/(a+b) if a is not None and b is not None and abs(a+b)>1e-12 else None
            w,s=transformer.transform(*(transform*(max(0,c-stride/2),min(height,r+stride/2))))
            e,n=transformer.transform(*(transform*(min(width,c+stride/2),max(0,r-stride/2))))
            row={'id':f'r{r}c{c}','source_row':r,'source_col':c,'lon':lon,'lat':lat,'west':w,'south':s,'east':e,'north':n,
                 'valid':int(optical),'thermal_valid':int(thermal),**vals,
                 'ndvi':ratio(vals['nir08'],vals['red']),'ndwi':ratio(vals['green'],vals['nir08']),
                 'temperature_c':dn['lwir11']*.00341802+149-273.15 if thermal else None,
                 **{b+'_dn':v for b,v in dn.items()}}
            rows.append({k:round(v,7) if isinstance(v,float) else v for k,v in row.items()})
    if not rows: raise ValueError('No sampled native-pixel centres fall inside these bounds; enlarge the study area.')
    with (output/'pixels.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    (output/'tracts.geojson').write_text(json.dumps(tracts,separators=(',',':')),encoding='utf-8',newline='\n')
    source_meta={'landsat':meta,'census':query}
    (output/'source-metadata.json').write_text(json.dumps(source_meta,indent=2),encoding='utf-8',newline='\n')
    clear=((arrays['qa_pixel']&63)==0)&(arrays['qa_radsat']==0)
    manifest={'schema_version':1,'title':'Fresno, California · real Landsat / Census snapshot' if research else 'User-selected U.S. study area',
      'bbox':bbox,'crs':'EPSG:4326','source_crs':str(crs),'scene_id':meta['item_id'],'satellite_datetime':meta['acquisition_datetime'],
      'population_date':'2020-04-01','retrieved_at':meta['retrieved_at'],'source_grid_m':30,'thermal_native_resolution_m':100,
      'sample_stride_native_pixels':stride,'sample_spacing_m':stride*30,'sample_count':len(rows),
      'sampling':'Systematic nearest native-pixel samples. Display tiles show sampling spacing, not the 30 m observation footprint. Means describe selected samples, not full-resolution area means.',
      'qa':'Reject QA_PIXEL bits 0–5 (fill/dilated cloud/cirrus/cloud/shadow/snow), any QA_RADSAT, optical zero DN, thermal zero DN. No gap filling.',
      'native_crop_clear_fraction':float(clear.mean()),'native_crop_shape':[height,width],
      'formulas':{'reflectance':'DN * 0.0000275 - 0.2','temperature_c':'DN * 0.00341802 + 149 - 273.15',
                  'ndvi':'(nir08 - red)/(nir08 + red), after scaling; zero denominator -> null',
                  'ndwi':'(green - nir08)/(green + nir08), after scaling; zero denominator -> null'},
      'units':{'red':'unitless surface reflectance','green':'unitless surface reflectance','blue':'unitless surface reflectance','nir08':'unitless surface reflectance','ndvi':'unitless vegetation proxy','ndwi':'unitless water proxy','temperature_c':'degrees Celsius; surface, not air','POP100':'people; whole 2020 Census tract'},
      'population_method':'Full-tract POP100 counts; bbox estimate uses spherical polygon-area fraction and assumes uniform within-tract population. Neither is a direct bbox headcount.',
      'rights':RIGHTS,'credits':['USGS EROS / NASA Landsat 8–9 Collection 2 Level-2. DOI:10.5066/P9OGBGM6','U.S. Census Bureau, 2020 Census TIGERweb tracts and POP100'],
      'source_files':source_files,'census_query':query,'files':{}}
    if meta.get('stac_query'): manifest['stac_query']=meta['stac_query']
    for name in ('pixels.csv','tracts.geojson','source-metadata.json'):
        manifest['files'][name]={'sha256':sha(output/name),'bytes':(output/name).stat().st_size}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8',newline='\n')
    package={'schema_version':1,'manifest':manifest,'pixels':rows,'tracts':tracts}
    (output/'profile-package.json').write_text(json.dumps(package,separators=(',',':')),encoding='utf-8',newline='\n')
    print(f'Wrote {len(rows)} real satellite samples and {len(tracts["features"])} Census tracts to {output}')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bbox',type=float,nargs=4,default=DEFAULT_BBOX)
    p.add_argument('--output',type=Path,default=Path('content/data'));p.add_argument('--from-research',type=Path)
    p.add_argument('--datetime',default='2024-06-01T00:00:00Z/2025-10-01T00:00:00Z');a=p.parse_args();validate_bbox(a.bbox)
    a.output.mkdir(parents=True,exist_ok=True)
    if a.from_research:
        meta=json.loads((a.from_research/'landsat-native-crop-manifest.json').read_text())
        tracts=json.loads((a.from_research/'census-2020-tracts-fresno.geojson').read_text())
        query=json.loads((a.from_research/'census-query.json').read_text())
        # Drop provider response headers/cookies from reproducibility metadata.
        query={k:v for k,v in query.items() if k in ('url','params','resolved_url','retrieved_at')}
        normalize(a.from_research,meta,tracts,query,a.output,True)
    else:
        raw,meta,tracts,query=acquire(a.bbox,a.output,a.datetime)
        normalize(raw,meta,tracts,query,a.output)
if __name__=='__main__': main()
