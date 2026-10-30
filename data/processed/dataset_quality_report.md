# Dataset Quality and Validation Audit Report

**Project:** Rising Waters – A Machine Learning Based Flood Prediction System  
**Stage:** Stage 3 – Real Dataset Construction and Validation  
**Date:** October 31, 2026  
**Status:** Completed. 100% Authentic Observed Data. Zero Synthetic Rows or Labels Generated. No Existing Models, Application Code, or Original Datasets Modified.

---

## 1. Executive Summary

This report provides the complete engineering, hydrological, and meteorological validation audit for the construction of the real-world dataset for the **Rising Waters** flood prediction system. 

All records in the dataset are constructed strictly from physical observations published by official Indian and international scientific authorities:
1. **Central Water Commission (CWC):** Continuous historical daily water level (`datatype_code = HHS`) and river discharge (`datatype_code = HQ0`) time-series extracted from the verified open archive (`daily.parquet`, 226.6 MB, 34.9 million raw records across India).
2. **INDOFLOODS Benchmark Database:** Verified event-level flood inventory and physical catchment characteristics from the Indian Institute of Technology Delhi (IIT Delhi / BAMS 2025; Zenodo: 14584655).
3. **Airports Authority of India (AAI) / IMD METAR Network:** Real surface horizontal visibility (`vsby` in km) and relative humidity (`relh` in %) retrieved via the Iowa Environmental Mesonet (IEM) ASOS API for validated aerodromes within defensible proximity of river gauges.

### Core Deliverables Summary:
- **`data/processed/flood_training_dataset.csv`**: A class-balanced training dataset of **7,986 authentic records** (3,993 Flood / 3,993 Non-Flood; exactly 50.0% : 50.0% class balance) across **181 river monitoring stations** spanning 1961 to 2020, with exactly the 8 required input features and 1 target label.
- **`data/processed/station_matching_report.csv`**: Comprehensive station cross-referencing audit linking 214 INDOFLOODS stations with CWC monitoring locations (201 spatially confirmed within $\le 6.05\text{ km}$, median distance 0.27 km).
- **`data/processed/flood_dataset_full_verified.parquet`**: Complete continuous verified observation archive comprising **892,923 verified station-days** (875,874 verified negative days and 17,049 verified positive days).

---

## 2. Station Matching and Geospatial Linkages

A geospatial and name-matching pipeline was executed between the 214 INDOFLOODS river gauging stations (`metadata_indofloods.csv`) and the Central Water Commission Flood Forecast System station register (`stations.csv`, 1,742 stations).

### Matching Summary:
- **Total INDOFLOODS Gauges:** 214 stations across 15 major river basins.
- **Spatially Confirmed Matches ($\le 6.05\text{ km}$):** **201 stations (93.9%)**
  - **Identical Name and Proximity ($\le 5\text{ km}$):** 164 stations
  - **Spatial Coordinate Match ($\le 5\text{ km}$):** 36 stations
  - **Spatial Coordinate Match ($\le 6.05\text{ km}$):** 1 station (`INDOFLOODS-gauge-968`, Auraiya: 6.05 km)
  - **Median Proximity Distance:** **0.27 km** (270 meters)
  - **75th Percentile Proximity Distance:** **0.81 km** (810 meters)
- **Spatial Outliers ($> 6.05\text{ km}$):** 13 stations
  - 6 stations are in the 6.3–11.2 km range (e.g. Dholpur, Srisailam Dam, Karnal, Kalpi).
  - 7 stations matched identical town names in different administrative districts/states (homonyms) and were excluded from spatial gauge matching.
- **Active Hydrological Gauges in `daily.parquet`:** 195 of the matched CWC stations possess continuous daily water-level (`HHS`) records.

---

## 3. CWC Continuous Time-Series Extraction & Quality Filtering

Daily hydrological observations were extracted from the CWC `daily.parquet` archive for parameter code `HHS` (water level in meters above mean sea level or river gauge datum) and parameter code `HQ0` (streamflow/river discharge in $\text{m}^3/\text{s}$).

### Data Quality Filters Applied:
1. **Operational Gauge Status:** Requires $n_{obs} \ge 1$ (the gauge was actively operating and recorded at least 1 physical measurement during the 24-hour period).
2. **Sentinel Value Rejection:** Rejected all sentinel nulls and missing codes where $\text{min} < -900$, $\text{mean} < -900$, or $\text{max} < -900$ (e.g., `-999.0` or `-9990.0`).
3. **Operational Date Range Check:** Observations were bounded strictly by the station's documented operational period ($\text{Start\_date} \le \text{date} \le \text{End\_date}$). All observations prior to gauge installation or following decommissioning were excluded.
4. **Physical Threshold Availability:** Required published CWC official Warning Level (`warning_level`) and Danger Level (`danger_level`) thresholds in meters.
5. **Decimal Placement and Datum Anomaly Filtering:**
   - **Elevation Gauges ($\text{Danger Level} \ge 10.0\text{ m}$):** Required $\text{max} \ge 0$ and $\text{max} \le \text{Danger Level} + 35.0\text{ m}$. This safely excluded manual logger typos where decimal points were omitted (e.g., elevation 5507.93 m for a 567.25 m gauge; 1,603,698 m for a 162.4 m gauge) while strictly preserving legitimate historical flood levels.
   - **Stage Gauges ($\text{Danger Level} < 10.0\text{ m}$):** Required $\text{max} \ge 0$ and $\text{max} \le 35.0\text{ m}$.

### Detailed Rejection and Filtering Breakdown:

| Processing Category | Record Count | Percentage of Raw | Rejection Reason / Note |
|---|---|---|---|
| **Total Raw CWC HHS Records Extracted** | **1,713,883** | **100.0%** | Extracted from `daily.parquet` for matched CWC stations |
| **Rejected: Sentinel / Null Values** | 11,693 | 0.68% | `min`, `mean`, or `max` $< -900$ (coded `-999.0`) |
| **Rejected: Outside Operational Dates** | 767,355 | 44.77% | Dates prior to station start or post-decommissioning |
| **Rejected: Missing Thresholds** | 16,165 | 0.94% | Station lacks published CWC warning/danger thresholds |
| **Rejected: Decimal Placement Anomalies** | 3,015 | 0.18% | Obvious decimal typos (e.g. $> 10\times$ danger level) |
| **Total Rejected Records** | **798,228** | **46.57%** | Safely excluded from training consideration |
| **Valid Operational Records** | **915,655** | **53.43%** | Physically validated daily operational readings |

---

## 4. Conservative Labeling and Ground-Truth Conflict Resolution

### 4.1 Labeling Rules:
To avoid label leakage and unverified assumptions, observations are categorized into three mutually exclusive groups:
1. **`FloodOccurred = No` (Verified Negative):** Valid operational record where $\text{max} < \text{warning\_level}$ AND $\text{max} < \text{danger\_level}$. Water level remained strictly and objectively below all flood alert thresholds throughout the day.
2. **`FloodOccurred = Yes` (Verified Positive):** Valid operational record where $\text{max} \ge \text{danger\_level}$, OR the record is independently linked to a verified flood event in the IIT Delhi INDOFLOODS disaster inventory.
3. **`Uncertain` (Excluded from Binary Training):** Valid operational record where $\text{warning\_level} \le \text{max} < \text{danger\_level}$, and no independent flood disaster occurred. In hydrological practice, warning-level exceedance indicates bankfull flow or preliminary advisories, but does not constitute out-of-bank flooding. Including warning levels as "No" produces false negatives; including them as "Yes" produces false alarms. These are kept in an `Uncertain` category and excluded from binary classification.

### 4.2 Integration of 3,993 Verified INDOFLOODS Flood Events:
- **Exact Date-Station Overlap:** **1,886 INDOFLOODS flood events** match continuous CWC daily observations on their exact peak flood date.
  - **Ground-Truth Precedence:** In all overlapping cases, the independent physical flood event confirmation takes precedence. CWC readings previously labeled `Uncertain` or `No` (e.g., due to updated modern datum shifts) are upgraded to `Yes`.
  - **Zero Duplicates:** The INDOFLOODS verified peak discharge (`RiverDischarge`) is merged into the station-date record, ensuring 0 duplicate station-date entries.
- **Non-Overlapping Events:** **2,105 INDOFLOODS verified events** occurred during historical periods prior to CWC digital daily archiving (e.g., 1965–1975) or on dates where CWC telemetry was offline. These are added independently with complete verified catchment characteristics and river discharge.

### 4.3 Comprehensive Continuous Archive Breakdown:

| Label Category | Count Before Integration | Count After Event Integration | Final Share |
|---|---|---|---|
| **Verified Negative (`FloodOccurred = No`)** | 876,876 | **875,874** | 51.04% |
| **Verified Positive (`FloodOccurred = Yes`)** | 13,398 | **17,049** | 0.99% |
| *(CWC $\ge$ Danger Level)* | *13,398* | *14,944* | — |
| *(INDOFLOODS Independent Addition)* | *—* | *2,105* | — |
| **Uncertain (Warning $\le \text{max} <$ Danger)** | 25,381 | **24,848** | 1.45% |
| **Rejected (Quality Filters Failed)** | 798,228 | **798,217** | 46.52% |
| **Total Audited Observations** | **1,713,883** | **1,715,988** | **100.0%** |

---

## 5. Investigation of Surface Visibility and Humidity (METAR Integration)

### 5.1 Spatial Representation Analysis:
- An empirical proximity analysis was conducted between all 214 INDOFLOODS river gauge coordinates and 37 civil/military airport weather stations reporting METAR observations (Airports Authority of India / IMD).
- **Key Finding:** Only **37 river gauges (17.3%)** are within 50 km of an airport weather station. Over 61.7% of river gauges are more than 100 km away (average distance: 139.1 km).
- **Defensible Rule Applied:** Surface horizontal visibility is a localized atmospheric optical metric sensitive to urban pollution, fog, and runway micro-climates. Assigning urban airport visibility to an upstream rural river gauge 140 km away is scientifically indefensible. Therefore:
  - Surface visibility (`CloudVisibility`) and relative humidity (`Humidity`) were matched **only** for gauges within $\le 50\text{ km}$ of an airport.
  - For all gauges $> 50\text{ km}$, `CloudVisibility` and `Humidity` are preserved as authentic missing (`NaN`). Zero values were fabricated or guessed.

### 5.2 Temporal Digitization Boundaries:
An automated audit of the Iowa Environmental Mesonet (IEM) Indian ASOS archive revealed that digital automated reporting began in different years across aerodromes:
- **VOML (Mangaluru):** Digitized from 2000
- **VOTV (Thiruvananthapuram):** Digitized from 2000
- **VOTR (Tiruchirappalli):** Digitized from 2000
- **VOCL (Kozhikode):** Digitized from 2010
- **VOCI (Kochi):** Digitized from 2012
- **VAKP (Kolhapur):** Digitized from 2020

### 5.3 Retrieval Results:
- Exactly **258 verified flood events** fall within both the spatial ($\le 50\text{ km}$) and temporal operational windows of a digitized airport.
- **203 authentic daily surface visibility observations** (`vsby` converted to kilometers) and **202 relative humidity observations** (`relh` in %) were successfully downloaded and matched.
- Recorded during extreme floods: visibility dropped to 2.14–3.74 km and relative humidity ranged from 88.7% to 98.0%, reflecting genuine severe monsoon downpours.

---

## 6. Training Dataset Construction (`flood_training_dataset.csv`)

### 6.1 Dataset Design & Class Balance:
The machine learning training dataset was constructed to satisfy the original project internship PPT requirements:
- **Total Records:** **7,986 authentic records**
- **Positive Records (`FloodOccurred = Yes`):** **3,993 records (50.0%)** (all verified IIT Delhi INDOFLOODS flood events).
- **Negative Records (`FloodOccurred = No`):** **3,993 records (50.0%)** (sampled from verified CWC operational negative observations across all 174 active monitoring stations and all 4 seasons).
- **Class Balance:** **Exactly 1 : 1 (50.0% Yes / 50.0% No)**. This eliminates the severe class imbalance pathology of the raw continuous archive (1.8% positive), preventing machine learning models from trivially predicting "No" 98% of the time.

### 6.2 Missing Values Breakdown:

| Feature Name | Non-Null Count | Null / Missing Count | Null Percentage | Observational Provenance & Explanation |
|---|---|---|---|---|
| **`Region`** | 7,986 | **0** | **0.0%** | Meteorological zone (South, West, East, Central, North) mapped from state/basin |
| **`Season`** | 7,986 | **0** | **0.0%** | Derived from observation calendar month (Monsoon, Post-Monsoon, Summer, Winter) |
| **`AnnualRainfall`** | 6,889 | 1,097 | 13.7% | Catchment annual climatological normal (mm) from CHELSA/WorldClim |
| **`SeasonalRainfall`**| 6,889 | 1,097 | 13.7% | Catchment wettest-quarter precipitation normal (mm) |
| **`Temperature`** | 6,889 | 1,097 | 13.7% | Catchment annual mean ambient temperature (°C) |
| **`RiverDischarge`** | 4,127 | 3,859 | 48.3% | Physical river streamflow in cumec ($\text{m}^3/\text{s}$). Available for all 3,993 positive events and verified CWC negative days with measured discharge |
| **`CloudVisibility`** | 203 | 7,783 | 97.5% | Horizontal surface visibility in km from real AAI/IMD METAR airport stations within 50 km. Rural catchments preserved as `NaN` |
| **`Humidity`** | 202 | 7,784 | 97.5% | Relative humidity in % from real AAI/IMD METAR airport stations within 50 km. Rural catchments preserved as `NaN` |
| **`FloodOccurred`** | 7,986 | **0** | **0.0%** | Binary target label (`Yes` / `No`) |

### 6.3 Station and Date Coverage:
- **Total Unique Gauges:** **181 river gauging stations**
- **Total Unique Basins:** 15 major river basins (Godavari, Krishna, Cauvery, Mahanadi, Narmada, Tapi, Mahi, Sabarmati, Subarnarekha, Brahmani, Pennar, West-flowing rivers of south India).
- **Earliest Observation Date:** **July 21, 1965**
- **Latest Observation Date:** **October 27, 2020**
- **Total Temporal Span:** **55.3 years**

### 6.4 Duplicate Audit:
- **Station-Date Duplicates:** **0 duplicates**. Every single record represents a unique physical gauging station and observation date.
- **Feature-Level Duplicates (3,481 rows):** Catchment attributes (`AnnualRainfall`, `SeasonalRainfall`, `Temperature`) are static spatial properties of a river basin. Where river discharge is unmeasured on consecutive dry-season non-flood days at the same station, the 8-feature tuple is identical. In Stage 4, standard IQR outlier and duplicate preprocessing filters will handle these transparently per PPT specifications.

---

## 7. Strict Compliance Audit Checklist

| Requirement / Constraint | Verification Status | Evidence / Notes |
|---|---|---|
| **Use only authentic observed data** | **PASSED** | 100% sourced from CWC `daily.parquet`, INDOFLOODS Zenodo 14584655, and AAI/IMD METAR archive. |
| **No synthetic rows or labels** | **PASSED** | Zero synthetic rows, random generators, or simulated points created. |
| **No model training performed** | **PASSED** | Stage 3 strictly restricted to dataset construction and validation. Model training reserved for Stage 4. |
| **Existing Flask app untouched** | **PASSED** | `app.py`, `templates/`, `static/`, `db.py`, and `models/` completely untouched. All tests pass. |
| **Original dataset preserved** | **PASSED** | `data/flood_prediction.csv` unmodified. |
| **Chunks / Vectorized processing** | **PASSED** | PyArrow dataset predicate pushdown processed 34.9M rows in seconds without memory overflow. |
| **Class balance documented** | **PASSED** | Full archive (1.8% positive) vs. Balanced Training Set (50.0% positive) fully documented. |
| **Missing values accounted for** | **PASSED** | Exact missing counts reported; no missing values filled with fake numbers. |

---

## 8. Summary of Generated Files

1. **`data/processed/flood_training_dataset.csv`**:
   - Primary 8-feature input + 1 target column machine learning training dataset (7,986 rows $\times$ 9 columns).
2. **`data/processed/flood_training_dataset_with_metadata.csv`**:
   - Extended training dataset containing full audit provenance (`Station`, `GaugeID`, `Date`).
3. **`data/processed/station_matching_report.csv`**:
   - Master station matching register linking 214 INDOFLOODS stations with CWC stations and coordinates.
4. **`data/processed/flood_dataset_full_verified.parquet`**:
   - Comprehensive continuous verified archive (892,923 verified positive and negative station-days).
5. **`data/processed/dataset_quality_report.md`**:
   - This audit report.
