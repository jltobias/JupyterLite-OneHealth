# Real Fresno evidence snapshot

All observations and tract geometries are actual public-domain federal inputs. No source observation is simulated, gap-filled or replaced.

- **Landsat:** `LC09_L2SP_042035_20240830_02_T1`, 2024-08-30T18:33:53.353894Z; USGS/NASA Landsat 9 Collection 2 Level-2. [Dataset DOI](https://doi.org/10.5066/P9OGBGM6). Seven exact raw native product-grid crops, 947 rows × 772 columns, EPSG:32611, 30 m grid, are in `native/`. Thermal instrument support is coarser (100 m); a 30 m grid does not create independent 30 m thermal observations.
- **Population:** U.S. Census Bureau, 2020 Census TIGERweb Census Tracts layer 6, POP100. `tracts.geojson` contains the original 166 intersecting tract geometries in EPSG:4326. Their whole-tract total is 764,468 people, **not bbox population**. Reference date: 2020-04-01.
- **Study bounds:** west −119.90°, south 36.65°, east −119.65°, north 36.90°.

`pixels.csv` systematically samples actual native pixels at stride 10 (approximately 300 m). The 6,890 retained sample centres are inside the geographic box. `source_row` and `source_col` index the **bundled crop**, zero-based; the crop's original full-scene offset is in `source-metadata.json`. A live browser package instead records indices relative to its unsigned source COG and includes the full source window and grid origin.

`*_dn` columns preserve the seven original digital numbers and quality values. `valid` marks optical validity; `thermal_valid` marks thermal validity. QA_PIXEL bits 0–5, any QA_RADSAT and relevant zero DNs are rejected. Reflectance is `DN*0.0000275-0.2`; surface Celsius is `DN*0.00341802+149-273.15`. NDVI is `(nir08-red)/(nir08+red)`, NDWI is `(green-nir08)/(green+nir08)`, using scaled reflectance. Zero ratio denominators and masked values remain empty/null. No clipping changes exported measurements.

`west/south/east/north` describe approximate display tiles at the sampling spacing. They **do not enlarge the original observation footprint** or assert homogeneous conditions between samples. Profile means summarize selected sample centres, not every full-resolution pixel or an exact area mean.

The manifest contains source identities, dates, units, formulas, rights evidence, unsigned asset URLs and SHA-256 checksums. `source-metadata.json` retains the exact source crop metadata and complete Census query without response cookies or signed access URLs. `profile-package.json` combines manifest, samples and tracts for explorer import/export. Raw TIFF hashes and all hashed text files are checked by `scripts/check_data.py`; text uses LF so Git checkout does not change their bytes.

Credit USGS EROS/NASA and U.S. Census Bureau. [USGS public-domain cloud-data statement](https://www.usgs.gov/faqs/are-landsat-data-cloud-still-considered-be-within-public-domain), [Census TIGER public-domain statement](https://www.census.gov/newsroom/archives/2014-pr/cb14-208.html). External educational prose, figures and code are not reproduced. No agency endorsement is implied.
