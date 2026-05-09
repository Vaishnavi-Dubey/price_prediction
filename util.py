"""
Prophecy Bangalore — utility layer.

Loads the trained LinearRegression model + locality statistics and provides:
  * price prediction
  * explainable feature contributions (exact, derived from model coefficients)
  * an Investment Score (0-10) benchmarked against locality + city price/sqft
  * a market-sentiment adjustment (bullish / neutral / bearish)
  * a deterministic, template-based "AI sales pitch" (LLM-optional)
"""

from __future__ import annotations

import json
import os
import pickle
import re
from pathlib import Path
from typing import Optional

import numpy as np


def _norm(s: str) -> str:
    s = str(s).lower().strip().rstrip(",.")
    return re.sub(r"\s+", " ", s)

BASE_DIR = Path(__file__).resolve().parent

__locations: list[str] = []
__data_columns: list[str] = []
__model = None
__stats: dict = {}
__coords: dict = {}

SENTIMENT_MULTIPLIERS = {
    "bullish": 1.05,   # +5% in a hot market
    "neutral": 1.00,
    "bearish": 0.93,   # -7% in a soft market
}


# ─────────────────────────────────────────────────────────────────────────────
# Artifact loading
# ─────────────────────────────────────────────────────────────────────────────
def load_saved_artifacts() -> None:
    global __data_columns, __locations, __model, __stats, __coords
    print("loading saved artifacts...start")

    with open(BASE_DIR / "columns.json", "r") as f:
        __data_columns = json.load(f)["data_columns"]
        __locations = __data_columns[3:]

    with open(BASE_DIR / "banglore_home_prices_model.pickle", "rb") as f:
        __model = pickle.load(f)

    stats_path = BASE_DIR / "locality_stats.json"
    if stats_path.exists():
        __stats = json.load(open(stats_path))
    else:
        __stats = {"city": {}, "locations": {}}

    coords_path = BASE_DIR / "locality_coords.json"
    if coords_path.exists():
        __coords = {k: v for k, v in json.load(open(coords_path)).items()
                    if not k.startswith("_") and isinstance(v, list)}
    print(f"loading saved artifacts...done  ({len(__locations)} locations)")


def get_location_names() -> list[str]:
    return __locations


# ─────────────────────────────────────────────────────────────────────────────
# Core inference
# ─────────────────────────────────────────────────────────────────────────────
def _build_feature_vector(location: str, sqft: float, bhk: int, bath: int):
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
    return x, loc_index, loc_key


def get_estimated_price(
    location: str,
    sqft: float,
    bhk: int,
    bath: int,
    sentiment: str = "neutral",
) -> float:
    x, _, _ = _build_feature_vector(location, sqft, bhk, bath)
    raw = float(__model.predict([x])[0])
    mult = SENTIMENT_MULTIPLIERS.get(sentiment, 1.0)
    return round(raw * mult, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Explainability — exact contribution per feature for a LinearRegression model
# ─────────────────────────────────────────────────────────────────────────────
def explain_prediction(location: str, sqft: float, bhk: int, bath: int,
                       top_k: int = 5) -> list[dict]:
    """Return ranked feature contributions (in lakhs) toward the prediction."""
    x, loc_index, loc_key = _build_feature_vector(location, sqft, bhk, bath)
    coefs = __model.coef_
    contributions = x * coefs  # element-wise

    items = []
    labels = {
        0: f"Area: {sqft:.0f} sqft",
        1: f"{bath} bathroom(s)",
        2: f"{bhk} BHK",
    }
    for i, contrib in enumerate(contributions):
        if abs(contrib) < 1e-6:
            continue
        label = labels.get(i, f"Location: {__data_columns[i].title()}")
        items.append({
            "feature": label,
            "contribution_lakh": round(float(contrib), 2),
            "direction": "increases" if contrib >= 0 else "decreases",
        })

    # Always surface the location row even if it had no coefficient
    if loc_index < 0:
        items.append({
            "feature": f"Location: {location} (unseen → city average used)",
            "contribution_lakh": 0.0,
            "direction": "neutral",
        })

    items.sort(key=lambda d: abs(d["contribution_lakh"]), reverse=True)
    return items[:top_k]


# ─────────────────────────────────────────────────────────────────────────────
# Investment Score
# ─────────────────────────────────────────────────────────────────────────────
def get_investment_score(location: str, sqft: float, bhk: int, bath: int,
                         sentiment: str = "neutral") -> dict:
    """
    Score 0-10. Higher means better value-for-money relative to locality.

    Logic:
      * predicted price-per-sqft is compared to the locality's median (from data).
      * A discount → higher score; a premium → lower score.
      * Score is clipped to [0, 10] and rounded to 1 decimal.
    """
    predicted = get_estimated_price(location, sqft, bhk, bath, sentiment)
    predicted_pps = (predicted * 100000.0) / max(sqft, 1.0)  # lakh → rupees

    loc_key = _norm(location)
    loc_stats = __stats.get("locations", {}).get(loc_key)
    city = __stats.get("city", {}) or {}
    benchmark_pps = (loc_stats or {}).get("median_pps") or city.get("median_pps", predicted_pps)

    # discount % vs benchmark (positive → cheaper than market)
    discount_pct = (benchmark_pps - predicted_pps) / max(benchmark_pps, 1.0) * 100.0
    # Map discount_pct in [-30%, +30%] to score in [0, 10]
    score = 5.0 + (discount_pct / 30.0) * 5.0
    score = max(0.0, min(10.0, score))

    if score >= 7.5:
        verdict = "Strong Buy"
    elif score >= 6.0:
        verdict = "Buy"
    elif score >= 4.5:
        verdict = "Hold"
    else:
        verdict = "Overpriced"

    return {
        "score": round(score, 1),
        "verdict": verdict,
        "predicted_price_per_sqft": round(predicted_pps, 2),
        "locality_median_price_per_sqft": round(float(benchmark_pps), 2),
        "discount_vs_market_pct": round(discount_pct, 1),
        "benchmark_source": "locality" if loc_stats else "city",
        "sample_size": (loc_stats or {}).get("count", 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Geospatial helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_coords(location: str) -> Optional[list[float]]:
    return __coords.get(_norm(location))


def get_all_coords() -> dict:
    return __coords


# ─────────────────────────────────────────────────────────────────────────────
# Comparison engine
# ─────────────────────────────────────────────────────────────────────────────
def compare_locations(loc_a: str, loc_b: str, sqft: float, bhk: int, bath: int,
                      sentiment: str = "neutral") -> dict:
    a = {
        "location": loc_a,
        "estimated_price": get_estimated_price(loc_a, sqft, bhk, bath, sentiment),
        "investment": get_investment_score(loc_a, sqft, bhk, bath, sentiment),
        "coords": get_coords(loc_a),
    }
    b = {
        "location": loc_b,
        "estimated_price": get_estimated_price(loc_b, sqft, bhk, bath, sentiment),
        "investment": get_investment_score(loc_b, sqft, bhk, bath, sentiment),
        "coords": get_coords(loc_b),
    }
    cheaper = a if a["estimated_price"] <= b["estimated_price"] else b
    pricier = b if cheaper is a else a
    delta_lakh = round(pricier["estimated_price"] - cheaper["estimated_price"], 2)
    delta_pct = round(delta_lakh / max(cheaper["estimated_price"], 1e-6) * 100.0, 1)
    a_pps = a["investment"]["predicted_price_per_sqft"]
    b_pps = b["investment"]["predicted_price_per_sqft"]
    better_value = a if a_pps <= b_pps else b
    return {
        "a": a,
        "b": b,
        "summary": {
            "cheaper_location": cheaper["location"],
            "delta_lakh": delta_lakh,
            "delta_pct": delta_pct,
            "better_value_per_sqft": better_value["location"],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI Sales Pitch (template-based by default; optional OpenAI hook)
# ─────────────────────────────────────────────────────────────────────────────
def generate_sales_pitch(location: str, sqft: float, bhk: int, bath: int,
                         sentiment: str = "neutral") -> str:
    price = get_estimated_price(location, sqft, bhk, bath, sentiment)
    inv = get_investment_score(location, sqft, bhk, bath, sentiment)

    prompt = (
        f"Write a 2-3 sentence real estate sales pitch for a {bhk} BHK, "
        f"{int(sqft)} sqft, {bath}-bath property in {location}, Bangalore. "
        f"Estimated price ₹{price} lakh, market verdict: {inv['verdict']} "
        f"({inv['discount_vs_market_pct']:+.1f}% vs locality median). "
        "Tone: confident, data-driven, no fluff."
    )

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return _openai_pitch(prompt, api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"OpenAI pitch failed, falling back to template: {exc}")

    # Deterministic, offline template
    verdict_blurb = {
        "Strong Buy": "a standout investment opportunity",
        "Buy": "a solid, well-priced pick",
        "Hold": "fairly valued for the locality",
        "Overpriced": "carrying a premium that buyers should justify carefully",
    }[inv["verdict"]]
    direction = "below" if inv["discount_vs_market_pct"] >= 0 else "above"
    return (
        f"A {bhk} BHK spread across {int(sqft)} sqft in {location.title()} is "
        f"{verdict_blurb}. At an estimated ₹{price} lakh, it sits "
        f"{abs(inv['discount_vs_market_pct']):.1f}% {direction} the locality's median "
        f"price per sqft (₹{inv['locality_median_price_per_sqft']:.0f}/sqft), "
        f"giving it a Prophecy Investment Score of {inv['score']}/10."
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
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    load_saved_artifacts()
    print("locations:", len(get_location_names()))
    print("price:", get_estimated_price("1st Phase JP Nagar", 1000, 3, 3))
    print("explain:", explain_prediction("1st Phase JP Nagar", 1000, 3, 3))
    print("invest:", get_investment_score("1st Phase JP Nagar", 1000, 3, 3))
    print("compare:", compare_locations("Whitefield", "Sarjapur Road", 1200, 2, 2))
    print("pitch:", generate_sales_pitch("Hebbal", 1200, 2, 2))
