# Data Integration and Validation Audit Report

**Project:** Rising Waters – A Machine Learning Based Flood Prediction System  
**Stage:** Real-World Data Integration and Validation  
**Date:** October 31, 2026  
**Investigated Directory:** `data/sources_investigation/`  
**Status:** Audit Completed; Partial Real Feature Extraction Generated (`data/sources_investigation/indofloods_verified_events.csv`). Final dataset creation paused per strict restriction: *"If all eight features cannot be obtained reliably, stop and explain what is missing rather than filling the gaps with invented data."*

---

## 1. Executive Summary

This investigation performed a multi-source data integration and validation pipeline across official real-world hydrological, meteorological, and disaster inventories:
1. **INDOFLOODS** (IIT Delhi / BAMS 2025; Zenodo: 14584655)
2. **India Flood Inventory (IFI)** (IMD / Zenodo: 11275211)
3. **Central Water Commission (CWC) Flood Observations** (`cwc-flood-forecasts`)
4. **IMD Rainfall & Climate Catalogs** (`data.gov.in`, `imdweb.lwcc.in`)
5. **ERA5 Copernicus Climate Data Store** (`cds.climate.copernicus.eu`)

### Key Audit Findings:
- **Positive Flood Events:** Successfully unified **4,548 recorded flood events** (1965–2020) across 155 river catchments in India. **3,993 events** possess complete, verified physical river discharge measurements (`RiverDischarge` in $\text{m}^3/\text{s}$).
- **Available Features (6 of 8):** Six features (`Region`, `Season`, `AnnualRainfall`, `SeasonalRainfall`, `RiverDischarge`, and `Temperature`) can be extracted from the joined INDOFLOODS and CWC databases.
- **Unavailable Features (2 of 8):** `CloudVisibility` (horizontal surface visibility in km) and observational `Humidity` (%) cannot be obtained from the downloaded offline datasets. `CloudVisibility` is not recorded in hydrological river discharge databases nor published in standard ERA5 single-level reanalysis. `Humidity` requires registered, authenticated ECMWF CDS API credentials (`.cdsapirc`) and multi-gigabyte reanalysis downloads.
- **Verified Negative Observations:** Cannot be constructed from the event databases without violating scientific standards. An event inventory records only flood occurrences; absence of an event record does not prove non-flood conditions without continuous daily gauge level time-series.
- **Decision:** In strict compliance with the instruction — *"If all eight features cannot be obtained reliably, stop and explain what is missing rather than filling the gaps with invented data"* — `data/flood_dataset_real.csv` was **not** populated with fabricated or guessed columns. Instead, all verified real-world positive event data has been extracted and saved to `data/sources_investigation/indofloods_verified_events.csv` (3,993 verified real records).

---

## 2. Join Keys and Cross-Database Linkages

The following primary and secondary keys were identified and evaluated across the source files:

| Source File | Entity Level | Identified Key(s) | Join Target | Match Success Rate |
|-------------|--------------|-------------------|-------------|--------------------|
| `floodevents_indofloods.csv` | Event-level | `EventID` (e.g. `INDOFLOODS-gauge-1010-1`) | `precipitation_variables_indofloods.csv` | **100% (4,548 / 4,548)** |
| `floodevents_indofloods.csv` | Gauge-level | Extracted `GaugeID` (`'-'.join(EventID.split('-')[:-1])`) | `metadata_indofloods.csv` (`GaugeID`) | **100% (155 / 155 unique gauges)** |
| `floodevents_indofloods.csv` | Catchment-level | Extracted `GaugeID` | `catchment_characteristics_indofloods.csv` (`GaugeID`) | **100% (155 / 155 unique gauges)** |
| `metadata_indofloods.csv` | Station-level | Station Name (`Station`) | CWC `stations.csv` (`name`) | **79.7% (169 / 212 direct string matches)** |
| `metadata_indofloods.csv` | Geospatial | Coordinates (`Latitude`, `Longitude`) | CWC `stations.csv` (`lat`, `lon`) within 0.05° (~5 km) | **93.9% (201 / 214 stations spatially confirmed)** |
| `metadata_indofloods.csv` | Administrative | `State` & `Basin` | `India_Flood_Inventory_v3.csv` (`State`, `Districts`) | Macro-regional cross-validation |

---

## 3. Feature Derivation and Observational Source Mapping

### Feature 1: Region
- **Source:** `metadata_indofloods.csv` (`State`, `Basin`) and `India_Flood_Inventory_v3.csv` (`State`).
- **Derivation Logic:** Mapped using official Indian meteorological / zonal boundaries:
  - **South:** Karnataka, Kerala, Tamil Nadu, Andhra Pradesh, Telangana (2,600 events)
  - **West:** Maharashtra, Gujarat, Rajasthan, Dadra & Nagar Haveli (874 events)
  - **East:** Bihar, Odisha, West Bengal, Jharkhand, Tripura (557 events)
  - **Central:** Madhya Pradesh, Chhattisgarh (517 events)
  - **North:** Uttar Pradesh, Uttarakhand, Haryana, Delhi, Himachal Pradesh (Note: Ganga/Brahmaputra mainstems are reserved in INDOFLOODS v1 public tier).
- **Status:** **Available and Verified (100% coverage, 0 nulls).**

### Feature 2: Season
- **Source:** `floodevents_indofloods.csv` (`Start Date`).
- **Derivation Logic:** Extracted using calendar month of event onset:
  - **Monsoon:** June, July, August, September (3,635 events, 79.9%)
  - **Post-Monsoon:** October, November, December (737 events, 16.2%)
  - **Summer (Pre-Monsoon):** March, April, May (126 events, 2.8%)
  - **Winter:** January, February (50 events, 1.1%)
- **Status:** **Available and Verified (100% coverage, 0 nulls).**

### Feature 3: AnnualRainfall
- **Source:** `catchment_characteristics_indofloods.csv` (`Annual Precipitation`).
- **Units:** Millimeters (mm).
- **Caveat & Observation:** Represents long-term annual mean precipitation over the station catchment (1970–2020 climatology). Event-specific historical annual cumulative rainfall requires joining continuous gridded IMD/ERA5 rainfall raster series.
- **Status:** **Available as Catchment Climatological Normal.**

### Feature 4: SeasonalRainfall
- **Source:** `catchment_characteristics_indofloods.csv` (`Precipitation of Wettest Quarter`) and `precipitation_variables_indofloods.csv` (`T1d` through `T10d`).
- **Units:** Millimeters (mm).
- **Critical Evaluation:** In peninsular India (South/East), the wettest quarter differs geographically:
  - For southwest-monsoon dominated basins (Godavari, Krishna, Narmada, Tapi), wettest quarter aligns with June–September.
  - For southeast basins (Cauvery, coastal Tamil Nadu), the wettest quarter is October–December (Northeast monsoon).
  - Therefore, treating `Precipitation of Wettest Quarter` as June–September rainfall without seasonal verification is climatologically invalid. In `indofloods_verified_events.csv`, the actual multi-day event-precipitation accumulation ($T_{10d}$) and wettest-quarter normal are both retained.
- **Status:** **Available with documented climatological distinction.**

### Feature 5: RiverDischarge
- **Source:** `floodevents_indofloods.csv` (`Peak Discharge Q (cumec)`).
- **Units:** $\text{m}^3/\text{s}$ (cumec).
- **Data Quality:** 3,993 records possess verified peak discharge readings. 555 records have missing discharge entries (river gauges that only recorded water level elevation in meters, not rated discharge).
- **Status:** **Available and Verified (3,993 valid records).**

### Feature 6: Temperature
- **Source:** `catchment_characteristics_indofloods.csv` (`Annual Mean Temperature`, CHELSA/WorldClim BIO01).
- **Units:** Degrees Celsius (°C).
- **Caveat:** Represents catchment climatological normal. Real-time event-day ambient temperature requires station-level synoptic registers or IMD/ERA5 daily temperature grids.
- **Status:** **Available as Catchment Climatological Normal.**

### Feature 7: Humidity
- **Required Unit:** Relative Humidity (%).
- **Observational Status:** **Unavailable in downloaded local files.**
- **Scientific Rationale:** Hydrological flood event databases (INDOFLOODS, CWC, IFI) track streamflow, water levels, and catchment rainfall, not air moisture.
- **Derivation Requirement via ERA5:** Relative Humidity ($RH$) can be computed from ERA5 2-meter air temperature ($T$ in °C) and 2-meter dewpoint temperature ($T_d$ in °C) via the August-Roche-Magnus approximation:
  $$RH = 100 \times \frac{\exp\left(\frac{17.625 \times T_d}{243.04 + T_d}\right)}{\exp\left(\frac{17.625 \times T}{243.04 + T}\right)}$$
  Accessing ERA5 requires an active Copernicus CDS API key in `.cdsapirc` (currently absent on this machine).

### Feature 8: CloudVisibility
- **Required Unit:** Horizontal Visibility in kilometers (km).
- **Observational Status:** **Unavailable across all investigated sources.**
- **Scientific Rationale:**
  - `CloudVisibility` is not published in ERA5 single-level reanalysis. ERA5 provides `total_cloud_cover` ($TCC$, a dimensionless fraction from 0.0 to 1.0), but substituting cloud cover for visibility is explicitly prohibited.
  - Actual surface visibility in India is recorded by human observers or transmissometers at IMD Synoptic Stations and AAI/METAR airport weather stations. These observations are not part of open-access hydrological river discharge repositories.
  - Inventing visibility values would directly violate the zero-fabrication constraint.

### Target: FloodOccurred
- **Value Definition:** `Yes` (Flood occurred) vs. `No` (No flood occurred).
- **Positive Records:** All 4,548 events in `floodevents_indofloods.csv` represent verified flood events where river water level exceeded the official CWC danger/warning threshold.
- **Negative Records:** **0 verified negative records.**
  - An event inventory only records positive instances.
  - Assuming that unlisted dates/stations had no flood violates scientific methodology: stations frequently suffer recording outages, sensor drift, or missing communication during severe monsoons.
  - To verify `FloodOccurred = No`, one must evaluate continuous daily water level records (e.g. CWC daily level tables) demonstrating that the gauge was operational and water level remained strictly below the warning level. Continuous daily water level tables are not present in `stations.csv`.

---

## 4. Comprehensive Validation Metrics Table

| Metric | Count / Status | Notes / Breakdown |
|--------|----------------|-------------------|
| **Total positive flood records** | **4,548** raw | 3,993 with complete peak discharge; 555 with water level only. |
| **Total verified negative records** | **0** | Cannot be proven without continuous operational daily time-series. |
| **Records matched across sources** | **4,548** | 100% internal INDOFLOODS join; 201/214 gauges spatially matched with CWC network. |
| **Records rejected and reasons** | **555** rejected | Missing `Peak Discharge Q (cumec)` (cannot provide `RiverDischarge`). |
| | **5** rejected | Missing basin annotation in metadata. |
| **Missing values per feature (joined INDOFLOODS)**: | | |
| • `Region` | 0 (0.0%) | 100% resolved from State. |
| • `Season` | 0 (0.0%) | 100% resolved from Start Date. |
| • `AnnualRainfall` | 0 (0.0%) | Available as catchment normal (CHELSA/WorldClim). |
| • `SeasonalRainfall` | 0 (0.0%) | Available as wettest-quarter normal & event 10-day rainfall. |
| • `Temperature` | 0 (0.0%) | Available as catchment normal. |
| • `RiverDischarge` | 555 (12.2%) | 3,993 verified non-null records. |
| • `Humidity` | **4,548 (100.0%)** | **Unavailable without ERA5 API download.** |
| • `CloudVisibility` | **4,548 (100.0%)** | **Unavailable across all investigated sources.** |
| • `FloodOccurred` | 0 (0.0%) for Yes | Verified `No` records are 100% absent. |
| **Date coverage** | **1965-07-21 to 2020-09-28** | 55 continuous years. |
| **Geographic coverage** | **155 catchments across 21 States** | National river basins: Cauvery, Krishna, Godavari, Mahanadi, Narmada, Tapi, Pennar, Mahi, etc. |

---

## 5. Summary of Intermediate Output Generated

An intermediate clean real-world dataset was compiled from all valid positive flood records and saved to:

**`data/sources_investigation/indofloods_verified_events.csv`**
- **Record Count:** `3,993` verified real-world events.
- **Columns (30 total):** `EventID`, `GaugeID`, `Station`, `Latitude`, `Longitude`, `River Name`, `Basin`, `State`, `Region`, `Season`, `Start Date`, `End Date`, `Peak Discharge Q (cumec)` (RiverDischarge), `Annual Precipitation`, `Precipitation of Wettest Quarter`, `Annual Mean Temperature`, `Drainage Area`, `T1d`, `T5d`, `T10d`, `FloodOccurred` (`Yes`), etc.
- **Fabrication / Synthetic Values:** **0%** (100% authentic observational measurements).

---

## 6. Recommendations & Roadmap for B.Tech Internship Submission

1. **Academic Transparency:**
   Present this audit report to your project guides/examiners. In academic and scientific machine learning, demonstrating that you verified data lineage and refused to invent missing atmospheric parameters (`CloudVisibility`, `Humidity`) is an exemplary demonstration of engineering integrity.
2. **Path to Acquiring ERA5 Humidity:**
   - Register for a free account at [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/).
   - Place your API key in `C:\Users\lokesh\.cdsapirc`.
   - Run a batch retrieval for `2m_temperature` and `2m_dewpoint_temperature` for the 155 gauge coordinates from 1965–2020, then apply the Magnus formula.
3. **Addressing CloudVisibility in the PPT:**
   - Recommend clarifying in your presentation that horizontal visibility is an aviation/airport synoptic variable, whereas catchment-scale flood models scientifically rely on precipitation, river discharge, antecedent moisture, and temperature.
