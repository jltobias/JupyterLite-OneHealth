---
title: Data and methods
---
# Follow the evidence chain

## Actual source data

**Satellite:** USGS Landsat 9 Collection 2 Level-2 scene `LC09_L2SP_042035_20240830_02_T1`, 30 August 2024 at 18:33:53 UTC, WRS path 042 / row 035. Blue, green, red, near-infrared, surface-temperature DN, QA_PIXEL and QA_RADSAT are native 30 m product-grid crops in **EPSG:32611**. Public Planetary Computer STAC/COG services distribute the USGS assets. Asset identities, raw crop SHA-256 values, source metadata and the acquisition query are bundled in `data/manifest.json` and `data/source-metadata.json`.

**Population:** U.S. Census Bureau `Census2020/tigerWMS_Census2020/MapServer/6`, queried for intersecting tracts and `POP100` with geographic geometry in **EPSG:4326**. All returned pages must be complete. The 166 starter tracts contain **764,468 people in their whole boundaries**; this is explicitly **not** the population inside the study box. The reference date is 1 April 2020, not the satellite acquisition date.

All source data are federal public-domain inputs. External copyrighted teaching materials and uncertain-rights datasets are excluded. Dataset credits, rights evidence, exact source identities and hashes travel with the snapshot. See [credits](credits.md).

## Quality and calibration

We reject QA_PIXEL bits 0–5: fill, dilated cloud, cirrus, cloud, cloud shadow and snow. We conservatively reject every nonzero QA_RADSAT flag. Optical measurements additionally require nonzero blue, green, red and NIR DN. Temperature additionally requires nonzero thermal DN. No masked or missing measurement is filled or interpolated.

For valid observations:

```text
surface reflectance = DN × 0.0000275 − 0.2
surface temperature (°C) = DN × 0.00341802 + 149 − 273.15
NDVI = (NIR − red) / (NIR + red)
NDWI in this project = (green − NIR) / (green + NIR)
```

Ratios use scaled reflectance. A zero denominator yields null. Numeric exports retain calculated values rather than clipping them to the map color ramp. Reflectance and normalized differences are unitless. Surface temperature is **not air temperature**, a daily maximum, indoor temperature or a personal heat dose.

The 30 m thermal product grid does not imply 30 m independent instrument measurements: Landsat 9 thermal observations have coarser native 100 m support. The producer resamples them onto the product grid. See [USGS surface temperature documentation](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature), [scaling](https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products) and [quality flags](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands).

## Sampling and selection

To keep browser packages compact, we systematically select actual nearest-native-pixel samples from the source crop (starter: every 10 native pixels, approximately 300 m spacing). Samples retain DN, QA and source row/column. **Display tiles show sampling spacing, not observation footprint.** They do not claim a homogeneous area or create new measurements.

The profile selects sample centres inside the requested longitude/latitude box. Its mean is an unweighted mean of those valid samples, **not a full-resolution area mean**. Validity is the fraction of selected sampled observations valid for the chosen measurement, **not the percentage of the entire landscape known with certainty**. Small boxes can contain no sample centres; the explorer then asks for a larger area or finer acquisition instead of inventing a value.

Maps use a local longitude scale corrected by cosine of mid-latitude, preserving local geographic aspect. The scene plane is geographic. Its RGB colors use a declared fixed linear reflectance contrast; they are not a downloaded photograph. 3D heights encode data values and never represent invented elevation.

## Population overlap

For the current box, the explorer reports two quantities separately:

1. **Population of intersecting whole tracts:** sum of POP100 for each tract with positive polygon overlap.
2. **Uniform-area bbox estimate:** sum of each tract's POP100 multiplied by its clipped polygon-area fraction.

Polygon rings are clipped to the geographic rectangle. A spherical area calculation weights longitude changes by latitude; holes subtract from their exterior. The estimate assumes population is distributed uniformly over each whole tract, including water and nonresidential land. It is a disclosed approximation, not an observed bbox count. No health rate or personal exposure is calculated from it.

## Another bounded U.S. area

The explorer's **Create profile from live sources** requests 2020 Census geometry/counts and a Landsat 8/9 Level-2 surface-temperature scene. It searches June 2024–September 2025 and chooses a low-cloud candidate covering the box; the chosen source ID and acquisition date are always shown. A scene-wide cloud percentage does not establish local pixel quality. COG bands are read through bounded HTTP range requests, transformed from the scene's UTM grid and masked. Signed access URLs are transient and never exported.

Live services can be unavailable, rate-limited or unsuitable for an area. Browser acquisition bounds memory by rejecting more than one million source pixels. Select a smaller box if necessary. No U.S. Census coverage, missing temperature assets, unsupported projections, incomplete pagination and network failures are explicit errors. The previous valid profile is retained and labeled until a new package completes.

For reproducible local acquisition:

```bash
python scripts/acquire_data.py --bbox -119.90 36.65 -119.65 36.90 --output my-profile
```

Install `requirements-acquire.txt` in a local Python environment first. The optional `--datetime START/END` changes the scene-search interval. Import `my-profile/profile-package.json` in the explorer. Inspect rights, dates, quality and source metadata before making comparisons. Packages can also be exported for later offline inspection; first-time browser Python and live acquisition still need network access.
