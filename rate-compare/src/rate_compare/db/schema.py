"""Database schema definitions."""

import sqlite3


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all database tables."""

    # Medicare rates table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicare_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hcpcs_code TEXT NOT NULL,
            modifier TEXT,
            carrier TEXT NOT NULL,
            locality TEXT NOT NULL,
            state TEXT,
            locality_name TEXT,
            non_facility_fee REAL,
            facility_fee REAL,
            status_code TEXT,
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_medicare_hcpcs ON medicare_rates(hcpcs_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_medicare_state ON medicare_rates(state)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_medicare_carrier_locality ON medicare_rates(carrier, locality)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_medicare_year ON medicare_rates(year)")

    # Payer rates table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payer_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hcpcs_code TEXT NOT NULL,
            modifier TEXT,
            payer_name TEXT NOT NULL,
            payer_type TEXT NOT NULL,
            state TEXT,
            non_facility_fee REAL,
            facility_fee REAL,
            percent_of_medicare REAL,
            effective_date TEXT,
            source TEXT,
            year INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_payer_hcpcs ON payer_rates(hcpcs_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payer_name ON payer_rates(payer_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_payer_state ON payer_rates(state)")

    # Localities reference table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS localities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            carrier TEXT NOT NULL,
            locality TEXT NOT NULL,
            state TEXT NOT NULL,
            locality_name TEXT,
            year INTEGER NOT NULL,
            UNIQUE(carrier, locality, year)
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_localities_state ON localities(state)")
