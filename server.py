"""Prophecy India — Flask API."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import util

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)


def _v(key: str, default=None):
    if request.is_json and request.json:
        return request.json.get(key, request.form.get(key, default))
    return request.form.get(key, default)


@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "app.html")


@app.route("/get_location_names", methods=["GET"])
def get_locations():
    return jsonify({"locations": util.get_location_names()})


@app.route("/cities", methods=["GET"])
def cities():
    return jsonify({"cities": util.get_cities(), "baseline": "bangalore"})


@app.route("/coords", methods=["GET"])
def coords():
    return jsonify({"coords": util.get_all_coords()})


@app.route("/areas/<path:city>", methods=["GET"])
def areas(city):
    return jsonify({"city": city, "areas": util.get_areas(city)})


@app.route("/predict_home_price", methods=["POST"])
def predict():
    sqft = float(_v("total_sqft"))
    bhk = int(_v("bhk"))
    bath = int(_v("bath"))
    city = _v("city") or "Bangalore"
    location = _v("location") or None
    sentiment = (_v("sentiment") or "neutral").lower()
    try:
        return jsonify(util.predict(city, location, sqft, bhk, bath, sentiment))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/compare_locations", methods=["POST"])
def compare():
    sqft = float(_v("total_sqft"))
    bhk = int(_v("bhk"))
    bath = int(_v("bath"))
    sentiment = (_v("sentiment") or "neutral").lower()
    return jsonify(util.compare(
        _v("city_a") or "Bangalore", _v("location_a") or None,
        _v("city_b") or "Bangalore", _v("location_b") or None,
        sqft, bhk, bath, sentiment,
    ))


@app.route("/sales_pitch", methods=["POST"])
def pitch():
    sqft = float(_v("total_sqft"))
    bhk = int(_v("bhk"))
    bath = int(_v("bath"))
    sentiment = (_v("sentiment") or "neutral").lower()
    return jsonify({
        "pitch": util.generate_sales_pitch(
            _v("city") or "Bangalore", _v("location") or None,
            sqft, bhk, bath, sentiment,
        ),
    })


if __name__ == "__main__":
    print("Starting Prophecy India Flask server…")
    util.load_saved_artifacts()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
