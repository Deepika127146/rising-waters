import pyarrow.dataset as ds
import pandas as pd
import numpy as np
import time

print("--- Testing Full Integration Pipeline ---")
t0 = time.time()

# 1. Load station matching report
sm = pd.read_csv('data/processed/station_matching_report.csv')
sm201 = sm.sort_values('Distance_km').iloc[:201].copy()
sm201['Spatially_Matched'] = True
print(f"Loaded {len(sm201)} spatially matched stations (max distance {sm201['Distance_km'].max():.2f} km).")

# Map station metadata
cwc_to_gauge = sm201.set_index('Station_Code_CWC')['GaugeID'].to_dict()
gauge_to_cwc = sm201.set_index('GaugeID')['Station_Code_CWC'].to_dict()
st_meta = sm201[['Station_Code_CWC', 'Warning_Level_CWC', 'Danger_Level_CWC', 'Start_date', 'End_date', 'State', 'Basin']].drop_duplicates(subset=['Station_Code_CWC']).rename(columns={'Station_Code_CWC': 'station_code'})

# 2. Load INDOFLOODS catchment characteristics
catch = pd.read_csv('data/sources_investigation/catchment_characteristics_indofloods.csv').set_index('GaugeID')
annual_precip_map = catch['Annual Precipitation'].to_dict()
wettest_quarter_map = catch['Precipitation of Wettest Quarter'].to_dict()
temp_map = catch['Annual Mean Temperature'].to_dict()

# Regional mapping rule from Stage 2
state_to_region = {
    'Karnataka': 'South', 'Kerala': 'South', 'Tamil Nadu': 'South', 'Andhra Pradesh': 'South', 'Telangana': 'South',
    'Maharashtra': 'West', 'Gujarat': 'West', 'Rajasthan': 'West', 'Dadra and Nagar Haveli': 'West',
    'Bihar': 'East', 'Odisha': 'East', 'West Bengal': 'East', 'Jharkhand': 'East', 'Tripura': 'East',
    'Madhya Pradesh': 'Central', 'Chhattisgarh': 'Central',
    'Uttar Pradesh': 'North', 'Uttarakhand': 'North', 'Haryana': 'North', 'Delhi': 'North', 'Himachal Pradesh': 'North'
}

# 3. Read CWC HHS from daily.parquet
cwc_codes = sm201['Station_Code_CWC'].unique().tolist()
dataset = ds.dataset('data/sources_investigation/daily.parquet', format='parquet')
filter_expr = (ds.field('datatype_code') == 'HHS') & (ds.field('station_code').isin(cwc_codes))
table = dataset.to_table(filter=filter_expr, columns=['station_code', 'date_ist', 'min', 'mean', 'max', 'n_obs'])
df_cwc = table.to_pandas()
print(f"Read {len(df_cwc):,} CWC HHS observations across {df_cwc['station_code'].nunique()} stations in {time.time()-t0:.2f}s.")

# Read CWC HQ0 (discharge)
filter_hq0 = (ds.field('datatype_code') == 'HQ0') & (ds.field('station_code').isin(cwc_codes))
table_hq0 = dataset.to_table(filter=filter_hq0, columns=['station_code', 'date_ist', 'mean'])
df_hq0 = table_hq0.to_pandas().rename(columns={'mean': 'discharge_cumec'})
print(f"Read {len(df_hq0):,} CWC HQ0 discharge observations in {time.time()-t0:.2f}s.")

# Merge HQ0 into HHS on (station_code, date_ist)
df_cwc = df_cwc.merge(df_hq0, on=['station_code', 'date_ist'], how='left')

# Merge station metadata
df_cwc = df_cwc.merge(st_meta, on='station_code', how='left')
df_cwc['GaugeID'] = df_cwc['station_code'].map(cwc_to_gauge)

# 4. Load INDOFLOODS verified positive records
pos = pd.read_csv('data/sources_investigation/indofloods_verified_events.csv')
print(f"Loaded {len(pos):,} verified INDOFLOODS positive flood events.")

# Map INDOFLOODS events to CWC stations and date keys
pos['Station_Code_CWC'] = pos['GaugeID'].map(gauge_to_cwc)
pos['peak_fl_date_str'] = pd.to_datetime(pos['Peak FL Date']).dt.strftime('%Y-%m-%d')
pos['key'] = pos['Station_Code_CWC'] + '_' + pos['peak_fl_date_str']

# Also create dictionary of event windows per station for fast lookup
event_windows = []
for _, r in pos.iterrows():
    if pd.notnull(r['Station_Code_CWC']):
        event_windows.append({
            'station_code': r['Station_Code_CWC'],
            'start': pd.to_datetime(r['Start Date']),
            'end': pd.to_datetime(r['End Date']),
            'discharge': r['Peak Discharge Q (cumec)'],
            'event_id': r['EventID']
        })
print(f"Mapped {len(event_windows)} event windows.")

# 5. Apply Data-Quality Filters to CWC records
df_cwc['date_dt'] = pd.to_datetime(df_cwc['date_ist'])
df_cwc['start_dt'] = pd.to_datetime(df_cwc['Start_date'])
df_cwc['end_dt'] = pd.to_datetime(df_cwc['End_date'])

is_nobs_valid = (df_cwc['n_obs'] >= 1)
is_nonsentinel = (df_cwc['max'] > -900) & (df_cwc['min'] > -900) & (df_cwc['mean'] > -900) & df_cwc['max'].notnull()
is_within_ops = (df_cwc['date_dt'] >= df_cwc['start_dt']) & (df_cwc['date_dt'] <= df_cwc['end_dt'])
has_thresholds = df_cwc['Danger_Level_CWC'].notnull() & df_cwc['Warning_Level_CWC'].notnull()

is_physically_plausible = (
    ((df_cwc['Danger_Level_CWC'] >= 10.0) & (df_cwc['max'] >= 0) & (df_cwc['max'] <= df_cwc['Danger_Level_CWC'] + 35.0)) |
    ((df_cwc['Danger_Level_CWC'] < 10.0) & (df_cwc['max'] >= 0) & (df_cwc['max'] <= 35.0))
)

valid_mask = is_nobs_valid & is_nonsentinel & is_within_ops & has_thresholds & is_physically_plausible

df_cwc['Label'] = 'Rejected'
# Initial CWC label
df_cwc.loc[valid_mask & (df_cwc['max'] < df_cwc['Warning_Level_CWC']) & (df_cwc['max'] < df_cwc['Danger_Level_CWC']), 'Label'] = 'No'
df_cwc.loc[valid_mask & (df_cwc['max'] >= df_cwc['Warning_Level_CWC']) & (df_cwc['max'] < df_cwc['Danger_Level_CWC']), 'Label'] = 'Uncertain'
df_cwc.loc[valid_mask & (df_cwc['max'] >= df_cwc['Danger_Level_CWC']), 'Label'] = 'Yes'

print("Initial CWC counts before event integration:")
print(df_cwc['Label'].value_counts())

# Check overlap with INDOFLOODS verified events
df_cwc['key'] = df_cwc['station_code'] + '_' + df_cwc['date_ist'].astype(str)
pos_keys = set(pos['key'])
overlap_peak_mask = df_cwc['key'].isin(pos_keys)
print(f"CWC records matching INDOFLOODS Peak FL Date exactly: {overlap_peak_mask.sum():,}")

# Overlap upgrade: if in INDOFLOODS verified event, upgrade to Yes
df_cwc.loc[overlap_peak_mask, 'Label'] = 'Yes'

# Attach INDOFLOODS discharge where CWC discharge is null but INDOFLOODS has it
peak_discharge_map = pos.set_index('key')['Peak Discharge Q (cumec)'].to_dict()
df_cwc['matched_event_discharge'] = df_cwc['key'].map(peak_discharge_map)
df_cwc['RiverDischarge'] = df_cwc['discharge_cumec'].fillna(df_cwc['matched_event_discharge'])

print("\nCWC counts after Peak FL Date event integration:")
print(df_cwc['Label'].value_counts())
