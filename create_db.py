import sqlite3

# Connect & Create DB
conn = sqlite3.connect('agri.db')
cursor = conn.cursor()

# Create 'users' table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        location TEXT,
        soil_type TEXT,
        land_size REAL,
        water_source TEXT,
        preferred_crops TEXT
    )
''')

conn.commit()
conn.close()

print("agri.db created successfully with 'users' table.")
