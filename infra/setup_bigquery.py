#!/usr/bin/env python3
"""Setup BigQuery dataset and tables for geography metadata index.

Creates:
- Dataset: geography_index
- Tables: countries, states, districts with sample Indian geography data
"""

import os
import sys
from google.cloud import bigquery
from google.api_core.exceptions import Forbidden, NotFound

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
DATASET_ID = "geography_index"
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4")

if not PROJECT_ID:
    print("Error: GOOGLE_CLOUD_PROJECT environment variable must be set")
    sys.exit(1)

client = bigquery.Client(project=PROJECT_ID)

def check_table_has_data(table_id: str) -> bool:
    """Check if table has data without running a query (workaround for permission issues)."""
    try:
        # Try to get table info
        table = client.get_table(table_id)
        # If num_rows > 0, we have data
        return table.num_rows > 0
    except (Forbidden, NotFound):
        # Table doesn't exist or no permission
        return False
    except Exception as e:
        print(f"Warning: Could not check if table has data: {e}")
        return False

# Create dataset
dataset_id = f"{PROJECT_ID}.{DATASET_ID}"
dataset = bigquery.Dataset(dataset_id)
dataset.location = LOCATION
dataset.description = "Geography metadata index for countries, states, and districts"

try:
    dataset = client.create_dataset(dataset, exists_ok=True)
    print(f"✓ Created dataset {dataset_id}")
except Exception as e:
    print(f"✓ Dataset {dataset_id} already exists or created")

# Create countries table
countries_schema = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("capital", "STRING"),
    bigquery.SchemaField("population", "INT64"),
    bigquery.SchemaField("area_km2", "FLOAT64"),
]

countries_table_id = f"{dataset_id}.countries"
countries_table = bigquery.Table(countries_table_id, schema=countries_schema)

try:
    countries_table = client.create_table(countries_table, exists_ok=True)
    print(f"✓ Created table {countries_table_id}")
except Exception as e:
    print(f"✓ Table {countries_table_id} already exists")

# Insert sample country data
countries_data = [
    {"id": 1, "name": "India", "capital": "New Delhi", "population": 1428000000, "area_km2": 3287263.0},
]

# Check if data already exists
if not check_table_has_data(countries_table_id):
    try:
        errors = client.insert_rows_json(countries_table_id, countries_data)
        if errors:
            print(f"Errors inserting countries: {errors}")
        else:
            print(f"✓ Inserted {len(countries_data)} countries")
    except Exception as e:
        print(f"⚠️ Could not insert countries data: {e}")
else:
    print(f"✓ Countries table already has data")

# Create states table
states_schema = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("country_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("capital", "STRING"),
    bigquery.SchemaField("population", "INT64"),
    bigquery.SchemaField("area_km2", "FLOAT64"),
]

states_table_id = f"{dataset_id}.states"
states_table = bigquery.Table(states_table_id, schema=states_schema)

try:
    states_table = client.create_table(states_table, exists_ok=True)
    print(f"✓ Created table {states_table_id}")
except Exception as e:
    print(f"✓ Table {states_table_id} already exists")

# Insert all 28 states of India
states_data = [
    {"id": 1, "country_id": 1, "name": "Andhra Pradesh", "capital": "Amaravati", "population": 49386799, "area_km2": 160205.0},
    {"id": 2, "country_id": 1, "name": "Arunachal Pradesh", "capital": "Itanagar", "population": 1382611, "area_km2": 83743.0},
    {"id": 3, "country_id": 1, "name": "Assam", "capital": "Dispur", "population": 31169272, "area_km2": 78438.0},
    {"id": 4, "country_id": 1, "name": "Bihar", "capital": "Patna", "population": 103804637, "area_km2": 94163.0},
    {"id": 5, "country_id": 1, "name": "Chhattisgarh", "capital": "Raipur", "population": 25540196, "area_km2": 135192.0},
    {"id": 6, "country_id": 1, "name": "Goa", "capital": "Panaji", "population": 1457723, "area_km2": 3702.0},
    {"id": 7, "country_id": 1, "name": "Gujarat", "capital": "Gandhinagar", "population": 60383628, "area_km2": 196244.0},
    {"id": 8, "country_id": 1, "name": "Haryana", "capital": "Chandigarh", "population": 25353081, "area_km2": 44212.0},
    {"id": 9, "country_id": 1, "name": "Himachal Pradesh", "capital": "Shimla", "population": 6856509, "area_km2": 55673.0},
    {"id": 10, "country_id": 1, "name": "Jharkhand", "capital": "Ranchi", "population": 32966238, "area_km2": 79716.0},
    {"id": 11, "country_id": 1, "name": "Karnataka", "capital": "Bengaluru", "population": 61130704, "area_km2": 191791.0},
    {"id": 12, "country_id": 1, "name": "Kerala", "capital": "Thiruvananthapuram", "population": 33387677, "area_km2": 38852.0},
    {"id": 13, "country_id": 1, "name": "Madhya Pradesh", "capital": "Bhopal", "population": 72597565, "area_km2": 308245.0},
    {"id": 14, "country_id": 1, "name": "Maharashtra", "capital": "Mumbai", "population": 112372972, "area_km2": 307713.0},
    {"id": 15, "country_id": 1, "name": "Manipur", "capital": "Imphal", "population": 2721756, "area_km2": 22327.0},
    {"id": 16, "country_id": 1, "name": "Meghalaya", "capital": "Shillong", "population": 2964007, "area_km2": 22429.0},
    {"id": 17, "country_id": 1, "name": "Mizoram", "capital": "Aizawl", "population": 1091014, "area_km2": 21081.0},
    {"id": 18, "country_id": 1, "name": "Nagaland", "capital": "Kohima", "population": 1980602, "area_km2": 16579.0},
    {"id": 19, "country_id": 1, "name": "Odisha", "capital": "Bhubaneswar", "population": 41947358, "area_km2": 155707.0},
    {"id": 20, "country_id": 1, "name": "Punjab", "capital": "Chandigarh", "population": 27704236, "area_km2": 50362.0},
    {"id": 21, "country_id": 1, "name": "Rajasthan", "capital": "Jaipur", "population": 68621012, "area_km2": 342239.0},
    {"id": 22, "country_id": 1, "name": "Sikkim", "capital": "Gangtok", "population": 607688, "area_km2": 7096.0},
    {"id": 23, "country_id": 1, "name": "Tamil Nadu", "capital": "Chennai", "population": 72138958, "area_km2": 130060.0},
    {"id": 24, "country_id": 1, "name": "Telangana", "capital": "Hyderabad", "population": 35193978, "area_km2": 112077.0},
    {"id": 25, "country_id": 1, "name": "Tripura", "capital": "Agartala", "population": 3671032, "area_km2": 10486.0},
    {"id": 26, "country_id": 1, "name": "Uttar Pradesh", "capital": "Lucknow", "population": 199581477, "area_km2": 240928.0},
    {"id": 27, "country_id": 1, "name": "Uttarakhand", "capital": "Dehradun", "population": 10116752, "area_km2": 53483.0},
    {"id": 28, "country_id": 1, "name": "West Bengal", "capital": "Kolkata", "population": 91347736, "area_km2": 88752.0},
]

if not check_table_has_data(states_table_id):
    try:
        errors = client.insert_rows_json(states_table_id, states_data)
        if errors:
            print(f"Errors inserting states: {errors}")
        else:
            print(f"✓ Inserted {len(states_data)} states")
    except Exception as e:
        print(f"⚠️ Could not insert states data: {e}")
else:
    print(f"✓ States table already has data")

# Create districts table
districts_schema = [
    bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("state_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("headquarters", "STRING"),
    bigquery.SchemaField("population", "INT64"),
    bigquery.SchemaField("area_km2", "FLOAT64"),
]

districts_table_id = f"{dataset_id}.districts"
districts_table = bigquery.Table(districts_table_id, schema=districts_schema)

try:
    districts_table = client.create_table(districts_table, exists_ok=True)
    print(f"✓ Created table {districts_table_id}")
except Exception as e:
    print(f"✓ Table {districts_table_id} already exists")

# Insert sample district data
districts_data = [
    # Maharashtra districts (state_id: 14)
    {"id": 1, "state_id": 14, "name": "Mumbai", "headquarters": "Mumbai", "population": 12442373, "area_km2": 603.4},
    {"id": 2, "state_id": 14, "name": "Pune", "headquarters": "Pune", "population": 9429408, "area_km2": 15642.0},
    {"id": 3, "state_id": 14, "name": "Nagpur", "headquarters": "Nagpur", "population": 4653171, "area_km2": 9892.0},
    # Karnataka districts (state_id: 11)
    {"id": 4, "state_id": 11, "name": "Bengaluru Urban", "headquarters": "Bengaluru", "population": 9621551, "area_km2": 2190.0},
    {"id": 5, "state_id": 11, "name": "Mysuru", "headquarters": "Mysuru", "population": 3001127, "area_km2": 6854.0},
    # Tamil Nadu districts (state_id: 23)
    {"id": 6, "state_id": 23, "name": "Chennai", "headquarters": "Chennai", "population": 7088000, "area_km2": 426.0},
    {"id": 7, "state_id": 23, "name": "Coimbatore", "headquarters": "Coimbatore", "population": 3458045, "area_km2": 7469.0},
]

if not check_table_has_data(districts_table_id):
    try:
        errors = client.insert_rows_json(districts_table_id, districts_data)
        if errors:
            print(f"Errors inserting districts: {errors}")
        else:
            print(f"✓ Inserted {len(districts_data)} districts")
    except Exception as e:
        print(f"⚠️ Could not insert districts data: {e}")
else:
    print(f"✓ Districts table already has data")

print("\n✅ BigQuery setup complete!")
print(f"Dataset: {dataset_id}")
print(f"Tables: countries ({len(countries_data)}), states ({len(states_data)}), districts ({len(districts_data)})")
print("\nNote: The BigQuery agent currently uses embedded data in its instruction,")
print("not database queries. This setup creates tables for consistency and future use.")
