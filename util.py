"""
Prophecy India — utility layer.

Provides:
  * Bangalore: full one-hot LinearRegression model (R² 0.84) — exact ML inference
  * Other Indian cities: city-index inference using public median ₹/sqft benchmarks
  * Explainable feature contributions for both modes
  * Investment Score (0-10) benchmarked against city / locality medians
  * Market sentiment multiplier (bullish / neutral / bearish)
  * Deterministic AI-style sales pitch (LLM optional via OPENAI_API_KEY)
"""

from __future__ import annotations

import json
import os
import pickle
import re
from pathlib import Path
from typing import Optional

import numpy as np

BASE_DIR = Path(__file__).resolve().parent

__locations: list[str] = []
__data_columns: list[str] = []
__model = None
__stats: dict = {}
__coords: dict = {}
__cities: dict = {}
__areas: dict = {}      # { city: { area_name: { pps, coords } } }
__baseline_city: str = "bangalore"

SENTIMENT_MULTIPLIERS = {
    "bullish": 1.05,
    "neutral": 1.00,
    "bearish": 0.93,
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).lower().strip().rstrip(",."))


# ─────────────────────────────────────────────────────────────────────────────
# Artifact loading
# ─────────────────────────────────────────────────────────────────────────────
def load_saved_artifacts() -> None:
    global __data_columns, __locations, __model, __stats, __coords, __cities, __areas, __baseline_city
    print("loading saved artifacts...start")

    with open(BASE_DIR / "columns.json", "r") as f:
        __data_columns = json.load(f)["data_columns"]
        __locations = __data_columns[3:]

    with open(BASE_DIR / "banglore_home_prices_model.pickle", "rb") as f:
        __model = pickle.load(f)

    if (BASE_DIR / "locality_stats.json").exists():
        __stats = json.load(open(BASE_DIR / "locality_stats.json"))
    else:
        __stats = {"city": {}, "locations": {}}

    if (BASE_DIR / "locality_coords.json").exists():
        __coords = {
            k: v for k, v in json.load(open(BASE_DIR / "locality_coords.json")).items()
            if not k.startswith("_") and isinstance(v, list)
        }

    if (BASE_DIR / "city_index.json").exists():
        ci = json.load(open(BASE_DIR / "city_index.json"))
        __cities = ci.get("cities", {})
        __baseline_city = ci.get("_baseline_city", "bangalore")

    if (BASE_DIR / "city_areas.json").exists():
        raw = json.load(open(BASE_DIR / "city_areas.json"))
        __areas = {k: v for k, v in raw.items() if not k.startswith("_")}

    print(
        f"loading saved artifacts...done  "
        f"({len(__locations)} BLR ML localities · "
        f"{len(__cities)} cities · "
        f"{sum(len(a) for a in __areas.values())} curated areas)"
    )


def get_location_names() -> list[str]:
    return __locations


def get_cities() -> dict:
    return __cities


def get_all_coords() -> dict:
    return __coords


def get_areas(city: str) -> dict:
    """Return curated areas for a city: { name: { pps, coords } }."""
    if not city:
        return {}
    target = _norm(city)
    for k, v in __areas.items():
        if _norm(k) == target:
            return v
    return {}


def _area_lookup(city: str, area: str) -> Optional[dict]:
    """Case-insensitive area lookup within a city."""
    if not city or not area:
        return None
    areas = get_areas(city)
    target = _norm(area)
    for k, v in areas.items():
        if _norm(k) == target:
            return {"name": k, **v}
    return None


def get_coords(location: str) -> Optional[list[float]]:
    return __coords.get(_norm(location))


# ─────────────────────────────────────────────────────────────────────────────
# Bangalore inference (full ML model)
# ─────────────────────────────────────────────────────────────────────────────
def _build_blr_vector(location: str, sqft: float, bhk: int, bath: int):
    loc_key = _norm(location)
    try:
        loc_index = __data_columns.index(loc_key)
    except ValueError:
        loc_index = -1
    x = np.zeros(len(__data_columns))
    x[0] = sqft
    x[1] = bath
    x[2] = bhk
    if loc_index >= 0:
        x[loc_index] = 1
    return x, loc_index


def _predict_blr(location: str, sqft: float, bhk: int, bath: int,
                 sentiment: str = "neutral") -> float:
    x, _ = _build_blr_vector(location, sqft, bhk, bath)
    raw = float(__model.predict([x])[0])
    return round(raw * SENTIMENT_MULTIPLIERS.get(sentiment, 1.0), 2)


def _explain_blr(location: str, sqft: float, bhk: int, bath: int,
                 top_k: int = 5) -> list[dict]:
    x, loc_index = _build_blr_vector(location, sqft, bhk, bath)
    coefs = __model.coef_
    contributions = x * coefs
    labels = {
        0: f"Area: {sqft:.0f} sqft",
        1: f"{bath} bathroom(s)",
        2: f"{bhk} BHK",
    }
    items = []
    for i, c in enumerate(contributions):
        if abs(c) < 1e-6:
            continue
        label = labels.get(i, f"Locality: {__data_columns[i].title()}")
        items.append({
            "feature": label,
            "contribution_lakh": round(float(c), 2),
            "direction": "increases" if c >= 0 else "decreases",
        })
    items.sort(key=lambda d: abs(d["contribution_lakh"]), reverse=True)
    return items[:top_k]


# ─────────────────────────────────────────────────────────────────────────────
# Pan-India inference (city-index extension)
# ─────────────────────────────────────────────────────────────────────────────
def _city_lookup(city: str) -> Optional[dict]:
    if not city:
        return None
    target = _norm(city)
    for k, v in __cities.items():
        if _norm(k) == target:
            return v
    return None


def _predict_area(area_data: dict, sqft: float, bhk: int, bath: int,
                  sentiment: str = "neutral") -> tuple[float, dict]:
    """Same math as city-index but uses the area's pps."""
    base_pps = float(area_data["pps"])
    base_lakh = (base_pps * sqft) / 100000.0
    bhk_factor = 1.0 + (bhk - 2) * 0.02
    bath_factor = 1.0 + (bath - 2) * 0.015
    sentiment_factor = SENTIMENT_MULTIPLIERS.get(sentiment, 1.0)
    price = base_lakh * bhk_factor * bath_factor * sentiment_factor
    breakdown = {
        "base_lakh": round(base_lakh, 2),
        "bhk_factor": round(bhk_factor, 3),
        "bath_factor": round(bath_factor, 3),
        "sentiment_factor": round(sentiment_factor, 3),
    }
    return round(price, 2), breakdown


def _explain_area(label: str, breakdown: dict, sqft: float, bhk: int, bath: int,
                  area_pps: float) -> list[dict]:
    base = breakdown["base_lakh"]
    items = [{
        "feature": f"Base · {label} median (₹{int(area_pps):,}/sqft × {int(sqft)} sqft)",
        "contribution_lakh": base,
        "direction": "increases",
    }]
    bhk_delta = base * (breakdown["bhk_factor"] - 1.0)
    if abs(bhk_delta) > 0.01:
        items.append({
            "feature": f"{bhk} BHK adjustment",
            "contribution_lakh": round(bhk_delta, 2),
            "direction": "increases" if bhk_delta >= 0 else "decreases",
        })
    bath_delta = base * (breakdown["bath_factor"] - 1.0)
    if abs(bath_delta) > 0.01:
        items.append({
            "feature": f"{bath} bath adjustment",
            "contribution_lakh": round(bath_delta, 2),
            "direction": "increases" if bath_delta >= 0 else "decreases",
        })
    sent_delta = base * (breakdown["sentiment_factor"] - 1.0)
    if abs(sent_delta) > 0.01:
        items.append({
            "feature": f"Market sentiment ({'bullish' if sent_delta>0 else 'bearish'})",
            "contribution_lakh": round(sent_delta, 2),
            "direction": "increases" if sent_delta >= 0 else "decreases",
        })
    items.sort(key=lambda d: abs(d["contribution_lakh"]), reverse=True)
    return items


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
def predict(city: str, location: Optional[str], sqft: float, bhk: int, bath: int,
            sentiment: str = "neutral") -> dict:
    """Unified predictor — 3 modes:
       (1) BLR + ML-known locality  → full LinearRegression model
       (2) any city + curated area  → area-index inference
       (3) city only (no area)      → city-index inference
    """
    is_blr = _norm(city) == _norm(__baseline_city)
    coords = None

    # 1 — BLR + ML-known locality (best mode for BLR)
    if is_blr and location and _norm(location) in __data_columns:
        price = _predict_blr(location, sqft, bhk, bath, sentiment)
        explanation = _explain_blr(location, sqft, bhk, bath)
        coords = get_coords(location) or _area_lookup(city, location)
        if isinstance(coords, dict):
            coords = coords.get("coords")
        if not coords:
            coords = __cities.get("Bangalore", {}).get("coords")
        mode = "ml-localized"

    else:
        # 2 — Any city + curated area
        area_data = _area_lookup(city, location) if location else None
        if area_data:
            price, bd = _predict_area(area_data, sqft, bhk, bath, sentiment)
            explanation = _explain_area(
                f"{area_data['name']}, {city}", bd, sqft, bhk, bath, area_data["pps"]
            )
            coords = area_data.get("coords")
            mode = "area-index"

        # 3 — City fallback
        else:
            city_data = _city_lookup(city)
            if not city_data:
                raise ValueError(f"Unknown city: {city}")
            price, bd = _predict_area(city_data, sqft, bhk, bath, sentiment)
            explanation = _explain_area(city, bd, sqft, bhk, bath, city_data["pps"])
            coords = city_data["coords"]
            mode = "city-index"

    investment = get_investment_score(city, location, sqft, bhk, bath, sentiment, price)

    return {
        "estimated_price": price,
        "currency": "INR Lakh",
        "city": city,
        "location": location,
        "explanation": explanation,
        "investment": investment,
        "coords": coords,
        "sentiment": sentiment,
        "mode": mode,
    }


def get_investment_score(city: str, location: Optional[str], sqft: float, bhk: int,
                         bath: int, sentiment: str, predicted_price: float) -> dict:
    predicted_pps = (predicted_price * 100000.0) / max(sqft, 1.0)
    benchmark = None
    source = "city"
    sample = 0

    # BLR + locality with empirical stats from training data
    if _norm(city) == _norm(__baseline_city) and location:
        loc_stats = __stats.get("locations", {}).get(_norm(location))
        if loc_stats:
            benchmark = loc_stats.get("median_pps")
            source = "BLR locality (empirical)"
            sample = loc_stats.get("count", 0)

    # Any city + curated area
    if benchmark is None and location:
        ad = _area_lookup(city, location)
        if ad:
            benchmark = float(ad["pps"])
            source = f"{ad['name']} curated"

    # City fallback
    if benchmark is None:
        cd = _city_lookup(city) or {}
        benchmark = float(cd.get("pps", predicted_pps))
        source = f"{city} median"

    discount_pct = (benchmark - predicted_pps) / max(benchmark, 1.0) * 100.0
    score = max(0.0, min(10.0, 5.0 + (discount_pct / 30.0) * 5.0))
    if score >= 7.5: verdict = "Strong Buy"
    elif score >= 6.0: verdict = "Buy"
    elif score >= 4.5: verdict = "Hold"
    else: verdict = "Overpriced"

    return {
        "score": round(score, 1),
        "verdict": verdict,
        "predicted_price_per_sqft": round(predicted_pps, 2),
        "benchmark_price_per_sqft": round(float(benchmark), 2),
        "discount_vs_market_pct": round(discount_pct, 1),
        "benchmark_source": source,
        "sample_size": sample,
    }


def compare(
    city_a: str, loc_a: Optional[str],
    city_b: str, loc_b: Optional[str],
    sqft: float, bhk: int, bath: int, sentiment: str = "neutral",
) -> dict:
    a = predict(city_a, loc_a, sqft, bhk, bath, sentiment)
    b = predict(city_b, loc_b, sqft, bhk, bath, sentiment)
    cheaper = a if a["estimated_price"] <= b["estimated_price"] else b
    pricier = b if cheaper is a else a
    delta = round(pricier["estimated_price"] - cheaper["estimated_price"], 2)
    delta_pct = round(delta / max(cheaper["estimated_price"], 1e-6) * 100.0, 1)
    a_pps = a["investment"]["predicted_price_per_sqft"]
    b_pps = b["investment"]["predicted_price_per_sqft"]
    better = a if a_pps <= b_pps else b
    return {
        "a": a, "b": b,
        "summary": {
            "cheaper": (cheaper["location"] or cheaper["city"]),
            "pricier": (pricier["location"] or pricier["city"]),
            "delta_lakh": delta,
            "delta_pct": delta_pct,
            "better_value_per_sqft": (better["location"] or better["city"]),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI Sales Pitch
# ─────────────────────────────────────────────────────────────────────────────
def generate_sales_pitch(city: str, location: Optional[str], sqft: float,
                         bhk: int, bath: int, sentiment: str = "neutral") -> str:
    p = predict(city, location, sqft, bhk, bath, sentiment)
    inv = p["investment"]
    where = location.title() if location else city

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        prompt = (
            f"Write a 2-3 sentence confident, data-driven real estate pitch for a {bhk} BHK, "
            f"{int(sqft)} sqft property in {where}, India. "
            f"Predicted price ₹{p['estimated_price']} lakh, verdict: {inv['verdict']}, "
            f"{inv['discount_vs_market_pct']:+.1f}% vs market median. No fluff."
        )
        try:
            return _openai_pitch(prompt, api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"OpenAI pitch failed → template fallback: {exc}")

    blurb = {
        "Strong Buy": "a standout investment opportunity",
        "Buy": "a solid, well-priced pick",
        "Hold": "fairly valued for the area",
        "Overpriced": "carrying a premium that buyers should justify carefully",
    }[inv["verdict"]]
    direction = "below" if inv["discount_vs_market_pct"] >= 0 else "above"
    return (
        f"A {bhk} BHK home spread across {int(sqft)} sqft in {where} is {blurb}. "
        f"At an estimated ₹{p['estimated_price']} lakh, it sits "
        f"{abs(inv['discount_vs_market_pct']):.1f}% {direction} the area's median (₹{inv['benchmark_price_per_sqft']:.0f}/sqft) — "
        f"earning a Prophecy Investment Score of {inv['score']}/10."
    )


def _openai_pitch(prompt: str, api_key: str) -> str:
    import urllib.request
    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120,
        "temperature": 0.6,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    load_saved_artifacts()
    print(predict("Bangalore", "Whitefield", 1200, 2, 2))
    print(predict("Mumbai", None, 1200, 2, 2))
    print(predict("Jaipur", None, 1500, 3, 3, sentiment="bullish"))
    print(compare("Mumbai", None, "Bangalore", "Whitefield", 1200, 2, 2))
