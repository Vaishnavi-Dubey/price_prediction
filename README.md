# 🚀 Bangalore House Price Prediction

<div align="center">

[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Stars](https://img.shields.io/github/stars/Vaishnavi-Dubey/price_prediction.svg?style=for-the-badge)](https://github.com/Vaishnavi-Dubey/price_prediction/stargazers)

![Python](https://img.shields.io/badge/Python-14354C?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)

</div>

> A complete **end-to-end Machine Learning project** predicting housing prices in Bangalore, India — featuring a comprehensive data science pipeline (13,000+ entries), trained ML models, a Flask prediction API, and a functional web frontend for instant price estimates.

---

## ✨ Key Features

- 📊 **Comprehensive Data Pipeline** — Full EDA, cleaning, and feature engineering on 13,000+ property records
- 🧹 **Advanced Data Cleaning** — Handles missing values, inconsistent formats, and noisy data
- 🔬 **Feature Engineering** — Engineered `price_per_sqft`, simplified `total_sqft`, and location grouping
- 📉 **Outlier Removal** — Domain-knowledge-driven removal using business logic + statistical methods
- 🤖 **Model Comparison** — Linear Regression vs Lasso Regression vs Decision Tree with cross-validation
- 🔍 **Hyperparameter Tuning** — GridSearchCV for optimal model selection
- 🌐 **Web Application** — Flask API + HTML/CSS/JS frontend for real-time price predictions
- 📦 **Model Serialization** — Trained model exported as pickle for production deployment

---

## 🧠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Data Science** | Python, Pandas, NumPy, Matplotlib |
| **Machine Learning** | Scikit-learn (Linear Regression, Lasso, Decision Tree, GridSearchCV) |
| **Model Tuning** | K-Fold Cross Validation, GridSearchCV |
| **Backend API** | Flask |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Serialization** | Pickle (model), JSON (columns) |

---

## 🏗️ Architecture / How It Works

```
┌─────────────────────────────────────────────────────────────┐
│              Data Science Pipeline (Jupyter)                │
│                                                             │
│  Raw Data (13K+ rows)                                       │
│       ↓                                                     │
│  Data Cleaning → Feature Engineering → Outlier Removal      │
│       ↓                                                     │
│  Dimensionality Reduction (location grouping)               │
│       ↓                                                     │
│  Model Training (Linear Reg, Lasso, Decision Tree)          │
│       ↓                                                     │
│  GridSearchCV → Best Model → Export (pickle + JSON)         │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask API (server.py + util.py)                │
│  Loads pickle model → Accepts HTTP requests → Returns price │
└──────────────────┬──────────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Web Frontend (app.html + app.js + app.css)     │
│  User inputs: Area (sqft), BHK, Bathrooms, Location        │
│  → API call → Instant price estimate displayed              │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Installation & Setup

```bash
# Clone the repository
git clone https://github.com/Vaishnavi-Dubey/price_prediction.git
cd price_prediction

# Install dependencies
pip install flask numpy pandas scikit-learn matplotlib jupyter
```

---

## ▶️ Usage

### 1. Explore the Data Science Pipeline (Optional)
```bash
jupyter notebook price-prediction.ipynb
```

### 2. Start the Prediction Server
```bash
python server.py
# Server starts at http://127.0.0.1:5000/
```

### 3. Use the Web Interface
Open `app.html` in any browser → Enter house details → Click **"Estimate Price"**

---

## 📂 Project Structure

```
price_prediction/
├── price-prediction.ipynb             # Full data science pipeline
├── server.py                          # Flask API server
├── util.py                            # Model loading & prediction logic
├── banglore_home_prices_model.pickle  # Trained ML model
├── columns.json                       # Feature columns for one-hot encoding
├── bhp.csv                            # Processed dataset
├── Bengaluru_House_Data.csv.xls       # Raw source dataset (13K+ entries)
├── app.html                           # Web frontend — user interface
├── app.js                             # Frontend JS — API integration
└── app.css                            # Frontend styles
```

---

## 📸 Screenshots / Demo

> Screenshots of the web interface and Jupyter visualizations coming soon!

---

## 📈 Impact / Learning / Highlights

- 📊 **13,000+ Data Points** — Real-world Bangalore housing data, not synthetic
- 🎯 **Location is King** — Analysis proved location as the #1 price predictor
- 📉 **Outlier Impact** — Smart outlier removal significantly improved R² scores
- 🔬 **Model Selection** — Systematic comparison showed Linear Regression outperforms Decision Tree on this dataset
- 🌐 **Full Deployment** — Model trained in Jupyter, served via Flask, consumed by web frontend
- 💡 **Feature Engineering** — `price_per_sqft` + location grouping dramatically improved model accuracy

---

## 🤝 Contributing

Contributions are welcome! Potential improvements:
- Add more regression models (XGBoost, Random Forest)
- Enhance the web frontend with interactive maps
- Add confidence intervals to predictions

---

## 📜 License

This project is licensed under the **MIT License**.

---

<p align="center">
  <b>Empowering data-driven real estate decisions</b><br>
  <b>Built by <a href="https://github.com/Vaishnavi-Dubey">Vaishnavi Dubey</a></b>
</p>
