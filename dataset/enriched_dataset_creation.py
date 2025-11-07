"""
Reads the raw csv files and creates a new, combined csv, with relevant information from each csv
"""
import pandas as pd
import numpy as np

# file paths
sessions_path = 'dataset/charging_sessions.csv'
stations_path = 'dataset/charging_stations.csv'
customers_path = 'dataset/customers.csv'
districts_path = 'dataset/districts.csv'
out_path = 'dataset/sessions_enriched.csv'

# load dataframes
sessions = pd.read_csv(sessions_path, skipinitialspace=True)
stations = pd.read_csv(stations_path, skipinitialspace=True)
customers = pd.read_csv(customers_path, skipinitialspace=True)
districts = pd.read_csv(districts_path, skipinitialspace=True)

# clean strings
for df in (sessions, stations, customers, districts):
    for c in df.select_dtypes(include='object').columns:
          df[c] = df[c].astype(str).str.strip()
          
# dtype fixes
# sessions
sessions['session_start_time'] = pd.to_datetime(sessions['session_start_time'], errors='coerce')
for c in ['kwh_charged', 'cost_per_kwh', 'total_cost']:
    if c in sessions.columns:
        sessions[c] = pd.to_numeric(sessions[c], errors='coerce')

# stations
if "plugs_count" in stations.columns:
    stations['plugs_count'] = pd.to_numeric(stations['plugs_count'], errors='coerce')
for c in ['latitude', 'longitude']:
    if c in stations.columns:
        stations[c] = pd.to_numeric(stations[c], errors='coerce')
        
# customers
if "battery_capacity_kwh" in customers.columns:
    customers["battery_capacity_kwh"] = pd.to_numeric(customers["battery_capacity_kwh"], errors='coerce')
    
# districts
for c in ['projected_evs', 'projected_plugs', 'projected_regular_customers']:
    if c in districts.columns:
        districts[c] = pd.to_numeric(districts[c], errors='coerce')
        
# rename overlapping columns
if 'income_tier' in stations.columns:
    stations = stations.rename(columns={'income_tier': 'station_income_tier'})
if 'income_tier' in customers.columns:
    customers = customers.rename(columns={'income_tier': 'customer_income_tier'})
if 'income_tier' in districts.columns:
    districts = districts.rename(columns={'income_tier': 'district_income_tier'})    
# join: sessions <- stations <- customers <- districts (left joins to keep all sessions)
se = (
    sessions
        .merge(stations, on='station_id', how='left')
    .merge(customers, on='customer_id', how='left')
        .merge(districts, on='district_name', how='left')
)

# derived columns
dt = se['session_start_time']
se['hour'] = dt.dt.hour
se['dow'] = dt.dt.dayofweek
se['is_weekend'] = se['dow'].isin([5, 6]).astype(int)

se['price_per_kwh_realized'] = (
    se['total_cost'] / se['kwh_charged']
).replace([np.inf, -np.inf], np.nan)

# keep relevant fields
cols = [
    # original session fields
    'session_id', 'customer_id', 'station_id', 'session_start_time', 'kwh_charged', 'cost_per_kwh', 'total_cost',
    # station context
    'district_name', 'station_income_tier', 'operator_name', 'plugs_count', 'latitude', 'longitude',
    # customer context
    'customer_income_tier', 'car_model', 'battery_capacity_kwh',
    # district context
    'district_income_tier', 'projected_evs', 'projected_plugs', 'projected_regular_customers',
    # derived
    'price_per_kwh_realized', 'hour', 'dow', 'is_weekend'
]
cols = [c for c in cols if c in se.columns]

se = se[cols].copy()

print(se.shape)

# write csv
se.to_csv(out_path, index=False)
print(f'Saved enriched data to {out_path}')
