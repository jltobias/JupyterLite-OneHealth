// Pure calculation and package tests; browser interaction companion is below.
const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path");
(async () => {
  const root = path.resolve(__dirname, ".."),
    m = await import("../web/model.mjs"),
    live = await import("../web/live.mjs"),
    pkg = JSON.parse(
      fs.readFileSync(
        path.join(root, "content/data/profile-package.json"),
        "utf8",
      ),
    );
  m.validatePackage(pkg);
  const fixture = () => structuredClone({ ...pkg, pixels: pkg.pixels.slice(0, 2), tracts: {type: "FeatureCollection", features: pkg.tracts.features.slice(0, 1)} });
  const invalid = mutate => { const candidate = fixture(); mutate(candidate); assert.throws(() => m.validatePackage(candidate)); };
  for (const key of ["title", "scene_id", "sampling", "qa", "population_method"])
    for (const value of [null, 1, {}, [], true, ""])
      invalid(p => p.manifest[key] = value);
  for (const value of ["credits", [], [null], [""], ["valid", {}]]) invalid(p => p.manifest.credits = value);
  for (const value of [null, 1, "2024-02-31T00:00:00Z", "not a date", "2024-08-30"])
    invalid(p => p.manifest.satellite_datetime = value);
  invalid(p => p.manifest.population_date = "2020-02-31");
  for (const flag of ["valid", "thermal_valid"])
    for (const value of [true, false, "1", 2, null]) invalid(p => p.pixels[0][flag] = value);
  for (const channel of ["blue", "green", "red", "nir08"])
    for (const value of [undefined, null, "0.1", Infinity, NaN]) invalid(p => p.pixels[0][channel] = value);
  invalid(p => p.pixels[0].id = {});
  invalid(p => p.pixels[1].id = p.pixels[0].id);
  invalid(p => { p.pixels[1].source_row = p.pixels[0].source_row; p.pixels[1].source_col = p.pixels[0].source_col; });
  invalid(p => p.tracts.features.push(structuredClone(p.tracts.features[0])));
  for (const type of ["Polygon", "MultiPolygon"])
    invalid(p => p.tracts.features[0].geometry = {type, coordinates: []});
  invalid(p => p.tracts.features[0].geometry.coordinates = [[]]);
  invalid(p => p.tracts.features[0].geometry = {type:"Polygon", coordinates:[[[0,0],[1,0],[2,0],[0,0]]]});
  invalid(p => p.tracts.features[0].geometry.coordinates[0].pop());
  for (const value of ["test", "123456789012", 60190001000]) invalid(p => p.tracts.features[0].properties.GEOID = value);
  invalid(p => p.tracts.features[0].properties.POP100 = Number.MAX_SAFE_INTEGER + 1);
  const quoted = fixture(); quoted.pixels[0].id = 'sample,"quoted"\nnext line'; m.validatePackage(quoted);
  assert.equal(m.serializeCsv([{ 'field,"name"': 'sample,"quoted"\nnext line', empty: null }]), '"field,""name""","empty"\n"sample,""quoted""\nnext line",""');
  const precise = fixture(); precise.manifest.bbox = [-119.90000012345678,36.65000012345678,-119.65000012345678,36.90000012345678];
  const inputBounds = m.boundsInputValues(precise.manifest.bbox).map(Number);
  assert.deepEqual(inputBounds, precise.manifest.bbox);
  assert.equal(m.summarize(precise, inputBounds, "ndvi").selected_samples, 2);
  const crypto = require("node:crypto");
  const independentlyHash = member => crypto.createHash("sha256").update(JSON.stringify(member)).digest("hex");
  const hashed = fixture(); hashed.manifest.hashes = {method:m.HASH_METHOD,pixels:independentlyHash(hashed.pixels),tracts:independentlyHash(hashed.tracts)};
  await m.verifyPackageHashes(hashed);
  assert.equal(await m.representationHash(hashed.pixels), independentlyHash(hashed.pixels));
  for (const key of ["pixels", "tracts"]) { const bad = structuredClone(hashed); bad.manifest.hashes[key] = "0".repeat(64); await assert.rejects(() => m.verifyPackageHashes(bad)); }
  const unknown = structuredClone(hashed); unknown.manifest.hashes.method = "unknown"; await assert.rejects(() => m.verifyPackageHashes(unknown));
  await m.verifyPackageHashes(fixture()); // Source-file hashes are intentionally not representation hashes.
  assert.equal(m.linearColor(0), "rgb(241,219,155)");
  assert.equal(m.linearColor(.5), "rgb(130,145,117)");
  assert.equal(m.linearColor(1), "rgb(18,70,78)");
  assert.deepEqual(live.sampleGrid(2,800), {stride:9,width:1,height:88});
  assert.deepEqual(live.sampleGrid(800,2), {stride:9,width:88,height:1});
  assert.throws(() => live.sampleGrid(0,800));
  function expectedCalibration(dn) {
    const channels = ["blue","green","red","nir08"];
    const present = key => Number.isInteger(dn[key]) && dn[key] >= 0 && dn[key] <= 65535;
    const clear = present("qa_pixel") && present("qa_radsat") && (dn.qa_pixel % 64 === 0) && dn.qa_radsat === 0;
    const optical = clear && channels.every(key => present(key) && dn[key] !== 0);
    const thermal = clear && present("lwir11") && dn.lwir11 !== 0;
    const result = {valid:Number(optical),thermal_valid:Number(thermal)};
    for (const key of channels) result[key] = optical ? dn[key] * 0.0000275 - 0.2 : null;
    result.temperature_c = thermal ? dn.lwir11 * 0.00341802 - 124.15 : null;
    for (const [name,left,right] of [["ndvi","nir08","red"],["ndwi","green","nir08"]])
      result[name] = optical && Math.abs(result[left]+result[right])>1e-12 ? (result[left]-result[right])/(result[left]+result[right]) : null;
    return result;
  }
  const compareCalibration = dn => {
    const actual = live.calibratePixel(dn), expected = expectedCalibration(dn);
    for (const [key,value] of Object.entries(expected))
      if (value === null) assert.equal(actual[key], null); else assert(Math.abs(actual[key]-value)<1e-10, key);
  };
  const bands = ["blue","green","red","nir08","lwir11","qa_pixel","qa_radsat"];
  for (const row of pkg.pixels) compareCalibration(Object.fromEntries(bands.map(key => [key,row[key+"_dn"]])));
  const dn = Object.fromEntries(bands.map(key => [key,pkg.pixels[0][key+"_dn"]]));
  for (const key of ["blue","green","red","nir08","lwir11"]) compareCalibration({...dn,[key]:0});
  for (const bit of [1,2,4,8,16,32]) compareCalibration({...dn,qa_pixel:bit});
  compareCalibration({...dn,qa_radsat:1}); compareCalibration({...dn,qa_pixel:undefined});
  const initial = m.summarize(pkg, pkg.manifest.bbox, "ndvi");
  assert.equal(initial.population.full_tract_population, 764468);
  assert.equal(initial.population.intersecting_tracts, 166);
  assert(Math.abs(initial.population.uniform_area_estimate - 686226.83) < 1);
  assert(initial.mean > 0.2 && initial.mean < 0.5);
  const b = [-119.84, 36.7, -119.74, 36.82],
    subset = m.summarize(pkg, b, "temperature_c");
  assert(subset.rows.length < initial.rows.length);
  assert(subset.rows.every((p) => m.inside(p.lon, p.lat, b)));
  assert(subset.mean > 20 && subset.mean < 70);
  assert(
    subset.population.full_tract_population <
      initial.population.full_tract_population,
  );
  for (const bad of [
    [NaN, 0, 1, 1],
    [-119, 36, -120, 37],
    [-119.9, 36.65, -118, 36.9],
  ])
    assert.throws(() => m.summarize(pkg, bad, "ndvi"));
  const missing = structuredClone(pkg);
  missing.pixels = missing.pixels.map((p) => ({ ...p, temperature_c: null }));
  assert.equal(
    m.summarize(missing, pkg.manifest.bbox, "temperature_c").mean,
    null,
  );
  for (const bad of [null, "", -1, 1.5]) {
    const candidate = structuredClone(pkg);
    candidate.tracts.features[0].properties.POP100 = bad;
    assert.throws(() => m.validatePackage(candidate));
  }
  const square = {
    type: "Feature",
    properties: { POP100: 100, GEOID: "test" },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
          [0, 0],
        ],
      ],
    },
  };
  const pop = m.population({ features: [square] }, [0, 0, 0.5, 1]);
  assert(Math.abs(pop.uniform_area_estimate - 50) < 1e-6);
  assert.equal(pop.full_tract_population, 100);
  console.log(
    `Explorer calculations passed: ${initial.rows.length} real samples, ${subset.rows.length} selected samples; masks/nulls, bounds, geometry and population checked.`,
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
