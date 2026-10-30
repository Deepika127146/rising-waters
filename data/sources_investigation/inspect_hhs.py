import pyarrow.dataset as ds
import pandas as pd
import numpy as np

sm = pd.read_csv('data/processed/station_matching_report.csv')
sm201 = sm.sort_values('Distance_km').iloc[:201].copy()

cwc_codes = sm201['Station_Code_CWC'].unique().tolist()
print(f'Querying {len(cwc_codes)} station codes...')

dataset = ds.dataset('data/sources_investigation/daily.parquet', format='parquet')
filter_expr = (ds.field('datatype_code') == 'HHS') & (ds.field('station_code').isin(cwc_codes))

table = dataset.to_table(filter=filter_expr, columns=['station_code', 'date_ist', 'min', 'mean', 'max', 'n_obs'])
df = table.to_pandas()

print(f'Total extracted raw HHS rows for 201 stations: {len(df):,}')
print(f'Unique station codes with HHS data: {df["station_code"].nunique()} / {len(cwc_codes)}')

# Check n_obs
print(f'Rows with n_obs == 0: {(df["n_obs"] == 0).sum():,}')
print(f'Rows with n_obs >= 1: {(df["n_obs"] >= 1).sum():,}')

# Check sentinels
print(f'Rows with max < -900: {(df["max"] < -900).sum():,}')
print(f'Rows with null max: {df["max"].isnull().sum():,}')
print(f'Rows with min < -900: {(df["min"] < -900).sum():,}')
print(f'Rows with mean < -900: {(df["mean"] < -900).sum():,}')

# Join station metadata (warning, danger, start_date, end_date)
# If multiple GaugeIDs map to same station_code, group or drop duplicates
st_meta = sm201[['Station_Code_CWC', 'Warning_Level_CWC', 'Danger_Level_CWC', 'Start_date', 'End_date']].drop_duplicates(subset=['Station_Code_CWC']).rename(columns={'Station_Code_CWC': 'station_code'})
df = df.merge(st_meta, on='station_code', how='left')

print('\nMerged with thresholds:')
print(f'Rows with null Danger_Level_CWC: {df["Danger_Level_CWC"].isnull().sum():,}')
print(f'Rows with null Warning_Level_CWC: {df["Warning_Level_CWC"].isnull().sum():,}')

# Operational date check
df['date_ist'] = pd.to_datetime(df['date_ist'])
df['Start_date'] = pd.to_datetime(df['Start_date'])
df['End_date'] = pd.to_datetime(df['End_date'])

outside_ops = (df['date_ist'] < df['Start_date']) | (df['date_ist'] > df['End_date'])
print(f'Rows outside station operational dates: {outside_ops.sum():,}')

# Valid non-sentinel, n_obs >= 1, non-null danger/warning
valid_base = (df['n_obs'] >= 1) & (df['max'] > -900) & (df['max'].notnull()) & (~outside_ops) & (df['Danger_Level_CWC'].notnull())
print(f'Rows passing base filters (n_obs>=1, non-sentinel, within ops dates, danger level present): {valid_base.sum():,}')

# Examine max vs danger level
df_valid = df[valid_base].copy()
ratio = df_valid['max'] / df_valid['Danger_Level_CWC']
print('Distribution of max / Danger_Level_CWC:')
print(ratio.describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99, 0.999]))

# Check extreme anomalies (e.g. ratio > 2.0 or 3.0 or max > 2000)
extreme_anomalies = ratio > 3.0
print(f'Decimal/datum anomalies (ratio > 3.0): {extreme_anomalies.sum():,}')
if extreme_anomalies.sum() > 0:
    print(df_valid[extreme_anomalies][['station_code', 'date_ist', 'max', 'Danger_Level_CWC']].head(10))
