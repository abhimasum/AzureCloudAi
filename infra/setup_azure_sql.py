#!/usr/bin/env python3
"""Setup Azure SQL Database and tables for geography metadata index.

Creates:
- Database: geography_index
- Tables: countries, states, districts with sample Indian geography data
"""

import os
import sys
import pyodbc

# Azure SQL connection details from environment variables
SERVER = os.environ.get("AZURE_SQL_SERVER")  # e.g., "yourserver.database.windows.net"
DATABASE = os.environ.get("AZURE_SQL_DATABASE", "geography_index")
USERNAME = os.environ.get("AZURE_SQL_USERNAME")
PASSWORD = os.environ.get("AZURE_SQL_PASSWORD")

if not all([SERVER, USERNAME, PASSWORD]):
    print("Error: Set AZURE_SQL_SERVER, AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD environment variables")
    sys.exit(1)

# Connection string for Azure SQL
connection_string = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USERNAME};"
    f"PWD={PASSWORD};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
)

print(f"Connecting to Azure SQL Server: {SERVER}")
print(f"Database: {DATABASE}")

try:
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    print("✓ Connected to Azure SQL Database")
except Exception as e:
    print(f"✗ Failed to connect: {e}")
    sys.exit(1)

# Create countries table
print("\nCreating countries table...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'countries')
    BEGIN
        CREATE TABLE countries (
            id INT PRIMARY KEY,
            name NVARCHAR(100) NOT NULL,
            capital NVARCHAR(100)
        )
    END
""")
conn.commit()
print("✓ Countries table created")

# Insert sample data (India)
cursor.execute("SELECT COUNT(*) FROM countries")
if cursor.fetchone()[0] == 0:
    cursor.execute("""
        INSERT INTO countries (id, name, capital) VALUES (1, 'India', 'New Delhi')
    """)
    conn.commit()
    print("✓ Inserted sample country: India")
else:
    print("✓ Countries table already has data")

# Create states table
print("\nCreating states table...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'states')
    BEGIN
        CREATE TABLE states (
            id INT PRIMARY KEY,
            name NVARCHAR(100) NOT NULL,
            capital NVARCHAR(100),
            country_id INT NOT NULL,
            FOREIGN KEY (country_id) REFERENCES countries(id)
        )
    END
""")
conn.commit()
print("✓ States table created")

# Insert all 28 Indian states + 8 union territories
cursor.execute("SELECT COUNT(*) FROM states")
if cursor.fetchone()[0] == 0:
    states_data = [
        (1, 'Andhra Pradesh', 'Amaravati', 1),
        (2, 'Arunachal Pradesh', 'Itanagar', 1),
        (3, 'Assam', 'Dispur', 1),
        (4, 'Bihar', 'Patna', 1),
        (5, 'Chhattisgarh', 'Raipur', 1),
        (6, 'Goa', 'Panaji', 1),
        (7, 'Gujarat', 'Gandhinagar', 1),
        (8, 'Haryana', 'Chandigarh', 1),
        (9, 'Himachal Pradesh', 'Shimla', 1),
        (10, 'Jharkhand', 'Ranchi', 1),
        (11, 'Karnataka', 'Bengaluru', 1),
        (12, 'Kerala', 'Thiruvananthapuram', 1),
        (13, 'Madhya Pradesh', 'Bhopal', 1),
        (14, 'Maharashtra', 'Mumbai', 1),
        (15, 'Manipur', 'Imphal', 1),
        (16, 'Meghalaya', 'Shillong', 1),
        (17, 'Mizoram', 'Aizawl', 1),
        (18, 'Nagaland', 'Kohima', 1),
        (19, 'Odisha', 'Bhubaneswar', 1),
        (20, 'Punjab', 'Chandigarh', 1),
        (21, 'Rajasthan', 'Jaipur', 1),
        (22, 'Sikkim', 'Gangtok', 1),
        (23, 'Tamil Nadu', 'Chennai', 1),
        (24, 'Telangana', 'Hyderabad', 1),
        (25, 'Tripura', 'Agartala', 1),
        (26, 'Uttar Pradesh', 'Lucknow', 1),
        (27, 'Uttarakhand', 'Dehradun', 1),
        (28, 'West Bengal', 'Kolkata', 1),
        (29, 'Andaman and Nicobar Islands', 'Port Blair', 1),
        (30, 'Chandigarh', 'Chandigarh', 1),
        (31, 'Dadra and Nagar Haveli and Daman and Diu', 'Daman', 1),
        (32, 'Delhi', 'New Delhi', 1),
        (33, 'Jammu and Kashmir', 'Srinagar', 1),
        (34, 'Ladakh', 'Leh', 1),
        (35, 'Lakshadweep', 'Kavaratti', 1),
        (36, 'Puducherry', 'Puducherry', 1),
    ]
    
    cursor.executemany("""
        INSERT INTO states (id, name, capital, country_id) VALUES (?, ?, ?, ?)
    """, states_data)
    conn.commit()
    print(f"✓ Inserted {len(states_data)} states/UTs")
else:
    print("✓ States table already has data")

# Create districts table
print("\nCreating districts table...")
cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'districts')
    BEGIN
        CREATE TABLE districts (
            id INT PRIMARY KEY,
            name NVARCHAR(100) NOT NULL,
            state_id INT NOT NULL,
            FOREIGN KEY (state_id) REFERENCES states(id)
        )
    END
""")
conn.commit()
print("✓ Districts table created")

# Insert sample districts
cursor.execute("SELECT COUNT(*) FROM districts")
if cursor.fetchone()[0] == 0:
    districts_data = [
        (1, 'Mumbai City', 14),
        (2, 'Mumbai Suburban', 14),
        (3, 'Pune', 14),
        (4, 'Nagpur', 14),
        (5, 'Thane', 14),
        (6, 'Bengaluru Urban', 11),
        (7, 'Mysuru', 11),
        (8, 'Chennai', 23),
        (9, 'Coimbatore', 23),
        (10, 'Lucknow', 26),
        (11, 'Kanpur Nagar', 26),
        (12, 'Kolkata', 28),
        (13, 'North 24 Parganas', 28),
    ]
    
    cursor.executemany("""
        INSERT INTO districts (id, name, state_id) VALUES (?, ?, ?)
    """, districts_data)
    conn.commit()
    print(f"✓ Inserted {len(districts_data)} districts")
else:
    print("✓ Districts table already has data")

# Verify data
print("\n=== Database Summary ===")
cursor.execute("SELECT COUNT(*) FROM countries")
print(f"Countries: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM states")
print(f"States/UTs: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM districts")
print(f"Districts: {cursor.fetchone()[0]}")

cursor.close()
conn.close()
print("\n✓ Azure SQL Database setup complete!")
