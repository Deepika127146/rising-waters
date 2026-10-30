# Rising Waters 🌊
### A Machine Learning-Based Catchment Flood Susceptibility Assessment System

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.0-green.svg)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn%201.5-orange.svg)](https://scikit-learn.org/)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost%202.1-red.svg)](https://xgboost.readthedocs.io/)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?logo=render&logoColor=white)](https://rising-waters-5r3a.onrender.com)
[![Tests](https://img.shields.io/badge/Tests-28%20Passing%20(100%25)-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Status-Verified%20Academic%20Submission-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT%20%2F%20Academic-lightgrey.svg)]()

---

> 🌐 **Live Deployed Application:** **[https://rising-waters-5r3a.onrender.com](https://rising-waters-5r3a.onrender.com)**  
> *Access the fully functional Catchment Flood Susceptibility Assessment platform online on Render.*

---

## 🚀 Quick Start (Run in Under 2 Minutes)

Anyone can clone and run this application locally on Windows, macOS, or Linux. The machine learning models and database are pre-packaged, requiring **zero extra training** to launch immediately.

### 1. Clone the Repository
```bash
git clone https://github.com/Deepika127146/rising-waters.git
cd rising-waters
```

### 2. Set Up Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy restriction, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` first).*

#### On Windows (Command Prompt):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify Installation (Run Automated Tests)
```bash
pytest -v tests/
```
*(All 28 tests should pass in under 5 seconds).*

### 5. Launch the Web Application
```bash
python app.py
```

Open your browser and navigate to:
👉 **Local:** [http://127.0.0.1:5000](http://127.0.0.1:5000)  
👉 **Live Deployment:** [https://rising-waters-5r3a.onrender.com](https://rising-waters-5r3a.onrender.com)

---

## 📖 Table of Contents
1. [Project Overview](#1-project-overview)
2. [Key Application Features](#2-key-application-features)
3. [Mandatory Scientific Advisory Notice](#3-mandatory-scientific-advisory-notice)
4. [Authentic Dataset & Curation](#4-authentic-dataset--curation)
5. [Feature Schema & Leakage Elimination](#5-feature-schema--leakage-elimination)
6. [Machine Learning Pipeline](#6-machine-learning-pipeline)
7. [Multi-Regime Validation Results](#7-multi-regime-validation-results)
8. [REST API Documentation](#8-rest-api-documentation)
9. [Project Directory Structure](#9-project-directory-structure)
10. [Troubleshooting & FAQs](#10-troubleshooting--faqs)
11. [License & Academic Disclaimer](#11-license--academic-disclaimer)

---

## 1. Project Overview

**Rising Waters** is an academic, data-driven machine learning system developed for **Catchment Flood Susceptibility Assessment** across Indian river basins. Built using authentic historical hydrological telemetry from the **Central Water Commission (CWC)** and verified flood disaster records from the **INDOFLOODS (IIT Delhi)** inventory, the system assesses whether a catchment exhibits elevated vulnerability to severe inundation under macro-climatological and precipitation regimes.

---

## 2. Key Application Features

- **🎯 Interactive Catchment Susceptibility Assessment:** Evaluate geographical basins using validated inputs (Region, Season, Annual Rainfall, Seasonal Rainfall, and Temperature).
- **🌧️ Backward-Compatible Legacy Risk Assessment:** Supports historical 4-season rainfall risk predictions (Decision Tree baseline).
- **📊 Real-Time Analytics Dashboard:** Interactive Chart.js visualizations (High vs. Low Susceptibility Donut, Regional Volume Bar, Seasonal Distribution Bar, and Chronological Rainfall Trend).
- **📋 Assessment History & Search:** Persistent SQLite database tracking user queries with status badges and clearing actions.
- **📥 Formula-Injection-Safe CSV Export:** Downloadable assessment history stream sanitized against spreadsheet formula injection (`=`, `+`, `-`, `@`).
- **⚡ Production JSON REST API:** Programmatic `/api/health`, `/api/assess`, and `/api/predict` endpoints for external integration.
- **🛡️ 100% Automated Test Coverage:** 28 comprehensive automated pytest tests verifying routing, inference, physical bounds, database concurrency, and security.

---

## 3. Mandatory Scientific Advisory Notice

The application permanently displays this advisory notice across all web templates and in all JSON API responses:

> ⚠️ **"This system assesses baseline macro-hydrological catchment flood susceptibility using historical CWC and INDOFLOODS observations and long-term climatological indicators. It does not forecast imminent floods or provide real-time evacuation warnings. Real-time flood warnings require live rainfall forecasts, river-gauge telemetry, and official advisories from relevant authorities."**

---

## 4. Authentic Dataset & Curation

Unlike standard projects that rely on artificial or synthetic toys, Rising Waters is trained on **7,986 authentic Indian hydrological records** across 180 river gauge stations:

1. **INDOFLOODS Historical Flood Event Inventory (IIT Delhi):**
   - 3,993 verified positive flood events (`FloodOccurred = Yes`) across 180 river gauging stations (1969–2020).
2. **Central Water Commission (CWC) River Gauging Telemetry:**
   - 3,993 verified non-flood operational gauge days (`FloodOccurred = No`) extracted from CWC's national telemetry archive (`daily.parquet`), verified to have remained strictly below Warning and Danger thresholds.
3. **Climatological Norms:**
   - CHELSA / WorldClim high-resolution gridded precipitation and temperature surfaces linked to river basin coordinates.

---

## 5. Feature Schema & Leakage Elimination

### Approved Predictive Features (5 Inputs)
All five inputs are available prior to any flood event and are completely free from target leakage:

| Feature Name | Type | Permitted Values / Physical Bounds | Description |
| :--- | :---: | :--- | :--- |
| **`Region`** | Categorical | `Central`, `East`, `North`, `South`, `West` | Indian geographical macro-zone. |
| **`Season`** | Categorical | `Monsoon`, `Post-Monsoon`, `Summer`, `Winter` | Climatological season of observation. |
| **`AnnualRainfall`** | Numeric | $0.0 \le x \le 15,000.0\text{ mm}$ | Total cumulative annual precipitation. |
| **`SeasonalRainfall`** | Numeric | $0.0 \le x \le 12,000.0\text{ mm}$ ($x \le \text{Annual}$) | Cumulative precipitation for selected season. |
| **`Temperature`** | Numeric | $-50.0^\circ\text{C} \le x \le 60.0^\circ\text{C}$ | Catchment mean ambient surface temperature. |

### Excluded Variables & Justifications
- **`RiverDischarge`:** Strictly excluded. In-stream river discharge is a concurrent or lagging hydraulic consequence of flooding, not an antecedent predictor. Training with discharge produces an artificial **99.69% accuracy** due to severe target leakage.
- **`CloudVisibility` & `Humidity`:** Strictly excluded because historical Indian gauge archives exhibit **>97.5% missing values**. Imputing 97.5% of values would fabricate synthetic data.

---

## 6. Machine Learning Pipeline

The active production model (`models/best_flood_model.pkl`) is a self-contained scikit-learn `Pipeline`:
- **Numeric Preprocessing:** `SimpleImputer(strategy='median')`
- **Categorical Preprocessing:** `SimpleImputer(strategy='most_frequent')` + `OneHotEncoder(drop='first', handle_unknown='ignore')`
- **Trained Estimator:** `XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)`

The pipeline accepts raw pandas DataFrames directly, eliminating training-serving feature drift.

---

## 7. Multi-Regime Validation Results

The project transparently documents performance across four distinct validation strategies:

| Validation Regime | Operational Scope | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Stratified 80:20 Split** | Known Catchments (Interpolation) | **88.92%** | **85.83%** | **93.24%** | **89.38%** | **0.9571** |
| **Station-Grouped 5-Fold CV** | Unseen Catchments (Spatial Generalization) | **60.25%** | **67.73%** | **33.92%** | **43.90%** | **0.7842** |
| **Chronological Backtest** | Future Decades (Temporal Shift) | **55.56%** | **28.69%** | **87.05%** | **43.16%** | **0.7090** |
| **Natural Operational Stream** | Real-World Base Rate (1.86% Floods) | **85.28%** | **3.58%** | **26.67%** | **6.31%** | **0.6429** |

---

## 8. REST API Documentation

The application exposes a production-ready JSON REST API for automated testing or integration into third-party dashboards.

### 1. Health & Service Metadata
- **Endpoint:** `GET /api/health`
- **Sample Request:**
  ```bash
  curl http://127.0.0.1:5000/api/health
  ```
- **Sample Response:**
  ```json
  {
    "status": "healthy",
    "service": "Rising Waters – Catchment Flood Susceptibility Assessment API",
    "model_loaded": true,
    "active_model": "XGBoost Catchment Susceptibility Model",
    "input_features": ["Region", "Season", "AnnualRainfall", "SeasonalRainfall", "Temperature"],
    "valid_regions": ["Central", "East", "North", "South", "West"],
    "valid_seasons": ["Monsoon", "Post-Monsoon", "Summer", "Winter"],
    "disclaimer": "This system assesses baseline macro-hydrological catchment flood susceptibility..."
  }
  ```

### 2. Catchment Susceptibility Assessment
- **Endpoint:** `POST /api/assess` (or `POST /api/predict`)
- **Headers:** `Content-Type: application/json`
- **Sample Request (cURL):**
  ```bash
  curl -X POST http://127.0.0.1:5000/api/assess \
    -H "Content-Type: application/json" \
    -d '{
      "region": "North",
      "season": "Monsoon",
      "annual_rainfall": 2600.0,
      "seasonal_rainfall": 1900.0,
      "temperature": 27.5
    }'
  ```
- **Sample Request (Python):**
  ```python
  import requests

  payload = {
      "region": "North",
      "season": "Monsoon",
      "annual_rainfall": 2600.0,
      "seasonal_rainfall": 1900.0,
      "temperature": 27.5
  }
  response = requests.post("http://127.0.0.1:5000/api/assess", json=payload)
  print(response.json())
  ```
- **Sample Response (HTTP 200 OK):**
  ```json
  {
    "status": "success",
    "prediction": 1,
    "susceptibility_tier": "High Flood Susceptibility",
    "is_flood_susceptible": true,
    "confidence_score": 89.24,
    "flood_susceptibility_score": 89.24,
    "model_name": "XGBoost Catchment Susceptibility Model",
    "assessment_type": "Catchment Flood Susceptibility Assessment",
    "inputs": {
      "region": "North",
      "season": "Monsoon",
      "annual_rainfall_mm": 2600.0,
      "seasonal_rainfall_mm": 1900.0,
      "temperature_c": 27.5
    },
    "explanation": "Catchment climatological indicators for North India during the Monsoon season indicate elevated macro-hydrological catchment flood susceptibility...",
    "disclaimer": "This system assesses baseline macro-hydrological catchment flood susceptibility..."
  }
  ```

---

## 9. Project Directory Structure

```text
Rising-Waters/
├── app.py                             # Main Flask application and REST API controllers
├── db.py                              # SQLite persistence layer with WAL mode & CSV sanitization
├── flood_history.db                   # SQLite database storing assessment history
├── requirements.txt                   # Verified package dependencies
├── train_model.py                     # Legacy baseline Decision Tree training script
├── README.md                          # Master project documentation and setup guide
│
├── data/                              # Hydrological datasets and exploratory analysis
│   ├── flood_prediction.csv           # Original baseline starter dataset
│   ├── univariate_analysis.py         # Statistical distribution analysis script
│   ├── processed/                     # Curated authentic Indian hydrological datasets
│   │   ├── flood_training_dataset.csv # Primary 7,986-record authentic training dataset
│   │   ├── flood_dataset_full_verified.parquet # High-precision parquet archive
│   │   ├── flood_training_dataset_with_metadata.csv # Feature set with coordinates
│   │   └── dataset_quality_report.md  # Comprehensive data curation report
│   └── sources_investigation/         # Research pipelines, CWC telemetry & METAR audits
│
├── models/                            # Trained machine learning model artifacts
│   ├── best_flood_model.pkl           # Approved XGBoost pipeline (260 KB)
│   ├── flood_model.pkl                # Approved legacy Decision Tree baseline (2.2 KB)
│   └── model_metadata.json            # Model lineage and accuracy metadata
│
├── static/
│   └── css/
│       └── styles.css                 # Master responsive CSS3 stylesheet
│
├── templates/                         # Accessible Jinja2 HTML5 user interface views
│   ├── index.html                     # Dual-tab assessment form
│   ├── result.html                    # Susceptibility outcome card
│   ├── dashboard.html                 # Analytics dashboard with Chart.js
│   └── history.html                   # Assessment history log and CSV export
│
├── tests/
│   └── test_app.py                    # 28 automated pytest unit & integration tests
│
├── docs/                              # Architectural schematics and workflow documentation
│   ├── er-diagram.svg                 # Database entity-relationship diagram
│   ├── project-workflow.md            # System development epics
│   └── tools-and-technologies.md      # Detailed technology stack rationale
│
└── results/                           # Authoritative evaluation reports and audit deliverables
    ├── pre_deployment_ppt_compliance_audit.md # PPT slide-by-slide compliance audit
    ├── ppt_requirement_gap_analysis.md        # Traceability matrix and gap analysis
    ├── final_project_scope.md                 # Operational boundaries specification
    ├── pre_deployment_checklist.md            # Pre-deployment verification checklist
    ├── final_cleanup_report.md                # Codebase inventory cleanup report
    ├── final_test_report.md                   # 28-test execution report
    └── final_project_audit.md                 # Master academic evaluation report
```

---

## 10. Troubleshooting & FAQs

### Q1: I get an execution policy error on Windows PowerShell when activating the virtual environment.
**Solution:** Run this command in PowerShell to temporarily permit local script execution:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### Q2: Port 5000 is already in use by another application.
**Solution:** Specify an alternative port when launching Flask:
```bash
# On Windows PowerShell:
$env:FLASK_RUN_PORT="5001"
python app.py

# Or on Linux/macOS:
FLASK_RUN_PORT=5001 python app.py
```
Or edit the port on line 665 of `app.py`: `app.run(..., port=5001)`.

### Q3: Do I need to train the model before running the web app?
**No.** The approved, pre-trained XGBoost model (`models/best_flood_model.pkl`) is already bundled in the repository. Running `python app.py` works immediately out of the box.

### Q4: How do I run the automated tests?
Run `pytest -v tests/` from the project root while the virtual environment is activated.

---

## 11. License & Academic Disclaimer

This project is developed for academic evaluation as a B.Tech internship capstone project. It is intended solely for research, demonstration, and educational purposes. Operational flood warnings and evacuation advisories must always be sourced from official government authorities, including the **Central Water Commission (CWC)**, **India Meteorological Department (IMD)**, and the **National Disaster Management Authority (NDMA)**.
