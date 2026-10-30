# Stage 6: Data Visualization & Result Analysis Notes

**Project:** Rising Waters – Catchment Flood Susceptibility Assessment  
**Document:** Visualization Design, Metric Rationale & Interpretation Guidelines  
**Date:** October 31, 2026  
**Status:** Completed  

---

## 1. Overview and Objectives

The Stage 6 visualization system provides a transparent, scientifically grounded analytics dashboard for the Rising Waters web application. Its primary design objectives are:

1. **Clear Scientific Distinguishment:** Clearly separate user-submitted susceptibility queries from physical river gauge telemetry or official flood disaster warnings.
2. **Multi-Faceted Catchment Auditing:** Present user query activity across macro-geographical zones, climatological seasons, and precipitation exposure levels.
3. **Rigorous Model Evaluation Transparency:** Display verified Stage 4.1 independent validation benchmarks for all four models (Decision Tree, Random Forest, KNN, XGBoost) across four distinct validation regimes.
4. **Educational Demarcation:** Expose the mathematical and hydrological mechanisms—such as feature memorization, prior distribution shifts, and the base rate fallacy—that govern machine learning performance in natural hazards.

---

## 2. Dashboard Visualizations Specification

The enhanced dashboard (`templates/dashboard.html`) incorporates four interactive Chart.js visualizations in a responsive 2x2 grid, supported by high-level KPI cards and recent assessment tables.

### 2.1 Chart 1: High vs. Low Susceptibility Distribution (`riskDonutChart`)
- **Chart Type:** Doughnut chart with cutout percentage (65%).
- **Color Palette:** 
  - High Flood Susceptibility: Alert Red (`#d64545`)
  - Low Flood Susceptibility: Safe Green (`#2e8b57`)
- **Data Source:** Live SQLite aggregation via `get_prediction_stats()` counting records matching `prediction_result LIKE '%High%'` vs. `LIKE '%Low%'`.
- **Mathematical Handling:** Displays `0.0%` rather than dividing by zero when no records exist.
- **Interpretation Guidance:** Reflects the proportion of user-submitted queries classified by the XGBoost pipeline as having elevated baseline runoff vulnerability. It does **not** represent the physical probability of a flood occurring on any given day.

### 2.2 Chart 2: Assessments by Geographical Region (`regionBarChart`)
- **Chart Type:** Vertical bar chart.
- **Categories:** All five canonical Indian macro-regions: `Central`, `East`, `North`, `South`, `West`.
- **Color Palette:** River Blue (`#1d7ea6`, alpha: 0.85).
- **Data Source:** SQL aggregation `SELECT region, COUNT(*) FROM predictions GROUP BY region` with zero-fill fallbacks for canonical regions.
- **Interpretation Guidance:** Highlights which Indian river basin zones are most frequently audited by users. For example, high volumes in South or East India reflect targeted exploration of flood-prone river basins (e.g., Cauvery, Krishna, Brahmaputra, Mahanadi).

### 2.3 Chart 3: Assessments by Climatological Season (`seasonBarChart`)
- **Chart Type:** Vertical bar chart with differentiated seasonal colors.
- **Categories:** `Monsoon`, `Post-Monsoon`, `Summer`, `Winter`.
- **Color Palette:** Deep Blue (`#0b3c5d`), Sky Blue (`#328cc1`), Warn Amber (`#e2a83b`), Safe Green (`#2e8b57`).
- **Data Source:** SQL aggregation `SELECT season, COUNT(*) FROM predictions GROUP BY season`.
- **Interpretation Guidance:** Shows the temporal distribution of assessment queries. In Indian hydrology, the Southwest Monsoon (June–September) accounts for over 75% of cumulative precipitation and is the primary driver of macro-catchment saturation.

### 2.4 Chart 4: Assessment History & Rainfall Trend (`trendBarChart`)
- **Chart Type:** Dual-attribute timeline bar chart.
- **Data Attributes:** Chronological sequence of recent queries (up to 15 latest), plotting total Annual Rainfall (mm) color-coded by susceptibility classification.
- **Color Coding:** Red bars for High Susceptibility queries; Green bars for Low Susceptibility queries.
- **Interpretation Guidance:** Allows users to visually observe the decision boundary of the XGBoost pipeline. Demonstrates how regional baseline thresholds interact with precipitation volume to trigger elevated susceptibility classifications.

---

## 3. Model Evaluation Benchmark Visualizations

The multi-regime evaluation chart (`results/stage_6_model_comparison.png`) visually synthesizes the verified findings of the Stage 4.1 independent validation audit.

### 3.1 Panel A: Stratified 80:20 Split (Memorization & Climatological Interpolation)
- **Key Metrics:**
  - XGBoost: Accuracy 88.92%, ROC-AUC 0.9571
  - Random Forest: Accuracy 88.42%, ROC-AUC 0.9555
  - KNN: Accuracy 88.36%, ROC-AUC 0.9410
  - Decision Tree: Accuracy 83.92%, ROC-AUC 0.8926
- **Scientific Analysis:** High scores in random splitting occur because **85.9% of test feature tuples and 100% of monitoring stations were already seen during training**. Because climatological normals (`AnnualRainfall`, `SeasonalRainfall`, `Temperature`) are static per river basin, tree-based models memorize basin identities rather than learning dynamic rainfall-runoff physics.

### 3.2 Panel B: Station-Grouped 5-Fold Cross-Validation (Spatial Generalization)
- **Key Metrics:**
  - KNN: Accuracy 65.44%, ROC-AUC 0.7437
  - Decision Tree: Accuracy 63.29%, ROC-AUC 0.7590
  - XGBoost: Accuracy 60.25%, ROC-AUC 0.7842
  - Random Forest: Accuracy 59.55%, ROC-AUC 0.7798
- **Scientific Analysis:** Evaluates models on completely unseen river basins using `GroupKFold` across 180 gauging stations. Performance drops by ~28% compared to the random split, establishing the true spatial generalization capability of static macro-climatological features.

### 3.3 Panel C: Chronological Validation (<2012 vs. ≥2012)
- **Key Metrics:**
  - XGBoost (Prior-Calibrated Thresh=0.80): Accuracy 55.56%, Precision 28.69%
  - KNN: Accuracy 53.54%, Precision 28.14%
  - Decision Tree: Accuracy 51.38%, Precision 27.77%
  - Random Forest: Accuracy 51.13%, Precision 27.50%
  - XGBoost (Default Thresh=0.50): Accuracy 44.93%, Precision 25.12%
- **Scientific Analysis:** Demonstrates the impact of **class prior shift**. Training data (pre-2012) had a 67.2% flood prevalence, whereas testing data (2012–2020) had a 19.4% flood prevalence. Models trained with high flood priors generate numerous false alarms on modern digital records, reducing precision to ~25–28%.

### 3.4 Panel D: Validation Divergence & The Base Rate Fallacy
- **Key Trend:** XGBoost accuracy shifts across regimes: 88.92% (Random) $\to$ 60.25% (Spatial) $\to$ 44.93% (Temporal) $\to$ 85.28% (Natural Continuous Stream).
- **The Precision Collapse:** In natural continuous streams ($N = 25,000$, flood prevalence = 1.86%), precision drops to **3.58%**.
- **Mathematical Explanation:**
  $$\text{Precision} = \frac{\text{Sensitivity} \times \text{Prevalence}}{\text{Sensitivity} \times \text{Prevalence} + (1 - \text{Specificity}) \times (1 - \text{Prevalence})}$$
  Even with an 86% specificity (14% false positive rate), the 14% false positives on the 98.1% non-flood days vastly outnumber the true positive detections on the 1.9% flood days.

---

## 4. UI & Scientific Presentation Safeguards

1. **Terminology Consistency:** The phrases **High Flood Susceptibility** and **Low Flood Susceptibility** are strictly maintained across form controls, result pages, dashboard metrics, and history logs.
2. **Model Confidence Disclaimer:** Model probabilities are explicitly labeled as **Model-Estimated Score / Confidence**, with accompanying subnotes clarifying that they reflect algorithmic certainty relative to training distributions, not calibrated physical event probabilities.
3. **Mandatory Scientific Notice:** Visibly embedded across all templates:
   > *"This AI system assesses baseline macro-hydrological catchment flood susceptibility using historical CWC and INDOFLOODS observations and long-term climatological indicators. It does not predict imminent floods or provide real-time evacuation warnings. Dynamic flood warnings require live rainfall forecasts, river-gauge telemetry and official information from relevant authorities."*
4. **Empty State Gracefulness:** If the database contains zero records, charts do not crash or render NaN values; an informative empty-state card is displayed with an invitation to run an initial assessment. The Model Evaluation benchmark section remains fully readable below.
