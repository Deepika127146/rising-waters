# Final Project Structure — Rising Waters Project

**Project Title:** Rising Waters – A Machine Learning Based Catchment Flood Susceptibility Assessment  
**Audit Phase:** Final Master Audit  
**Date:** October 2026  
**Status:** Clean, Logically Structured, and Verified  

---

## 1. Directory Tree Overview

```text
D:\IT-PROJECT\WATER\
│
├── app.py                             # Core Flask application, HTTP routing, and inference engine
├── db.py                              # SQLite database layer, schema migrations, and CSV export
├── train_model.py                     # Legacy baseline model training script (Decision Tree)
├── flood_history.db                   # Active SQLite database with stored user assessments
├── requirements.txt                   # Verified production & testing dependencies
├── README.md                          # Comprehensive academic project documentation
├── .gitignore                         # Version control ignore rules (including caches & venvs)
│
├── data/                              # Hydrological datasets and exploratory analysis
│   ├── flood_prediction.csv           # Original starter/baseline dataset (8 features)
│   ├── Flood_Prediction.ipynb         # Initial exploratory data analysis notebook
│   ├── univariate_analysis.py         # Statistical distribution and normality checks
│   │
│   ├── processed/                     # Curated authentic Indian hydrological datasets
│   │   ├── flood_training_dataset.csv # Primary 7,986-record authentic training dataset
│   │   ├── flood_dataset_full_verified.parquet # Parquet archive with geographic coordinates
│   │   ├── flood_training_dataset_with_metadata.csv # Feature set with station & date metadata
│   │   ├── station_matching_report.csv# Spatial matching log of 180 CWC gauge stations
│   │   └── dataset_quality_report.md  # Comprehensive data quality and validation report
│   │
│   └── sources_investigation/         # Real-world data investigation and ingestion pipeline
│       ├── build_stage3_dataset.py    # Pipeline script constructing Stage 3 dataset
│       ├── train_stage4_models.py     # Stage 4 ML training script across classifiers
│       ├── generate_stage4_1_artifacts.py # Validation audit script (GroupKFold & Time)
│       ├── fetch_defensible_metar.py  # METAR weather observation retrieval script
│       ├── inspect_hhs.py             # CWC water-level HHS observation parser
│       ├── test_ml_pipeline.py        # Machine learning pipeline verification script
│       ├── test_pipeline.py           # Data ingestion regression test script
│       ├── daily.parquet              # CWC daily river gauge observation archive (~216 MB)
│       ├── floodevents_indofloods.csv # Raw INDOFLOODS flood event database
│       ├── indofloods_verified_events.csv # Verified positive flood events
│       ├── catchment_characteristics_indofloods.csv # Basin geomorphology & drainage data
│       ├── precipitation_variables_indofloods.csv # Basin-level climatological normals
│       ├── metadata_indofloods.csv    # Gauge station spatial metadata
│       ├── District_FloodImpact.csv   # State/district flood impact observations
│       ├── District_FloodedArea.csv   # Historical flooded area records
│       ├── India_Flood_Inventory_v3.csv # Multi-source flood inventory database
│       ├── indian_airports_metar.csv  # Airport METAR observation reference
│       ├── metar_matched_observations.csv # Co-located METAR weather observations
│       ├── DATA_INTEGRATION_REPORT.md # Stage 2 data integration findings
│       ├── NEGATIVE_DATA_AND_VISIBILITY_AUDIT.md # Audit on non-flood gauge days & visibility
│       └── cwc-flood-forecasts/       # Sub-repository clone for CWC telemetry scrapers
│
├── models/                            # Trained machine learning model artifacts & pipelines
│   ├── .gitkeep                       # Git tracking placeholder for model directory
│   ├── best_flood_model.pkl           # Approved XGBoost Pipeline (Imputer + OHE + XGBoost)
│   ├── flood_model.pkl                # Approved legacy Decision Tree baseline model
│   ├── preprocessing_pipeline.pkl     # Legacy scikit-learn OneHotEncoder + Imputer
│   ├── scaler.pkl                     # Legacy StandardScaler serialization
│   ├── model_metadata.json            # Model lineage, hyperparameter, and version metadata
│   ├── model_columns.pkl              # Legacy model input feature column names
│   └── numeric_columns.pkl            # Legacy numerical feature list
│
├── templates/                         # Jinja2 HTML user-interface templates
│   ├── index.html                     # Home page & 5-feature susceptibility assessment form
│   ├── result.html                    # Susceptibility tier result card with scientific advisory
│   ├── dashboard.html                 # Analytics dashboard with 4 interactive Chart.js graphs
│   └── history.html                   # Assessment history table with search and CSV export
│
├── static/                            # Static web assets
│   └── css/
│       └── styles.css                 # Responsive, modern CSS styling and design system
│
├── tests/                             # Automated testing suite
│   └── test_app.py                    # 24 comprehensive pytest tests (routing, ML, security)
│
├── docs/                              # Project design and technical architecture documentation
│   ├── er-diagram.svg                 # SQLite database entity-relationship schema diagram
│   ├── project-workflow.md            # System workflow, user journey, and execution stages
│   └── tools-and-technologies.md      # Technology stack and library rationale
│
└── results/                           # Authoritative stage reports, charts, and audit deliverables
    ├── model_evaluation_report.md     # Stage 4 baseline vs ensemble evaluation report
    ├── stage_4_1_validation_audit.md  # Stage 4.1 independent validation audit (GroupKFold)
    ├── stage_5_integration_report.md  # Stage 5 Flask integration and routing report
    ├── stage_6_dashboard_report.md    # Stage 6 dashboard and visualization report
    ├── stage_6_visualization_notes.md # Stage 6 Chart.js design and accessibility notes
    ├── model_comparison.csv           # Stage 4 classifier performance metrics
    ├── stage_4_1_dataset_audit.csv    # Stage 4.1 feature distribution and missingness audit
    ├── stage_4_1_model_comparison.csv # Stage 4.1 multi-validation regime performance table
    ├── confusion_matrix.png           # Stage 4 confusion matrix visualization
    ├── model_comparison.png           # Stage 4 model comparison bar chart
    ├── stage_4_1_audit_visualizations.png # Stage 4.1 ROC curves and validation charts
    ├── stage_5_integration_architecture.png # Stage 5 architecture block diagram
    ├── stage_5_ui_assessment_form.png # Stage 5 assessment form interface preview
    ├── stage_5_ui_assessment_result.png # Stage 5 assessment result interface preview
    ├── stage_6_dashboard_preview.png  # Stage 6 analytics dashboard interface preview
    ├── stage_6_model_comparison.png   # Stage 6 updated model performance comparison chart
    ├── final_cleanup_report.md        # Master cleanup report & inventory audit
    ├── final_test_report.md           # Master automated test suite execution report
    ├── final_project_structure.md     # This structural organization document
    ├── final_submission_checklist.md  # Academic evaluation & submission checklist
    └── final_project_audit.md         # Comprehensive final master audit report
```

---

## 2. Directory Functional Breakdown

| Logical Folder | Primary Role | Key Integrity Guarantee |
| :--- | :--- | :--- |
| `data/` | Preserves both raw source archives and processed authentic datasets. | Preserves all raw INDOFLOODS and CWC archives to guarantee full empirical reproducibility. |
| `data/processed/` | Holds the verified 7,986-record dataset used for training the approved XGBoost pipeline. | Ensures zero data leakage; records contain verified hydrological normals and labels. |
| `models/` | Holds production-ready pickled model pipelines and metadata. | The active model `best_flood_model.pkl` is an end-to-end `sklearn.pipeline.Pipeline`, preventing training-serving skew. |
| `templates/` | Defines accessible, responsive Jinja2 HTML templates. | Every view includes the mandatory scientific advisory notice and dynamic data rendering. |
| `static/` | Centralizes vanilla CSS stylesheets. | Modern color palette, glassmorphism, responsive grid layout, and dark/light contrast. |
| `tests/` | Contains the comprehensive 24-test pytest suite. | Covers routing, input bounds, ML inference, database concurrency, migration, and security. |
| `docs/` | Contains high-level architecture specifications and ER diagrams. | Ready for academic demonstration and viva voce examination. |
| `results/` | Central repository for empirical evaluation reports, graphs, and master deliverables. | Fully documents every development phase from data ingestion to final sign-off. |

---

## 3. Path Stability & Dependency Verification

During the final audit, careful verification was conducted to ensure no files were arbitrarily renamed, moved, or deleted in a manner that would break existing paths or dependencies:

1. **Flask Application Path Verification (`app.py`):**
   - Model path: `models/best_flood_model.pkl` (Confirmed accessible)
   - Legacy model path: `models/flood_model.pkl` (Confirmed accessible)
   - Database path: `flood_history.db` in project root (Confirmed accessible)
   - Template folder: `templates/` (Default Flask template loader verified)
   - Static folder: `static/` (Default Flask static asset loader verified)
2. **Database Layer Path Verification (`db.py`):**
   - Database file: `flood_history.db` (Default sqlite path preserved)
3. **Automated Test Suite Verification (`tests/test_app.py`):**
   - References `app.app` and executes against temporary isolated databases without altering production records.
4. **Data Ingestion Scripts (`data/sources_investigation/`):**
   - Script-relative paths allow standalone execution from either root or subfolders.

---

## 4. Key File Metric Summary

| File | Purpose | Size (approx) | Primary Technologies |
| :--- | :--- | :--- | :--- |
| `app.py` | Flask Web Server & Inference | ~22.6 KB | Python, Flask, scikit-learn, XGBoost |
| `db.py` | SQLite Data Access Layer | ~15.7 KB | Python, sqlite3, CSV, WAL PRAGMA |
| `tests/test_app.py` | Automated Pytest Suite | ~27.4 KB | Python, pytest, unittest.mock |
| `templates/dashboard.html` | Analytics Dashboard | ~27.6 KB | Jinja2, HTML5, Chart.js |
| `templates/index.html` | Assessment Form | ~9.5 KB | Jinja2, HTML5, CSS |
| `templates/result.html` | Assessment Result Card | ~5.5 KB | Jinja2, HTML5, CSS |
| `templates/history.html` | Assessment History View | ~5.3 KB | Jinja2, HTML5, CSS |
| `static/css/styles.css` | Application Design System | ~14.8 KB | Vanilla CSS3, Grid, Flexbox |
| `README.md` | Comprehensive Project Guide | ~19.3 KB | GitHub Flavored Markdown |

---

## 5. Conclusion

The directory organization of **Rising Waters** meets the highest standards of software engineering and academic project structure. All modules are cleanly separated into dedicated functional directories, relative path stability is preserved, and all files necessary for compilation, execution, testing, and evaluation are present and verified.
