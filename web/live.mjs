import { validateBounds, representationHash, HASH_METHOD } from "./model.mjs";
const BANDS = [
  "blue",
  "green",
  "red",
  "nir08",
  "lwir11",
  "qa_pixel",
  "qa_radsat",
];
const STAC = "https://planetarycomputer.microsoft.com/api/stac/v1";
const CENSUS =
  "https://tigerweb.geo.census.gov/arcgis/rest/services/Census2020/tigerWMS_Census2020/MapServer/6/query";
export function calibratePixel(dn) {
  const native = key => Number.isInteger(dn[key]) && dn[key] >= 0 && dn[key] <= 65535;
  const clear = native("qa_pixel") && native("qa_radsat") && (dn.qa_pixel & 63) === 0 && dn.qa_radsat === 0;
  const optical = clear && ["blue", "green", "red", "nir08"].every(key => native(key) && dn[key] > 0);
  const thermal = clear && native("lwir11") && dn.lwir11 > 0;
  const reflectance = Object.fromEntries(["blue", "green", "red", "nir08"].map(key => [key, optical ? dn[key] * 0.0000275 - 0.2 : null]));
  const ratio = (a, b) => a !== null && b !== null && Math.abs(a + b) > 1e-12 ? (a - b) / (a + b) : null;
  return {
    valid: optical ? 1 : 0,
    thermal_valid: thermal ? 1 : 0,
    ...reflectance,
    ndvi: ratio(reflectance.nir08, reflectance.red),
    ndwi: ratio(reflectance.green, reflectance.nir08),
    temperature_c: thermal ? dn.lwir11 * 0.00341802 + 149 - 273.15 : null,
  };
}
export function sampleGrid(nativeWidth, nativeHeight) {
  if (!Number.isInteger(nativeWidth) || !Number.isInteger(nativeHeight) || nativeWidth < 1 || nativeHeight < 1)
    throw Error("The selected source window has no native pixels.");
  const stride = Math.max(1, Math.ceil(Math.max(nativeWidth, nativeHeight) / 96));
  return { stride, width: Math.max(1, Math.floor(nativeWidth / stride)), height: Math.max(1, Math.floor(nativeHeight / stride)) };
}
async function json(url, params) {
  const u = new URL(url);
  if (params)
    Object.entries(params).forEach(([k, v]) => u.searchParams.set(k, v));
  for (let attempt = 0; attempt < 3; attempt++) {
    const controller = new AbortController(),
      timer = setTimeout(() => controller.abort(), 120000);
    try {
      const r = await fetch(u, {
        signal: controller.signal,
        credentials: "omit",
      });
      if ((r.status === 429 || r.status === 503) && attempt < 2) {
        const retry = r.headers.get("Retry-After"),
          seconds = retry
            ? Number.isFinite(Number(retry))
              ? Number(retry)
              : Math.max(0, (Date.parse(retry) - Date.now()) / 1000)
            : 2 ** (attempt + 1);
        if (!Number.isFinite(seconds) || seconds > 30)
          throw Error(
            `${u.host} requests a longer retry delay; please retry later.`,
          );
        await new Promise((resolve) =>
          setTimeout(resolve, Math.max(1, seconds) * 1000),
        );
        continue;
      }
      if (!r.ok) throw Error(`${u.host}: HTTP ${r.status}`);
      return await r.json();
    } finally {
      clearTimeout(timer);
    }
  }
}
const tokenCache = new Map();
async function signAsset(unsigned) {
  const u = new URL(unsigned),
    account = u.hostname.split(".")[0],
    container = u.pathname.split("/")[1],
    key = account + "/" + container;
  let cached = tokenCache.get(key);
  if (!cached || Date.now() - cached.time > 10 * 60 * 1000) {
    const value = await json(
      "https://planetarycomputer.microsoft.com/api/sas/v1/token/" + key,
    );
    if (!value.token)
      throw Error("Provider did not return a usable asset token.");
    cached = { token: value.token, time: Date.now() };
    tokenCache.set(key, cached);
  }
  return unsigned + (unsigned.includes("?") ? "&" : "?") + cached.token;
}

function script(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = new URL(src, import.meta.url);
    s.onload = resolve;
    s.onerror = () =>
      reject(Error("Could not load local raster/projection software."));
    document.head.append(s);
  });
}
async function census(b, progress) {
  const params = {
      where: "1=1",
      geometry: b.join(","),
      geometryType: "esriGeometryEnvelope",
      inSR: 4326,
      spatialRel: "esriSpatialRelIntersects",
      outFields: "GEOID,NAME,POP100,AREALAND",
      outSR: 4326,
      returnGeometry: true,
      f: "geojson",
      orderByFields: "GEOID",
      resultRecordCount: 1000,
    },
    features = [];
  let offset = 0;
  while (true) {
    progress(`Reading Census 2020 tracts (${offset} received)…`);
    const page = await json(CENSUS, { ...params, resultOffset: offset });
    if (page.error) throw Error(`Census: ${page.error.message}`);
    const batch = page.features || [];
    features.push(...batch);
    const more =
      page.exceededTransferLimit || page.properties?.exceededTransferLimit;
    if (!more && batch.length < 1000) break;
    if (!batch.length)
      throw Error("Census pagination ended before a complete result.");
    offset += batch.length;
    if (offset > 10000) throw Error("Too many tracts; reduce the study area.");
  }
  if (!features.length)
    throw Error("No U.S. 2020 Census coverage for this box.");
  return {
    tracts: {
      type: "FeatureCollection",
      features: [
        ...new Map(features.map((f) => [f.properties.GEOID, f])).values(),
      ],
    },
    query: {
      url: CENSUS,
      params,
      pagination: "GEOID-ordered pages until complete",
    },
  };
}
function points(b) {
  const out = [];
  for (let i = 0; i <= 20; i++) {
    const x = b[0] + ((b[2] - b[0]) * i) / 20,
      y = b[1] + ((b[3] - b[1]) * i) / 20;
    out.push([x, b[1]], [x, b[3]], [b[0], y], [b[2], y]);
  }
  return out;
}
export async function acquireLive(b, progress = () => {}) {
  validateBounds(b);
  if (b[0] < -180 || b[2] > -60 || b[1] < 15 || b[3] > 75)
    throw Error(
      "Select a bounded U.S. study area; only public-domain U.S. population coverage is supported.",
    );
  if (!window.GeoTIFF) await script("./vendor/geotiff.js");
  if (!window.proj4) await script("./vendor/proj4.js");
  const { tracts, query } = await census(b, progress);
  progress(
    "Searching actual Landsat 8/9 Level-2 acquisitions (June 2024–September 2025)…",
  );
  const result = await json(STAC + "/search", {
    collections: "landsat-c2-l2",
    bbox: b.join(","),
    datetime: "2024-06-01T00:00:00Z/2025-10-01T00:00:00Z",
    limit: 100,
  });
  const candidates = (result.features || [])
    .filter(
      (f) =>
        (f.id.startsWith("LC08_") || f.id.startsWith("LC09_")) &&
        f.id.includes("_L2SP_") &&
        BANDS.every((k) => f.assets[k]) &&
        f.bbox[0] <= b[0] &&
        f.bbox[1] <= b[1] &&
        f.bbox[2] >= b[2] &&
        f.bbox[3] >= b[3],
    )
    .sort(
      (a, z) =>
        (a.properties["eo:cloud_cover"] ?? 100) -
        (z.properties["eo:cloud_cover"] ?? 100),
    );
  if (!candidates.length)
    throw Error(
      "No fully bounding Landsat surface-temperature scene found in the supported date interval.",
    );
  const item = candidates[0],
    epsg = item.properties["proj:epsg"] || item.assets.red["proj:epsg"];
  if (!((epsg >= 32601 && epsg <= 32660) || (epsg >= 32701 && epsg <= 32760)))
    throw Error(
      `Unsupported source projection ${epsg}; use the Python acquisition route.`,
    );
  const zone = epsg % 100,
    definition = `+proj=utm +zone=${zone} ${epsg >= 32700 ? "+south " : ""}+datum=WGS84 +units=m +no_defs`,
    project = (xy) => window.proj4("EPSG:4326", definition, xy),
    inverse = (xy) => window.proj4(definition, "EPSG:4326", xy),
    projected = points(b).map(project),
    pb = [
      Math.min(...projected.map((x) => x[0])),
      Math.min(...projected.map((x) => x[1])),
      Math.max(...projected.map((x) => x[0])),
      Math.max(...projected.map((x) => x[1])),
    ];
  const arrays = {},
    sources = {},
    rows = [];
  let geometry;
  // Single-range GeoTIFF reads tolerate the provider's unexposed Content-Range header.
  for (const band of BANDS) {
    progress(
      `${item.id}: reading ${band} from its actual COG (no substitutes)…`,
    );
    const unsigned = item.assets[band].href,
      signed = await signAsset(unsigned);
    const controller = new AbortController(),
      timer = setTimeout(() => controller.abort(), 180000);
    try {
      const tiff = await window.GeoTIFF.fromUrl(
          signed,
          {
            allowFullFile: false,
            maxRanges: 0,
            blockSize: 65536,
            cacheSize: 32,
          },
          controller.signal,
        ),
        image = await tiff.getImage(),
        origin = image.getOrigin(),
        res = image.getResolution();
      if (image.getGeoKeys().GTRasterTypeGeoKey === 2) {
        origin[0] -= res[0] / 2;
        origin[1] -= res[1] / 2;
      }
      if (res[0] <= 0 || res[1] >= 0)
        throw Error("Unsupported raster orientation.");
      const win = [
        Math.floor((pb[0] - origin[0]) / res[0]),
        Math.floor((pb[3] - origin[1]) / res[1]),
        Math.ceil((pb[2] - origin[0]) / res[0]),
        Math.ceil((pb[1] - origin[1]) / res[1]),
      ];
      if (
        win[0] < 0 ||
        win[1] < 0 ||
        win[2] > image.getWidth() ||
        win[3] > image.getHeight()
      )
        throw Error(
          "Chosen scene does not cover the full study area. Try a smaller box or the Python acquisition route.",
        );
      if ((win[2] - win[0]) * (win[3] - win[1]) > 1000000)
        throw Error(
          "This box exceeds one million native pixels. Choose a smaller area to bound browser memory.",
        );
      const {stride, width, height} = sampleGrid(win[2] - win[0], win[3] - win[1]);
      if (!geometry) geometry = { win, origin, res, stride, width, height };
      else if (
        JSON.stringify([win, origin, res]) !==
        JSON.stringify([geometry.win, geometry.origin, geometry.res])
      )
        throw Error("Source bands do not share the same grid.");
      const a = await image.readRasters({
        window: win,
        samples: [0],
        width,
        height,
        resampleMethod: "nearest",
        signal: controller.signal,
      });
      arrays[band] = a[0];
      sources[band] = {
        unsigned_asset: unsigned,
        source_window: win,
        source_shape: [image.getHeight(), image.getWidth()],
        corner_origin: origin,
        source_resolution: res,
        pixel_is_point: image.getGeoKeys().GTRasterTypeGeoKey === 2,
      };
    } finally {
      clearTimeout(timer);
    }
  }
  const { win, origin, res, width, height } = geometry;
  for (let r = 0; r < height; r++)
    for (let c = 0; c < width; c++) {
      const sourceCol =
          win[0] +
          Math.min(
            win[2] - win[0] - 1,
            Math.round((c * (win[2] - win[0])) / width),
          ),
        sourceRow =
          win[1] +
          Math.min(
            win[3] - win[1] - 1,
            Math.round((r * (win[3] - win[1])) / height),
          ),
        xy = [
          origin[0] + (sourceCol + 0.5) * res[0],
          origin[1] + (sourceRow + 0.5) * res[1],
        ],
        [lon, lat] = inverse(xy);
      if (lon < b[0] || lon > b[2] || lat < b[1] || lat > b[3]) continue;
      const index = r * width + c,
        dn = Object.fromEntries(BANDS.map((k) => [k, arrays[k][index]])),
        dx = (((win[2] - win[0]) / width) * res[0]) / 2,
        dy = ((-(win[3] - win[1]) / height) * res[1]) / 2,
        [west, south] = inverse([xy[0] - dx, xy[1] - dy]),
        [east, north] = inverse([xy[0] + dx, xy[1] + dy]);
      rows.push({
        id: `r${sourceRow}c${sourceCol}`,
        source_row: sourceRow,
        source_col: sourceCol,
        lon,
        lat,
        west,
        south,
        east,
        north,
        ...calibratePixel(dn),
        ...Object.fromEntries(BANDS.map((k) => [k + "_dn", dn[k]])),
      });
    }
  if (!rows.length)
    throw Error("No samples fall within the geographic bounds.");
  progress("Calculating selected real samples and population overlaps…");
  const packageData = {
    schema_version: 1,
    manifest: {
      schema_version: 1,
      title: "Live U.S. study-area observations",
      bbox: b,
      crs: "EPSG:4326",
      source_crs: `EPSG:${epsg}`,
      scene_id: item.id,
      satellite_datetime: item.properties.datetime,
      population_date: "2020-04-01",
      retrieved_at: new Date().toISOString(),
      source_grid_m: 30,
      thermal_native_resolution_m: 100,
      sample_count: rows.length,
      sampling:
        "Nearest-native-pixel samples on a reduced projected grid. Display tiles show sampling spacing; sample means are not full-resolution area means.",
      qa: "Reject QA_PIXEL bits 0–5, any QA_RADSAT, optical zero DN and thermal zero DN. Missing measurements remain null.",
      population_method:
        "Full-tract counts are separate from the bbox estimate. The latter uses spherical polygon-area fractions with a uniform within-tract population assumption.",
      credits: [
        "USGS EROS / NASA Landsat 8–9 Collection 2 Level-2. DOI:10.5066/P9OGBGM6",
        "U.S. Census Bureau, 2020 Census TIGERweb tracts and POP100",
      ],
      source_files: sources,
      census_query: query,
      stac_query: {
        url: STAC + "/search",
        params: {
          collections: "landsat-c2-l2",
          bbox: b.join(","),
          datetime: "2024-06-01T00:00:00Z/2025-10-01T00:00:00Z",
          limit: 100,
        },
        selection:
          "Lowest scene-cloud-cover candidate among up to 100 returned L2SP items with required bands and a scene bbox covering the study bounds.",
      },
      rights: {
        landsat:
          "https://www.usgs.gov/faqs/are-landsat-data-cloud-still-considered-be-within-public-domain",
        census:
          "https://www.census.gov/newsroom/archives/2014-pr/cb14-208.html",
      },
      formulas: {
        reflectance: "DN*0.0000275-0.2",
        temperature_c: "DN*0.00341802+149-273.15",
        ndvi: "(nir08-red)/(nir08+red)",
        ndwi: "(green-nir08)/(green+nir08)",
      },
    },
    pixels: rows,
    tracts,
  };
  packageData.manifest.hashes = {
    method: HASH_METHOD,
    pixels: await representationHash(rows),
    tracts: await representationHash(tracts),
  };
  return packageData;
}
