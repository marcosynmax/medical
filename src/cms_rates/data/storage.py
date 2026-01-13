"""SQLite database storage for CMS data."""

import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Optional

from cms_rates.config import get_db_path, ensure_data_dirs
from cms_rates.models.rvu import RVURecord
from cms_rates.models.gpci import GPCIRecord
from cms_rates.models.payer import PayerRate


SCHEMA = """
-- RVU table
CREATE TABLE IF NOT EXISTS rvu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hcpcs_code TEXT NOT NULL,
    modifier TEXT,
    description TEXT,
    status_code TEXT,
    work_rvu REAL,
    non_facility_pe_rvu REAL,
    facility_pe_rvu REAL,
    malpractice_rvu REAL,
    conversion_factor REAL,
    global_days TEXT,
    year INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rvu_hcpcs ON rvu(hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_rvu_hcpcs_mod ON rvu(hcpcs_code, modifier);
CREATE INDEX IF NOT EXISTS idx_rvu_year ON rvu(year);

-- GPCI table
CREATE TABLE IF NOT EXISTS gpci (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier TEXT NOT NULL,
    locality TEXT NOT NULL,
    locality_name TEXT,
    state TEXT,
    work_gpci REAL,
    pe_gpci REAL,
    mp_gpci REAL,
    year INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gpci_carrier_locality ON gpci(carrier, locality);
CREATE INDEX IF NOT EXISTS idx_gpci_state ON gpci(state);
CREATE INDEX IF NOT EXISTS idx_gpci_year ON gpci(year);

-- Metadata table for version tracking
CREATE TABLE IF NOT EXISTS data_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    source_file TEXT,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER
);

-- Payer rates table for commercial/Medicaid rate comparison
CREATE TABLE IF NOT EXISTS payer_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hcpcs_code TEXT NOT NULL,
    modifier TEXT,
    payer_name TEXT NOT NULL,
    payer_type TEXT NOT NULL,
    state TEXT,
    facility_rate REAL,
    non_facility_rate REAL,
    percent_of_medicare REAL,
    effective_date TEXT,
    expiration_date TEXT,
    source TEXT,
    year INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payer_hcpcs ON payer_rates(hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_payer_name ON payer_rates(payer_name);
CREATE INDEX IF NOT EXISTS idx_payer_state ON payer_rates(state);
CREATE INDEX IF NOT EXISTS idx_payer_year ON payer_rates(year);
"""


@contextmanager
def get_connection():
    """Get a database connection context manager."""
    ensure_data_dirs()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> None:
    """Initialize the database schema."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def clear_rvu_data(year: int) -> None:
    """Clear RVU data for a specific year."""
    with get_connection() as conn:
        conn.execute("DELETE FROM rvu WHERE year = ?", (year,))
        conn.commit()


def clear_gpci_data(year: int) -> None:
    """Clear GPCI data for a specific year."""
    with get_connection() as conn:
        conn.execute("DELETE FROM gpci WHERE year = ?", (year,))
        conn.commit()


def insert_rvu_records(records: Iterator[RVURecord]) -> int:
    """Insert RVU records into the database.

    Args:
        records: Iterator of RVURecord objects

    Returns:
        Number of records inserted
    """
    count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for record in records:
            cursor.execute(
                """
                INSERT INTO rvu (
                    hcpcs_code, modifier, description, status_code,
                    work_rvu, non_facility_pe_rvu, facility_pe_rvu, malpractice_rvu,
                    conversion_factor, global_days, year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.hcpcs_code,
                    record.modifier,
                    record.description,
                    record.status_code,
                    float(record.work_rvu),
                    float(record.non_facility_pe_rvu),
                    float(record.facility_pe_rvu),
                    float(record.malpractice_rvu),
                    float(record.conversion_factor),
                    record.global_days,
                    record.year,
                ),
            )
            count += 1
            if count % 1000 == 0:
                conn.commit()
        conn.commit()
    return count


def insert_gpci_records(records: Iterator[GPCIRecord]) -> int:
    """Insert GPCI records into the database.

    Args:
        records: Iterator of GPCIRecord objects

    Returns:
        Number of records inserted
    """
    count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for record in records:
            cursor.execute(
                """
                INSERT INTO gpci (
                    carrier, locality, locality_name, state,
                    work_gpci, pe_gpci, mp_gpci, year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.carrier,
                    record.locality,
                    record.locality_name,
                    record.state,
                    float(record.work_gpci),
                    float(record.pe_gpci),
                    float(record.mp_gpci),
                    record.year,
                ),
            )
            count += 1
        conn.commit()
    return count


def get_rvu(
    hcpcs_code: str,
    year: int,
    modifier: Optional[str] = None
) -> Optional[RVURecord]:
    """Get RVU data for a specific code.

    Args:
        hcpcs_code: CPT or HCPCS code
        year: Fee schedule year
        modifier: Optional modifier code

    Returns:
        RVURecord if found, None otherwise
    """
    with get_connection() as conn:
        if modifier:
            row = conn.execute(
                """
                SELECT * FROM rvu
                WHERE hcpcs_code = ? AND year = ? AND modifier = ?
                LIMIT 1
                """,
                (hcpcs_code.upper(), year, modifier.upper()),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM rvu
                WHERE hcpcs_code = ? AND year = ? AND (modifier IS NULL OR modifier = '')
                LIMIT 1
                """,
                (hcpcs_code.upper(), year),
            ).fetchone()

        if not row:
            # Try without modifier constraint
            row = conn.execute(
                """
                SELECT * FROM rvu
                WHERE hcpcs_code = ? AND year = ?
                ORDER BY modifier NULLS FIRST
                LIMIT 1
                """,
                (hcpcs_code.upper(), year),
            ).fetchone()

        if row:
            return RVURecord(
                hcpcs_code=row["hcpcs_code"],
                modifier=row["modifier"],
                description=row["description"],
                status_code=row["status_code"],
                work_rvu=Decimal(str(row["work_rvu"])),
                non_facility_pe_rvu=Decimal(str(row["non_facility_pe_rvu"])),
                facility_pe_rvu=Decimal(str(row["facility_pe_rvu"])),
                malpractice_rvu=Decimal(str(row["malpractice_rvu"])),
                conversion_factor=Decimal(str(row["conversion_factor"])),
                global_days=row["global_days"],
                year=row["year"],
            )
    return None


def get_gpci(carrier: str, locality: str, year: int) -> Optional[GPCIRecord]:
    """Get GPCI data for a specific locality.

    Args:
        carrier: MAC carrier number
        locality: Locality code
        year: Fee schedule year

    Returns:
        GPCIRecord if found, None otherwise
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM gpci
            WHERE carrier = ? AND locality = ? AND year = ?
            LIMIT 1
            """,
            (carrier, locality, year),
        ).fetchone()

        if row:
            return GPCIRecord(
                carrier=row["carrier"],
                locality=row["locality"],
                locality_name=row["locality_name"],
                state=row["state"],
                work_gpci=Decimal(str(row["work_gpci"])),
                pe_gpci=Decimal(str(row["pe_gpci"])),
                mp_gpci=Decimal(str(row["mp_gpci"])),
                year=row["year"],
            )
    return None


def get_gpci_by_state(state: str, year: int) -> list[GPCIRecord]:
    """Get all GPCI records for a state.

    Args:
        state: State abbreviation (e.g., "CA")
        year: Fee schedule year

    Returns:
        List of GPCIRecord objects for the state
    """
    results = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM gpci
            WHERE state = ? AND year = ?
            ORDER BY locality_name
            """,
            (state.upper(), year),
        ).fetchall()

        for row in rows:
            results.append(GPCIRecord(
                carrier=row["carrier"],
                locality=row["locality"],
                locality_name=row["locality_name"],
                state=row["state"],
                work_gpci=Decimal(str(row["work_gpci"])),
                pe_gpci=Decimal(str(row["pe_gpci"])),
                mp_gpci=Decimal(str(row["mp_gpci"])),
                year=row["year"],
            ))
    return results


def has_data(year: int) -> bool:
    """Check if data exists for a given year."""
    try:
        with get_connection() as conn:
            rvu_count = conn.execute(
                "SELECT COUNT(*) FROM rvu WHERE year = ?", (year,)
            ).fetchone()[0]
            gpci_count = conn.execute(
                "SELECT COUNT(*) FROM gpci WHERE year = ?", (year,)
            ).fetchone()[0]
        return rvu_count > 0 and gpci_count > 0
    except sqlite3.OperationalError:
        return False


def get_all_localities(year: int) -> list[GPCIRecord]:
    """Get all localities for a given year."""
    results = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM gpci
            WHERE year = ?
            ORDER BY state, locality_name
            """,
            (year,),
        ).fetchall()

        for row in rows:
            results.append(GPCIRecord(
                carrier=row["carrier"],
                locality=row["locality"],
                locality_name=row["locality_name"],
                state=row["state"],
                work_gpci=Decimal(str(row["work_gpci"])),
                pe_gpci=Decimal(str(row["pe_gpci"])),
                mp_gpci=Decimal(str(row["mp_gpci"])),
                year=row["year"],
            ))
    return results


def search_by_description(query: str, year: int, limit: int = 50) -> list[RVURecord]:
    """Search for CPT codes by description.

    Args:
        query: Search query (matches against description)
        year: Fee schedule year
        limit: Maximum number of results to return

    Returns:
        List of matching RVURecord objects
    """
    results = []
    with get_connection() as conn:
        # Use LIKE for case-insensitive search
        search_pattern = f"%{query}%"
        rows = conn.execute(
            """
            SELECT * FROM rvu
            WHERE year = ? AND description LIKE ?
            ORDER BY hcpcs_code
            LIMIT ?
            """,
            (year, search_pattern, limit),
        ).fetchall()

        for row in rows:
            results.append(RVURecord(
                hcpcs_code=row["hcpcs_code"],
                modifier=row["modifier"],
                description=row["description"],
                status_code=row["status_code"],
                work_rvu=Decimal(str(row["work_rvu"])),
                non_facility_pe_rvu=Decimal(str(row["non_facility_pe_rvu"])),
                facility_pe_rvu=Decimal(str(row["facility_pe_rvu"])),
                malpractice_rvu=Decimal(str(row["malpractice_rvu"])),
                conversion_factor=Decimal(str(row["conversion_factor"])),
                global_days=row["global_days"],
                year=row["year"],
            ))
    return results


# Payer rate functions

def insert_payer_rate(rate: PayerRate) -> int:
    """Insert a payer rate into the database.

    Args:
        rate: PayerRate object to insert

    Returns:
        ID of the inserted record
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO payer_rates (
                hcpcs_code, modifier, payer_name, payer_type, state,
                facility_rate, non_facility_rate, percent_of_medicare,
                effective_date, expiration_date, source, year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rate.hcpcs_code.upper(),
                rate.modifier.upper() if rate.modifier else None,
                rate.payer_name,
                rate.payer_type,
                rate.state.upper() if rate.state else None,
                float(rate.facility_rate) if rate.facility_rate else None,
                float(rate.non_facility_rate) if rate.non_facility_rate else None,
                float(rate.percent_of_medicare) if rate.percent_of_medicare else None,
                rate.effective_date,
                rate.expiration_date,
                rate.source,
                rate.year,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def insert_payer_rates(rates: Iterator[PayerRate]) -> int:
    """Insert multiple payer rates into the database.

    Args:
        rates: Iterator of PayerRate objects

    Returns:
        Number of records inserted
    """
    count = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        for rate in rates:
            cursor.execute(
                """
                INSERT INTO payer_rates (
                    hcpcs_code, modifier, payer_name, payer_type, state,
                    facility_rate, non_facility_rate, percent_of_medicare,
                    effective_date, expiration_date, source, year
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rate.hcpcs_code.upper(),
                    rate.modifier.upper() if rate.modifier else None,
                    rate.payer_name,
                    rate.payer_type,
                    rate.state.upper() if rate.state else None,
                    float(rate.facility_rate) if rate.facility_rate else None,
                    float(rate.non_facility_rate) if rate.non_facility_rate else None,
                    float(rate.percent_of_medicare) if rate.percent_of_medicare else None,
                    rate.effective_date,
                    rate.expiration_date,
                    rate.source,
                    rate.year,
                ),
            )
            count += 1
            if count % 1000 == 0:
                conn.commit()
        conn.commit()
    return count


def get_payer_rates(
    hcpcs_code: str,
    year: int,
    state: Optional[str] = None,
    payer_name: Optional[str] = None,
    modifier: Optional[str] = None
) -> list[PayerRate]:
    """Get payer rates for a specific CPT code.

    Args:
        hcpcs_code: CPT or HCPCS code
        year: Fee schedule year
        state: Optional state filter
        payer_name: Optional payer name filter
        modifier: Optional modifier code

    Returns:
        List of PayerRate objects
    """
    results = []
    with get_connection() as conn:
        query = "SELECT * FROM payer_rates WHERE hcpcs_code = ? AND year = ?"
        params = [hcpcs_code.upper(), year]

        if state:
            query += " AND (state = ? OR state IS NULL)"
            params.append(state.upper())

        if payer_name:
            query += " AND payer_name = ?"
            params.append(payer_name)

        if modifier:
            query += " AND (modifier = ? OR modifier IS NULL)"
            params.append(modifier.upper())

        query += " ORDER BY payer_name"

        rows = conn.execute(query, params).fetchall()

        for row in rows:
            results.append(PayerRate(
                hcpcs_code=row["hcpcs_code"],
                modifier=row["modifier"],
                payer_name=row["payer_name"],
                payer_type=row["payer_type"],
                state=row["state"],
                facility_rate=Decimal(str(row["facility_rate"])) if row["facility_rate"] else None,
                non_facility_rate=Decimal(str(row["non_facility_rate"])) if row["non_facility_rate"] else None,
                percent_of_medicare=Decimal(str(row["percent_of_medicare"])) if row["percent_of_medicare"] else None,
                effective_date=row["effective_date"],
                expiration_date=row["expiration_date"],
                source=row["source"],
                year=row["year"],
            ))
    return results


def get_all_payers(year: Optional[int] = None) -> list[dict]:
    """Get all unique payers in the database.

    Args:
        year: Optional year filter

    Returns:
        List of dicts with payer_name, payer_type, state, and rate_count
    """
    results = []
    with get_connection() as conn:
        if year:
            rows = conn.execute(
                """
                SELECT payer_name, payer_type, state, COUNT(*) as rate_count
                FROM payer_rates
                WHERE year = ?
                GROUP BY payer_name, payer_type, state
                ORDER BY payer_name, state
                """,
                (year,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT payer_name, payer_type, state, COUNT(*) as rate_count
                FROM payer_rates
                GROUP BY payer_name, payer_type, state
                ORDER BY payer_name, state
                """
            ).fetchall()

        for row in rows:
            results.append({
                "payer_name": row["payer_name"],
                "payer_type": row["payer_type"],
                "state": row["state"],
                "rate_count": row["rate_count"],
            })
    return results


def delete_payer_rates(
    payer_name: str,
    year: Optional[int] = None,
    state: Optional[str] = None
) -> int:
    """Delete payer rates from the database.

    Args:
        payer_name: Name of payer to delete rates for
        year: Optional year filter
        state: Optional state filter

    Returns:
        Number of records deleted
    """
    with get_connection() as conn:
        query = "DELETE FROM payer_rates WHERE payer_name = ?"
        params = [payer_name]

        if year:
            query += " AND year = ?"
            params.append(year)

        if state:
            query += " AND state = ?"
            params.append(state.upper())

        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount


def clear_payer_rates(payer_name: Optional[str] = None, year: Optional[int] = None) -> int:
    """Clear payer rates from the database.

    Args:
        payer_name: Optional payer name to clear (all if None)
        year: Optional year to clear (all years if None)

    Returns:
        Number of records deleted
    """
    with get_connection() as conn:
        if payer_name and year:
            cursor = conn.execute(
                "DELETE FROM payer_rates WHERE payer_name = ? AND year = ?",
                (payer_name, year)
            )
        elif payer_name:
            cursor = conn.execute(
                "DELETE FROM payer_rates WHERE payer_name = ?",
                (payer_name,)
            )
        elif year:
            cursor = conn.execute(
                "DELETE FROM payer_rates WHERE year = ?",
                (year,)
            )
        else:
            cursor = conn.execute("DELETE FROM payer_rates")
        conn.commit()
        return cursor.rowcount
