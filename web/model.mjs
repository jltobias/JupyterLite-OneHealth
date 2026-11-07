export const METRICS = {
  ndvi: { label: "NDVI", units: "unitless", domain: [-1, 1] },
  ndwi: { label: "NDWI", units: "unitless", domain: [-1, 1] },
  temperature_c: {
    label: "Land surface temperature",
    units: "°C",
    domain: null,
  },
  red: {
    label: "Red surface reflectance",
    units: "unitless",
    domain: [0, 0.6],
  },
};
export const HASH_METHOD = "SHA-256 of JSON.stringify of the named package member; UTF-8";
export function boundsInputValues(bounds) {
  return bounds.map(String);
}
export function linearColor(t) {
  const fraction = Math.max(0, Math.min(1, t));
  return `rgb(${Math.round(241 - 223 * fraction)},${Math.round(219 - 149 * fraction)},${Math.round(155 - 77 * fraction)})`;
}
export function serializeCsv(rows) {
  if (!rows.length) return "";
  const keys = Object.keys(rows[0]);
  const cell = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
  return [keys.map(cell).join(","), ...rows.map(row => keys.map(key => cell(row[key])).join(","))].join("\n");
}
export async function representationHash(member) {
  const bytes = new TextEncoder().encode(JSON.stringify(member));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}
export async function verifyPackageHashes(pkg) {
  const hashes = pkg.manifest.hashes;
  if (hashes === undefined) return pkg; // manifest.files hashes source files, a different representation.
  if (!hashes || hashes.method !== HASH_METHOD) throw Error("Unsupported package representation hash method.");
  for (const key of ["pixels", "tracts"]) {
    if (typeof hashes[key] !== "string" || !/^[a-f0-9]{64}$/i.test(hashes[key]))
      throw Error(`Invalid ${key} representation hash.`);
    if (await representationHash(pkg[key]) !== hashes[key].toLowerCase())
      throw Error(`${key} representation hash does not match the package contents.`);
  }
  return pkg;
}
export function validateBounds(b) {
  if (
    !Array.isArray(b) ||
    b.length !== 4 ||
    !b.every(Number.isFinite) ||
    b[0] >= b[2] ||
    b[1] >= b[3] ||
    b[0] < -180 ||
    b[2] > 180 ||
    b[1] < -90 ||
    b[3] > 90
  )
    throw Error(
      "Enter finite west < east and south < north, within longitude ±180° and latitude ±90°.",
    );
  if (b[2] - b[0] > 0.5 || b[3] - b[1] > 0.5)
    throw Error("Choose bounds at most 0.5° wide and high.");
  return b;
}
export function inside(lon, lat, b) {
  return lon >= b[0] && lon <= b[2] && lat >= b[1] && lat <= b[3];
}
export function selectPixels(pixels, b) {
  return pixels.filter((p) => inside(p.lon, p.lat, b));
}
export function mean(values) {
  const a = values.filter(Number.isFinite);
  return a.length ? a.reduce((s, x) => s + x, 0) / a.length : null;
}
export function quantile(values, q) {
  const a = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!a.length) return null;
  const x = (a.length - 1) * q,
    i = Math.floor(x);
  return a[i] + (a[Math.min(i + 1, a.length - 1)] - a[i]) * (x - i);
}
export function clipRing(ring, b) {
  let p = ring.slice();
  if (p.length && p[0][0] === p.at(-1)[0] && p[0][1] === p.at(-1)[1]) p.pop();
  for (const [axis, edge, greater] of [
    [0, b[0], true],
    [0, b[2], false],
    [1, b[1], true],
    [1, b[3], false],
  ]) {
    const out = [];
    for (let i = 0; i < p.length; i++) {
      const a = p[i],
        z = p[(i + 1) % p.length],
        ain = greater ? a[axis] >= edge : a[axis] <= edge,
        zin = greater ? z[axis] >= edge : z[axis] <= edge;
      if (ain) out.push(a);
      if (ain !== zin) {
        const t = (edge - a[axis]) / (z[axis] - a[axis]);
        out.push([a[0] + t * (z[0] - a[0]), a[1] + t * (z[1] - a[1])]);
      }
    }
    p = out;
    if (!p.length) break;
  }
  return p;
}
export function ringArea(r) {
  if (r.length < 3) return 0;
  let a = 0;
  for (let i = 0; i < r.length; i++) {
    const x = r[i],
      y = r[(i + 1) % r.length];
    a +=
      (((y[0] - x[0]) * Math.PI) / 180) *
      (2 + Math.sin((x[1] * Math.PI) / 180) + Math.sin((y[1] * Math.PI) / 180));
  }
  return (Math.abs(a) * 6371008.8 ** 2) / 2;
}
export function polygons(feature) {
  return feature.geometry.type === "Polygon"
    ? [feature.geometry.coordinates]
    : feature.geometry.type === "MultiPolygon"
      ? feature.geometry.coordinates
      : [];
}
export function geometryArea(feature, b = null) {
  return polygons(feature).reduce(
    (s, p) =>
      s +
      Math.max(
        0,
        p.reduce(
          (a, r, i) => a + (i ? -1 : 1) * ringArea(b ? clipRing(r, b) : r),
          0,
        ),
      ),
    0,
  );
}
export function population(tracts, b) {
  let full = 0,
    estimate = 0,
    count = 0;
  const overlaps = [];
  for (const f of tracts.features) {
    const total = geometryArea(f),
      overlap = geometryArea(f, b);
    if (overlap > 1 && total > 0) {
      const pop = Number(f.properties.POP100);
      if (!Number.isFinite(pop) || pop < 0)
        throw Error("Invalid Census POP100 value.");
      const fraction = Math.min(1, overlap / total);
      full += pop;
      estimate += pop * fraction;
      count++;
      overlaps.push({
        geoid: f.properties.GEOID,
        population: pop,
        area_fraction: fraction,
        uniform_area_estimate: pop * fraction,
      });
    }
  }
  return {
    full_tract_population: full,
    uniform_area_estimate: estimate,
    intersecting_tracts: count,
    overlaps,
  };
}
export function summarize(pkg, b, metric) {
  validateBounds(b);
  if (!Object.hasOwn(METRICS, metric)) throw Error("Unknown environmental measurement.");
  const c = pkg.manifest.bbox;
  if (
    b[0] < c[0] - 1e-8 ||
    b[1] < c[1] - 1e-8 ||
    b[2] > c[2] + 1e-8 ||
    b[3] > c[3] + 1e-8
  )
    throw Error(
      "These bounds extend beyond the loaded package. Use Create profile from live sources or import a package covering the entire area.",
    );
  const rows = selectPixels(pkg.pixels, b);
  if (!rows.length)
    throw Error(
      "No sampled observations fall in these bounds. Enlarge the box or acquire a finer grid.",
    );
  const values = rows.map((p) => p[metric]).filter(Number.isFinite);
  return {
    bbox: b,
    metric,
    rows,
    selected_samples: rows.length,
    valid_samples: values.length,
    valid_fraction: values.length / rows.length,
    mean: mean(values),
    p10: quantile(values, 0.1),
    p90: quantile(values, 0.9),
    population: population(pkg.tracts, b),
    satellite_datetime: pkg.manifest.satellite_datetime,
    population_date: pkg.manifest.population_date,
  };
}
export function validatePackage(p) {
  if (
    p?.schema_version !== 1 ||
    !p.manifest ||
    !Array.isArray(p.pixels) ||
    !p.pixels.length ||
    p.tracts?.type !== "FeatureCollection" ||
    !Array.isArray(p.tracts.features) || !p.tracts.features.length
  )
    throw Error(
      "Expected a version 1 profile package with manifest, real pixels and Census tract features.",
    );
  validateBounds(p.manifest.bbox);
  const text = value => typeof value === "string" && value.trim().length > 0;
  for (const key of ["title", "scene_id", "sampling", "qa", "population_method"])
    if (!text(p.manifest[key])) throw Error(`Package ${key} must be a nonempty string.`);
  const date = (value, timestamp = false) => {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(value)) return false;
    const day = value.slice(0, 10), parsed = new Date(day + "T00:00:00Z");
    if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== day) return false;
    return timestamp
      ? /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value))
      : value === day;
  };
  if (!date(p.manifest.satellite_datetime, true) || !date(p.manifest.population_date) ||
      !Array.isArray(p.manifest.credits) || !p.manifest.credits.length || !p.manifest.credits.every(text))
    throw Error("Package has invalid source dates or credits.");
  if (p.pixels.length > 30000 || p.tracts.features.length > 10000)
    throw Error("Package is too large for this browser workspace.");
  const pixelIds = new Set(), sourceIndices = new Set();
  for (const row of p.pixels) {
    if (!row || !text(row.id) || row.id.length > 200 ||
        !Number.isInteger(row.source_row) || row.source_row < 0 ||
        !Number.isInteger(row.source_col) || row.source_col < 0 ||
        ![0, 1].includes(row.valid) || ![0, 1].includes(row.thermal_valid))
      throw Error("Invalid sample ID, source index or validity flag.");
    const sourceIndex = `${row.source_row},${row.source_col}`;
    if (pixelIds.has(row.id) || sourceIndices.has(sourceIndex)) throw Error("Duplicate sample ID or source index.");
    pixelIds.add(row.id); sourceIndices.add(sourceIndex);
    if (
      !Number.isFinite(row.lon) ||
      !Number.isFinite(row.lat) ||
      !inside(row.lon, row.lat, p.manifest.bbox)
    )
      throw Error("A package sample has invalid geographic coordinates.");
    for (const k of ["blue", "green", "red", "nir08", "ndvi", "ndwi", "temperature_c"])
      if (row[k] !== null && !Number.isFinite(row[k]))
        throw Error("A measurement must be finite or null.");
    for (const key of ["blue", "green", "red", "nir08"])
      if (row.valid ? !Number.isFinite(row[key]) : row[key] !== null)
        throw Error("Optical channels must agree with the optical validity flag.");
    if (!row.valid && (row.ndvi !== null || row.ndwi !== null))
      throw Error("Masked optical ratios must remain null.");
    if (row.thermal_valid ? !Number.isFinite(row.temperature_c) : row.temperature_c !== null)
      throw Error("Surface temperature must agree with the thermal validity flag.");
    if (
      ![row.west, row.south, row.east, row.north].every(Number.isFinite) ||
      row.west >= row.east || row.south >= row.north
    ) throw Error("A sample has invalid geographic display bounds.");
  }
  const geoids = new Set();
  for (const f of p.tracts.features) {
    const count = f.properties?.POP100;
    if (
      f.type !== "Feature" ||
      !["Polygon", "MultiPolygon"].includes(f.geometry?.type) ||
      typeof f.properties?.GEOID !== "string" || !/^\d{11}$/.test(f.properties.GEOID) ||
      geoids.has(f.properties.GEOID) ||
      count === null ||
      count === undefined ||
      String(count).trim() === "" ||
      !["string", "number"].includes(typeof count) ||
      (typeof count === "string" && !/^\d+$/.test(count)) ||
      !Number.isSafeInteger(Number(count)) ||
      Number(count) < 0
    )
      throw Error("Invalid Census geometry or POP100.");
    geoids.add(f.properties.GEOID);
    if (!Array.isArray(f.geometry.coordinates) || !polygons(f).length)
      throw Error("Census geometry must not be empty.");
    for (const polygon of polygons(f)) {
      if (!Array.isArray(polygon) || !polygon.length) throw Error("Census polygon must not be empty.");
      for (const ring of polygon) {
        if (!Array.isArray(ring) || ring.length < 4)
          throw Error("Invalid polygon ring.");
        for (const xy of ring)
          if (
            !Array.isArray(xy) ||
            xy.length < 2 ||
            !xy.every(Number.isFinite) ||
            Math.abs(xy[0]) > 180 ||
            Math.abs(xy[1]) > 90
          )
            throw Error("Invalid polygon coordinates.");
        if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1])
          throw Error("GeoJSON polygon rings must be closed.");
        if (!(ringArea(ring) > 0)) throw Error("Census rings must have positive area.");
      }
      if (!(ringArea(polygon[0]) - polygon.slice(1).reduce((area, ring) => area + ringArea(ring), 0) > 0))
        throw Error("Census polygons must have positive area after subtracting holes.");
    }
  }
  return p;
}
