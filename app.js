/* ============================================================
   Prophecy India — frontend logic
   - GSAP + ScrollTrigger for choreography
   - IntersectionObserver fallbacks for reduced-motion
   - Magnetic cursor on CTAs
   - Hero word-by-word reveal, blueprint draw-on, scroll-linked stats
   ============================================================ */
const API = (window.location.port && window.location.port !== "")
  ? "" // same origin — Flask serves us
  : "http://127.0.0.1:5000";

const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const state = {
  bhk: 2, bath: 2, sentiment: "neutral",
  cities: {},      // pan-India map
  blrLocs: [],
  coords: {},      // BLR locality coords
  map: null,
  markers: { a: null, b: null },
  cityMarkers: {},
};

/* ─── helpers ─────────────────────────────────────────── */
const fmt = (x) => Number(x).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const cap = (s) => s.replace(/\b\w/g, (c) => c.toUpperCase());

/* ─── data load ───────────────────────────────────────── */
async function loadDataCatalogues() {
  const [cR, lR, ccR] = await Promise.all([
    fetch(`${API}/cities`),
    fetch(`${API}/get_location_names`),
    fetch(`${API}/coords`),
  ]);
  state.cities = (await cR.json()).cities;
  state.blrLocs = (await lR.json()).locations;
  state.coords = (await ccR.json()).coords;

  // City selectors (sort: Bangalore first, then alphabetical)
  const cityKeys = Object.keys(state.cities).sort((a, b) =>
    a === "Bangalore" ? -1 : b === "Bangalore" ? 1 : a.localeCompare(b)
  );
  const cityHtml = cityKeys.map((c) =>
    `<option value="${c}">${c} · ₹${fmt(state.cities[c].pps)}/sqft</option>`
  ).join("");
  $("#uiCity").innerHTML = cityHtml;
  $("#uiCityB").innerHTML = cityHtml;
  $("#uiCityB").value = "Mumbai";

  // Ticker
  const tick = $("#ticker");
  const tickItems = cityKeys.map((c) => `<span>${c} <b>₹${fmt(state.cities[c].pps)}</b></span>`).join("");
  tick.innerHTML = tickItems + tickItems;
}

async function populateAreaDropdowns() {
  await Promise.all([
    loadAreasFor("Bangalore", "#uiLocations", "#hintA", false),
    loadAreasFor("Mumbai",    "#uiLocationsB", "#hintB", true),
  ]);
}

/* ─── Areas: every city now has its own dropdown ──────── */
async function loadAreasFor(city, selectSel, hintSel, optional) {
  const sel = $(selectSel);
  const hint = hintSel ? $(hintSel) : null;
  let opts = [];
  try {
    const r = await fetch(`${API}/areas/${encodeURIComponent(city)}`);
    const d = await r.json();
    opts = Object.keys(d.areas || {});
  } catch (e) { opts = []; }

  // For Bangalore, also offer the full ML-trained locality catalogue
  if (city === "Bangalore" && state.blrLocs.length) {
    const seen = new Set(opts.map((o) => o.toLowerCase()));
    state.blrLocs.forEach((l) => {
      const pretty = cap(l);
      if (!seen.has(l.toLowerCase())) opts.push(pretty);
    });
  }

  opts.sort((a, b) => a.localeCompare(b));
  const optHtml = opts.map((o) => `<option>${o}</option>`).join("");
  sel.innerHTML = (optional ? `<option value="">— optional —</option>` : "") + optHtml;
  if (!optional && opts.length) {
    // pick a popular default per city
    const popular = { Bangalore: "Whitefield", Mumbai: "Bandra West", Delhi: "Saket",
      Pune: "Hinjewadi", Hyderabad: "Gachibowli", Chennai: "Adyar", Kolkata: "Salt Lake" };
    sel.value = (popular[city] && opts.includes(popular[city])) ? popular[city] : opts[0];
  }
  if (hint) hint.textContent = `${opts.length} ${city} ${opts.length === 1 ? "area" : "areas"}`;

  // Repaint area pins on map for this city (slot a only when not optional)
  if (!optional) plotAreaPins(city);
}

/* ─── Inputs wiring ───────────────────────────────────── */
function wireSegments() {
  $$('.seg').forEach((seg) => {
    const key = seg.dataset.name;
    seg.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const v = btn.dataset.value;
      state[key] = isNaN(+v) ? v : +v;
    });
  });
}

/* ─── Predict ─────────────────────────────────────────── */
async function runPredict() {
  const city = $("#uiCity").value;
  const body = new URLSearchParams({
    total_sqft: +$("#uiSqft").value,
    bhk: state.bhk, bath: state.bath, sentiment: state.sentiment,
    city,
    location: $("#uiLocations").value || "",
  });
  const r = await fetch(`${API}/predict_home_price`, { method: "POST", body });
  const d = await r.json();
  if (d.error) { console.error(d.error); return; }
  renderResult(d);
}

function renderResult(d) {
  // Mode badge + meta
  $("#resultBadge").textContent = d.mode === "ml-localized" ? "ml · localized" : "city-index";
  $("#resultMeta").textContent = `${d.location || d.city} · ${state.bhk} BHK · ${$('#uiSqft').value} sqft`;

  // Price typography (animate count)
  animateNumber($("#priceValue"), parseFloat($("#priceValue").dataset.last || 0), d.estimated_price, 900, 2);
  $("#priceValue").dataset.last = d.estimated_price;
  const inv = d.investment;
  $("#ppsLine").textContent = `~ ₹${fmt(inv.predicted_price_per_sqft)} per sqft · ${d.sentiment} market · ${d.mode}`;

  // Score arc
  const dial = $("#scoreArc");
  const offset = 263.9 * (1 - inv.score / 10);
  gsap.to(dial, { strokeDashoffset: offset, duration: 1.0, ease: "power3.out" });
  animateNumber($("#scoreValue"), parseFloat($("#scoreValue").dataset.last || 0), inv.score, 700, 1);
  $("#scoreValue").dataset.last = inv.score;
  const v = $("#scoreVerdict");
  v.textContent = inv.verdict;
  v.className = "verdict " + (inv.score >= 7.5 ? "good" : inv.score >= 4.5 ? "warn" : "bad");
  $("#scoreDiscount").textContent =
    `${inv.discount_vs_market_pct >= 0 ? "−" : "+"}${Math.abs(inv.discount_vs_market_pct)}% vs market median`;
  $("#scoreBenchmark").textContent =
    `benchmark: ₹${fmt(inv.benchmark_price_per_sqft)}/sqft · source: ${inv.benchmark_source}`;

  // Explainability bars
  const list = $("#explainList");
  list.innerHTML = "";
  const max = Math.max(...d.explanation.map((e) => Math.abs(e.contribution_lakh)), 1);
  d.explanation.forEach((e, i) => {
    const pct = (Math.abs(e.contribution_lakh) / max) * 100;
    const sign = e.contribution_lakh >= 0 ? "pos" : "neg";
    const sym = e.contribution_lakh >= 0 ? "+" : "−";
    const row = document.createElement("div");
    row.className = "explain-row";
    row.innerHTML = `
      <div>
        <div class="label">${e.feature}</div>
        <div class="bar"><div class="${sign}" style="--w:${pct}%"></div></div>
      </div>
      <div class="value ${sign}">${sym}₹${fmt(Math.abs(e.contribution_lakh))}L</div>`;
    list.appendChild(row);
    // animate bar
    const bar = row.querySelector('.bar > div');
    gsap.to(bar, {
      scaleX: pct / 100,
      duration: 0.8,
      delay: 0.05 + i * 0.07,
      ease: "power3.out",
    });
  });

  // Map marker
  if (d.coords && state.map) {
    placeMarker("a", d.coords, `${d.location || d.city}<br/><b>₹${fmt(d.estimated_price)}L</b>`);
    state.map.flyTo(d.coords, d.location ? 13 : 11, { duration: 1.2 });
  }
}

function animateNumber(el, from, to, dur, decimals = 0) {
  if (reduce) { el.textContent = (+to).toFixed(decimals); return; }
  const obj = { v: from };
  gsap.to(obj, {
    v: to, duration: dur / 1000, ease: "power3.out",
    onUpdate: () => {
      el.textContent = obj.v.toLocaleString("en-IN", {
        minimumFractionDigits: decimals, maximumFractionDigits: decimals,
      });
    },
  });
}

/* ─── Compare ─────────────────────────────────────────── */
async function runCompare() {
  const cityA = $("#uiCity").value;
  const cityB = $("#uiCityB").value;
  const body = new URLSearchParams({
    total_sqft: +$("#uiSqft").value,
    bhk: state.bhk, bath: state.bath, sentiment: state.sentiment,
    city_a: cityA, location_a: $("#uiLocations").value || "",
    city_b: cityB, location_b: $("#uiLocationsB").value || "",
  });
  const r = await fetch(`${API}/compare_locations`, { method: "POST", body });
  const d = await r.json();
  $("#compareStage").hidden = false;
  $("#cmpAName").textContent = d.a.location || d.a.city;
  $("#cmpBName").textContent = d.b.location || d.b.city;
  $("#cmpAPrice").textContent = `₹${fmt(d.a.estimated_price)} L`;
  $("#cmpBPrice").textContent = `₹${fmt(d.b.estimated_price)} L`;
  $("#cmpAPps").textContent = `₹${fmt(d.a.investment.predicted_price_per_sqft)}/sqft · score ${d.a.investment.score}/10`;
  $("#cmpBPps").textContent = `₹${fmt(d.b.investment.predicted_price_per_sqft)}/sqft · score ${d.b.investment.score}/10`;
  $("#cmpDelta").textContent = `Δ ₹${fmt(d.summary.delta_lakh)}L`;
  $("#cmpSummary").textContent =
    `${d.summary.cheaper} is cheaper by ₹${fmt(d.summary.delta_lakh)}L (${d.summary.delta_pct}%). ` +
    `Better value per sqft: ${d.summary.better_value_per_sqft}.`;

  if (d.b.coords && state.map) placeMarker("b", d.b.coords, `${d.b.location || d.b.city}<br/><b>₹${fmt(d.b.estimated_price)}L</b>`);

  gsap.fromTo(".compare-side.a", { x: -40, opacity: 0 }, { x: 0, opacity: 1, duration: 0.6, ease: "power3.out" });
  gsap.fromTo(".compare-side.b", { x: 40, opacity: 0 },  { x: 0, opacity: 1, duration: 0.6, ease: "power3.out", delay: 0.08 });
}

/* ─── Pitch ───────────────────────────────────────────── */
async function runPitch() {
  const city = $("#uiCity").value;
  const body = new URLSearchParams({
    total_sqft: +$("#uiSqft").value,
    bhk: state.bhk, bath: state.bath, sentiment: state.sentiment,
    city,
    location: $("#uiLocations").value || "",
  });
  $("#pitchBlock").hidden = false;
  $("#pitchText").textContent = "Composing…";
  const r = await fetch(`${API}/sales_pitch`, { method: "POST", body });
  const d = await r.json();
  $("#pitchText").textContent = "";
  // typewriter-ish reveal
  const text = d.pitch;
  let i = 0;
  const tick = () => {
    if (i >= text.length) return;
    $("#pitchText").textContent += text[i++];
    setTimeout(tick, 12);
  };
  tick();
}

/* ─── Map ─────────────────────────────────────────────── */
function initMap() {
  state.map = L.map("mapEl", { zoomControl: true, attributionControl: false })
    .setView([22.0, 79.0], 5);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19 })
    .addTo(state.map);

  // City pulse pins
  Object.entries(state.cities).forEach(([name, c]) => {
    const el = document.createElement("div");
    el.className = "pulse-pin";
    const icon = L.divIcon({ html: el.outerHTML, className: '', iconSize: [12, 12] });
    const m = L.marker(c.coords, { icon })
      .addTo(state.map)
      .bindPopup(`<b>${name}</b><br/>₹${fmt(c.pps)}/sqft · ${c.tier}`);
    m.on("click", () => {
      $("#uiCity").value = name;
      loadAreasFor(name, "#uiLocations", "#hintA", false).then(runPredict);
      document.getElementById("predict").scrollIntoView({ behavior: "smooth" });
    });
    state.cityMarkers[name] = m;
  });
}

/* ─── Area pins (per-city overlay) ────────────────────── */
function plotAreaPins(city) {
  if (!state.map) return;
  // Clear previous area overlay
  if (state._areaLayer) { state.map.removeLayer(state._areaLayer); state._areaLayer = null; }
  fetch(`${API}/areas/${encodeURIComponent(city)}`).then((r) => r.json()).then((d) => {
    const areas = d.areas || {};
    const grp = L.layerGroup();
    Object.entries(areas).forEach(([name, a]) => {
      if (!a.coords) return;
      const dot = L.circleMarker(a.coords, {
        radius: 5, color: "#7d8aa3", weight: 1.5, fillColor: "#7d8aa3", fillOpacity: 0.45,
      }).bindTooltip(`${name} · ₹${fmt(a.pps)}/sqft`, { direction: "top", offset: [0, -4] });
      dot.on("click", () => {
        $("#uiLocations").value = name;
        runPredict();
      });
      grp.addLayer(dot);
    });
    grp.addTo(state.map);
    state._areaLayer = grp;
  }).catch(() => {});
}

function placeMarker(slot, coords, label) {
  if (!state.map || !coords) return;
  if (state.markers[slot]) state.map.removeLayer(state.markers[slot]);
  const color = slot === "a" ? "#d97757" : "#f5ede0";
  state.markers[slot] = L.circleMarker(coords, {
    radius: 12, color, weight: 3, fillColor: color, fillOpacity: 0.25,
  }).addTo(state.map).bindPopup(label);
}

/* ─── Magnetic CTA ────────────────────────────────────── */
function wireMagnetic() {
  if (reduce) return;
  $$('[data-magnet]').forEach((btn) => {
    let raf;
    btn.addEventListener("mousemove", (e) => {
      const r = btn.getBoundingClientRect();
      const dx = (e.clientX - (r.left + r.width / 2)) * 0.25;
      const dy = (e.clientY - (r.top + r.height / 2)) * 0.4;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        gsap.to(btn, { x: dx, y: dy, scale: 1.04, duration: 0.4, ease: "power3.out" });
      });
    });
    btn.addEventListener("mouseleave", () => {
      gsap.to(btn, { x: 0, y: 0, scale: 1, duration: 0.6, ease: "elastic.out(1, 0.5)" });
    });
  });
}

/* ─── Scroll choreography (GSAP) ──────────────────────── */
function initScrollAnims() {
  if (reduce) {
    // Just show everything
    gsap.set(".hero-title .word", { y: 0 });
    gsap.set([".hero-meta", ".hero-sub", ".hero-actions", ".hero-scroll"], { opacity: 1 });
    gsap.set(".reveal", { opacity: 1, y: 0 });
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  // 1 — Hero entrance: word-by-word
  const tl = gsap.timeline({ defaults: { ease: "expo.out" } });
  tl.to(".hero-title .word", {
      y: 0, duration: 1.0, stagger: 0.07,
    })
    .to(".hero-meta",     { opacity: 1, duration: 0.6 }, 0.2)
    .to(".hero-sub",      { opacity: 1, y: 0, duration: 0.7 }, 0.6)
    .to(".hero-actions",  { opacity: 1, y: 0, duration: 0.7 }, 0.8)
    .to(".hero-scroll",   { opacity: 1, duration: 0.6 }, 1.2);

  // Blueprint draw-on
  gsap.to(".bp-line", {
    strokeDashoffset: 0, duration: 2.4,
    ease: "power2.inOut", delay: 0.2,
  });
  gsap.to(".bp-anno text", {
    opacity: 0.7, duration: 0.5, stagger: 0.15, delay: 1.4,
  });

  // 2 — Reveal blocks on scroll
  $$('.reveal').forEach((el) => {
    gsap.to(el, {
      opacity: 1, y: 0, duration: 0.9, ease: "expo.out",
      scrollTrigger: { trigger: el, start: "top 85%", toggleActions: "play none none none" },
    });
  });

  // 3 — Section title parallax (scroll-linked)
  $$('.section-title.big').forEach((el) => {
    gsap.fromTo(el, { y: 60 }, {
      y: -30, ease: "none",
      scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: 0.6 },
    });
  });

  // 4 — Animated counters (data section)
  $$('.stat-value').forEach((el) => {
    const target = parseFloat(el.dataset.count);
    const decimals = parseInt(el.dataset.decimals || "0", 10);
    ScrollTrigger.create({
      trigger: el, start: "top 80%", once: true,
      onEnter: () => {
        const obj = { v: 0 };
        gsap.to(obj, {
          v: target, duration: 1.6, ease: "power3.out",
          onUpdate: () => {
            el.textContent = obj.v.toLocaleString("en-IN", {
              minimumFractionDigits: decimals, maximumFractionDigits: decimals,
            });
          },
        });
      },
    });
  });

  // 5 — Pipeline stagger
  ScrollTrigger.create({
    trigger: ".pipeline", start: "top 80%", once: true,
    onEnter: () => {
      gsap.fromTo(".pipe-step, .pipe-arrow",
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.7, ease: "expo.out", stagger: 0.08 });
    },
  });
}

/* ─── Nav: scrolled state + active link indicator ────── */
function initNav() {
  const nav = $("#nav");
  const indicator = $(".nav-indicator");
  const links = $$(".nav-links a[data-link]");

  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 30);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  // Hover indicator
  const moveIndicator = (el) => {
    if (!el) { indicator.style.opacity = 0; return; }
    const r = el.getBoundingClientRect();
    const pr = el.parentElement.parentElement.getBoundingClientRect();
    indicator.style.opacity = 1;
    indicator.style.left = (r.left - pr.left + 8) + "px";
    indicator.style.width = (r.width - 16) + "px";
  };
  links.forEach((a) => a.addEventListener("mouseenter", () => moveIndicator(a)));
  $(".nav-links").addEventListener("mouseleave", () => moveIndicator(null));

  // Active section based on scroll
  const sections = links.map((a) => document.querySelector(a.getAttribute("href")));
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) {
        const i = sections.indexOf(en.target);
        if (i >= 0) moveIndicator(links[i]);
      }
    });
  }, { rootMargin: "-40% 0px -55% 0px" });
  sections.forEach((s) => s && obs.observe(s));

  // Mobile burger
  $(".nav-burger").addEventListener("click", () => nav.classList.toggle("open"));
  links.forEach((a) => a.addEventListener("click", () => nav.classList.remove("open")));
}

/* ─── Boot ────────────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", async () => {
  wireSegments();
  $("#uiCity").addEventListener("change", (e) => {
    loadAreasFor(e.target.value, "#uiLocations", "#hintA", false);
  });
  $("#uiCityB").addEventListener("change", (e) => {
    loadAreasFor(e.target.value, "#uiLocationsB", "#hintB", true);
  });
  $("#btnEstimate").addEventListener("click", runPredict);
  $("#btnPitch").addEventListener("click", runPitch);
  $("#btnCompare").addEventListener("click", runCompare);

  initNav();
  wireMagnetic();
  initScrollAnims();

  // Load city/coords/locality catalogues, init map, then populate area dropdowns
  await loadDataCatalogues();
  initMap();
  await populateAreaDropdowns();
  // first prediction
  setTimeout(runPredict, 600);
});
