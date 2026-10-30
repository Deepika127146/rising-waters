import pyarrow.dataset as ds
import pandas as pd
import numpy as np
import os
import time

print("=================================================================")
print("  RISING WATERS - STAGE 3: REAL DATASET CONSTRUCTION & VALIDATION")
print("=================================================================")
t0 = time.time()

# Ensure processed directory exists
os.makedirs('data/processed', exist_ok=True)

# -------------------------------------------------------------------------
# TASK 2: STATION MATCHING REPORT
# -------------------------------------------------------------------------
print("\n--- Step 1: Generating Station Matching Report ---")
sm_raw = pd.read_csv('data/processed/station_matching_report.csv')

# Flag the 201 spatially matched stations (distance <= 6.05 km)
sm_raw['Spatially_Matched'] = sm_raw['Distance_km'] <= 6.05

# Sort by Distance_km
sm_sorted = sm_raw.sort_values('Distance_km').reset_index(drop=True)
sm_sorted.to_csv('data/processed/station_matching_report.csv', index=False)
print(f"Station matching report saved: {len(sm_sorted)} total stations.")
print(f"  - Spatially matched (<= 6.05 km): {sm_sorted['Spatially_Matched'].sum()} stations")
print(f"  - Outliers (> 6.05 km): {(~sm_sorted['Spatially_Matched']).sum()} stations")

sm201 = sm_sorted[sm_sorted['Spatially_Matched']].copy()
cwc_codes = sm201['Station_Code_CWC'].unique().tolist()
cwc_to_gauge = sm201.set_index('Station_Code_CWC')['GaugeID'].to_dict()
gauge_to_cwc = sm201.set_index('GaugeID')['Station_Code_CWC'].to_dict()
gauge_to_stname = sm201.set_index('GaugeID')['Station_INDOFLOODS'].to_dict()

st_meta = sm201[['Station_Code_CWC', 'Warning_Level_CWC', 'Danger_Level_CWC', 'Start_date', 'End_date', 'State', 'Basin']].drop_duplicates(subset=['Station_Code_CWC']).rename(columns={'Station_Code_CWC': 'station_code'})

# -------------------------------------------------------------------------
# TASK 3: EXTRACT DAILY CWC OBSERVATIONS (HHS and HQ0)
# -------------------------------------------------------------------------
print("\n--- Step 2: Extracting CWC HHS and HQ0 Observations ---")
dataset = ds.dataset('data/sources_investigation/daily.parquet', format='parquet')

# Filter HHS for the 201 stations
filter_hhs = (ds.field('datatype_code') == 'HHS') & (ds.field('station_code').isin(cwc_codes))
table_hhs = dataset.to_table(filter=filter_hhs, columns=['station_code', 'date_ist', 'min', 'mean', 'max', 'n_obs'])
df_cwc = table_hhs.to_pandas()
print(f"Raw HHS water-level records extracted: {len(df_cwc):,} rows across {df_cwc['station_code'].nunique()} stations.")

# Filter HQ0 (discharge)
filter_hq0 = (ds.field('datatype_code') == 'HQ0') & (ds.field('station_code').isin(cwc_codes))
table_hq0 = dataset.to_table(filter=filter_hq0, columns=['station_code', 'date_ist', 'mean'])
df_hq0 = table_hq0.to_pandas().rename(columns={'mean': 'discharge_cwc_cumec'})
print(f"Raw HQ0 discharge records extracted: {len(df_hq0):,} rows.")

# Merge HQ0 into HHS on (station_code, date_ist)
df_cwc = df_cwc.merge(df_hq0, on=['station_code', 'date_ist'], how='left')

# Merge station metadata
df_cwc = df_cwc.merge(st_meta, on='station_code', how='left')
df_cwc['GaugeID'] = df_cwc['station_code'].map(cwc_to_gauge)

# -------------------------------------------------------------------------
# TASK 4: APPLY DATA QUALITY FILTERS
# -------------------------------------------------------------------------
print("\n--- Step 3: Applying Hydrological Data Quality Filters ---")
df_cwc['date_dt'] = pd.to_datetime(df_cwc['date_ist'])
df_cwc['start_dt'] = pd.to_datetime(df_cwc['Start_date'])
df_cwc['end_dt'] = pd.to_datetime(df_cwc['End_date'])

# Quality check masks
f_nobs = df_cwc['n_obs'] >= 1
f_sentinel = (df_cwc['max'] > -900) & (df_cwc['min'] > -900) & (df_cwc['mean'] > -900) & df_cwc['max'].notnull()
f_ops = (df_cwc['date_dt'] >= df_cwc['start_dt']) & (df_cwc['date_dt'] <= df_cwc['end_dt'])
f_thresh = df_cwc['Danger_Level_CWC'].notnull() & df_cwc['Warning_Level_CWC'].notnull()

# Decimal placement and physical plausibility
# For elevation gauges (danger >= 10m): max >= 0 and max <= danger + 35m
# For stage gauges (danger < 10m): max >= 0 and max <= 35m
f_plausible = (
    ((df_cwc['Danger_Level_CWC'] >= 10.0) & (df_cwc['max'] >= 0) & (df_cwc['max'] <= df_cwc['Danger_Level_CWC'] + 35.0)) |
    ((df_cwc['Danger_Level_CWC'] < 10.0) & (df_cwc['max'] >= 0) & (df_cwc['max'] <= 35.0))
)

valid_mask = f_nobs & f_sentinel & f_ops & f_thresh & f_plausible

# Detail rejected reasons
rejection_sentinel = (~f_sentinel).sum()
rejection_ops = f_sentinel & (~f_ops)
rejection_thresh = f_sentinel & f_ops & (~f_thresh)
rejection_decimal = f_sentinel & f_ops & f_thresh & (~f_plausible)

print(f"Data Quality Filter Breakdown:")
print(f"  - Total Raw HHS Observations: {len(df_cwc):,}")
print(f"  - Rejected - Sentinels (max/min/mean < -900): {rejection_sentinel:,}")
print(f"  - Rejected - Outside Operational Dates: {rejection_ops.sum():,}")
print(f"  - Rejected - Missing Warning/Danger Thresholds: {rejection_thresh.sum():,}")
print(f"  - Rejected - Decimal/Datum Anomalies: {rejection_decimal.sum():,}")
print(f"  - Total Rejected Records: {(~valid_mask).sum():,}")
print(f"  - Total Valid Operational Records: {valid_mask.sum():,}")

# -------------------------------------------------------------------------
# TASK 5: CREATE LABELS CONSERVATIVELY
# -------------------------------------------------------------------------
print("\n--- Step 4: Initial Labeling of CWC Operational Observations ---")
df_cwc['Label'] = 'Rejected'
df_cwc.loc[valid_mask & (df_cwc['max'] < df_cwc['Warning_Level_CWC']) & (df_cwc['max'] < df_cwc['Danger_Level_CWC']), 'Label'] = 'No'
df_cwc.loc[valid_mask & (df_cwc['max'] >= df_cwc['Warning_Level_CWC']) & (df_cwc['max'] < df_cwc['Danger_Level_CWC']), 'Label'] = 'Uncertain'
df_cwc.loc[valid_mask & (df_cwc['max'] >= df_cwc['Danger_Level_CWC']), 'Label'] = 'Yes'

print("Initial CWC Operational Label Distribution:")
print(df_cwc['Label'].value_counts())

# -------------------------------------------------------------------------
# TASK 6: INTEGRATE 3,993 VERIFIED INDOFLOODS POSITIVE RECORDS
# -------------------------------------------------------------------------
print("\n--- Step 5: Integrating INDOFLOODS Verified Events & Resolving Conflicts ---")
pos = pd.read_csv('data/sources_investigation/indofloods_verified_events.csv')
print(f"Loaded {len(pos):,} verified INDOFLOODS positive flood events.")

pos['Station_Code_CWC'] = pos['GaugeID'].map(gauge_to_cwc)
pos['peak_fl_date_str'] = pd.to_datetime(pos['Peak FL Date']).dt.strftime('%Y-%m-%d')
pos['key'] = pos['Station_Code_CWC'] + '_' + pos['peak_fl_date_str']

df_cwc['key'] = df_cwc['station_code'] + '_' + df_cwc['date_ist'].astype(str)

# Match on exact peak flood date
pos_keys = set(pos['key'].dropna())
peak_match_mask = df_cwc['key'].isin(pos_keys)
print(f"CWC daily records matching INDOFLOODS Peak FL Date: {peak_match_mask.sum():,}")

# Upgrade CWC record to Yes upon independent ground-truth verification
df_cwc.loc[peak_match_mask, 'Label'] = 'Yes'

# Attach INDOFLOODS verified discharge to matched CWC record
peak_q_map = pos.set_index('key')['Peak Discharge Q (cumec)'].to_dict()
df_cwc['event_discharge'] = df_cwc['key'].map(peak_q_map)
df_cwc['RiverDischarge'] = df_cwc['discharge_cwc_cumec'].fillna(df_cwc['event_discharge'])

print("CWC Operational Label Distribution after Peak Date Integration:")
print(df_cwc['Label'].value_counts())

# Non-overlapping INDOFLOODS events (events occurring on dates without CWC digital HHS record)
matched_cwc_keys = set(df_cwc.loc[peak_match_mask, 'key'])
non_overlap_pos = pos[~pos['key'].isin(matched_cwc_keys)].copy()
print(f"INDOFLOODS verified events added independently (non-overlapping): {len(non_overlap_pos):,}")

# -------------------------------------------------------------------------
# TASK 7: METAR SURFACE VISIBILITY & HUMIDITY INTEGRATION
# -------------------------------------------------------------------------
print("\n--- Step 6: Integrating Real METAR Observations ---")
metar = pd.read_csv('data/sources_investigation/metar_matched_observations.csv')
print(f"Loaded {len(metar):,} real METAR airport observations.")

# Create lookup for METAR visibility and humidity on (Airport_Code, peak_dt)
metar_vsby_map = metar.set_index(['Airport_Code', 'peak_dt'])['vsby_km'].to_dict()
metar_relh_map = metar.set_index(['Airport_Code', 'peak_dt'])['relh_pct'].to_dict()

# Airport mapping for stations within 50 km
airports = [
    ('VOML', 'Mangaluru', 12.9613, 74.8901, 2000),
    ('VOTV', 'Thiruvananthapuram', 8.4821, 76.9200, 2000),
    ('VOTR', 'Tiruchirappalli', 10.7654, 78.7097, 2000),
    ('VOCL', 'Kozhikode', 11.1368, 75.9553, 2010),
    ('VOCI', 'Kochi', 10.1520, 76.4019, 2012),
    ('VAKP', 'Kolhapur', 16.6644, 74.2817, 2020)
]
a_df = pd.DataFrame(airports, columns=['code', 'name', 'lat', 'lon', 'start_yr'])

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

gauge_airport = {}
for _, r in sm201.iterrows():
    dists = haversine(r['Latitude_INDOFLOODS'], r['Longitude_INDOFLOODS'], a_df['lat'], a_df['lon'])
    min_idx = dists.idxmin()
    min_d = dists[min_idx]
    if min_d <= 50.0:
        gauge_airport[r['GaugeID']] = (a_df.loc[min_idx, 'code'], a_df.loc[min_idx, 'name'], round(min_d, 1), a_df.loc[min_idx, 'start_yr'])

# Attach METAR to INDOFLOODS positive events
pos['Airport_Code'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[0])
pos['Airport_Name'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[1])
pos['Airport_Dist_km'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[2])
pos['Airport_Start_Yr'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[3])
pos['Event_Year'] = pd.to_datetime(pos['Start Date']).dt.year

pos['CloudVisibility'] = np.nan
pos['Humidity'] = np.nan

for idx, r in pos.iterrows():
    acode = r['Airport_Code']
    pdt = r['peak_fl_date_str']
    if pd.notnull(acode) and (acode, pdt) in metar_vsby_map:
        pos.at[idx, 'CloudVisibility'] = metar_vsby_map[(acode, pdt)]
        pos.at[idx, 'Humidity'] = metar_relh_map[(acode, pdt)]

print(f"Positive records with matched real CloudVisibility: {pos['CloudVisibility'].notnull().sum()}")
print(f"Positive records with matched real Humidity: {pos['Humidity'].notnull().sum()}")

# -------------------------------------------------------------------------
# TASK 8: CONSTRUCT TRAINING DATASET
# -------------------------------------------------------------------------
print("\n--- Step 7: Constructing flood_training_dataset.csv ---")

# Load Catchment Attributes
catch = pd.read_csv('data/sources_investigation/catchment_characteristics_indofloods.csv').set_index('GaugeID')
annual_precip_map = catch['Annual Precipitation'].to_dict()
wettest_quarter_map = catch['Precipitation of Wettest Quarter'].to_dict()
temp_map = catch['Annual Mean Temperature'].to_dict()

state_to_region = {
    'Karnataka': 'South', 'Kerala': 'South', 'Tamil Nadu': 'South', 'Andhra Pradesh': 'South', 'Telangana': 'South',
    'Maharashtra': 'West', 'Gujarat': 'West', 'Rajasthan': 'West', 'Dadra and Nagar Haveli': 'West',
    'Bihar': 'East', 'Odisha': 'East', 'West Bengal': 'East', 'Jharkhand': 'East', 'Tripura': 'East',
    'Madhya Pradesh': 'Central', 'Chhattisgarh': 'Central',
    'Uttar Pradesh': 'North', 'Uttarakhand': 'North', 'Haryana': 'North', 'Delhi': 'North', 'Himachal Pradesh': 'North'
}

def derive_season(month):
    if month in [6, 7, 8, 9]:
        return 'Monsoon'
    elif month in [10, 11, 12]:
        return 'Post-Monsoon'
    elif month in [3, 4, 5]:
        return 'Summer'
    else:
        return 'Winter'

# Format all 3,993 verified positive INDOFLOODS records
pos_df = pd.DataFrame({
    'Region': pos['Region'],
    'Season': pos['Season'],
    'AnnualRainfall': pos['Annual Precipitation'],
    'SeasonalRainfall': pos['Precipitation of Wettest Quarter'],
    'CloudVisibility': pos['CloudVisibility'],
    'Humidity': pos['Humidity'],
    'Temperature': pos['Annual Mean Temperature'],
    'RiverDischarge': pos['Peak Discharge Q (cumec)'],
    'FloodOccurred': 'Yes',
    'Station': pos['Station'],
    'GaugeID': pos['GaugeID'],
    'Date': pos['Peak FL Date']
})

# Construct negative records (FloodOccurred = No)
# Filter verified negative CWC records
df_neg = df_cwc[df_cwc['Label'] == 'No'].copy()
df_neg['month'] = df_neg['date_dt'].dt.month
df_neg['Season'] = df_neg['month'].apply(derive_season)
df_neg['Region'] = df_neg['State'].map(state_to_region).fillna('Central')
df_neg['AnnualRainfall'] = df_neg['GaugeID'].map(annual_precip_map)
df_neg['SeasonalRainfall'] = df_neg['GaugeID'].map(wettest_quarter_map)
df_neg['Temperature'] = df_neg['GaugeID'].map(temp_map)
df_neg['Station'] = df_neg['GaugeID'].map(gauge_to_stname)
df_neg['Date'] = df_neg['date_ist']

# Check METAR matching for negative records near airports
df_neg['Airport_Code'] = df_neg['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[0])
df_neg['CloudVisibility'] = np.nan
df_neg['Humidity'] = np.nan
for idx, r in df_neg.iterrows():
    acode = r['Airport_Code']
    dstr = str(r['date_ist'])
    if pd.notnull(acode) and (acode, dstr) in metar_vsby_map:
        df_neg.at[idx, 'CloudVisibility'] = metar_vsby_map[(acode, dstr)]
        df_neg.at[idx, 'Humidity'] = metar_relh_map[(acode, dstr)]

# Sample a stratified negative cohort matching positive count (3,993 Yes : 3,993 No)
# Ensure comprehensive station coverage across all active stations (174 stations) and all 4 seasons
print(f"Sampling 3,993 verified negative records across all {df_neg['station_code'].nunique()} active monitoring stations...")

# Group by station and sample proportionally across diverse years and seasons
def sample_station_neg(grp):
    # Prioritize rows with measured discharge if available
    with_q = grp[grp['RiverDischarge'].notnull()]
    without_q = grp[grp['RiverDischarge'].isnull()]
    
    # Target ~23-25 per station
    n_target = 25
    if len(with_q) >= n_target:
        return with_q.sample(n=n_target, random_state=42)
    elif len(with_q) > 0:
        n_rem = min(n_target - len(with_q), len(without_q))
        sub_no_q = without_q.sample(n=n_rem, random_state=42) if n_rem > 0 else pd.DataFrame()
        return pd.concat([with_q, sub_no_q], ignore_index=True)
    else:
        return without_q.sample(n=min(len(without_q), n_target), random_state=42)

sampled_neg_by_st = df_neg.groupby('station_code', group_keys=False).apply(sample_station_neg)
if len(sampled_neg_by_st) > len(pos_df):
    selected_neg = sampled_neg_by_st.sample(n=len(pos_df), random_state=42).reset_index(drop=True)
else:
    selected_neg = sampled_neg_by_st.reset_index(drop=True)

print(f"Selected {len(selected_neg):,} verified negative records across {selected_neg['station_code'].nunique()} stations.")

neg_df = pd.DataFrame({
    'Region': selected_neg['Region'],
    'Season': selected_neg['Season'],
    'AnnualRainfall': selected_neg['AnnualRainfall'],
    'SeasonalRainfall': selected_neg['SeasonalRainfall'],
    'CloudVisibility': selected_neg['CloudVisibility'],
    'Humidity': selected_neg['Humidity'],
    'Temperature': selected_neg['Temperature'],
    'RiverDischarge': selected_neg['RiverDischarge'],
    'FloodOccurred': 'No',
    'Station': selected_neg['Station'],
    'GaugeID': selected_neg['GaugeID'],
    'Date': selected_neg['Date']
})

# Combine into training dataset
training_df_full = pd.concat([pos_df, neg_df], ignore_index=True)

# Shuffle deterministically
training_df_full = training_df_full.sample(frac=1.0, random_state=42).reset_index(drop=True)

# Required 8 input features + 1 target
target_cols = ['Region', 'Season', 'AnnualRainfall', 'SeasonalRainfall', 'CloudVisibility', 'Humidity', 'Temperature', 'RiverDischarge', 'FloodOccurred']
final_training_csv = training_df_full[target_cols].copy()

# Save training dataset
final_training_csv.to_csv('data/processed/flood_training_dataset.csv', index=False)
training_df_full.to_csv('data/processed/flood_training_dataset_with_metadata.csv', index=False)
print(f"\nFinal training dataset saved to data/processed/flood_training_dataset.csv")
print(f"  - Total Rows: {len(final_training_csv):,}")
print(f"  - Positive (Yes): {(final_training_csv['FloodOccurred'] == 'Yes').sum():,}")
print(f"  - Negative (No): {(final_training_csv['FloodOccurred'] == 'No').sum():,}")
print(f"  - Class Balance: {(final_training_csv['FloodOccurred'] == 'Yes').mean()*100:.1f}% Yes / {(final_training_csv['FloodOccurred'] == 'No').mean()*100:.1f}% No")

# Check duplicates
dups = final_training_csv.duplicated().sum()
print(f"  - Feature-level Duplicate Rows: {dups}")
st_date_dups = training_df_full.duplicated(subset=['Station', 'Date']).sum()
print(f"  - Station-Date Duplicates: {st_date_dups}")

# Missing values
print("\nMissing Values per Feature:")
for col in target_cols:
    null_cnt = final_training_csv[col].isnull().sum()
    null_pct = null_cnt / len(final_training_csv) * 100
    print(f"  - {col}: {null_cnt:,} ({null_pct:.1f}%)")

# Date and Station Coverage
dates = pd.to_datetime(training_df_full['Date'])
print(f"\nDataset Coverage:")
print(f"  - Unique Stations: {training_df_full['Station'].nunique()}")
print(f"  - Unique Gauges: {training_df_full['GaugeID'].nunique()}")
print(f"  - Date Range: {dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}")

# Save full verified archive as parquet for completeness
wl_map = sm201.set_index('Station_Code_CWC')['Warning_Level_CWC'].to_dict()
dl_map = sm201.set_index('Station_Code_CWC')['Danger_Level_CWC'].to_dict()
non_overlap_pos['Warning_Level_CWC'] = non_overlap_pos['Station_Code_CWC'].map(wl_map)
non_overlap_pos['Danger_Level_CWC'] = non_overlap_pos['Station_Code_CWC'].map(dl_map)

full_verified_records = pd.concat([
    df_cwc[df_cwc['Label'].isin(['Yes', 'No'])][['station_code', 'date_ist', 'max', 'Warning_Level_CWC', 'Danger_Level_CWC', 'RiverDischarge', 'Label']],
    non_overlap_pos[['Station_Code_CWC', 'Peak FL Date', 'Peak Flood Level (m)', 'Warning_Level_CWC', 'Danger_Level_CWC', 'Peak Discharge Q (cumec)', 'FloodOccurred']].rename(columns={
        'Station_Code_CWC': 'station_code', 'Peak FL Date': 'date_ist', 'Peak Flood Level (m)': 'max', 'Peak Discharge Q (cumec)': 'RiverDischarge', 'FloodOccurred': 'Label'
    })
], ignore_index=True)
full_verified_records['date_ist'] = pd.to_datetime(full_verified_records['date_ist'])
full_verified_records.to_parquet('data/processed/flood_dataset_full_verified.parquet', index=False)
print(f"\nFull verified archive saved to data/processed/flood_dataset_full_verified.parquet: {len(full_verified_records):,} rows.")

print(f"\nExecution completed in {time.time()-t0:.2f}s.")
