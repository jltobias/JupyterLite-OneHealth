---
title: OneHealth fieldnotes
---
# One place, connected questions

The Fresno starter connects an actual Landsat acquisition with actual 2020 Census tract population. It is a small evidence workspace for asking how people, animals, plants and environmental conditions share a place. Its maps do not estimate illness, personal exposure or intervention outcomes.

Open the [Python Lab](https://jltobias.github.io/JupyterLite-OneHealth/lite/lab/index.html), [study-area profiler](https://jltobias.github.io/JupyterLite-OneHealth/explorer/profile/) or [portal](https://jltobias.github.io/JupyterLite-OneHealth/).

Begin with [the provenance lesson](../content/00_provenance_profile.ipynb). Then work through the shared notebooks, using the [methods](methods.md) to distinguish observation, transformation and assumption. The same notebooks run in the browser Lab and produce the figures in this Book.

## A practical learning path

Use the [CDC/EPA case-study guide](case-studies.md) alongside these lessons to connect real investigations and agency partnerships with your evidence questions.

1. **Locate the evidence.** Identify the study bounds, scene, dates, units and missing values.
2. **Read the measurements.** Decode quality flags, scale digital numbers, and interpret vegetation, water and surface-temperature proxies.
3. **Respect the population boundary.** Keep whole-tract counts separate from estimates inside a bounding box.
4. **Inspect a spatial join.** Compare the support of a pixel, a tract and a person without treating them as interchangeable.
5. **Write an evidence brief.** State the decision, partners, limits and observations needed next.

## The study area

Default bounds are west −119.90°, south 36.65°, east −119.65°, north 36.90° in Fresno, California. The Landsat 9 scene is `LC09_L2SP_042035_20240830_02_T1`, acquired **30 August 2024**. Population is **2020 Census POP100**, referring to usual residence on 1 April 2020. Tracts can extend beyond the study box.

The original splash is a conceptual illustration, clearly separate from analytical maps. All analytical measurements in this project come from the credited federal inputs; no observations or geometries are simulated.

## Work in the browser

The portal links to the map, charts, orbitable views, profile and Python Lab. In the explorer, edit bounds inside the loaded snapshot, select a measurement, and export the selected rows. For another bounded U.S. area, use live acquisition or the reproducible Python acquisition command described in [methods](methods.md). Provider failures remain errors; the site never substitutes generated observations.

JupyterLite initially downloads a Python runtime and packages. Save and download edited notebooks and generated files before clearing browser storage. A desktop notebook run and a browser Python run are separate checks.
