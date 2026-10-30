# Rising Waters 🌊
### A Machine Learning-Based Catchment Flood Susceptibility Assessment System

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.0-green.svg)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn%201.5-orange.svg)](https://scikit-learn.org/)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost%202.1-red.svg)](https://xgboost.readthedocs.io/)
[![Tests](https://img.shields.io/badge/Tests-24%20Passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Status-Verified%20Academic%20Submission-success.svg)]()

---

## 1. Project Introduction

**Rising Waters** is an educational and decision-support machine learning system designed to evaluate **baseline macro-hydrological catchment flood susceptibility** across Indian river basins. Built using authentic historical hydrological telemetry from the **Central Water Commission (CWC)** and verified flood disaster records from the **INDOFLOODS (IIT Delhi)** inventory, the system assesses whether a catchment exhibits elevated vulnerability to severe inundation under specific regional and seasonal climatological regimes.

> ### ⚠️ Mandatory Scientific Limitation & Advisory Notice
> **"This system assesses baseline macro-hydrological catchment flood susceptibility using historical CWC and INDOFLOODS observations and long-term climatological indicators. It does not forecast imminent floods or provide real-time evacuation warnings. Real-time flood warnings require live rainfall forecasts, river-gauge telemetry, and official advisories from relevant authorities."**

---

## 2. Problem Statement

Flooding in Indian river basins causes severe socioeconomic destruction, displacing millions and endangering lives during the Southwest and Northeast monsoon periods. Traditional flood warning relies heavily on physical hydrodynamic modeling and localized manual gauge observation, which are often computationally intensive and difficult to deploy across ungauged or data-sparse catchment zones.

While machine learning offers rapid, scalable classification, standard approaches frequently suffer from:
1. **Target Leakage:** Using post-surge water discharge (`RiverDischarge`) or downstream gauge stages measured *during* a flood disaster to predict the event itself.
2. **Excessive Sensor Missingness:** Relying on meteorological parameters such as airport cloud visibility or relative humidity that are unavailable at rural river gauging stations.
3. **Overestimated Generalization:** Using random test splits on static climatological normals, leading models to memorize basin identities rather than generalized hydrological physics.
4. **Base Rate Fallacy:** Ignoring that natural floods occur on only ~1.9% of days, causing high false-alarm rates in continuous operational streams.

Rising Waters addresses these methodological gaps through rigorous feature curation, leakage elimination, multi-regime evaluation, and a transparent Catchment Flood Susceptibility Assessment platform.

---

## 3. Project Objectives

- **Develop a Scientifically Defensible Pipeline:** Integrate real-world, verified Indian hydrological observations (7,986 samples across 180 CWC river gauging stations) without synthetic data fabrication.
- **Eliminate Target Leakage & Missingness Bias:** Exclude post-event variables (`RiverDischarge`) and sensor-sparse features (`CloudVisibility`, `Humidity`) from predictive inference.
- **Multi-Algorithm Benchmarking:** Train, compare, and validate **Decision Tree**, **Random Forest**, **K-Nearest Neighbors (KNN)**, and **XGBoost** models.
- **Multi-Regime Validation Audit:** Quantify model performance across Stratified (80:20), Station-Grouped (unseen basins), Chronological (pre/post-2012), and Natural Continuous Stream regimes.
- **Deliver an Interactive Web Platform:** Implement a responsive Flask web application with strict physical input validation, SQLite persistence, Chart.js analytics dashboard, CSV export, and complete audit reports.

---

## 4. Existing System vs. Proposed System

| Dimension | Conventional / Legacy Systems | Rising Waters Proposed System |
| :--- | :--- | :--- |
| **Scientific Scope** | Often mislabeled as 12–48h real-time evacuation warning without live radar feeds | Accurately framed as **Catchment Flood Susceptibility Assessment** based on macro-hydrological baselines |
| **Data Authenticity** | Often relies on synthetic records or unverified toy datasets | Sourced 100% from authentic **CWC** river gauge telemetry & **INDOFLOODS (IIT Delhi)** disaster archives |
| **Target Leakage** | Frequently includes peak surge discharge ($Q$), producing artificial ~100% accuracy | Strict exclusion of post-event river discharge; uses clean pre-event climatological normals |
| **Validation Strategy** | Standard random train/test split only (overestimating accuracy via station memorization) | Evaluated across **4 validation regimes** (Stratified, Station-Grouped, Chronological, and Natural Stream) |
| **Application Architecture** | Static, unvalidated forms with minimal error protection | Full Flask web application with physical bounds validation, SQLite persistence, Chart.js analytics, and CSV export |

---

## 5. Dataset Sources & Curation

The primary training dataset (`data/processed/flood_training_dataset_with_metadata.csv`) comprises **7,986 authentic Indian observational records** curated across Stage 1 to Stage 3:

1. **INDOFLOODS Historical Flood Event Inventory (IIT Delhi):**
   - 3,993 verified positive flood events (`FloodOccurred = Yes`) across 180 river gauging stations.
   - Verified against CWC danger-level exceedances and national disaster records (1969–2020).
2. **Central Water Commission (CWC) River Gauging Telemetry:**
   - Sourced from India's national river gauge network (`daily.parquet`, 34.7M daily observations).
   - 3,993 verified non-flood records (`FloodOccurred = No`) selected exclusively from operational stations where water stage remained strictly below Warning and Danger thresholds.
3. **Climatological & Catchment Normal Sources:**
   - Long-term gridded climatological precipitation and temperature normals derived from CHELSA / WorldClim global high-resolution environmental surfaces.

---

## 6. Features & Target Variable

### Approved Predictive Features (5 Inputs)
All five inputs are available prior to any flood event and are completely free from target leakage:

| Feature Name | Type | Unit / Categories | Description | Physical Bounds Validated |
| :--- | :--- | :--- | :--- | :--- |
| **Region** | Categorical | `Central`, `East`, `North`, `South`, `West` | Indian geographical macro-zone | Whitelisted canonical set |
| **Season** | Categorical | `Monsoon`, `Post-Monsoon`, `Summer`, `Winter` | Climatological season of observation | Whitelisted canonical set |
| **AnnualRainfall** | Numeric | Millimeters (mm) | Total cumulative annual precipitation | $0.0 \le x \le 15,000.0\text{ mm}$ |
| **SeasonalRainfall** | Numeric | Millimeters (mm) | Cumulative precipitation for selected season | $0.0 \le x \le 12,000.0\text{ mm}$ ($x \le \text{Annual}$) |
| **Temperature** | Numeric | Degrees Celsius (°C) | Catchment mean ambient surface temperature | $-50.0^\circ\text{C} \le x \le 60.0^\circ\text{C}$ |

### Excluded Features
- **RiverDischarge (m³/s):** Excluded because peak surge is measured *during* a flood disaster; including it introduces catastrophic target leakage.
- **CloudVisibility (km) & Humidity (%):** Excluded because they exhibit >97.5% missingness at upstream rural river monitoring stations.

### Target Variable
- **`FloodOccurred`:** Binary indicator (`0` = Low Flood Susceptibility, `1` = High Flood Susceptibility).

---

## 7. Machine Learning Algorithms & Pipeline Architecture

The deployed model (`models/best_flood_model.pkl`) is serialized as an end-to-end `sklearn.pipeline.Pipeline`:
- **Numeric Transformer:** `SimpleImputer(strategy='median')` followed by `StandardScaler()`.
- **Categorical Transformer:** `SimpleImputer(strategy='most_frequent')` followed by `OneHotEncoder(handle_unknown='ignore', sparse_output=False)`.
- **Primary Estimator:** `XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, colsample_bytree=0.8, eval_metric='logloss', random_state=42)`.

No manual scaling or external categorical encoding is performed in web code, eliminating training-serving feature drift.

---

## 8. Multi-Regime Model Evaluation & Scientific Boundaries

A key academic strength of Rising Waters is its transparent multi-regime evaluation:

```text
+---------------------------------------------------------------------------------------------------+
| Multi-Regime Benchmark Results (Stage 4.1 Independent Audit)                                     |
+----------------------+--------------------+----------+-----------+--------+----------+---------+
| Validation Regime    | Operational Scope  | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
+----------------------+--------------------+----------+-----------+--------+----------+---------+
| Stratified 80:20     | Known Catchments   | 88.92%   | 85.83%    | 93.24% | 89.38%   | 0.9571  |
| Station-Grouped 5-CV | Unseen Catchments  | 60.25%   | 67.73%    | 33.92% | 43.90%   | 0.7842  |
| Chronological Split  | Future Decades     | 55.56%   | 28.69%    | 87.05% | 43.16%   | 0.7090  |
| Natural Continuous   | 1.86% Flood Stream | 85.28%   |  3.58%    | 26.67% |  6.31%   | 0.6429  |
+----------------------+--------------------+----------+-----------+--------+----------+---------+
```

### Core Scientific Findings:
1. **The Memorization Effect in Random Splits:** 85.9% of test feature combinations and 100% of stations appear in training. High random-split accuracy (88.92%) reflects catchment memorization rather than generalized hydrodynamic physics.
2. **Spatial Generalization (Unseen River Basins):** Performance drops to 60.25% (0.7842 AUC) under 5-fold `GroupKFold`, establishing the true generalization boundary for ungauged basins.
3. **Class Prior Shift Over Decades:** Training data (<2012) had 67.2% floods; modern digital archives (2012–2020) have 19.4% floods. Models over-predict floods without prior calibration.
4. **Base Rate Fallacy in Operational Streams:** In nature, floods occur on ~1.9% of days. With a 14% false-positive rate, false alarms swamp true positives, reducing precision to 3.58% unless combined with live radar and telemetry.

---

## 9. System Architecture

```text
[ Browser Client ]
       │
       ▼ (HTTP POST /assess-susceptibility)
[ Flask Application (app.py) ]
       │
       ├──► [ Input Validation Engine ] ──(Invalid)──► [ HTTP 400 Explanatory Card ]
       │          │ (Valid Clean DataFrame)
       │          ▼
       ├──► [ XGBoost Pipeline (best_flood_model.pkl) ]
       │          │ (ColumnTransformer: Median Impute + Scaler + OHE)
       │          ▼
       │    [ Inference: High / Low Susceptibility + Model Confidence % ]
       │          │
       ├──► [ SQLite Persistence (flood_history.db) ]
       │          │
       ▼          ▼
[ UI Output (result.html) ]      [ Analytics Dashboard (dashboard.html) ]
- High / Low Susceptibility       - 4 Real-Database Chart.js Visualizations
- Model Confidence Score %        - Multi-Regime Benchmark Tables
- Climatological Interpretation   - 4 Scientific Diagnostic Cards
- Mandatory Limitation Notice     - CSV Export (/history/export)
```

---

## 10. Project Structure

```text
Rising-Waters/
├── app.py                             # Core Flask application and route controllers
├── db.py                              # SQLite persistence helper with WAL mode and CSV sanitization
├── flood_history.db                   # SQLite database storing prediction history
├── requirements.txt                   # Verified reproducible package dependencies
├── train_model.py                     # Legacy baseline Decision Tree training script
├── README.md                          # Comprehensive academic project documentation
├── data/
│   ├── flood_prediction.csv           # Original 118-row baseline dataset
│   ├── univariate_analysis.py         # Exploratory data analysis script
│   ├── processed/
│   │   ├── dataset_quality_report.md  # Stage 3 dataset curation report
│   │   ├── flood_dataset_full_verified.parquet # Full 892K verified observation archive
│   │   ├── flood_training_dataset.csv # Curated 7,986 balanced training dataset
│   │   ├── flood_training_dataset_with_metadata.csv # Training set with station coordinates
│   │   └── station_matching_report.csv# Spatial matching report for 201 CWC stations
│   └── sources_investigation/         # Downloaded CWC, INDOFLOODS & METAR research source files
├── models/
│   ├── best_flood_model.pkl           # Approved Stage 4 XGBoost pipeline (260.9 KB)
│   ├── flood_model.pkl                # Preserved legacy Decision Tree model (2.3 KB)
│   ├── model_columns.pkl              # Legacy model feature columns
│   ├── model_metadata.json            # Model metadata and accuracy metrics
│   ├── numeric_columns.pkl            # Legacy numerical columns list
│   ├── preprocessing_pipeline.pkl     # Standalone preprocessing pipeline artifact
│   └── scaler.pkl                     # Legacy StandardScaler artifact
├── results/
│   ├── stage_4_1_validation_audit.md  # Independent scientific validation audit report
│   ├── stage_4_1_model_comparison.csv # Verified benchmark metrics across 4 regimes
│   ├── stage_4_1_audit_visualizations.png # 4-panel diagnostic plot of validation divergence
│   ├── stage_5_integration_architecture.png # Flask integration architectural diagram
│   ├── stage_5_integration_report.md  # Stage 5 integration report
│   ├── stage_5_ui_assessment_form.png # Assessment interface preview
│   ├── stage_5_ui_assessment_result.png # Assessment result preview
│   ├── stage_6_dashboard_preview.png  # Analytics dashboard preview
│   ├── stage_6_dashboard_report.md    # Stage 6 dashboard and visualization report
│   ├── stage_6_model_comparison.png   # Stage 6 multi-panel model comparison chart
│   └── stage_6_visualization_notes.md # Data visualization design notes
├── static/
│   └── css/
│       └── styles.css                 # Master application stylesheet
├── templates/
│   ├── index.html                     # Catchment susceptibility assessment interface
│   ├── result.html                    # Susceptibility outcome & explanation view
│   ├── dashboard.html                 # Analytics dashboard with Chart.js & benchmark tables
│   └── history.html                   # Prediction history log and CSV export
└── tests/
    └── test_app.py                    # Comprehensive test suite (24 passing automated tests)
```

---

## 11. Installation & How to Run

### Prerequisites
- Python 3.10 or 3.11
- Virtual environment tool (`venv`)

### Setup Instructions

```bash
# 1. Clone or navigate to the repository
cd D:\IT-Project\water

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install verified dependencies
pip install -r requirements.txt

# 4. Run automated test suite
pytest -v tests/

# 5. Start the web application
python app.py
```

Open your browser at:
```text
http://127.0.0.1:5000
```

---

## 12. Screenshots & Expected User Workflow

1. **Assessment Interface (`/`):**
   - User selects **Geographical Region** (e.g., *South India*) and **Season** (e.g., *Monsoon*).
   - User enters **Annual Rainfall** (e.g., *2,400 mm*), **Seasonal Rainfall** (e.g., *1,800 mm*), and **Temperature** (e.g., *28.5 °C*).
   - Form validates physical bounds ($\text{Seasonal} \le \text{Annual}$, temperatures between $-50^\circ\text{C}$ and $60^\circ\text{C}$).
   - User clicks **"Assess Susceptibility"**.
2. **Assessment Result View (`/assess-susceptibility`):**
   - Displays **High Flood Susceptibility** or **Low Flood Susceptibility**.
   - Displays **Model-Estimated Score / Confidence** with explicit note that it is an algorithmic score, not a calibrated event probability.
   - Provides scientific interpretation and mandatory limitation disclaimer.
   - Automatically saves query to `flood_history.db`.
3. **Analytics Dashboard (`/dashboard`):**
   - Displays summary metrics, 4 Chart.js charts, recent query table, and the multi-regime evaluation benchmark section.
4. **History & CSV Export (`/history`):**
   - Displays logged queries with region/season badges and allows one-click sanitized CSV download (`/history/export`).

---

## 13. Automated Test Suite

The test suite in [`tests/test_app.py`](file:///D:/IT-Project/water/tests/test_app.py) contains **24 automated tests** covering:
- Home page loading and navigation.
- Legacy 4-season rainfall risk predictions and backward compatibility.
- Approved XGBoost susceptibility pipeline loading and inference.
- Validation bounds (negative rainfall, rain >15,000 mm, seasonal > annual, temperature extremes).
- Type validation (non-numeric, infinite, missing values) returning HTTP 400.
- Database persistence, schema migration idempotency, and repeated submissions.
- Empty-state and populated dashboard rendering with 4 Chart.js charts.
- Verified Stage 4.1 model evaluation benchmark metrics integrity.
- Security protections against CSV formula injection.
- Graceful handling of model loading failures returning HTTP 500.

Run all tests via:
```bash
pytest -v tests/
```
**Result:** `24 passed in 4.21s (100% success rate)`.

---

## 14. Future Scope & Operational Evolution

1. **Coupling with Numerical Weather Prediction (NWP):** Integrate live 24–48 hour quantitative precipitation forecasts (QPF) from the India Meteorological Department (IMD) to evolve from static susceptibility to dynamic event nowcasting.
2. **Satellite Soil Moisture Assimilation:** Incorporate SMAP / Sentinel-1 antecedent soil moisture saturation grids to improve ungauged basin generalization.
3. **Hydrodynamic River Stage Telemetry:** Ingest live upstream CWC gauge rates-of-rise to provide calibrated hydraulic warning stages.
4. **Bayesian Base-Rate Calibration:** Apply Platt scaling or isotonic regression to calibrate model scores against natural 1.9% flood prevalence in operational continuous streams.

---

## License & Academic Disclaimer

This project is developed for academic evaluation as a B.Tech internship capstone project. It is intended solely for research, demonstration, and educational purposes. Operational flood warnings and evacuation advisories must always be sourced from official government authorities, including the **Central Water Commission (CWC)**, **India Meteorological Department (IMD)**, and the **National Disaster Management Authority (NDMA)**.
