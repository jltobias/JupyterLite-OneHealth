"""Author the original project notebooks from these maintained lesson sources.

This authors teaching text and code only; observations are acquired separately.
"""
from pathlib import Path
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
SETUP='''import sys, csv, json, math, statistics
from pathlib import Path
if sys.platform == "emscripten":
    import piplite
    await piplite.install("matplotlib")
import matplotlib.pyplot as plt
get_ipython().run_line_magic("matplotlib", "inline")
manifest = json.loads(Path("data/manifest.json").read_text())
with Path("data/pixels.csv").open() as f:
    rows = list(csv.DictReader(f))
text_fields = {"id"}
data = [{k: (v if k in text_fields else float(v) if v else None)
         for k, v in row.items()} for row in rows]
tracts = json.loads(Path("data/tracts.geojson").read_text())["features"]
def values(key, source=data):
    return [r[key] for r in source if r[key] is not None and math.isfinite(r[key])]
def avg(key, source=data):
    a = values(key, source)
    return statistics.mean(a) if a else None
plt.rcParams.update({"figure.figsize": (8, 4), "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10})
print(manifest["scene_id"], manifest["satellite_datetime"])
print("Real satellite samples:", len(data), "| population reference:", manifest["population_date"])
'''
LESSONS=[
('00_provenance_profile','Start with provenance and a study-area profile',
 'Trace an observation to its source, distinguish spatial support, and make a reproducible study-area summary.',
 '''A profile begins with a bounded question rather than a score. This real Fresno snapshot joins USGS Landsat observations from **30 August 2024** to **2020 Census** tract counts. The two dates do not match. Our satellite table is a systematic sample of actual native product pixels, not a census of every pixel. Display tiles mark sampling spacing and do not enlarge the physical observation footprint.

The manifest records source identifiers, transformations, units and provenance. SHA-256 file verification is performed by the repository data check. Browser filesystems may reserialize JSON, so this lesson checks scientific values rather than raw JSON bytes.''',
 '''assert manifest["scene_id"] == "LC09_L2SP_042035_20240830_02_T1"
assert manifest["source_crs"] == "EPSG:32611"
assert all(-180 <= r["lon"] <= 180 and -90 <= r["lat"] <= 90 for r in data)
print("Bounds [west, south, east, north]:", manifest["bbox"])
print("Sample spacing (m):", manifest["sample_spacing_m"])
print("Mean sampled NDVI:", round(avg("ndvi"), 4))
print("Mean sampled surface temperature (°C):", round(avg("temperature_c"), 2))''',
 '''plt.scatter(values("lon"), values("lat"), c=[r["ndvi"] for r in data], s=5, cmap="YlGn", vmin=-1, vmax=1)
plt.colorbar(label="NDVI (unitless)")
plt.gca().set_aspect(1 / math.cos(math.radians(36.775)))
plt.xlabel("Longitude (degrees)"); plt.ylabel("Latitude (degrees)")
plt.title("Actual Fresno Landsat samples · 2024-08-30")
plt.tight_layout(); plt.show()''',
 'Change the question from vegetation to human heat exposure. List three additional observations needed before this satellite map can answer it. Explain why the 2020 population count cannot resolve the time mismatch.',
 ['usgs','census']),
('01_agency_questions','Five perspectives, one evidence inventory',
 'Translate agency readings into answerable questions and identify evidence that this package does not contain.',
 '''CDC links human, animal and environmental work; WHO emphasizes coordinated action across sectors. NOAA helps frame aquatic conditions and coastal connections. USGS brings environmental measurement and pathways; NASA supports the interpretation of Earth observations. These are complementary prompts, not five interchangeable sources of health outcomes.

This package includes surface reflectance, a derived surface temperature and population. It includes no diagnoses, animal surveillance, water chemistry, personal exposure, mobility or health-service records. The NASA presentation supplied during planning is **excluded** from all lesson material.''',
 '''questions = {
    "CDC": ("Could an exposure pathway be investigated?", "diagnoses, contact and animal surveillance"),
    "WHO": ("Who needs a voice in a shared decision?", "community priorities and service access"),
    "NOAA": ("What would establish a water-quality concern?", "in-situ chemistry and ecological observations"),
    "USGS": ("What conditions can we locate?", "field validation and repeated observations"),
    "NASA": ("Does this sensor fit the question?", "temporal coverage and measurement uncertainty")}
for agency, (question, missing) in questions.items():
    print(f"{agency}: {question} Missing: {missing}.")
assert len(questions) == 5''',
 '''available = [len(values(k)) / len(data) * 100 for k in ("red", "ndvi", "ndwi", "temperature_c")]
plt.barh(["Red reflectance", "NDVI", "NDWI", "Surface temperature"], available, color="#176c59")
plt.xlim(0, 100); plt.xlabel("Valid sampled observations (%)")
plt.title("Available environmental evidence · not completeness of One Health evidence")
plt.tight_layout(); plt.show()''',
 'Choose one agency question and write an observation plan with a population, place, time, measurement unit and missing partner. A high valid-pixel percentage does not mean the question is answered.',
 ['cdc','who','noaa','usgs','nasa']),
('02_population','Population has a date and a boundary',
 'Distinguish full-tract counts from a study-area estimate and examine a population distribution without assigning individuals to pixels.',
 '''POP100 is the 2020 Census total population for the **whole tract**. A tract that touches our box may extend far beyond it. Adding all intersecting tracts therefore does not count people within the box. The portal separately offers a polygon-area estimate with a strong assumption: people are distributed uniformly within each tract, including nonresidential land. This assumption can be badly wrong.

Population in 2020 is not a measured population at the Landsat overpass in 2024. Counts do not reveal vulnerability, daily movement or who was exposed.''',
 '''counts = [int(f["properties"]["POP100"]) for f in tracts]
assert len(counts) == 166 and sum(counts) == 764468
print("People in the 166 WHOLE intersecting tracts:", sum(counts))
print("This is NOT bbox population.")
print("Median whole-tract population:", statistics.median(counts))''',
 '''plt.hist(counts, bins=20, color="#176c59", edgecolor="white")
plt.xlabel("People per whole 2020 Census tract"); plt.ylabel("Number of intersecting tracts")
plt.title("Full-tract population distribution · Fresno study-area intersections")
plt.tight_layout(); plt.show()''',
 'Compare an agricultural tract and a dense residential tract in the explorer. Explain how area weighting could misallocate people. Which public-domain source might improve the spatial allocation, and what rights and vintage checks would be necessary?',
 ['census']),
('03_qa_scaling','Mask first, scale second',
 'Decode quality flags and reproduce reflectance and temperature scaling from actual digital numbers.',
 '''Landsat digital numbers are encoded measurements. A zero fill value must not become a plausible temperature after scaling. We reject QA_PIXEL bits 0–5: fill, dilated cloud, cirrus, cloud, cloud shadow and snow; any nonzero QA_RADSAT is conservatively rejected. Optical bands additionally require nonzero DN, and temperature requires nonzero thermal DN. Missing values remain null.

Surface reflectance is **DN × 0.0000275 − 0.2**. Temperature in Celsius is **DN × 0.00341802 + 149 − 273.15**. The reflectance offset matters when computing normalized differences; it does not cancel in their denominator.''',
 '''for r in data:
    clear = (int(r["qa_pixel_dn"]) & 63) == 0 and r["qa_radsat_dn"] == 0
    optical = clear and all(r[k + "_dn"] > 0 for k in ("blue", "green", "red", "nir08"))
    assert bool(r["valid"]) == optical
    if optical:
        assert abs(r["red"] - (r["red_dn"] * .0000275 - .2)) < 1e-6
    if r["temperature_c"] is not None:
        assert abs(r["temperature_c"] - (r["lwir11_dn"] * .00341802 + 149 - 273.15)) < 1e-6
print("QA/scaling checks passed for", len(data), "actual sampled pixels.")''',
 '''plt.scatter(values("red_dn"), values("red"), s=4, alpha=.25, color="#176c59")
plt.xlabel("Red-band digital number (DN)"); plt.ylabel("Scaled surface reflectance (unitless)")
plt.title("Actual samples follow the declared scale and offset")
plt.tight_layout(); plt.show()''',
 'Calculate the temperature that zero DN would produce if fill were accidentally scaled. Explain why an arithmetic result alone cannot establish that a measurement is valid. Inspect which QA flags your selected scene actually contains.',
 ['scale','qa']),
('04_vegetation_water','Vegetation and water are proxies',
 'Calculate NDVI and a green–NIR NDWI after scaling, and separate spectral patterns from ecological or health outcomes.',
 '''NDVI = (NIR − red)/(NIR + red) describes a spectral contrast often used to study vegetation. Here NDWI = (green − NIR)/(green + NIR); this definition must be stated because other indices also use the name NDWI. Neither ratio measures pathogen concentration, water safety, crop yield or animal health.

We retain a null when a ratio denominator is zero. Very small or negative reflectance can produce ratios outside familiar bounds; the arithmetic and masks should be inspected rather than silently clipping exported values.''',
 '''for r in data:
    if r["ndvi"] is not None:
        calculated = (r["nir08"] - r["red"]) / (r["nir08"] + r["red"])
        assert abs(calculated - r["ndvi"]) < 1e-5
print("Median NDVI:", round(statistics.median(values("ndvi")), 4))
print("Median green–NIR NDWI:", round(statistics.median(values("ndwi")), 4))''',
 '''plt.hist(values("ndvi"), bins=30, alpha=.7, label="NDVI", color="#176c59")
plt.hist(values("ndwi"), bins=30, alpha=.6, label="Green–NIR NDWI", color="#c89943")
plt.xlabel("Normalized difference (unitless)"); plt.ylabel("Sample count")
plt.title("Real spectral proxies · Fresno 2024-08-30"); plt.legend()
plt.tight_layout(); plt.show()''',
 'Select high and low NDVI samples and inspect their positions. Propose two land-cover explanations and one field observation that could distinguish them. Do not assign a disease or crop condition from the index alone.',
 ['ndvi','noaa']),
('05_surface_heat','A warm surface is not an air thermometer',
 'Describe a measured surface-temperature distribution and distinguish its support from human heat exposure.',
 '''The Landsat surface-temperature product estimates the emitting surface at the acquisition time. It is not the temperature of air at two metres, an indoor environment or a person. Landsat 9 thermal measurements have coarser native resolution (100 m) than the 30 m product grid. Resampling does not create 30 m independent thermal observations.

The table is systematically sampled again for this small browser package. A sample percentile describes this acquisition and this sampling scheme, not a daily maximum or a heat-health threshold.''',
 '''temperatures = sorted(values("temperature_c"))
def percentile(a, q):
    x = (len(a)-1)*q; i = int(x)
    return a[i] + (a[min(i+1, len(a)-1)]-a[i])*(x-i)
for q in (.05, .5, .95):
    print(f"Sample surface-temperature percentile {q:.0%}: {percentile(temperatures,q):.2f} °C")
assert all(-50 < t < 100 for t in temperatures)''',
 '''plt.hist(temperatures, bins=30, color="#be7544", edgecolor="white")
plt.xlabel("Land surface temperature (°C)"); plt.ylabel("Sample count")
plt.title("One acquisition of actual surface conditions · 2024-08-30")
plt.tight_layout(); plt.show()''',
 'Write a short warning label for a map that could be mistaken for personal heat exposure. Then design a comparison with air-temperature stations, naming time alignment and station siting as requirements.',
 ['temperature','nasa']),
('06_spatial_scale','Scale changes the evidence you see',
 'Test systematic sampling sensitivity and distinguish data spacing, observation support and statistical independence.',
 '''A source grid, an instrument footprint and a display tile are different objects. The source Landsat product is gridded at 30 m; this package selects native pixels at a larger systematic spacing. Adjacent thermal product pixels also share a coarser original measurement support.

Below, retaining every second or fourth table row is an inspectable sensitivity exercise on the existing sample. It is not a new full-resolution resampling procedure. Similar means do not prove absence of local features, bias or spatial dependence.''',
 '''steps = [1, 2, 4, 8]
summaries = [(step, len(data[::step]), avg("ndvi", data[::step]), avg("temperature_c", data[::step])) for step in steps]
for step,n,ndvi,temp in summaries:
    print(f"Every {step}th row: n={n}; NDVI={ndvi:.4f}; surface={temp:.2f} °C")''',
 '''fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
ax[0].plot(steps, [s[2] for s in summaries], "o-", color="#176c59")
ax[0].set(xlabel="Table-row sampling interval", ylabel="Mean NDVI (unitless)")
ax[1].plot(steps, [s[3] for s in summaries], "o-", color="#be7544")
ax[1].set(xlabel="Table-row sampling interval", ylabel="Mean surface temperature (°C)")
fig.suptitle("Sensitivity within the real sampled table"); fig.tight_layout(); plt.show()''',
 'Try different starting offsets with the same interval. Why can systematic spacing miss a narrow stream or street? Explain why treating every displayed tile as an independent thermal measurement would overstate the evidence.',
 ['usgs','temperature']),
('07_eo_population_joins','Join carefully: pixels and populations',
 'Join actual sample centres to tract polygons and avoid interpreting tract population as a per-pixel measurement.',
 '''A spatial join is a geometric operation, not a causal model. We locate each satellite sample centre within Census tract geometry. Population remains the whole-tract POP100 count. We do not divide that count among pixels or infer how many people experienced a surface condition.

The original Census polygons use geographic longitude/latitude. A point-in-ring test handles polygon holes and multipolygons. Points exactly on a boundary have ambiguous assignment at numerical precision; the method should be declared for formal analysis.''',
 '''def in_ring(x,y,ring):
    inside = False
    for a,b in zip(ring, ring[1:]+ring[:1]):
        if (a[1]>y) != (b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside
def contains(f,x,y):
    g=f["geometry"]
    polys=[g["coordinates"]] if g["type"]=="Polygon" else g["coordinates"]
    return any(in_ring(x,y,p[0]) and not any(in_ring(x,y,h) for h in p[1:]) for p in polys)
groups = {}
# Use every tenth actual sample to keep this pure-Python browser exercise small.
for r in data[::10]:
    for f in tracts:
        if contains(f,r["lon"],r["lat"]):
            groups.setdefault(f["properties"]["GEOID"], []).append(r)
            break
joined = [(g,len(rs),avg("temperature_c",rs)) for g,rs in groups.items() if avg("temperature_c",rs) is not None]
# Independent GEOS point-in-polygon audit of this frozen real snapshot:
assert len(joined) == 155 and sum(s[1] for s in joined) == 689
expected_memberships = {
    "r5c35": "06039001100", "r145c455": "06019005507",
    "r415c375": "06019005100", "r815c555": "06019001500",
}
for sample_id, expected_geoid in expected_memberships.items():
    row = next(r for r in data if r["id"] == sample_id)
    hits = [f["properties"]["GEOID"] for f in tracts if contains(f,row["lon"],row["lat"])]
    assert hits == [expected_geoid], (sample_id, hits)
print("Tracts with joined subsamples:", len(joined), "| joined sample centres:", sum(s[1] for s in joined))''',
 '''plt.scatter([s[1] for s in joined], [s[2] for s in joined], color="#176c59", alpha=.7)
plt.xlabel("Joined satellite subsamples per tract"); plt.ylabel("Mean sampled surface temperature (°C)")
plt.title("Geometric join coverage varies among tracts; no health outcome is inferred")
plt.tight_layout(); plt.show()''',
 'Repeat with every fifth sample. Which tracts gain observations? Why is the tract average not a population-weighted personal exposure? Identify the ecological inference you would avoid.',
 ['census','usgs']),
('08_equity_evidence_gaps','Global Health starts with the missing voices',
 'Use observable contrasts to frame equitable questions without inventing vulnerability scores or intervention effects.',
 '''A satellite can locate surface differences; it cannot identify community priorities, social protection, disability, occupation or access to care. Global Health asks how a decision is developed with affected people and how its burdens and benefits are distributed. The WHO framing is a starting point for that conversation, not a method for turning NDVI into a vulnerability index.

We compare geographic halves only as a descriptive sensitivity check. Neither half is a real neighborhood, an administrative decision area or a defined social group. A difference in surface conditions does not establish a difference in disease.''',
 '''mid = (manifest["bbox"][0] + manifest["bbox"][2])/2
west = [r for r in data if r["lon"] < mid]
east = [r for r in data if r["lon"] >= mid]
for label, subset in [("West geometric half",west),("East geometric half",east)]:
    print(label, "samples",len(subset), "surface °C",round(avg("temperature_c",subset),2))
missing = ["Community priorities", "Air and indoor temperature", "Animal health", "Water chemistry", "Service access"]
print("Evidence absent from this package:", "; ".join(missing))''',
 '''plt.bar(["West geometric half","East geometric half"], [avg("temperature_c",west),avg("temperature_c",east)], color=["#176c59","#c89943"])
plt.ylabel("Mean sampled land surface temperature (°C)")
plt.title("Descriptive geographic contrast · no social or health attribution")
plt.tight_layout(); plt.show()''',
 'Draft a meeting agenda for community, veterinary, environmental and health-service partners. Name one question they could reject or redefine. Explain what evidence would be needed to evaluate an intervention rather than simulate its benefits.',
 ['who','cdc']),
('09_visualization_3d','Display choices are analytical choices',
 'Build a 3D display of measured values while making its height, support and perceptual limits explicit.',
 '''A 3D column can encode temperature, reflectance or population. It should never imply terrain unless actual elevation was acquired. The explorer scene places measured red/green/blue reflectance on a geographic plane, then adds whole-tract population columns. It does not contain an elevation model.

In this figure, height is actual land surface temperature in Celsius. Perspective can hide columns and distort comparisons, so a 2D plot and the accessible table remain essential alternatives. Sample rows are thinned only for legibility; no values are generated.''',
 '''sample = [r for r in data[::15] if r["temperature_c"] is not None]
print("Displayed actual sample count:", len(sample))
print("Height variable: land surface temperature in °C; not elevation.")''',
 '''fig = plt.figure(figsize=(8,5))
ax = fig.add_subplot(111, projection="3d")
points = ax.scatter([r["lon"] for r in sample], [r["lat"] for r in sample],
                    [r["temperature_c"] for r in sample], c=[r["ndvi"] for r in sample],
                    cmap="YlGn", s=9, vmin=-1, vmax=1)
ax.set(xlabel="Longitude (degrees)", ylabel="Latitude (degrees)", zlabel="Surface temperature (°C)")
ax.set_title("Actual sample values in 3D · height is not terrain")
fig.colorbar(points, ax=ax, shrink=.6, label="NDVI (unitless)")
plt.tight_layout(); plt.show()''',
 'Rotate the interactive explorer scene. Name two comparisons made harder by perspective. Recreate one comparison as a 2D chart with a numeric legend and explain which display you would publish.',
 ['nasa','temperature']),
('10_capstone','Build an evidence brief, not a risk score',
 'Produce a reproducible study-area brief with explicit data boundaries, a real observation figure and an acquisition plan for the next question.',
 '''A useful One Health brief connects a decision to evidence and its limits. Start by choosing a smaller bounding box inside the loaded package. Report what was observed, when and at what spatial support. Separate facts, assumptions and unanswered questions. No intervention outcomes, health-risk scores or probabilities can be estimated from this package alone.

To explore another bounded U.S. area, use **Create profile from live sources** in the explorer or `scripts/acquire_data.py --bbox ... --output ...` in a local acquisition environment. Export the package and keep its scene identity, Census query, dates and formulas. This notebook uses the bundled, independently verified starter rather than silently replacing it with live values.''',
 '''w,s,e,n = manifest["bbox"]
# EDIT these bounds within the loaded Fresno snapshot.
study_bbox = [w+.04, s+.04, e-.04, n-.04]
assert w <= study_bbox[0] < study_bbox[2] <= e and s <= study_bbox[1] < study_bbox[3] <= n
selected = [r for r in data if study_bbox[0] <= r["lon"] <= study_bbox[2] and study_bbox[1] <= r["lat"] <= study_bbox[3]]
assert selected
report = {"bbox":study_bbox, "scene_id":manifest["scene_id"], "satellite_datetime":manifest["satellite_datetime"],
          "population_reference":manifest["population_date"], "selected_samples":len(selected),
          "mean_sample_ndvi":avg("ndvi",selected), "mean_sample_surface_c":avg("temperature_c",selected),
          "limits":["Systematic samples, not full-resolution area means", "Surface is not air temperature", "No health outcomes or animal observations"]}
print(json.dumps(report,indent=2))
Path("my-evidence-brief.json").write_text(json.dumps(report,indent=2))''',
 '''paired = [r for r in selected if r["ndvi"] is not None and r["temperature_c"] is not None]
plt.scatter([r["ndvi"] for r in paired], [r["temperature_c"] for r in paired], s=8, alpha=.3, color="#176c59")
plt.xlabel("NDVI (unitless)"); plt.ylabel("Land surface temperature (°C)")
plt.title("Selected real observations for an evidence brief · association only")
plt.tight_layout(); plt.show()''',
 'Write a 300-word brief: decision and partners; observed evidence and dates; population interpretation; missing measurements; next acquisition; and a statement of what cannot be concluded. Download the JSON and your edited notebook from JupyterLite before clearing browser storage.',
 ['cdc','who','usgs','census'])]
SOURCES={
 'cdc':('CDC, About One Health','https://www.cdc.gov/one-health/about/index.html'),
 'who':('WHO, One Health','https://www.who.int/health-topics/one-health'),
 'noaa':('NOAA National Ocean Service, Are all algal blooms harmful?','https://oceanservice.noaa.gov/facts/habharm.html'),
 'usgs':('USGS EROS, Landsat Collection 2 Level-2 science products; dataset DOI 10.5066/P9OGBGM6','https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products'),
 'census':('U.S. Census Bureau, Census2020 TIGERweb Census Tracts layer 6 and POP100','https://tigerweb.geo.census.gov/arcgis/rest/services/Census2020/tigerWMS_Census2020/MapServer/6'),
 'nasa':('NASA, Landsat 9','https://science.nasa.gov/mission/landsat-9/'),
 'scale':('USGS, How do I use a scale factor with Landsat Level-2 science products?','https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products'),
 'qa':('USGS, Landsat Collection 2 quality assessment bands','https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands'),
 'ndvi':('USGS, Landsat Normalized Difference Vegetation Index','https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index'),
 'temperature':('USGS, Landsat Collection 2 surface temperature','https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature')}
def main():
 for name,title,objective,explanation,calculation,figure,exercise,sources in LESSONS:
    nb=nbf.v4.new_notebook(metadata={'kernelspec':{'display_name':'Python (Pyodide)','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'},'authors':[{'name':'JupyterLite-OneHealth project'}]})
    nb.cells=[nbf.v4.new_markdown_cell(f'# {title}\n\n**Objective:** {objective}\n\nOriginal project lesson. All observations are real USGS Landsat / U.S. Census inputs, with source details in `data/manifest.json`. No health outcome is inferred.\n\n{explanation}'),nbf.v4.new_markdown_cell('## Load the real bundled evidence\n\nRun cells in order. In JupyterLite, the first run may download Python and Matplotlib and requires internet access. Wait for the kernel to finish. Files are in browser storage: use **File → Save and Export Notebook As** or right-click a file and **Download** to keep work outside this browser. Desktop execution uses the pinned build environment.'),nbf.v4.new_code_cell(SETUP),nbf.v4.new_markdown_cell('## Inspect the calculation\n\nThe following code keeps source units and dates explicit. Edit assumptions only after recording what changes.'),nbf.v4.new_code_cell(calculation),nbf.v4.new_markdown_cell('## Make a figure from the observations\n\nThe figure describes the selected real evidence. It does not establish personal exposure or a causal health effect.'),nbf.v4.new_code_cell(figure),nbf.v4.new_markdown_cell('## Interpret and extend\n\n'+exercise+'\n\n## Sources and attribution\n\n'+ '\n'.join(f'- [{SOURCES[k][0]}]({SOURCES[k][1]}).' for k in dict.fromkeys(sources+['usgs','census']))+'\n\nData: USGS/NASA Landsat 8–9 Collection 2 Level-2, public domain; U.S. Census Bureau 2020 Census tracts and population, public domain. Accessed/acquired 7 November 2026. External readings are linked only; their prose, photographs, figures and code are not reproduced. Source organizations do not endorse this lesson.')]
    nb.cells[0].source += f'\n\n[Run this exact lesson in the browser Python Lab](https://jltobias.github.io/JupyterLite-OneHealth/lite/lab/index.html?path={name}.ipynb).'
    nbf.write(nb,ROOT/'content'/f'{name}.ipynb')
 print(f'Authored {len(LESSONS)} original notebooks.')
if __name__=='__main__': main()
