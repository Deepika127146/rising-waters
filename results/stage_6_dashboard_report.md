# Stage 6: Dashboard, Data Visualization & Result Analysis Report

**Project:** Rising Waters – Catchment Flood Susceptibility Assessment  
**Stage:** 6 – Dashboard Enhancement, Multi-Regime Visualization & Scientific Analysis  
**Date:** October 31, 2026  
**Status:** Completed & Verified  
**Audited Directory:** `D:\IT-Project\water`  

---

## Executive Summary

Stage 6 of the Rising Waters project delivered an enhanced analytics dashboard and visualization suite in [`templates/dashboard.html`](file:///D:/IT-Project/water/templates/dashboard.html), backed by robust database query logic in [`db.py`](file:///D:/IT-Project/water/db.py) and endpoint routing in [`app.py`](file:///D:/IT-Project/water/app.py).

The implementation strictly honors all project constraints:
1. **Preserved Models & Data Integrity:** No models were retrained or altered (`best_flood_model.pkl` and `flood_model.pkl` remain untouched). No synthetic records or fabricated metrics were generated.
2. **Four Real-Database Visualizations:** Integrated four interactive Chart.js visualizations (High vs. Low Susceptibility doughnut chart, Regional assessment bar chart, Seasonal assessment bar chart, and Rainfall/Susceptibility trend chart). All charts consume authentic SQLite database records and degrade gracefully when empty.
3. **Scientific Distinguishment:** Prominently frames all dashboard charts and metrics as **user-submitted model assessment queries**, explicitly distinguishing them from real-time flood telemetry or live emergency warnings.
4. **Comprehensive Model Evaluation Section:** Integrated verified independent validation benchmarks from the Stage 4.1 audit across four distinct validation regimes (Stratified 80:20 Split, Station-Grouped 5-Fold CV, Chronological Split, and Natural Continuous Stream) for Decision Tree, Random Forest, KNN, and XGBoost.
5. **Rigorous Explanatory Framework:** Added clear scientific insight cards explaining feature memorization in random splits, spatial generalization across ungauged basins, temporal class prior shifts, and the Base Rate Fallacy under natural flood prevalence.
6. **100% Test Suite Verification:** All 16 previous tests continue to pass without modification, complemented by 4 new automated Stage 6 tests (20/20 tests passing, 0 failures).

---

## 1. Files Modified and Created

### Files Modified

| File | Purpose of Modification |
| :--- | :--- |
| [`db.py`](file:///D:/IT-Project/water/db.py) | Enhanced `get_prediction_stats()` to compute canonical regional counts (`regional_counts` for Central, East, North, South, West) and seasonal counts (`seasonal_counts` for Monsoon, Post-Monsoon, Summer, Winter), zero-filling missing categories to prevent chart rendering errors. Expanded chronological timeline queries up to 15 records. |
| [`app.py`](file:///D:/IT-Project/water/app.py) | Defined `STAGE_4_1_EVALUATION_METRICS` dictionary containing authentic verified benchmark metrics from `results/stage_4_1_model_comparison.csv`. Passed evaluation metrics and scientific disclaimers to the `/dashboard` route. |
| [`templates/dashboard.html`](file:///D:/IT-Project/water/templates/dashboard.html) | Restructured layout into a responsive 2x2 chart grid with detailed beginner-friendly explanatory captions. Added the Model Evaluation & Scientific Benchmark section with comparison tables and four diagnostic insight cards. Added the Scientific Distinguishment Notice. Maintained empty-state handling and backward compatibility with legacy test selectors. |
| [`static/css/styles.css`](file:///D:/IT-Project/water/static/css/styles.css) | Appended styles for `charts-grid-4`, `chart-explanation`, `eval-card`, `eval-table`, `insights-grid`, and `insight-card` without altering existing stylesheet rules. |
| [`tests/test_app.py`](file:///D:/IT-Project/water/tests/test_app.py) | Added 4 automated tests covering dashboard empty-state rendering, multi-record aggregations across 5 regions and 4 seasons, legacy record handling, and model evaluation metrics integrity. Total tests increased from 16 to 20. |

### Files Created

| File | Description |
| :--- | :--- |
| [`results/stage_6_dashboard_preview.png`](file:///D:/IT-Project/water/results/stage_6_dashboard_preview.png) | High-resolution visual capture of the enhanced analytics dashboard layout, KPI cards, and four Chart.js visualizations. |
| [`results/stage_6_model_comparison.png`](file:///D:/IT-Project/water/results/stage_6_model_comparison.png) | High-resolution 4-panel diagnostic chart comparing Decision Tree, Random Forest, KNN, and XGBoost across the 4 validation regimes. |
| [`results/stage_6_visualization_notes.md`](file:///D:/IT-Project/water/results/stage_6_visualization_notes.md) | Technical documentation on visualization design, chart data sources, metric rationale, and interpretation guidelines. |
| [`results/stage_6_dashboard_report.md`](file:///D:/IT-Project/water/results/stage_6_dashboard_report.md) | This comprehensive Stage 6 report. |

---

## 2. Dashboard Visualizations & Data Logic

### 2.1 Live Database Metrics
The dashboard presents four primary KPI metric cards computed dynamically from SQLite:
- **Total Predictions:** Total count of all records logged in `predictions`.
- **High Susceptibility / Risk:** Count and percentage of queries classified as High Risk / High Susceptibility (`0.0%` shown when empty, preventing division-by-zero).
- **Low Susceptibility / Safe:** Count and percentage of queries classified as Low Risk / Safe.
- **Average Annual Rainfall:** Arithmetic mean of submitted annual rainfall across all queries.

### 2.2 Four Dedicated Chart.js Visualizations
1. **Doughnut Chart: High vs. Low Susceptibility (`riskDonutChart`):**  
   Visualizes the proportion of assessments classified as High vs. Low Flood Susceptibility. Displays tooltips with exact counts and dynamic percentages.
2. **Bar Chart: Assessments by Geographical Region (`regionBarChart`):**  
   Aggregates assessment volume across `Central`, `East`, `North`, `South`, and `West` India. Uses zero-filled defaults so all five regions always render smoothly on the x-axis even if some regions have zero queries.
3. **Bar Chart: Assessments by Climatological Season (`seasonBarChart`):**  
   Aggregates assessments across `Monsoon`, `Post-Monsoon`, `Summer`, and `Winter`. Color-coded by seasonal climate characteristics.
4. **Timeline Bar Chart: Recent Rainfall & Classification Trend (`trendBarChart`):**  
   Displays the latest queries (up to 15) in chronological order, with annual rainfall on the y-axis and color-coded bars indicating whether the model classified the condition as High Susceptibility (Red) or Low Susceptibility (Green).

### 2.3 Explanatory Text Below Charts
Every chart includes an explicit beginner-friendly caption directly beneath the canvas:
- Clarifies what the chart represents in plain language.
- Contextualizes Indian hydrological realities (e.g., explaining why the Monsoon season dominates rainfall volume).
- Reminds users that distributions reflect application usage, not physical event probabilities.

### 2.4 Empty-State Handling
When the database contains zero records:
- The dashboard displays the clean empty-state card: `No Prediction Data Yet`.
- Metric percentages display `0.0%` rather than NaN or error strings.
- Chart scripts do not execute or throw JavaScript errors.
- The **Model Evaluation & Scientific Benchmark** section remains fully readable below, allowing users to inspect model capabilities before running their first prediction.

---

## 3. Model Evaluation Benchmark & Scientific Analysis

The dashboard embeds the complete verified Stage 4.1 validation audit across four regimes, preventing misleading conflation of different evaluation methodologies:

### 3.1 Quantitative Multi-Regime Comparison

#### Regime 1: Stratified 80:20 Split (Known Catchments / Memorization & Interpolation)
*Evaluates model performance when testing on the same river basins observed during training.*
- **XGBoost (Approved):** **88.92% Accuracy**, 85.83% Precision, 93.24% Recall, 89.38% F1, **0.9571 ROC-AUC**
- **Random Forest:** 88.42% Accuracy, 85.21% Precision, 92.99% Recall, 88.93% F1, 0.9555 ROC-AUC
- **KNN:** 88.36% Accuracy, 85.93% Precision, 91.74% Recall, 88.74% F1, 0.9410 ROC-AUC
- **Decision Tree:** 83.92% Accuracy, 78.47% Precision, 93.49% Recall, 85.32% F1, 0.8926 ROC-AUC

#### Regime 2: Station-Grouped 5-Fold Cross-Validation (Unseen Catchments / Spatial Generalization)
*Evaluates models on completely unseen river basins using `GroupKFold` across 180 gauging stations (zero station overlap).*
- **KNN:** **65.44% Accuracy**, 72.77% Precision, 47.78% Recall, 56.57% F1, 0.7437 ROC-AUC
- **Decision Tree:** 63.29% Accuracy, 69.38% Precision, 46.16% Recall, 54.14% F1, 0.7590 ROC-AUC
- **XGBoost (Approved):** 60.25% Accuracy, 67.73% Precision, 33.92% Recall, 43.90% F1, **0.7842 ROC-AUC**
- **Random Forest:** 59.55% Accuracy, 66.92% Precision, 35.42% Recall, 45.57% F1, 0.7798 ROC-AUC

#### Regime 3: Chronological Split (<2012 vs. ≥2012) (Temporal Distribution Shift)
*Trains on historical inventory archives (<2012, 67.2% floods) and tests on modern digital telemetry (2012–2020, 19.4% floods).*
- **XGBoost (Prior-Calibrated Thresh=0.80):** **55.56% Accuracy**, 28.69% Precision, 87.05% Recall, 43.16% F1, 0.7090 ROC-AUC
- **KNN:** 53.54% Accuracy, 28.14% Precision, 89.93% Recall, 42.86% F1, 0.7093 ROC-AUC
- **Decision Tree:** 51.38% Accuracy, 27.77% Precision, 94.24% Recall, 42.90% F1, 0.6684 ROC-AUC
- **Random Forest:** 51.13% Accuracy, 27.50% Precision, 92.99% Recall, 42.45% F1, 0.7658 ROC-AUC
- **XGBoost (Default Thresh=0.50):** 44.93% Accuracy, 25.12% Precision, 92.99% Recall, 39.56% F1, 0.7090 ROC-AUC

#### Regime 4: Real-World Continuous Stream (Natural 1.86% Flood Prevalence)
*Diagnostic evaluation on N = 25,000 continuous daily observations reflecting natural non-flood imbalance.*
- **XGBoost (Natural Stream):** 85.28% Accuracy, **3.58% Precision**, 26.67% Recall, 6.31% F1, 0.6429 ROC-AUC
- **Decision Tree / Random Forest / KNN:** **Not available** (only XGBoost was evaluated under continuous stream sampling in Stage 4.1 audit).

---

### 3.2 Four Core Scientific Insights

1. **Why Random Split Overestimates Generalization:**  
   In a random 80:20 split, **85.9% of test feature tuples** and **100.0% of monitoring stations** were already present in the training set. Because climatological normals (`AnnualRainfall`, `SeasonalRainfall`, `Temperature`) are static per river basin, tree-based models memorize basin identities rather than learning dynamic rainfall-runoff physics.
2. **Why Spatial and Temporal Splits are More Demanding:**  
   When tested on unseen catchments (`GroupKFold`), accuracy drops to ~60–65%, demonstrating the true spatial boundary of static macro-climatology. In chronological evaluation, models trained on flood-heavy historical inventories suffer from a major class prior shift (67% $\to$ 19%), triggering excessive false alarms on normal non-flood days.
3. **The Base Rate Fallacy in Operational Floods:**  
   Natural floods occur on only **1.91% of days** across all monitoring stations. Even with 86% specificity, the 14% false-positive rate on the 98.1% normal days vastly outnumbers true flood occurrences, lowering precision to **3.58%** without live radar and rainfall telemetry.
4. **Educational Demonstrator vs. Operational Warning System:**  
   The Rising Waters system is an **educational catchment susceptibility demonstrator**. It assesses baseline macro-hydrological catchment vulnerability based on historical observations and climate normals. Operational flood forecasting requires live 24–48h NWP rainfall forecasts, radar feeds, and river-gauge telemetry from official agencies.

---

## 4. Scientific Presentation & Disclaimer Compliance

- **Terminology Consistency:** Wording is strictly standardized to **High Flood Susceptibility** and **Low Flood Susceptibility** across all views.
- **Model Confidence Framing:** Model scores are strictly labeled as **Model-Estimated Score / Confidence**, with subnotes stating: *"Model confidence score based on historical training distribution. Not a calibrated real-world flood probability."*
- **Mandatory Scientific Limitation Notice:** Visibly embedded at the top of the dashboard:
  > *"This AI system assesses baseline macro-hydrological catchment flood susceptibility using historical CWC and INDOFLOODS observations and long-term climatological indicators. It does not predict imminent floods or provide real-time evacuation warnings. Dynamic flood warnings require live rainfall forecasts, river-gauge telemetry and official information from relevant authorities."*
- **Scientific Distinguishment Notice:** Highlighted in a dedicated alert box directly above the metrics grid:
  > *"Scientific Distinguishment Notice: All metrics and distributions below represent user-submitted model assessment queries and stored evaluation records. They do not represent real-time flood warnings or live telemetry from official CWC gauging stations."*

---

## 5. Automated Test Suite Results

The complete test suite in [`tests/test_app.py`](file:///D:/IT-Project/water/tests/test_app.py) was executed with `pytest` using an isolated temporary SQLite database fixture.

### Test Execution Summary
- **Total Tests Collected:** 20
- **Passed:** 20 (100%)
- **Failed:** 0 (0%)
- **Execution Time:** 2.66s

### Test Breakdown

| # | Test Name | Stage | Scope / Assertion | Status |
| :---: | :--- | :---: | :--- | :---: |
| 1 | `test_index_loads` | Legacy | Navigation links and home page structure | **PASS** |
| 2 | `test_predict_route_handles_post_and_saves_to_db` | Legacy | 4-season rainfall prediction & SQLite persistence | **PASS** |
| 3 | `test_dashboard_empty_and_populated` | Legacy | Empty & populated dashboard state with chart canvases | **PASS** |
| 4 | `test_history_page_and_table` | Legacy | Prediction history table & action controls | **PASS** |
| 5 | `test_csv_export` | Legacy | CSV download format, headers, unmasked timestamps | **PASS** |
| 6 | `test_clear_history` | Legacy | History purge and database cleanup | **PASS** |
| 7 | `test_susceptibility_model_loading` | Stage 5 | Verification of `best_flood_model.pkl` pipeline | **PASS** |
| 8 | `test_valid_susceptibility_prediction_submission` | Stage 5 | 200 OK, High/Low susceptibility output, score, persistence | **PASS** |
| 9 | `test_predict_route_delegates_to_susceptibility` | Stage 5 | Backward compatibility delegation on `/predict` | **PASS** |
| 10 | `test_invalid_region_and_season` | Stage 5 | 400 Bad Request on invalid region/season strings | **PASS** |
| 11 | `test_missing_inputs` | Stage 5 | 400 Bad Request on missing form inputs | **PASS** |
| 12 | `test_invalid_numerical_values` | Stage 5 | 400 Bad Request on non-numeric strings | **PASS** |
| 13 | `test_out_of_range_and_inconsistent_values` | Stage 5 | 400 on negative rainfall, seasonal > annual, temp bounds | **PASS** |
| 14 | `test_susceptibility_history_and_csv_export` | Stage 5 | History & CSV export with Region, Season, Temp | **PASS** |
| 15 | `test_dashboard_with_susceptibility_breakdown` | Stage 5 | Susceptibility metrics breakdown on dashboard | **PASS** |
| 16 | `test_disclaimer_presence_on_all_views` | Stage 5 | Mandatory disclaimer present on home and dashboard | **PASS** |
| 17 | `test_stage6_dashboard_empty_database` | **Stage 6** | Empty state rendering, 0.0% metrics, model eval section | **PASS** |
| 18 | `test_stage6_dashboard_with_multiple_records_and_aggregations` | **Stage 6** | Multi-record counts across 5 regions & 4 seasons, 4 charts | **PASS** |
| 19 | `test_stage6_dashboard_legacy_record_handling` | **Stage 6** | Graceful handling of legacy records with null regions | **PASS** |
| 20 | `test_stage6_model_evaluation_metrics_integrity` | **Stage 6** | Verified Stage 4.1 metrics integrity & 'Not available' labels | **PASS** |

---

## 6. Manual Verification Report

Manual verification of the live Flask application was performed via HTTP client testing on `http://127.0.0.1:5000`:

1. **Dashboard Endpoint (`GET /dashboard`):**
   - Verified status code `200 OK`.
   - Verified presence of all four metric cards (`Total Predictions`, `High Susceptibility`, `Low Susceptibility`, `Avg. Annual Rainfall`).
   - Verified presence of all four Chart.js canvases: `riskDonutChart`, `regionBarChart`, `seasonBarChart`, and `trendBarChart`.
   - Verified presence of chart explanatory text below each canvas.
   - Verified presence of the **Scientific Distinguishment Notice** and the **Mandatory Scientific Limitation Disclaimer**.
2. **Model Evaluation Benchmark Section (`GET /dashboard`):**
   - Verified rendering of all four validation regimes with correct metric tables for Decision Tree, Random Forest, KNN, and XGBoost.
   - Verified display of `"Not available"` for untested natural stream models.
   - Verified all four scientific diagnostic cards (Random Split, Spatial/Temporal Splits, Base Rate Fallacy, Educational Demonstrator).
3. **Assessment Workflow (`POST /assess-susceptibility`):**
   - Submitted valid assessment: Region `South`, Season `Monsoon`, Annual `2400.0`, Seasonal `1800.0`, Temperature `28.5`.
   - Verified output: `High Flood Susceptibility`, model confidence `82.4%`, contextual explanation, and database persistence status.
4. **History & CSV Export (`GET /history` & `GET /history/export`):**
   - Verified that new assessment was appended to the history table with Region, Season, and Type badges.
   - Verified that CSV export downloaded with complete headers and unmasked `DD-MM-YYYY HH:MM:SS` timestamps.

---

## 7. Remaining Limitations

1. **Climatological vs. Dynamic Weather Telemetry:** The dashboard metrics and underlying model represent static macro-climatological catchment susceptibility. They cannot detect dynamic flash floods or unpredicted convective cloudbursts.
2. **User-Query Representation:** Dashboard charts display the distribution of queries submitted by application users, which may reflect user testing focus rather than actual geographical flood frequencies.
3. **Model Scores:** Model confidence scores emitted by the XGBoost pipeline are algorithmic classification confidence values and should not be cited as calibrated real-world event probabilities.
