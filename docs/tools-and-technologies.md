# Tools and Technologies — Rising Waters Project

**Project Title:** Rising Waters – A Machine Learning Based Catchment Flood Susceptibility Assessment  
**Audit & Deployment Status:** Audited and Verified (October 2026)  

---

## 1. Programming Language & Runtime
- **Python 3.11.9 (64-bit)**: Core language for machine learning, data processing, persistence, and web routing.

---

## 2. Machine Learning, Preprocessing & Data Engineering
- **scikit-learn (1.6.1)**:
  - Classification models: Decision Tree, Random Forest, K-Nearest Neighbors (KNN).
  - Preprocessing: `SimpleImputer`, `OneHotEncoder`, `StandardScaler`, `ColumnTransformer`.
  - Model Pipelines: `sklearn.pipeline.Pipeline` encapsulating imputation, encoding, and classifier inference.
  - Evaluation & Cross-Validation: `train_test_split`, `StratifiedKFold`, `GroupKFold`, confusion matrix, precision, recall, F1-score, ROC-AUC.
- **XGBoost (2.1.4)**:
  - Primary approved production model (`XGBClassifier`) calibrated for catchment flood susceptibility assessment.
  - Efficient tree boosting, internal sparsity handling, and high-performance gradient boosting.
- **pandas (2.2.3)**:
  - Hydrological dataset manipulation, time-series parsing, multi-file merging, and categorical feature cleaning.
- **NumPy (2.4.6)**:
  - High-performance numerical computations, vector arithmetic, and array slicing.
- **pyarrow (19.0.1)**:
  - Fast read access for large Apache Parquet archives (`data/sources_investigation/daily.parquet` ~216 MB and `data/processed/flood_dataset_full_verified.parquet`).

---

## 3. Exploratory Data Analysis & Visualization
- **Matplotlib (3.11.2) & Seaborn (0.13.2)**:
  - Headless visualization generation (`matplotlib.use('Agg')`).
  - Production of confusion matrix heatmaps, multi-classifier comparison bar charts, and validation audit plots saved in `results/`.
- **Chart.js (4.4.1 CDN)**:
  - Client-side interactive data visualizations on `/dashboard` (Donut chart for High/Low susceptibility, Regional bar chart, Seasonal bar chart, and chronological rainfall/susceptibility trend chart).

---

## 4. Model Persistence & Metadata
- **joblib (1.4.2)**:
  - Serialization and deserialization of the approved XGBoost pipeline (`models/best_flood_model.pkl`), legacy Decision Tree baseline (`models/flood_model.pkl`), and preprocessing scalers.
- **JSON**:
  - Model lineage, training parameters, and performance metadata tracking (`models/model_metadata.json`).

---

## 5. Web Application Framework & Architecture
- **Flask (3.1.0)**:
  - Backend WSGI web framework, URL routing, request parsing, session handling, and template rendering.
- **Jinja2 (3.1.6)**:
  - Server-side HTML template rendering with conditional logic, loops, safe auto-escaping, and macro components.
- **HTML5**:
  - Semantic markup (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`) ensuring accessibility and SEO compliance.
- **Vanilla CSS3 (Custom Design System)**:
  - Tailored design system (`static/css/styles.css`) using CSS Grid, Flexbox, glassmorphic card containers, and curated modern color variables (`--deep-blue`, `--ocean-blue`, `--alert-red`, `--safe-green`).
  - *Note on Bootstrap 5:* The original project PPT listed Bootstrap 5. In the audited implementation, custom Vanilla CSS was intentionally chosen to eliminate external framework bloat, prevent layout bugs, and achieve complete fine-grained control over micro-animations and typography.

---

## 6. Persistence & Storage Layer
- **SQLite 3 (`sqlite3` built-in)**:
  - Embedded relational database (`flood_history.db`) storing user assessment queries, input parameters, prediction results, timestamps, and model identifiers.
  - Concurrency optimization: Configured with **Write-Ahead Logging (`PRAGMA journal_mode=WAL;`)** and `PRAGMA busy_timeout=10000;`.
  - Security: 100% parameterized queries preventing SQL injection; CSV formula injection defense via `sanitize_csv_cell()`.
  - *Note on SQLAlchemy:* The original review PPT mentioned SQLAlchemy; the audited application directly utilizes Python's native `sqlite3` driver to ensure zero ORM overhead, full control over WAL pragmas, and lightweight execution.

---

## 7. Quality Assurance & Automated Testing
- **pytest (9.2.0)**:
  - Automated test runner executing 28 comprehensive test cases across web routing, ML pipeline execution, input validation bounds, physical consistency rules, database concurrency, migration idempotency, and REST API functionality.
- **unittest.mock**:
  - Python standard library mocking tool for simulating model loading failures and isolated testing.

---

## 8. Version Control & Development Environment
- **Git & GitHub**: Distributed version control and source code repository tracking.
- **Jupyter Notebook (`data/Flood_Prediction.ipynb`)**: Initial data exploration and exploratory modeling.
- **VS Code / Antigravity IDE**: Development, debugging, and audit environment.

---

## 9. Technology Stack Compliance Summary

| Technology from PPT | Audited Implementation Status | Status | Notes |
| :--- | :--- | :---: | :--- |
| **Python** | Python 3.11.9 64-bit | **USED** | Core language for ML and web runtime. |
| **Flask** | Flask 3.1.0 | **USED** | Web framework and routing engine. |
| **Scikit-learn** | scikit-learn 1.6.1 | **USED** | Decision Tree, Random Forest, KNN, preprocessing. |
| **XGBoost** | XGBoost 2.1.4 | **USED** | Selected primary production model pipeline. |
| **Pandas** | Pandas 2.2.3 | **USED** | Dataset ingestion and feature preparation. |
| **NumPy** | NumPy 2.4.6 | **USED** | Numerical array processing. |
| **HTML5 & CSS3** | HTML5 Semantic + Vanilla CSS3 | **USED** | Custom responsive UI design system. |
| **Bootstrap 5** | Replaced with Custom Vanilla CSS | **SCIENTIFICALLY MODIFIED** | Vanilla CSS selected for superior styling control and performance. |
| **Chart.js** | Chart.js 4.4.1 (CDN) | **USED** | Four interactive dashboard visualizations. |
| **SQLite** | SQLite 3 (`sqlite3` module) | **USED** | Stored assessment database (`flood_history.db`). |
| **SQLAlchemy** | Native `sqlite3` driver with WAL mode | **SCIENTIFICALLY MODIFIED** | Raw `sqlite3` chosen for fine PRAGMA control and zero ORM overhead. |
| **Matplotlib / Seaborn** | Matplotlib 3.11.2 / Seaborn 0.13.2 | **USED** | Visualizations for evaluation reports in `results/`. |
| **Jupyter** | `data/Flood_Prediction.ipynb` | **USED** | Initial exploratory data analysis notebook preserved. |
| **Git / GitHub** | Git repo configured with origin | **USED** | Version control active on `main` branch. |
