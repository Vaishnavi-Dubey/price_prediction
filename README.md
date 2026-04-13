# 🏠 Bangalore House Price Prediction

> A complete end-to-end Machine Learning project to predict housing prices in Bangalore, India, featuring a comprehensive data science pipeline and a functional web application.

This project covers the full lifecycle of a data science project: from data cleaning and feature engineering to model deployment via a local Flask server and a simple web frontend.

---

## ✨ Features

### 📊 Comprehensive Data Pipeline
- **Data Cleaning**: Handled missing values and inconsistent data in the original dataset of 13,000+ entries.
- **Feature Engineering**: Simplified complex features like `total_sqft` and added `price_per_sqft` for better analysis.
- **Outlier Removal**: Used domain knowledge and business logic (e.g., minimum sqft per bedroom) and standard deviations to remove data noise.
- **Dimensionality Reduction**: Grouped infrequent locations into an 'other' category to optimize one-hot encoding.

### 🤖 Machine Learning Modeling
- Trained multiple models including **Linear Regression**, **Lasso Regression**, and **Decision Tree**.
- Used **K-Fold Cross Validation** and **GridSearchCV** for hyperparameter tuning and model selection.
- Achieved high accuracy with Linear Regression as the final production model.

### 🌐 Web Application
- **Backend**: Python Flask server to serve predictions.
- **Frontend**: Clean UI (HTML/CSS/JS) for users to input area, BHK, bathrooms, and location to get instant price estimates.

---

## 🏗️ Architecture

```
price_prediction/
├── model/
│   ├── price-prediction.ipynb        # Data science workspace (Jupyter)
│   ├── banglore_home_prices_model.pickle # Exported trained model
│   └── columns.json                  # Data structure for one-hot encoding
├── server/
│   ├── server.py                     # Flask API
│   └── util.py                       # Prediction logic & model loading
├── client/
│   ├── app.html                      # Frontend UI
│   ├── app.js                        # API calls to Flask
│   └── app.css                       # Styling
└── data/
    └── Bengaluru_House_Data.csv.xls  # Source dataset
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Data Science** | Python, Pandas, Matplotlib, NumPy |
| **Machine Learning** | Scikit-learn (Linear Regression, GridSearchCV) |
| **Backend** | Flask |
| **Frontend** | HTML, CSS, JavaScript |

---

## 🚀 Getting Started

### 1. Model Training (Optional)
Open `price-prediction.ipynb` in Jupyter Notebook or Google Colab to see the full analysis, visualizations, and model training steps.

### 2. Run the Prediction Server
```bash
# Install dependencies
pip install flask numpy pandas scikit-learn

# Start the server
python server/server.py
```
The server will start at `http://127.0.0.1:5000/`.

### 3. Use the Web UI
Simply open `client/app.html` in any modern web browser. 
Enter the house details and click **"Estimate Price"** to get the result from the backend.

---

## 📈 Key Insights
- Location is the most significant factor affecting prices in Bangalore.
- Removing outliers where `price_per_sqft` was too low or too high significantly improved model R² scores.

---

## 👩‍💻 Author
**Vaishnavi Dubey**  
[GitHub Profile](https://github.com/Vaishnavi-Dubey)

---

<p align="center">Empowering data-driven real estate decisions</p>
