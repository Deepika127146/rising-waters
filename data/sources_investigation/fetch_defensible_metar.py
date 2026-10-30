import urllib.request
import http.client
import pandas as pd
import numpy as np
import io
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

print("=== Fetching Defensible Real METAR Data (IEM ASOS) ===")
t0 = time.time()

meta = pd.read_csv('data/sources_investigation/metadata_indofloods.csv').dropna(subset=['Latitude', 'Longitude'])
pos = pd.read_csv('data/sources_investigation/indofloods_verified_events.csv')

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
for _, r in meta.iterrows():
    dists = haversine(r['Latitude'], r['Longitude'], a_df['lat'], a_df['lon'])
    min_idx = dists.idxmin()
    min_d = dists[min_idx]
    if min_d <= 50.0:
        gauge_airport[r['GaugeID']] = (a_df.loc[min_idx, 'code'], a_df.loc[min_idx, 'name'], round(min_d, 1), a_df.loc[min_idx, 'start_yr'])

pos['Airport_Code'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[0])
pos['Airport_Name'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[1])
pos['Airport_Dist_km'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[2])
pos['Airport_Start_Yr'] = pos['GaugeID'].map(lambda g: gauge_airport.get(g, (None, None, None, None))[3])
pos['Event_Year'] = pd.to_datetime(pos['Start Date']).dt.year

valid = pos[pos['Airport_Code'].notnull() & (pos['Event_Year'] >= pos['Airport_Start_Yr'])].copy()
valid['peak_dt'] = pd.to_datetime(valid['Peak FL Date']).dt.strftime('%Y-%m-%d')
tasks = valid[['Airport_Code', 'peak_dt']].drop_duplicates().values.tolist()
print(f"Total unique (Airport, Peak Date) tasks to fetch: {len(tasks)}")

def fetch_single_date(airport, date_str):
    dt = pd.to_datetime(date_str)
    url = f'https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station={airport}&data=tmpc&data=dwpc&data=relh&data=vsby&year1={dt.year}&month1={dt.month}&day1={dt.day}&year2={dt.year}&month2={dt.month}&day2={dt.day}&tz=Asia%2FKolkata&format=onlycomma&latlon=yes'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
    except http.client.IncompleteRead as exc:
        data = exc.partial
    except Exception:
        return airport, date_str, None, None, None, 0

    try:
        df = pd.read_csv(io.StringIO(data.decode('utf-8', errors='ignore')), comment='#')
        if len(df) == 0:
            return airport, date_str, None, None, None, 0
        
        # vsby is in miles -> convert to km (1 mile = 1.60934 km)
        vsby_vals = pd.to_numeric(df['vsby'], errors='coerce') * 1.60934
        relh_vals = pd.to_numeric(df['relh'], errors='coerce')
        tmpc_vals = pd.to_numeric(df['tmpc'], errors='coerce')
        
        mean_vsby = round(vsby_vals.mean(), 2) if vsby_vals.notnull().sum() > 0 else None
        mean_relh = round(relh_vals.mean(), 2) if relh_vals.notnull().sum() > 0 else None
        mean_tmpc = round(tmpc_vals.mean(), 2) if tmpc_vals.notnull().sum() > 0 else None
        n_readings = len(df)
        return airport, date_str, mean_vsby, mean_relh, mean_tmpc, n_readings
    except Exception:
        return airport, date_str, None, None, None, 0

results = []
completed = 0
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(fetch_single_date, code, d): (code, d) for code, d in tasks}
    for fut in as_completed(futures):
        res = fut.result()
        results.append(res)
        completed += 1
        if completed % 25 == 0 or completed == len(tasks):
            print(f"Progress: {completed}/{len(tasks)} ({time.time()-t0:.1f}s)")

res_df = pd.DataFrame(results, columns=['Airport_Code', 'peak_dt', 'vsby_km', 'relh_pct', 'tmpc_degc', 'n_obs'])
os.makedirs('data/sources_investigation', exist_ok=True)
res_df.to_csv('data/sources_investigation/metar_matched_observations.csv', index=False)

print(f"Saved {len(res_df)} METAR observations to data/sources_investigation/metar_matched_observations.csv")
print(f"Successful non-null vsby: {res_df['vsby_km'].notnull().sum()} / {len(res_df)}")
print(f"Successful non-null relh: {res_df['relh_pct'].notnull().sum()} / {len(res_df)}")
print(res_df[res_df['vsby_km'].notnull()].head(10))
