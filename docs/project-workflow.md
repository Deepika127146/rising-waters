# Project Workflow — Rising Waters Project

**Project Title:** Rising Waters – A Machine Learning Based Catchment Flood Susceptibility Assessment  
**Audit & Deployment Status:** Audited and Verified (October 2026)  

The project follows a rigorous, multi-stage engineering workflow from authentic hydrological data curation to production web deployment and automated testing.

---

## Epic 1 — Authentic Data Collection & Curation

Rather than relying on unverified synthetic data, the project integrates authentic observational records from premier Indian hydrological and meteorological repositories:
1. **INDOFLOODS Database**: 3,993 verified historical flood inundation events across Indian river basins.
2. **Central Water Commission (CWC) Telemetry**: Daily river gauge and discharge observations (`daily.parquet` archive, ~216 MB) spanning 180 matched river gauge stations.
3. **Verified Non-Flood Ground Truth**: Extraction of 3,993 operational gauge days where water levels were safely below warning and danger thresholds, creating a balanced 7,986-record authentic training dataset (`data/processed/flood_training_dataset.csv`).
4. **Target Leakage Audit**: Evaluated and removed `RiverDischarge` from predictive inputs because gauge stage is a concurrent consequence of flooding, not a pre-flood predictor.
5. **Missingness Audit**: Evaluated and removed `CloudVisibility` and `Humidity` due to >97.5% missing records in Indian observational archives.

---

## Epic 2 — Exploratory Data Analysis & Climatological Normalization

1. **Univariate and Multivariate Analysis**: Explored seasonal rainfall distributions, regional variance, and temperature patterns across Indian macro-geographical zones.
2. **Physical Boundary Enforcement**: Established terrestrial domain boundaries:
   - Annual Rainfall: $0 \text{ to } 12,000 \text{ mm}$
   - Seasonal Rainfall: $0 \le SeasonalRainfall \le AnnualRainfall \le 8,000 \text{ mm}$
   - Temperature: $-20.0^\circ\text{C} \text{ to } 55.0^\circ\text{C}$
3. **Authoritative Feature Set Selection**: Finalized the 5 approved macro-hydrological features:
   - `Region` (Central, East, North, South, West)
   - `Season` (Monsoon, Post-Monsoon, Summer, Winter)
   - `AnnualRainfall` (Long-term basin normal in mm)
   - `SeasonalRainfall` (Long-term seasonal normal in mm)
   - `Temperature` (Mean ambient temperature in °C)

---

## Epic 3 — Preprocessing & Pipeline Encapsulation

To eliminate training-serving skew, all transformations were encapsulated within a unified scikit-learn `Pipeline`:
1. **Numerical Pipeline**: Missing value imputation via `SimpleImputer(strategy='median')`.
2. **Categorical Pipeline**: Missing value imputation via `SimpleImputer(strategy='most_frequent')` followed by `OneHotEncoder(drop='first', handle_unknown='ignore')`.
3. **Column Transformer**: Combines numerical and categorical transformations into a single object (`preprocessor`).
4. **Target Variable**: Label-encoded target `FloodOccurred` ($0 = \text{Low Susceptibility}, 1 = \text{High Susceptibility}$).

---

## Epic 4 — Machine Learning Model Training & Multi-Regime Evaluation

Four candidate classifiers were trained and benchmarked across multiple evaluation regimes:
- **Decision Tree Classifier**
- **Random Forest Classifier**
- **K-Nearest Neighbors (KNN)**
- **XGBoost Classifier**

### Multi-Regime Validation Strategy:
1. **Random Stratified Split (80:20)**: Simulates known catchment interpolation (XGBoost achieved **88.92% accuracy**, **0.9571 ROC-AUC**, **89.38% F1-score**).
2. **Station-Grouped Split (GroupKFold across 180 Gauging Stations)**: Evaluates pure spatial generalization to unseen catchments (Accuracy: **60.25%**, ROC-AUC: **0.7842**).
3. **Chronological Backtest Split (<2012 vs >=2012)**: Evaluates temporal stability across climate shifts and changing data collection regimes (Accuracy: **44.93%**, F1: **39.56%**).
4. **Continuous Operational Stream Simulation**: Demonstrates the Base Rate Fallacy where natural flood prevalence is ~1.91%, explaining why the system is framed as a susceptibility screening tool rather than a 12–48 hour evacuation alarm.

The best-performing pipeline was serialized as `models/best_flood_model.pkl`.

---

## Epic 5 — Application Engineering & REST API

1. **Flask Web Application (`app.py`)**:
   - `/` — Interactive home assessment form supporting both primary 5-feature XGBoost susceptibility assessment and legacy 4-season model.
   - `/assess-susceptibility` — Post-inference result card rendering susceptibility tier, confidence score, and explanation.
   - `/dashboard` — Analytics dashboard with 4 interactive Chart.js charts and multi-regime evaluation tables.
   - `/history` & `/history/export` — SQLite prediction history table and CSV export.
   - `/api/health` & `/api/assess` — Production JSON REST API endpoints supporting programmatic integration.
2. **Security Hardening**:
   - Sanitized CSV formula injection via `sanitize_csv_cell()`.
   - SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
   - Parameterized queries preventing SQL injection.
   - Graceful HTTP 500 error cards for model loading failures.
3. **Automated Testing Suite (`tests/test_app.py`)**:
   - 28 automated pytest tests covering all routes, validations, edge cases, and REST API calls (100% pass rate).

---

## Deployment & Academic Presentation

- **Local Execution**: Run via `python app.py` on `http://127.0.0.1:5000`.
- **Production Readiness**: Ready for deployment on WSGI servers (Gunicorn/Waitress) or containerized cloud infrastructure.
- **Academic Presentation**: The application and documentation strictly uphold the approved project definition: **Catchment Flood Susceptibility Assessment**, reinforced by the permanent scientific advisory notice.
