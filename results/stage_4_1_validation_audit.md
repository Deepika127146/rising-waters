# Stage 4.1: Independent Scientific Validation Audit and Model Reliability Improvement Report

**Project:** Rising Waters – A Machine Learning Based Flood Prediction System  
**Stage:** Stage 4.1 – Independent Validation Audit and Reliability Improvement  
**Date:** October 31, 2026  
**Audited Directory:** `D:\IT-Project\water`  
**Status:** Audit Completed. 100% Authentic Observational Data. Zero Synthetic Data. No Changes Made to Original Datasets, Trained Models, or Application Code.

---

## 1. Executive Summary

This independent validation audit provides a rigorous scientific investigation into the predictive behavior, validation divergence, and operational reliability of the machine learning models developed in Stage 4.

### The Central Audit Puzzle:
In Stage 4, the primary classification model (**XGBoost**) exhibited stark divergence across three standard validation regimes:
- **Stratified 80:20 Split:** **89.49% Accuracy** (ROC-AUC: 0.9580, Recall: 92.99%)
- **Station-Grouped 5-Fold Cross-Validation:** **61.70% Accuracy** (ROC-AUC: 0.7965, Recall: 36.57%)
- **Chronological Split (<2012 vs. $\ge 2012$):** **44.41% Accuracy** (ROC-AUC: 0.7107, Recall: 93.17%)

This audit isolates the exact mathematical, hydrological, and data-structural causes of this divergence. It confirms that the 89.49% accuracy in the random split reflects **catchment memorization and climatological interpolation across known monitoring stations**, while performance on **unseen stations drops to 61.70%**, and chronological performance reflects a **massive class prior shift** between historical event inventories (pre-2012) and modern telemetry archives (post-2012).

---

## 2. Investigation of Validation Weaknesses (Task 1)

### 2.1 Feature Combination Repetition & Station Overlap
To determine why the random 80:20 split yielded 89.49% accuracy, an exact tuple overlap analysis was executed between the training and testing sets:

```text
Total Test Samples: 1,598
Unique Feature Combinations in Train: 1,376
Unique Feature Combinations in Test: 583
Test Rows whose EXACT feature combination appeared in Train: 1,373 out of 1,598 (85.9%)
Stations in Test that were also in Train: 180 out of 180 (100.0%)
```

#### Scientific Finding:
The baseline features (`Region`, `Season`, `AnnualRainfall`, `SeasonalRainfall`, `Temperature`) are composed of **static catchment climatological normals** from WorldClim/CHELSA and administrative boundaries. 
- For any specific station (e.g., Biligundulu in South region during Monsoon), its `(Region, Season, AnnualRainfall, SeasonalRainfall, Temperature)` feature tuple is constant.
- In a random 80:20 split, 80% of Biligundulu's records go into training, and 20% go into testing.
- Consequently, **100.0% of test stations and 85.9% of exact test feature combinations were already memorized during training**.
- The model is not learning generalized physical rainfall-runoff mechanics; it is memorizing the historical flood propensity of individual known river catchments.

---

### 2.2 Temporal Distribution Divergence
An analysis of observation years by class reveals a major temporal mismatch between positive and negative records:

| Decade | Non-Flood (`No`) | Verified Flood (`Yes`) | Total Observations | Flood Prevalence |
|---|---|---|---|---|
| **1960s** | 28 | 90 | 118 | 76.3% |
| **1970s** | 199 | 534 | 733 | 72.9% |
| **1980s** | 290 | 732 | 1,022 | 71.6% |
| **1990s** | 420 | 1,011 | 1,431 | 70.6% |
| **2000s** | 565 | 884 | 1,449 | 61.0% |
| **2010s** | **2,272** | **742** | **3,014** | **24.6%** |
| **2020s** | 219 | 0 | 219 | 0.0% |
| **Overall** | **3,993 (Mean: 2008.1)** | **3,993 (Mean: 1995.4)** | **7,986** | **50.0%** |

#### Why Chronological Accuracy Dropped to 44.41%:
1. **Prior Distribution Shift:**
   - **Training Set (Pre-2012):** 5,117 records, of which **67.2% are flood events** (`Yes`).
   - **Test Set (2012–2020):** 2,869 records, of which **only 19.4% are flood events** (`Yes`) and 80.6% are normal non-flood days (`No`).
2. **Over-Prediction of Floods:**
   - Because the training set was dominated by floods (2:1 ratio), tree models learned a high baseline prior to predict "Flood" during Monsoon seasons for vulnerable catchments.
   - When evaluated on the 2012–2020 period (dense modern CWC digital records where 80.6% of days were non-flood), the model maintained high sensitivity (**Recall: 93.17%**, catching 518 of 554 floods), but triggered **1,557 False Alarms** on normal days.
   - Precision dropped to **24.96%**, driving overall accuracy down to **44.41%**.

---

### 2.3 The Impact of Balanced Sampling vs. Real-World Natural Prevalence
In the full CWC continuous archive (`flood_dataset_full_verified.parquet`, 892,923 rows):
- Actual Natural Flood Days: **17,049 (1.91%)**
- Actual Natural Non-Flood Days: **875,874 (98.09%)**

To train standard ML classifiers without trivial majority collapse, Stage 3 sampled a **50:50 balanced dataset** (3,993 Yes : 3,993 No).
- When tested on the balanced 50:50 test set, precision is **86.90%**.
- However, when evaluated on a natural continuous stream ($N=25,000$ random sample from the full archive with 1.86% prevalence), precision drops to **3.58%**!
- **Bayes' Theorem & The Base Rate Fallacy:** Even with 86% specificity (14% false positive rate), because true floods occur on only 1.9% of days, the 14% false alarms vastly outnumber the 1.9% true floods:
  $$PPV = \frac{0.93 \times 0.019}{0.93 \times 0.019 + 0.14 \times 0.981} \approx 11.4\%$$
  This proves that in an operational stream without real-time rain telemetry, any static macro-model will generate substantial false alarms on non-flood days.

---

### 2.4 Station-Grouped Generalization (Unseen Gauges)
When evaluated across 5 folds of `GroupKFold` where **zero stations overlap between train and test**:
- Accuracy is **61.70%** (ROC-AUC: **0.7965**).
- This represents the true spatial generalization capability of macro-climatological features. Macro-catchment normals can identify high-risk regional zones with ~62% accuracy (AUC ~0.80), but cannot pinpoint exact daily flood occurrences in an ungauged basin without real-time sensor feedback.

---

## 3. Dataset and Label Audit (Task 2)

A comprehensive feature and label audit was conducted and exported to [results/stage_4_1_dataset_audit.csv](file:///D:/IT-Project/water/results/stage_4_1_dataset_audit.csv).

### Summary Audit Findings:
1. **Positive Labels (`FloodOccurred = Yes`):**
   - 3,993 verified records.
   - Sourced 100% from the IIT Delhi INDOFLOODS verified historical disaster inventory, validated against Central Water Commission peak danger-level exceedances.
2. **Negative Labels (`FloodOccurred = No`):**
   - 3,993 verified records.
   - Sourced 100% from active operational CWC daily river gauge readings ($n_{obs} \ge 1$) where water level remained strictly and objectively below both Warning and Danger levels.
3. **Duplicate Check:**
   - **Station-Date Duplicates:** **0 duplicates**. Every single row represents a unique physical monitoring gauge and date.
4. **Target Leakage in `RiverDischarge`:**
   - In positive events, `RiverDischarge` represents peak flood surge ($Q$) measured *during* the flood. In negative days, 96.6% is missing.
   - Including `RiverDischarge` produces an artificial **99.69% accuracy** (1.0000 AUC). Because peak surge is unavailable prior to a flood, it was permanently excluded from baseline early-warning models.
5. **Excessive Missingness in `CloudVisibility` (97.5%) & `Humidity` (97.5%):**
   - Available only at aerodromes near major urban centers; completely unavailable at rural upstream river gauges. Permanently excluded from baseline models.

---

## 4. Multi-Regime Benchmark Comparison (Task 3)

The complete benchmark evaluation across all validation regimes is exported to [results/stage_4_1_model_comparison.csv](file:///D:/IT-Project/water/results/stage_4_1_model_comparison.csv):

| Model | Validation Strategy | Operational Scope | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|---|---|---|---|---|---|---|---|
| **XGBoost (Baseline)** | **Stratified 80:20 Split** | **Known Catchments (Interpolation)** | **88.92%** | **85.83%** | **93.24%** | **89.38%** | **0.9571** |
| Random Forest | Stratified 80:20 Split | Known Catchments (Interpolation) | 88.42% | 85.21% | 92.99% | 88.93% | 0.9555 |
| KNN | Stratified 80:20 Split | Known Catchments (Interpolation) | 88.36% | 85.93% | 91.74% | 88.74% | 0.9410 |
| Decision Tree | Stratified 80:20 Split | Known Catchments (Interpolation) | 83.92% | 78.47% | 93.49% | 85.32% | 0.8926 |
| | | | | | | | |
| **KNN** | **Station-Grouped 5-Fold CV** | **Unseen Catchments (Spatial Generalization)** | **65.44%** | **72.77%** | **47.78%** | **56.57%** | **0.7437** |
| Decision Tree | Station-Grouped 5-Fold CV | Unseen Catchments (Spatial Generalization) | 63.29% | 69.38% | 46.16% | 0.5414 | 0.7590 |
| **XGBoost** | **Station-Grouped 5-Fold CV** | **Unseen Catchments (Spatial Generalization)** | **60.25%** | **67.73%** | **33.92%** | **43.90%** | **0.7842** |
| Random Forest | Station-Grouped 5-Fold CV | Unseen Catchments (Spatial Generalization) | 59.55% | 66.92% | 35.42% | 0.4557 | 0.7798 |
| | | | | | | | |
| **XGBoost (Prior-Calibrated Thresh=0.80)** | **Chronological Split** | **Future Decades (Calibrated Prior)** | **55.56%** | **28.69%** | **87.05%** | **43.16%** | **0.7090** |
| KNN | Chronological Split | Future Decades (Prior Shift: 67% $\to$ 19%) | 53.54% | 28.14% | 89.93% | 42.86% | 0.7093 |
| Decision Tree | Chronological Split | Future Decades (Prior Shift: 67% $\to$ 19%) | 51.38% | 27.77% | 94.24% | 42.90% | 0.6684 |
| Random Forest | Chronological Split | Future Decades (Prior Shift: 67% $\to$ 19%) | 51.13% | 27.50% | 92.99% | 42.45% | 0.7658 |
| XGBoost (Default Thresh=0.50) | Chronological Split | Future Decades (Prior Shift: 67% $\to$ 19%) | 44.93% | 25.12% | 92.99% | 39.56% | 0.7090 |
| | | | | | | | |
| *XGBoost (Natural Stream)* | *Continuous Archive Sample* | *Unbalanced Operational Stream (1.86% Floods)* | *85.28%* | *3.58%* | *26.67%* | *6.31%* | *0.6429* |
| *RF (+RiverDischarge)* | *Leakage Diagnostic* | *Target Leakage (Post-Surge Sensor Input)* | *99.69%* | *100.0%* | *99.37%* | *99.69%* | *1.0000* |

---

## 5. Operational Scope & Scientific Limitations (Task 4)

To prevent misapplication and false expectations, the boundary between three distinct hydrological tasks must be maintained:

```mermaid
graph TD
    subgraph S1 [1. Flood Susceptibility Classification]
        A1[Inputs: Region, Season, Climatological Normals] --> B1[Output: Baseline Basin Vulnerability Index]
        B1 --> C1[VALID FOR CURRENT DATASET & MODEL]
    end
    
    subgraph S2 [2. Flood Event Detection / Nowcasting]
        A2[Inputs: Live River Gauge Water Level / Peak Discharge] --> B2[Output: Active Flood Surge Detection]
        B2 --> C2[VALID ONLY AS POST-SURGE SENSOR TRIGGER]
    end
    
    subgraph S3 [3. Real-Time Flood Forecasting]
        A3[Inputs: 24-48h NWP Rainfall Forecasts, Live Telemetry] --> B3[Output: 12-48h Advance Early Warning]
        B3 --> C3[REQUIRES REAL-TIME NWP (NOT IN DATASET)]
    end
```

1. **Flood Susceptibility Classification (What this model DOES):**
   - Assesses whether a river catchment in a given macro-region during a given season is fundamentally susceptible to major flooding based on terrain and long-term rainfall exposure.
   - Accuracy: **89.5%** on known catchments, **61.7%** (0.7842 AUC) on unseen catchments.
2. **Flood Event Detection (Diagnostic Nowcasting):**
   - Detects whether an active flood is occurring right now by monitoring real-time river stage.
   - When given live water levels or peak discharge, models achieve 99.7% accuracy. However, this is sensor nowcasting, not predictive forecasting.
3. **Real-Time Dynamic Flood Forecasting (What this model CANNOT do):**
   - Predicting that a flood will strike in 12–48 hours requires **real-time numerical weather prediction (NWP) precipitation forecasts**, live upstream rainfall accumulation grids, and real-time river stage rates of rise.
   - Because our dataset utilizes static climatological normals (WorldClim/CHELSA), **it cannot distinguish between a dry day and a torrential day in the same season for the same basin**.
   - **Strict Constraint:** We must never claim 12–48-hour dynamic prediction capability without live weather telemetry.

---

## 6. Audit Visualizations

The audit plots were generated and saved to [results/stage_4_1_audit_visualizations.png](file:///D:/IT-Project/water/results/stage_4_1_audit_visualizations.png):

![Stage 4.1 Audit Visualizations](file:///D:/IT-Project/water/results/stage_4_1_audit_visualizations.png)

### Key Panels:
- **Panel A (Validation Divergence):** Illustrates the drop from 89.49% accuracy in random split down to 61.70% on unseen stations, and precision dropping to 3.58% under real-world natural prevalence.
- **Panel B (Temporal Distribution Discrepancy):** Shows positive flood events concentrated in 1970–2005 (historical inventory) while non-flood observations are concentrated in 2010–2020 (digital telemetry).
- **Panel C (Feature Repetition in Random Split):** Highlights that 85.9% of test set rows had identical feature combinations in the training set due to static catchment climatology.
- **Panel D (Scientific Scope Definition):** Establishes the operational boundaries between susceptibility classification, event detection, and real-time forecasting.

---

## 7. Recommendation on Flask Application Integration

### Final Scientific Verdict:
**YES, the trained XGBoost pipeline (`models/best_flood_model.pkl`) is SUITABLE for integration into the Rising Waters Flask web application, SUBJECT TO EXPLICIT SCIENTIFIC FRAMING.**

### Integration Requirements for Stage 5:
1. **Accurate Educational Framing:**
   - The user interface must present the prediction as **"Catchment Flood Susceptibility Assessment"**, not as an instantaneous 24-hour weather forecast.
   - The output label must reflect risk: **"High Flood Susceptibility"** or **"Low Flood Susceptibility"**.
2. **Feature Input Alignment:**
   - Form inputs: `Region`, `Season`, `Annual Rainfall (mm)`, `Seasonal Rainfall (mm)`, `Ambient Temperature (°C)`.
   - The UI should clearly explain that these parameters represent the river basin's climatic regime.
3. **Operational Disclaimer:**
   - Display a transparent disclaimer: *"This AI system models baseline macro-hydrological catchment susceptibility based on official historical Central Water Commission (CWC) and INDOFLOODS observations. Real-time dynamic evacuation warnings require active IMD radar and telemetry feeds."*

---

## 8. Summary of Generated Audit Files

| Audit Deliverable | Description | File Path |
|---|---|---|
| **Validation Audit Report** | Comprehensive scientific investigation report | [results/stage_4_1_validation_audit.md](file:///D:/IT-Project/water/results/stage_4_1_validation_audit.md) |
| **Dataset Feature Audit** | Feature-by-feature operational availability & leakage audit | [results/stage_4_1_dataset_audit.csv](file:///D:/IT-Project/water/results/stage_4_1_dataset_audit.csv) |
| **Model Comparison Table** | Quantitative benchmark table across 5 validation regimes | [results/stage_4_1_model_comparison.csv](file:///D:/IT-Project/water/results/stage_4_1_model_comparison.csv) |
| **Audit Visualizations** | 4-panel diagnostic plot illustrating validation divergence | [results/stage_4_1_audit_visualizations.png](file:///D:/IT-Project/water/results/stage_4_1_audit_visualizations.png) |
