// Prophecy Bangalore — frontend logic
const API = window.location.origin.startsWith("http") && window.location.port
  ? "" // same origin (Flask serves us)
  : "http://127.0.0.1:5000";

const state = {
  bhk: 2,
  bath: 2,
  sentiment: "neutral",
  coords: {},
  map: null,
  marker: null,
  markerB: null,
};

// ── helpers ─────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);

function wireSwitch(name, key) {
  document.querySelectorAll(`[data-name="${name}"] button`).forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.parentElement.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const v = btn.dataset.value;
      state[key] = isNaN(+v) ? v : +v;
    });
  });
}

function fmtLakh(x) { return Number(x).toLocaleString("en-IN", { maximumFractionDigits: 2 }); }

// ── data load ───────────────────────────────────────────
async function loadLocations() {
  const r = await fetch(`${API}/get_location_names`);
  const { locations } = await r.json();
  const a = $("#uiLocations"); const b = $("#uiLocationsB");
  a.innerHTML = locations.map((l) => `<option>${l}</option>`).join("");
  b.innerHTML = `<option value="">— Optional —</option>` + locations.map((l) => `<option>${l}</option>`).join("");
  // sensible default
  const def = locations.find((l) => l.includes("whitefield")) || locations[0];
  a.value = def;
}

async function loadCoords() {
  const r = await fetch(`${API}/coords`);
  const { coords } = await r.json();
  state.coords = coords;
}

// ── map ─────────────────────────────────────────────────
function initMap() {
  state.map = L.map("map", { zoomControl: true }).setView([12.9716, 77.5946], 11);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap &copy; CARTO',
  }).addTo(state.map);

  // click-to-predict on the map: snap to nearest known locality
  state.map.on("click", (e) => {
    const nearest = nearestLocality(e.latlng.lat, e.latlng.lng);
    if (!nearest) return;
    $("#uiLocations").value = capitalCase(nearest);
    runEstimate();
  });
}

function nearestLocality(lat, lng) {
  let best = null, bestD = Infinity;
  for (const [k, [la, lo]] of Object.entries(state.coords)) {
    const d = (la - lat) ** 2 + (lo - lng) ** 2;
    if (d < bestD) { bestD = d; best = k; }
  }
  return best;
}

function capitalCase(s) {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

function placeMarker(coords, label, isB = false) {
  if (!coords) return;
  const key = isB ? "markerB" : "marker";
  if (state[key]) state.map.removeLayer(state[key]);
  const color = isB ? "#7c5cff" : "#00e0a4";
  state[key] = L.circleMarker(coords, {
    radius: 10, color, weight: 3, fillColor: color, fillOpacity: 0.35,
  }).addTo(state.map).bindPopup(`<b>${label}</b>`);
}

// ── render result ───────────────────────────────────────
function renderResult(data, location) {
  $("#estPrice").innerHTML = `${fmtLakh(data.estimated_price)} <span class="unit">Lakh</span>`;
  const inv = data.investment;
  $("#ppsLine").textContent = `~ ₹${fmtLakh(inv.predicted_price_per_sqft)} per sqft · ${data.sentiment} market`;

  // score
  $("#scoreCard").hidden = false;
  $("#scoreValue").textContent = inv.score;
  $("#scoreCard .score-circle").style.setProperty("--score", inv.score);
  const v = $("#scoreVerdict");
  v.textContent = `${inv.verdict} · ${inv.discount_vs_market_pct >= 0 ? "−" : "+"}${Math.abs(inv.discount_vs_market_pct)}% vs market`;
  v.className = "verdict " + (inv.score >= 7.5 ? "good" : inv.score >= 4.5 ? "warn" : "bad");

  // explanation bars
  const list = $("#explainList");
  list.innerHTML = "";
  const max = Math.max(...data.explanation.map((e) => Math.abs(e.contribution_lakh)), 1);
  for (const e of data.explanation) {
    const pct = (Math.abs(e.contribution_lakh) / max) * 100;
    const sign = e.contribution_lakh >= 0 ? "pos" : "neg";
    const sym = e.contribution_lakh >= 0 ? "+" : "−";
    list.insertAdjacentHTML("beforeend", `
      <div class="explain-row">
        <div>
          <div class="label">${e.feature}</div>
          <div class="bar"><div class="${sign}" style="width:${pct}%"></div></div>
        </div>
        <div class="value ${sign}">${sym}₹${fmtLakh(Math.abs(e.contribution_lakh))}L</div>
      </div>`);
  }

  if (data.coords) {
    placeMarker(data.coords, `${location}: ₹${fmtLakh(data.estimated_price)}L`);
    state.map.setView(data.coords, 13);
  }
}

// ── actions ─────────────────────────────────────────────
async function runEstimate() {
  const sqft = +$("#uiSqft").value;
  const location = $("#uiLocations").value;
  const locationB = $("#uiLocationsB").value;
  const body = new URLSearchParams({
    total_sqft: sqft, location, bhk: state.bhk, bath: state.bath, sentiment: state.sentiment,
  });
  const r = await fetch(`${API}/predict_home_price`, { method: "POST", body });
  const data = await r.json();
  renderResult(data, location);
  $("#pitchBlock").hidden = true;

  if (locationB) {
    runCompare(sqft, location, locationB);
  } else {
    $("#compareBox").hidden = true;
    if (state.markerB) { state.map.removeLayer(state.markerB); state.markerB = null; }
  }
}

async function runCompare(sqft, a, b) {
  const body = new URLSearchParams({
    total_sqft: sqft, location_a: a, location_b: b,
    bhk: state.bhk, bath: state.bath, sentiment: state.sentiment,
  });
  const r = await fetch(`${API}/compare_locations`, { method: "POST", body });
  const data = await r.json();
  $("#compareBox").hidden = false;
  $("#cmpA").textContent = `${data.a.location}: ₹${fmtLakh(data.a.estimated_price)}L`;
  $("#cmpB").textContent = `${data.b.location}: ₹${fmtLakh(data.b.estimated_price)}L`;
  $("#cmpSummary").textContent =
    `${data.summary.cheaper_location} is cheaper by ₹${fmtLakh(data.summary.delta_lakh)}L (${data.summary.delta_pct}%). ` +
    `Better value per sqft: ${data.summary.better_value_per_sqft}.`;
  if (data.b.coords) placeMarker(data.b.coords, `${data.b.location}: ₹${fmtLakh(data.b.estimated_price)}L`, true);
}

async function runPitch() {
  const body = new URLSearchParams({
    total_sqft: +$("#uiSqft").value,
    location: $("#uiLocations").value,
    bhk: state.bhk, bath: state.bath, sentiment: state.sentiment,
  });
  $("#pitchBlock").hidden = false;
  $("#pitchText").textContent = "Generating…";
  const r = await fetch(`${API}/sales_pitch`, { method: "POST", body });
  const data = await r.json();
  $("#pitchText").textContent = data.pitch;
}

// ── boot ────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", async () => {
  wireSwitch("uiBHK", "bhk");
  wireSwitch("uiBath", "bath");
  wireSwitch("uiSentiment", "sentiment");
  $("#btnEstimate").addEventListener("click", runEstimate);
  $("#btnPitch").addEventListener("click", runPitch);

  initMap();
  await Promise.all([loadLocations(), loadCoords()]);
  runEstimate();
});
