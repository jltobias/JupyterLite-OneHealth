import {
  METRICS,
  validateBounds,
  validatePackage,
  summarize,
  mean,
  polygons,
  clipRing,
  boundsInputValues,
  linearColor,
  serializeCsv,
  verifyPackageHashes,
} from "./model.mjs";
const $ = (s) => document.querySelector(s);
const needsData = ["apply", "reset", "csv", "json", "download", "previous", "next", "orbit-left", "orbit-right", "metric", "tracts"];
needsData.forEach(id => $("#" + id).disabled = true);
let pkg,
  profile,
  page = 0,
  angle = 0.7,
  tilt = 0.65,
  view = location.pathname.split("/").filter(Boolean).at(-1) || "profile",
  drag,
  generation = 0;
const fmt = (n, d = 2) =>
  n === null || !Number.isFinite(n)
    ? "Unavailable"
    : n.toLocaleString(undefined, { maximumFractionDigits: d });
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function status(text, error = false) {
  $("#status").textContent = text;
  $("#status").classList.toggle("error", error);
}
function bounds() {
  return ["west", "south", "east", "north"].map((k) => {
    const x = $("#" + k).value;
    return x.trim() === "" ? NaN : Number(x);
  });
}
function setBounds(b) {
  const values = boundsInputValues(b);
  ["west", "south", "east", "north"].forEach(
    (k, i) => ($("#" + k).value = values[i]),
  );
}
function beginOperation() {
  $("#live").disabled = false;
  return ++generation;
}
function showProfileStatus() {
  status(`Showing ${pkg.manifest.title}. Bounds ${profile.bbox.map(v => v.toFixed(4)).join(", ")}. ${fmt(profile.valid_fraction * 100, 1)}% of selected samples valid for ${METRICS[profile.metric].label}.`);
}
function commitState(nextPackage, nextProfile) {
  const previous = {pkg, profile, page, metric: $("#metric").value, inputs: bounds()};
  pkg = nextPackage;
  profile = nextProfile;
  page = 0;
  try {
    render();
    setBounds(profile.bbox);
  } catch (error) {
    ({pkg, profile, page} = previous);
    $("#metric").value = profile?.metric ?? previous.metric;
    setBounds(profile?.bbox ?? previous.inputs);
    if (profile) {
      try { render(); } catch { /* Preserve the previous valid data even if rendering is unavailable. */ }
    } else {
      needsData.forEach(id => $("#" + id).disabled = true);
      for (const id of ["stats", "visual", "profile-details", "rows", "population-rows", "source"])
        $("#" + id).replaceChildren();
    }
    throw error;
  }
}
async function acceptPackage(next, requestedBounds, token) {
  validatePackage(next);
  await verifyPackageHashes(next);
  if (token !== generation) return false;
  const nextProfile = summarize(next, requestedBounds ?? next.manifest.bbox, $("#metric").value);
  commitState(next, nextProfile);
  showProfileStatus();
  return true;
}
function apply(b = bounds()) {
  if (!pkg) {
    status(
      "Wait for a package to load, or import a valid profile package.",
      true,
    );
    return;
  }
  beginOperation();
  try {
    const next = summarize(pkg, b, $("#metric").value);
    commitState(pkg, next);
    showProfileStatus();
  } catch (e) {
    status(e.message + " The previous valid profile remains displayed.", true);
  }
}
function mapGeometry() {
  const b = profile.bbox,
    cos = Math.cos((((b[1] + b[3]) / 2) * Math.PI) / 180),
    factor = Math.min(810 / ((b[2] - b[0]) * cos), 485 / (b[3] - b[1])),
    w = (b[2] - b[0]) * cos * factor,
    h = (b[3] - b[1]) * factor;
  return { cos, factor, w, h, left: (900 - w) / 2, top: (590 - h) / 2 };
}
function scale() {
  const b = profile.bbox,
    g = mapGeometry();
  return ([x, y]) => [
    g.left + (x - b[0]) * g.cos * g.factor,
    g.top + (b[3] - y) * g.factor,
  ];
}
function color(v) {
  if (!Number.isFinite(v)) return "#d7d8d0";
  const m = METRICS[profile.metric],
    lo = m.domain?.[0] ?? profile.p10 ?? 0,
    hi = m.domain?.[1] ?? profile.p90 ?? 1,
    t = Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1)));
  return linearColor(t);
}
function svg(content, label) {
  $("#visual").innerHTML =
    `<svg viewBox="0 0 900 590" role="img" aria-label="${esc(label)}"><rect width="900" height="590" fill="#f2f5ee"/>${content}</svg>`;
}
function tractPaths(project = scale(), fill = "none") {
  let s = "";
  for (const f of pkg.tracts.features) {
    for (const p of polygons(f)) {
      const rings = p
        .map((r) => clipRing(r, profile.bbox))
        .filter((r) => r.length > 2);
      if (!rings.length) continue;
      const d = rings
        .map(
          (r) =>
            r
              .map(
                (xy, i) =>
                  `${i ? "L" : "M"}${project(xy)
                    .map((x) => x.toFixed(1))
                    .join(",")}`,
              )
              .join(" ") + "Z",
        )
        .join(" ");
      s += `<path d="${d}" fill="${fill}" fill-rule="evenodd" stroke="#143d43" stroke-width=".65" opacity=".6"/>`;
    }
  }
  return s;
}
function map() {
  const project = scale(),
    g = mapGeometry();
  let s = "";
  for (const p of profile.rows) {
    const a = project([
        Math.max(p.west, profile.bbox[0]),
        Math.min(p.north, profile.bbox[3]),
      ]),
      z = project([
        Math.min(p.east, profile.bbox[2]),
        Math.max(p.south, profile.bbox[1]),
      ]);
    s += `<rect x="${a[0]}" y="${a[1]}" width="${Math.max(1, z[0] - a[0])}" height="${Math.max(1, z[1] - a[1])}" fill="${color(p[profile.metric])}"><title>${esc(p.id)}: ${fmt(p[profile.metric])} ${METRICS[profile.metric].units}</title></rect>`;
  }
  if ($("#tracts").checked) s += tractPaths();
  s += `<text x="45" y="575" font-size="13" fill="#163d42">${profile.bbox[0].toFixed(3)}° → ${profile.bbox[2].toFixed(3)}° longitude · north ↑</text><rect x="${g.left}" y="${g.top}" width="${g.w}" height="${g.h}" fill="none" stroke="#54756c"/>`;
  svg(s, "Geographic map of real Landsat samples and Census tracts");
}
function projection() {
  const b = profile.bbox,
    cos = Math.cos(angle),
    sin = Math.sin(angle),
    latitudeFactor = Math.cos((b[1] + b[3]) / 2 * Math.PI / 180),
    planeScale = Math.min(520 / ((b[2] - b[0]) * latitudeFactor), 380 / (b[3] - b[1]));
  return ([lon, lat], h = 0) => {
    const x = (lon - (b[0] + b[2]) / 2) * latitudeFactor * planeScale,
      y = (lat - (b[1] + b[3]) / 2) * planeScale;
    return [450 + x * cos - y * sin, 340 + (x * sin + y * cos) * tilt - h];
  };
}
function three(scene = false) {
  const proj = projection();
  let s = `<path d="${[
    [profile.bbox[0], profile.bbox[1]],
    [profile.bbox[2], profile.bbox[1]],
    [profile.bbox[2], profile.bbox[3]],
    [profile.bbox[0], profile.bbox[3]],
  ]
    .map((p, i) => (i ? "L" : "M") + proj(p).join(","))
    .join(" ")}Z" fill="#e0e8dc" stroke="#9fb3aa"/>`;
  const values = profile.rows
      .map((p) => p[profile.metric])
      .filter(Number.isFinite),
    lo = Math.min(...values),
    hi = Math.max(...values);
  const points = profile.rows
    .slice()
    .sort((a, b) => proj([a.lon, a.lat])[1] - proj([b.lon, b.lat])[1]);
  for (const p of points) {
    const base = proj([p.lon, p.lat]),
      v = p[profile.metric];
    if (scene) {
      const rgb = ["red", "green", "blue"].map((k) =>
        Math.round(Math.max(0, Math.min(1, (p[k] ?? 0) / 0.35)) * 255),
      );
      const corners = [
        [p.west, p.south],
        [p.east, p.south],
        [p.east, p.north],
        [p.west, p.north],
      ].map((x) => proj(x));
      s += `<path d="${corners.map((q, i) => (i ? "L" : "M") + q.join(",")).join(" ")}Z" fill="${p.valid ? `rgb(${rgb.join(",")})` : "#d7d8d0"}"/>`;
    } else if (Number.isFinite(v)) {
      const top = proj([p.lon, p.lat], 15 + (170 * (v - lo)) / (hi - lo || 1));
      s += `<path d="M${base.join(",")}L${top.join(",")}" stroke="${color(v)}" stroke-width="3"><title>${esc(p.id)}: ${fmt(v)}</title></path>`;
    }
  }
  if (scene) {
    for (const o of profile.population.overlaps) {
      const f = pkg.tracts.features.find((f) => f.properties.GEOID === o.geoid);
      const pts = polygons(f).flatMap((poly) =>
        clipRing(poly[0], profile.bbox),
      );
      if (!pts.length) continue;
      const c = [mean(pts.map((p) => p[0])), mean(pts.map((p) => p[1]))],
        a = proj(c),
        z = proj(c, Math.sqrt(o.population) * 1.6);
      s += `<path d="M${a.join(",")}L${z.join(",")}" stroke="#f4c66b" stroke-width="5"><title>Tract ${esc(o.geoid)}: ${o.population} people in whole tract (2020)</title></path>`;
    }
  }
  s +=
    '<text x="25" y="570" font-size="13" fill="#163d42">Drag to orbit · height is a data display, not terrain</text>';
  svg(
    s,
    scene
      ? "Actual satellite reflectance on a plane with whole-tract population columns"
      : "Orbitable columns of real satellite measurements",
  );
}
function charts() {
  const values = profile.rows
    .map((p) => p[profile.metric])
    .filter(Number.isFinite);
  if (!values.length) {
    svg(
      '<text x="30" y="80">No valid values for this measurement.</text>',
      "No valid data",
    );
    return;
  }
  const lo = Math.min(...values),
    hi = Math.max(...values),
    bins = Array(20).fill(0);
  values.forEach(
    (v) => bins[Math.min(19, Math.floor(((v - lo) / (hi - lo || 1)) * 20))]++,
  );
  const max = Math.max(...bins);
  let s = `<text x="55" y="35" font-size="18">${esc(METRICS[profile.metric].label)} · selected sample distribution</text>`;
  bins.forEach(
    (n, i) =>
      (s += `<rect x="${55 + i * 24}" y="${285 - (n / max) * 210}" width="22" height="${(n / max) * 210}" fill="#216e5a"><title>${n} samples</title></rect>`),
  );
  s += `<text x="55" y="310" font-size="13">${fmt(lo)} → ${fmt(hi)} ${METRICS[profile.metric].units} · vertical axis: sample count (max ${max})</text><text x="55" y="355" font-size="18">NDVI and land surface temperature · paired observations</text>`;
  const pairs = profile.rows.filter(
    (p) => Number.isFinite(p.ndvi) && Number.isFinite(p.temperature_c),
  );
  const ts = pairs.map((p) => p.temperature_c),
    t0 = Math.min(...ts),
    t1 = Math.max(...ts);
  for (const p of pairs)
    s += `<circle cx="${55 + ((p.ndvi + 1) / 2) * 760}" cy="${535 - ((p.temperature_c - t0) / (t1 - t0 || 1)) * 150}" r="2" opacity=".3" fill="#146a59"/>`;
  s += `<path d="M55,375V535H830" fill="none" stroke="#163d42"/><text x="55" y="565" font-size="13">NDVI −1 → +1 · vertical: ${fmt(t0)} → ${fmt(t1)} °C (surface) · association does not establish causation</text>`;
  svg(
    s,
    "Measurement histogram and NDVI versus surface-temperature scatterplot",
  );
}
function render() {
  if (!profile) return;
  needsData.forEach(id => $("#" + id).disabled = false);
  ["orbit-left", "orbit-right"].forEach(id => $("#" + id).classList.toggle("hidden", !["3d", "scene"].includes(view)));
  const m = METRICS[profile.metric],
    pop = profile.population;
  const stats = [
    ["Selected sample mean", `${fmt(profile.mean)} ${m.units}`, m.label],
    [
      "Valid selected samples",
      `${fmt(profile.valid_fraction * 100, 1)}%`,
      `${profile.valid_samples} / ${profile.selected_samples} systematic samples`,
    ],
    [
      "Population of intersecting tracts",
      fmt(pop.full_tract_population, 0),
      `${pop.intersecting_tracts} whole tracts · 2020`,
    ],
    [
      "Uniform-area bbox estimate",
      fmt(pop.uniform_area_estimate, 0),
      "Estimated people · strong uniformity assumption",
    ],
    [
      "Satellite acquisition",
      pkg.manifest.satellite_datetime.slice(0, 10),
      pkg.manifest.scene_id,
    ],
    [
      "Population reference",
      pkg.manifest.population_date,
      "Usual residence · a different date",
    ],
  ];
  $("#stats").innerHTML = stats
    .map(
      ([a, b, c]) =>
        `<div class="stat"><span>${esc(a)}</span><strong>${esc(b)}</strong><span>${esc(c)}</span></div>`,
    )
    .join("");
  document
    .querySelectorAll("[data-view]")
    .forEach((a) =>
      a.setAttribute(
        "aria-current",
        a.dataset.view === view ? "page" : "false",
      ),
    );
  const titles = {
    profile: "Study-area profile",
    "2d": "Read the landscape",
    "3d": "Measurements in three dimensions",
    scene: "A georeferenced evidence scene",
    charts: "Distributions and relationships",
    lab: "One Health evidence lab",
  };
  $("#view-title").textContent = titles[view] || titles.profile;
  $("#view-copy").textContent = {
    profile:
      "A reproducible subset of satellite samples and 2020 Census tract polygons. Every view and export uses the bounds shown above.",
    "2d": "Display tiles show sampling spacing. Each color is one actual nearest-native-pixel sample; gaps are unavailable values. Tract boundaries have no implied epidemiological meaning.",
    "3d": "Column heights encode the selected measurement, normalized within this profile. Drag to rotate. This is not an elevation model.",
    scene:
      "Actual red/green/blue surface reflectance is displayed on a geographic plane with fixed linear contrast (0–0.35). Gold columns encode square root of whole-tract 2020 population; their locations are graphical anchors derived from clipped boundaries, not population locations.",
    charts:
      "Sample distributions are sensitive to acquisition date, cloud masking and systematic spacing. The scatterplot is descriptive; pixels are spatially dependent.",
    lab: "Change the study bounds or measurement to inspect evidence sensitivity. No intervention effects or health outcomes are simulated. Write a question, identify missing evidence, and decide which additional measurements would be needed.",
  }[view];
  $("#view-help").textContent = ["3d", "scene"].includes(view)
    ? "Drag horizontally to orbit and vertically to adjust tilt. The 2D map and table provide the same observations without 3D interaction."
    : "On the map, drag a rectangle to select smaller study bounds. Keyboard users can enter all four coordinates in Study bounds.";
  if (view === "charts") charts();
  else if (view === "3d" || view === "scene") three(view === "scene");
  else map();
  $("#legend").classList.toggle(
    "hidden",
    view === "scene" || view === "charts",
  );
  $("#legend-units").textContent =
    m.label + " · " + m.units + " · color limits " +
    fmt(m.domain?.[0] ?? profile.p10) + " to " + fmt(m.domain?.[1] ?? profile.p90) +
    (m.domain ? "" : " (sample p10–p90; tails clipped for color only)");
  $("#profile-details").innerHTML = ["profile", "lab"].includes(view)
    ? `<div class="profile-list"><p><strong>Observation support:</strong> ${esc(pkg.manifest.sampling)} QA: ${esc(pkg.manifest.qa)}</p><p><strong>Population interpretation:</strong> ${esc(pkg.manifest.population_method)}</p><p><strong>Evidence questions:</strong> What do the selected samples leave out? Where would air-temperature, exposure, animal-health, water-quality, service-access and community information change your interpretation? Which dates would need to align?</p><p><a href="../../book/methods/">Methods, formulas and limitations</a> · <a href="../../lite/lab/index.html?path=10_capstone.ipynb">Build a reproducible capstone in Python</a></p></div>`
    : "";
  $("#source").textContent =
    pkg.manifest.credits.join(" · ") +
    ` · Satellite ${pkg.manifest.satellite_datetime}; population ${pkg.manifest.population_date}.`;
  table();
  $("#population-rows").innerHTML = profile.population.overlaps.map(o =>
    `<tr><td>${esc(o.geoid)}</td><td>${fmt(o.population, 0)}</td><td>${fmt(o.area_fraction, 6)}</td><td>${fmt(o.uniform_area_estimate, 2)}</td></tr>`
  ).join("");
  $("#population-caption").textContent = `Whole-tract ${pkg.manifest.population_date} counts and uniform-area estimates for bounds ${profile.bbox.join(", ")}`;
}
function table() {
  const rows = profile.rows.slice(page * 50, (page + 1) * 50);
  $("#rows").innerHTML = rows
    .map(
      (p) =>
        `<tr><td>${esc(p.id)}</td><td>${fmt(p.lon, 5)}</td><td>${fmt(p.lat, 5)}</td><td>${p.valid ? "Yes" : "No"}</td><td>${fmt(p.red, 5)}</td><td>${fmt(p.ndvi, 4)}</td><td>${fmt(p.ndwi, 4)}</td><td>${fmt(p.temperature_c, 3)}</td></tr>`,
    )
    .join("");
  $("#page").textContent =
    `${page + 1} / ${Math.ceil(profile.rows.length / 50)} · ${profile.rows.length} rows`;
  $("#previous").disabled = page === 0;
  $("#next").disabled = (page + 1) * 50 >= profile.rows.length;
  $("#table-caption").textContent =
    `${pkg.manifest.scene_id} · bounds ${profile.bbox.join(", ")}`;
}
function download(data, name, type) {
  const u = URL.createObjectURL(new Blob([data], { type })),
    a = document.createElement("a");
  a.href = u;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}
$("#apply").onclick = () => apply();
$("#reset").onclick = () => {
  if (!profile) return;
  setBounds(pkg.manifest.bbox);
  apply(pkg.manifest.bbox);
};
$("#metric").onchange = () => { if (profile) apply(profile.bbox); };
$("#tracts").onchange = () => { if (profile) render(); };
$("#previous").onclick = () => {
  if (!profile) return;
  page = Math.max(0, page - 1);
  table();
};
$("#next").onclick = () => {
  if (!profile) return;
  page = Math.min(Math.ceil(profile.rows.length / 50) - 1, page + 1);
  table();
};
$("#csv").onclick = () => {
  if (!profile) return;
  download(
    serializeCsv(profile.rows),
    "onehealth-selected-observations.csv",
    "text/csv",
  );
};
$("#json").onclick = () => {
  if (!profile) return;
  const { rows, ...summary } = profile;
  download(
    JSON.stringify(
      { schema_version: 1, summary, manifest: pkg.manifest, pixels: rows },
      null,
      2,
    ),
    "onehealth-profile.json",
    "application/json",
  );
};
$("#download").onclick = () => {
  if (profile) download(JSON.stringify(pkg), "profile-package.json", "application/json");
};
$("#package").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const token = beginOperation();
  try {
    if (f.size > 60e6) throw Error("Package exceeds 60 MB.");
    const text = await f.text();
    if (token !== generation) return;
    await acceptPackage(JSON.parse(text), undefined, token);
    if (token !== generation) return;
  } catch (e) {
    if (token !== generation) return;
    status(
      "Import failed: " + e.message + " Previous valid package retained.",
      true,
    );
  }
};
$("#live").onclick = async () => {
  const button = $("#live"), token = beginOperation();
  try {
    const b = validateBounds(bounds());
    button.disabled = true;
    status(
      "Acquiring real observations. Existing results remain the previous profile until acquisition completes.",
    );
    const { acquireLive } = await import("./live.mjs");
    if (token !== generation) return;
    const next = await acquireLive(b, (t) => { if (token === generation) $("#progress").textContent = t; });
    if (token !== generation) return;
    await acceptPackage(next, b, token);
    if (token !== generation) return;
  } catch (e) {
    if (token !== generation) return;
    status(
      "Live acquisition failed: " +
        e.message +
        " Previous valid profile retained. You can also acquire a package with Python and import it.",
      true,
    );
  } finally {
    if (token === generation) button.disabled = false;
  }
};
$("#visual").addEventListener("pointerdown", (e) => {
  if (!profile) return;
  const r = $("#visual").getBoundingClientRect();
  drag = { x: e.clientX, y: e.clientY, angle, tilt, r };
  $("#visual").setPointerCapture(e.pointerId);
});
$("#visual").addEventListener("pointermove", (e) => {
  if (!drag) return;
  if (["3d", "scene"].includes(view)) {
    angle = drag.angle + (e.clientX - drag.x) / 150;
    tilt = Math.max(
      0.15,
      Math.min(0.9, drag.tilt + (e.clientY - drag.y) / 250),
    );
    three(view === "scene");
  }
});
$("#visual").addEventListener("pointerup", (e) => {
  if (!drag || !profile) return;
  const d = drag;
  drag = null;
  if (
    ["3d", "scene", "charts"].includes(view) ||
    Math.abs(e.clientX - d.x) < 15 ||
    Math.abs(e.clientY - d.y) < 15
  )
    return;
  const b = profile.bbox,
    g = mapGeometry(),
    toGeo = (x, y) => [
      b[0] + (((x - d.r.left) / d.r.width) * 900 - g.left) / (g.cos * g.factor),
      b[3] - (((y - d.r.top) / d.r.height) * 590 - g.top) / g.factor,
    ];
  const a = toGeo(d.x, d.y),
    z = toGeo(e.clientX, e.clientY),
    next = [
      Math.max(b[0], Math.min(a[0], z[0])),
      Math.max(b[1], Math.min(a[1], z[1])),
      Math.min(b[2], Math.max(a[0], z[0])),
      Math.min(b[3], Math.max(a[1], z[1])),
    ];
  setBounds(next);
  apply(next);
});
window.oneHealth = {
  get package() {
    return pkg;
  },
  get profile() {
    return profile;
  },
  get view() { return view; },
  apply,
};

$("#orbit-left").onclick = () => {
  if (profile) {
    angle -= 0.2;
    render();
  }
};
$("#orbit-right").onclick = () => {
  if (profile) {
    angle += 0.2;
    render();
  }
};
const viewNames = new Set([...document.querySelectorAll("[data-view]")].map(a => a.dataset.view));
function navigate(next, url, push = false) {
  if (!viewNames.has(next)) return;
  const previous = view;
  view = next;
  try {
    if (profile) render();
    if (push) history.pushState({oneHealthView: view}, "", url);
  } catch (error) {
    view = previous;
    if (profile) render();
    status("View could not render: " + error.message, true);
  }
}
document.querySelectorAll("[data-view]").forEach(link => link.addEventListener("click", event => {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  navigate(link.dataset.view, link.href, true);
}));
window.addEventListener("popstate", () => navigate(location.pathname.split("/").filter(Boolean).at(-1)));
async function loadStarter() {
  const token = beginOperation();
  try {
    const response = await fetch("../../data/profile-package.json");
    if (token !== generation) return;
    if (!response.ok) throw Error(`HTTP ${response.status}`);
    const next = await response.json();
    if (token !== generation) return;
    await acceptPackage(next, undefined, token);
    if (token !== generation) return;
  } catch (error) {
    if (token !== generation) return;
    status("Snapshot unavailable: " + error.message + ". No substituted observations are shown.", true);
  }
}
void loadStarter();
