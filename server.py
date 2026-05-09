"""
Prophecy Bangalore — Flask API.

Endpoints:
  GET  /                       → serve the SPA (app.html)
  GET  /get_location_names     → list of locations the model knows
  POST /predict_home_price     → price + explanation + investment score
  POST /compare_locations      → side-by-side comparison
  POST /sales_pitch            → AI-generated property pitch
  GET  /coords                 → bulk locality coordinates for the map
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import util

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)


def _form(key: str, default=None):
    return request.form.get(key, request.json.get(key, default) if request.is_json else default)


@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "app.html")


@app.route("/get_location_names", methods=["GET"])
def get_location_names():
    return jsonify({"locations": util.get_location_names()})


@app.route("/coords", methods=["GET"])
def coords():
    return jsonify({"coords": util.get_all_coords()})


@app.route("/predict_home_price", methods=["POST"])
def predict_home_price():
    sqft = float(_form("total_sqft"))
    location = _form("location")
    bhk = int(_form("bhk"))
    bath = int(_form("bath"))
    sentiment = (_form("sentiment") or "neutral").lower()

    price = util.get_estimated_price(location, sqft, bhk, bath, sentiment)
    explanation = util.explain_prediction(location, sqft, bhk, bath)
    investment = util.get_investment_score(location, sqft, bhk, bath, sentiment)
    coords = util.get_coords(location)
    return jsonify({
        "estimated_price": price,
        "currency": "INR Lakh",
        "explanation": explanation,
        "investment": investment,
        "coords": coords,
        "sentiment": sentiment,
    })


@app.route("/compare_locations", methods=["POST"])
def compare_locations():
    sqft = float(_form("total_sqft"))
    bhk = int(_form("bhk"))
    bath = int(_form("bath"))
    sentiment = (_form("sentiment") or "neutral").lower()
    return jsonify(util.compare_locations(
        _form("location_a"), _form("location_b"), sqft, bhk, bath, sentiment,
    ))


@app.route("/sales_pitch", methods=["POST"])
def sales_pitch():
    sqft = float(_form("total_sqft"))
    bhk = int(_form("bhk"))
    bath = int(_form("bath"))
    sentiment = (_form("sentiment") or "neutral").lower()
    pitch = util.generate_sales_pitch(_form("location"), sqft, bhk, bath, sentiment)
    return jsonify({"pitch": pitch})


if __name__ == "__main__":
    print("Starting Prophecy Bangalore Flask server…")
    util.load_saved_artifacts()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
