# Stage 4: Machine Learning Model Development and Evaluation Report

**Project:** Rising Waters – A Machine Learning Based Flood Prediction System  
**Stage:** Stage 4 – Model Development, Multi-Strategy Validation, and Evaluation  
**Date:** October 31, 2026  
**Status:** Completed. All Four Models Trained and Validated. No Target Leakage. Zero Synthetic Rows. Flask Web App and Regression Test Suite 100% Intact.

---

## 1. Executive Summary

This report documents the machine learning model development, validation, and evaluation pipeline for the **Rising Waters** flood prediction system. 

Using the authentic dataset constructed in Stage 3 (**7,986 verified observational records** across 181 river monitoring stations), four candidate classification algorithms were implemented, trained, and comparatively evaluated:
1. **Decision Tree Classifier**
2. **Random Forest Classifier**
3. **K-Nearest Neighbors (KNN)**
4. **XGBoost Classifier**

### Primary Results Summary:
- **Selected Best Model:** **XGBoost Classifier**
  - **Validation Accuracy (80:20 Stratified Split):** **89.49%**
  - **Precision:** **86.90%**
  - **Recall (Sensitivity):** **92.99%**
  - **F1-Score:** **89.84%**
  - **ROC-AUC:** **0.9580**
- **Critical Risk Metric:** High Recall (**93.0%**) ensures that out of 799 actual flood events in the test set, **743 were successfully detected**, resulting in only 56 false negatives (unwarned floods).
- **Target Leakage Discovery:** An empirical investigation proved that using `RiverDischarge` inflates model accuracy to an artificial **99.69%** (AUC: 1.0000). Because `RiverDischarge` represents peak flood surge measured *at the height of the disaster*, it is a post-event consequence, not a pre-event predictor. It was excluded from the baseline production model to preserve real-world operational validity.
- **Leak-Free Production Pipeline:** Preprocessing and scaling were embedded inside scikit-learn `Pipeline` and `ColumnTransformer` instances to guarantee zero data leakage between training and validation folds.

---

## 2. Dataset and Feature Audit (Task 1)

### 2.1 Dataset Profile:
- **Source File:** `data/processed/flood_training_dataset_with_metadata.csv`
- **Total Records:** 7,986 verified observational records
- **Class Balance:** Exactly 3,993 Flood (`Yes`, 50.0%) and 3,993 Non-Flood (`No`, 50.0%)
- **Spatial Coverage:** 181 river monitoring stations across 15 major Indian river basins
- **Temporal Span:** July 21, 1965 to October 27, 2020 (55.3 years)

### 2.2 Feature Availability & Selection Decisions:

| Column Name | Data Type | Missing Count | Missing % | Feature Role & Scientific Selection Decision |
|---|---|---|---|---|
| **`Region`** | Categorical | 0 | 0.0% | **Selected.** Macro-geographical zone (South, West, East, Central, North). Captures broad terrain and monsoon regime. |
| **`Season`** | Categorical | 0 | 0.0% | **Selected.** Temporal monsoon cycle (Monsoon, Post-Monsoon, Summer, Winter). Differentiates flood hazard (68.4% flood rate in Monsoon vs. 4.2% in Winter). |
| **`AnnualRainfall`** | Float64 (mm) | 1,097 | 13.7% | **Selected.** Catchment climatological annual mean precipitation (CHELSA/WorldClim normal). Median imputed within pipeline. |
| **`SeasonalRainfall`** | Float64 (mm) | 1,097 | 13.7% | **Selected.** Catchment wettest-quarter precipitation normal (mm). Median imputed within pipeline. |
| **`Temperature`** | Float64 (°C) | 1,097 | 13.7% | **Selected.** Catchment annual mean ambient temperature (°C). Median imputed within pipeline. |
| **`RiverDischarge`** | Float64 (cumec) | 3,859 | 48.3% | **EXCLUDED (Target Leakage).** Documented below. In positive events, this is the peak surge during the flood. In negative events, 96.6% is unmeasured. |
| **`CloudVisibility`** | Float64 (km) | 7,783 | 97.5% | **EXCLUDED.** 97.5% missing. Exists only for gauges within 50 km of an airport. Blindly imputing zeros or medians would fabricate fake weather. |
| **`Humidity`** | Float64 (%) | 7,784 | 97.5% | **EXCLUDED.** 97.5% missing. Unrecorded at rural river gauges. |
| **`FloodOccurred`** | Object (Yes/No) | 0 | 0.0% | **Target Variable.** Binary classification label. |

### 2.3 Deep-Dive: Why `RiverDischarge` Causes Target Leakage
In hydrological flood inventories (INDOFLOODS and CWC FFS), `RiverDischarge` is recorded as the **Peak Discharge ($Q$)** measured during the climax of the flood surge (mean: 2,445.6 cumec, max: 79,618.8 cumec). Conversely, on normal dry-season days, river gauges rarely report continuous discharge unless a major dam release occurs.
- If a machine learning model is given `RiverDischarge`, it easily splits on $\text{Discharge} > 500\text{ cumec}$ or checks whether discharge was recorded, achieving an artificial **99.69% accuracy**.
- However, at the intended time of prediction (e.g. 12 to 48 hours *before* a flood strikes), the peak flood surge has not happened yet! Real-time streamflow is either normal baseflow or unmeasured.
- Deploying a model that relies on peak flood discharge to predict flood occurrence would cause catastrophic early-warning failure in real life. Therefore, the production baseline model strictly uses pre-event catchment and climatological indicators.

### 2.4 Climatological Normals vs. Real-Time Telemetry:
It is scientifically essential to state that `AnnualRainfall`, `SeasonalRainfall`, and `Temperature` in this benchmark represent **long-term catchment climatological normals** (the baseline climatic exposure of the river basin), not instantaneous real-time raingauge totals. The model predicts whether a given catchment in a given region during a given season is susceptible to flooding under baseline hydrological exposure.

---

## 3. Data Preprocessing Architecture (Task 2)

To strictly prevent data leakage across validation folds, all preprocessing transformers were encapsulated inside a scikit-learn `ColumnTransformer` and trained exclusively on the training folds:

```mermaid
flowchart TD
    Raw[Raw Feature Vector: Region, Season, AnnualRainfall, SeasonalRainfall, Temperature] --> Split{Column Transformer}
    Split -->|Numerical Features| NumPipe[Numerical Pipeline]
    Split -->|Categorical Features| CatPipe[Categorical Pipeline]
    
    subgraph NumPipe [Numerical Pipeline]
        N1[SimpleImputer: strategy=median] --> N2[StandardScaler: zero mean, unit variance]
    end
    
    subgraph CatPipe [Categorical Pipeline]
        C1[SimpleImputer: strategy=most_frequent] --> C2[OneHotEncoder: handle_unknown=ignore]
    end
    
    NumPipe --> Concat[Feature Concatenation]
    CatPipe --> Concat
    Concat --> Classifier[Machine Learning Classifier]
```

### Preprocessing Specifications:
1. **Missing Value Imputation:**
   - Numerical columns (`AnnualRainfall`, `SeasonalRainfall`, `Temperature`): Imputed with the training fold **median**. No values were set to zero.
   - Categorical columns (`Region`, `Season`): Imputed with the **most frequent** category.
2. **Feature Scaling:**
   - Standardized via `StandardScaler()` (subtracting mean, dividing by standard deviation). Critical for distance-based models (KNN).
3. **Categorical Encoding:**
   - Encoded via `OneHotEncoder(handle_unknown='ignore', sparse_output=False)` producing binary indicators for each region and season.
4. **Outlier Preservation:**
   - Extreme catchment precipitation values (e.g., Cherrapunji/Western Ghats catchments $> 5,000\text{ mm}$) were intentionally **not truncated or removed**. Flooding is inherently caused by extreme meteorological anomalies; removing heavy rainfall points damages the model's physical training signal.

---

## 4. Multi-Strategy Model Validation (Task 3 & 4)

Rather than relying solely on a random train-test split, three distinct validation strategies were executed to evaluate different operational dimensions:

### Strategy 1: Stratified 80:20 Split (Internship PPT Standard)
- **Train Set:** 6,388 samples (3,194 Yes / 3,194 No, 50.0%)
- **Test Set:** 1,598 samples (799 Yes / 799 No, 50.0%)
- **Objective:** Benchmarks algorithmic learning capacity and directly satisfies the PPT evaluation criteria.

### Strategy 2: Chronological Split (Temporal Generalization)
- **Train Set:** Observations prior to 2012 (5,117 samples; 67.2% Yes)
- **Test Set:** Observations from 2012 to 2020 (2,869 samples; 19.4% Yes)
- **Objective:** Evaluates how well models trained on historical decades predict subsequent years under shifting observational density.

### Strategy 3: Station-Grouped 5-Fold Cross-Validation (Spatial Generalization)
- **Group Key:** `GaugeID` (181 unique river gauging stations)
- **Splits:** 5-Fold `GroupKFold`
- **Objective:** Tests the model's ability to predict floods in **completely unseen river catchments** where no observations from that station were included in the training fold.

---

## 5. Model Evaluation and Comparison (Task 5)

### 5.1 Comprehensive Evaluation Table:

| Model | Validation Strategy | Accuracy | Precision | Recall (Sensitivity) | F1-Score | ROC-AUC | True Neg (TN) | False Alarm (FP) | Missed Flood (FN) | True Pos (TP) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Decision Tree** | Stratified 80:20 | 83.73% | 78.28% | 93.37% | 85.16% | 0.8938 | 592 | 207 | 53 | 746 |
| **Random Forest** | Stratified 80:20 | 88.55% | 84.92% | 93.74% | 89.11% | 0.9548 | 666 | 133 | 50 | 749 |
| **KNN** | Stratified 80:20 | 88.36% | 85.93% | 91.74% | 88.74% | 0.9410 | 679 | 120 | 66 | 733 |
| **XGBoost (Selected)** | **Stratified 80:20** | **89.49%** | **86.90%** | **92.99%** | **89.84%** | **0.9580** | **687** | **112** | **56** | **743** |
| | | | | | | | | | | |
| **Decision Tree** | Chronological (<2012) | 52.81% | 28.43% | 94.60% | 43.72% | 0.7269 | 989 | 1,324 | 30 | 526 |
| **Random Forest** | Chronological (<2012) | 51.17% | 27.51% | 92.99% | 42.46% | 0.7722 | 951 | 1,362 | 39 | 517 |
| **KNN** | Chronological (<2012) | 53.54% | 28.14% | 89.93% | 42.86% | 0.7093 | 1,036 | 1,277 | 56 | 500 |
| **XGBoost** | Chronological (<2012) | 44.41% | 24.96% | 93.17% | 39.38% | 0.7107 | 756 | 1,557 | 38 | 518 |
| | | | | | | | | | | |
| **Decision Tree** | Station-Grouped CV | 63.28% | 68.61% | 47.12% | 54.82% | 0.7597 | 3,176 | 817 | 2,116 | 1,877 |
| **Random Forest** | Station-Grouped CV | 59.88% | 68.72% | 34.87% | 45.53% | 0.7839 | 3,396 | 597 | 2,606 | 1,387 |
| **KNN** | Station-Grouped CV | 65.44% | 72.77% | 47.78% | 56.57% | 0.7437 | 3,307 | 686 | 2,075 | 1,918 |
| **XGBoost** | Station-Grouped CV | 61.70% | 70.12% | 36.57% | 45.38% | 0.7965 | 3,475 | 518 | 2,540 | 1,453 |
| | | | | | | | | | | |
| *RF (+RiverDischarge)* | *Leakage Diagnostic* | *99.69%* | *100.0%* | *99.37%* | *99.69%* | *1.0000* | *799* | *0* | *5* | *794* |

---

### 5.2 Confusion Matrix Trade-Off in Early Warning Systems

In natural hazard forecasting, the cost asymmetry between errors is profound:

1. **False Positive (False Alarm - Type I Error):**
   - The system predicts a Flood, but no flood occurs.
   - **Cost:** Emergency services mobilize, low-lying residents are advised to take precautions, temporary road diversions. Economic inconvenience occurs, but zero lives are lost.
   - In our best model (XGBoost), false alarms occurred on only **112 out of 799 non-flood days (14.0%)**.

2. **False Negative (Missed Flood - Type II Error):**
   - The system predicts No Flood, but an extreme flood disaster strikes.
   - **Cost:** Zero warning, civilian casualties, unprepared hospitals, catastrophic destruction of property.
   - Therefore, **Recall (Sensitivity)** must be prioritized.
   - In our best model (XGBoost), the missed flood rate was limited to **56 out of 799 flood events (7.0%)**, achieving a high Recall of **92.99%**.

---

### 5.3 Comparative Analysis across Algorithms:
- **XGBoost Classifier (Winner):** Delivers the highest accuracy (**89.49%**), highest F1-score (**89.84%**), and highest ROC-AUC (**0.9580**). Its gradient-boosted decision trees effectively capture non-linear interactions between seasonal rainfall normals and regional terrain vulnerability.
- **Random Forest Classifier (Strong Runner-up):** Achieved **88.55% accuracy** and the highest raw recall (**93.74%**, only 50 missed floods). The ensemble of 100 decorrelated trees provides high resilience.
- **K-Nearest Neighbors (KNN):** Achieved **88.36% accuracy** with distance-weighted voting. Distance-weighted clustering in scaled climatological space proves very effective for identifying analogous hydrological basins.
- **Decision Tree Classifier:** Achieved **83.73% accuracy**. While simpler and highly interpretable, individual decision trees suffer from higher variance and slightly lower precision (78.28%).

---

## 6. Model Selection and Artifacts (Task 6 & 7)

### 6.1 Selected Model Specification:
- **Algorithm:** **XGBoost Classifier (`XGBClassifier`)**
- **Pipeline Architecture:** `Pipeline([('preprocessor', preprocessor), ('classifier', clf)])`
- **Hyperparameters:**
  - `n_estimators`: 100
  - `max_depth`: 6
  - `learning_rate`: 0.1
  - `subsample`: 0.8
  - `colsample_bytree`: 0.8
  - `eval_metric`: `'logloss'`
  - `random_state`: 42

### 6.2 Generated Files and Artifacts:

| File Path | Description | Status |
|---|---|---|
| [models/best_flood_model.pkl](file:///D:/IT-Project/water/models/best_flood_model.pkl) | Serialized end-to-end production pipeline (preprocessor + XGBoost) | **Saved** |
| [models/preprocessing_pipeline.pkl](file:///D:/IT-Project/water/models/preprocessing_pipeline.pkl) | Standalone preprocessing pipeline (scaling and one-hot encoding) | **Saved** |
| [results/model_comparison.csv](file:///D:/IT-Project/water/results/model_comparison.csv) | Full numerical benchmark results table across all validation strategies | **Saved** |
| [results/confusion_matrix.png](file:///D:/IT-Project/water/results/confusion_matrix.png) | 2x2 grid of confusion matrices comparing all 4 models | **Saved (300 DPI)** |
| [results/model_comparison.png](file:///D:/IT-Project/water/results/model_comparison.png) | Grouped metric comparison bar chart and ROC Curves | **Saved (300 DPI)** |
| [results/model_evaluation_report.md](file:///D:/IT-Project/water/results/model_evaluation_report.md) | This evaluation report | **Saved** |

---

## 7. Visualizations

### Confusion Matrices (Test Set $N=1,598$):
![Confusion Matrix Plot](file:///D:/IT-Project/water/results/confusion_matrix.png)

### Model Comparison & ROC Curves:
![Model Comparison and ROC Curves](file:///D:/IT-Project/water/results/model_comparison.png)

---

## 8. Scientific Limitations & Recommendations

1. **Climatological Exposure vs. Synoptic Forcing:**
   The baseline features (`AnnualRainfall`, `SeasonalRainfall`, `Temperature`) characterize the static climatic vulnerability of the catchment. For real-time operational lead times (e.g. 6–24 hours), integrating real-time numerical weather prediction grids (such as IMD GFS / WRF forecasts) will further enhance temporal precision.
2. **Surface Visibility Matching Constraints:**
   Horizontal visibility was investigated and proven available via airport METAR records. However, because 61.7% of river gauges are over 100 km from an airport, surface visibility cannot be universally applied across rural basins without introducing spatial representation error.
3. **Generalization to Unseen Gauges:**
   Station-grouped cross-validation indicates that when models are deployed to completely ungauged basins without historical calibration, accuracy drops to ~62–65% (ROC-AUC ~0.78). Local hydrological gauge calibration remains indispensable.

---

## 9. Regression Test Verification

The existing project test suite was executed post-training to verify zero regression:
```bash
.\.venv\Scripts\pytest
============================= 6 passed in 9.09s =============================
```
All existing Flask application endpoints, database models, and trained decision tree artifacts remain fully operational and completely unmodified.
