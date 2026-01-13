"""Medicare rate lookup service."""

from decimal import Decimal
from pathlib import Path
from typing import Iterator, Optional

from rate_compare.db.database import get_connection, init_db
from rate_compare.models.medicare import MedicareRate, get_locality_info
from rate_compare.parsers.cms_parser import parse_cms_file


def import_medicare_data(
    file_path: Path,
    year: int = 2026,
    clear_existing: bool = False,
    progress_callback: Optional[callable] = None,
) -> int:
    """Import Medicare rates from CMS Payment Amount file.

    Args:
        file_path: Path to PFALL26A format file
        year: Fee schedule year
        clear_existing: If True, clear existing data for the year
        progress_callback: Optional callback for progress updates

    Returns:
        Number of records imported
    """
    init_db()

    with get_connection() as conn:
        if clear_existing:
            conn.execute("DELETE FROM medicare_rates WHERE year = ?", (year,))
            conn.execute("DELETE FROM localities WHERE year = ?", (year,))

        # Track localities
        localities_seen = set()
        count = 0
        batch = []
        batch_size = 5000

        for record in parse_cms_file(file_path, year):
            batch.append(record)

            # Track locality
            loc_key = (record.carrier, record.locality)
            if loc_key not in localities_seen:
                localities_seen.add(loc_key)
                _insert_locality(conn, record)

            # Insert in batches
            if len(batch) >= batch_size:
                _insert_batch(conn, batch)
                count += len(batch)
                batch = []
                if progress_callback:
                    progress_callback(count)

        # Insert remaining records
        if batch:
            _insert_batch(conn, batch)
            count += len(batch)

    return count


def _insert_batch(conn, records: list[MedicareRate]) -> None:
    """Insert a batch of records."""
    conn.executemany(
        """
        INSERT INTO medicare_rates
        (hcpcs_code, modifier, carrier, locality, state, locality_name,
         non_facility_fee, facility_fee, status_code, year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.hcpcs_code,
                r.modifier,
                r.carrier,
                r.locality,
                r.state,
                r.locality_name,
                float(r.non_facility_fee),
                float(r.facility_fee),
                r.status_code,
                r.year,
            )
            for r in records
        ],
    )


def _insert_locality(conn, record: MedicareRate) -> None:
    """Insert a locality record if not exists."""
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO localities (carrier, locality, state, locality_name, year)
            VALUES (?, ?, ?, ?, ?)
            """,
            (record.carrier, record.locality, record.state, record.locality_name, record.year),
        )
    except Exception:
        pass


def get_medicare_rate(
    hcpcs_code: str,
    carrier: str,
    locality: str,
    year: int,
    modifier: Optional[str] = None,
) -> Optional[MedicareRate]:
    """Get Medicare rate for specific code and locality."""
    with get_connection() as conn:
        if modifier:
            row = conn.execute(
                """
                SELECT * FROM medicare_rates
                WHERE hcpcs_code = ? AND carrier = ? AND locality = ? AND year = ?
                AND (modifier = ? OR modifier IS NULL)
                LIMIT 1
                """,
                (hcpcs_code.upper(), carrier, locality, year, modifier),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM medicare_rates
                WHERE hcpcs_code = ? AND carrier = ? AND locality = ? AND year = ?
                AND (modifier IS NULL OR modifier = '')
                LIMIT 1
                """,
                (hcpcs_code.upper(), carrier, locality, year),
            ).fetchone()

        if row:
            return _row_to_medicare_rate(row)
    return None


def get_medicare_rates_by_state(
    hcpcs_code: str,
    state: str,
    year: int,
    modifier: Optional[str] = None,
) -> list[MedicareRate]:
    """Get all Medicare rates for a code in a state."""
    with get_connection() as conn:
        if modifier:
            rows = conn.execute(
                """
                SELECT * FROM medicare_rates
                WHERE hcpcs_code = ? AND state = ? AND year = ?
                AND (modifier = ? OR modifier IS NULL)
                ORDER BY locality_name
                """,
                (hcpcs_code.upper(), state.upper(), year, modifier),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM medicare_rates
                WHERE hcpcs_code = ? AND state = ? AND year = ?
                AND (modifier IS NULL OR modifier = '')
                ORDER BY locality_name
                """,
                (hcpcs_code.upper(), state.upper(), year),
            ).fetchall()

        return [_row_to_medicare_rate(row) for row in rows]


def get_localities_by_state(state: str, year: int) -> list[dict]:
    """Get all localities for a state."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT carrier, locality, state, locality_name
            FROM localities
            WHERE state = ? AND year = ?
            ORDER BY locality_name
            """,
            (state.upper(), year),
        ).fetchall()

        return [
            {
                "carrier": row["carrier"],
                "locality": row["locality"],
                "state": row["state"],
                "locality_name": row["locality_name"],
            }
            for row in rows
        ]


def get_all_states(year: int) -> list[str]:
    """Get all states with data for a year."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT state FROM localities
            WHERE year = ? AND state IS NOT NULL
            ORDER BY state
            """,
            (year,),
        ).fetchall()
        return [row["state"] for row in rows]


def search_medicare_codes(query: str, year: int, limit: int = 50) -> list[str]:
    """Search for HCPCS codes matching a query."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT hcpcs_code FROM medicare_rates
            WHERE hcpcs_code LIKE ? AND year = ?
            ORDER BY hcpcs_code
            LIMIT ?
            """,
            (f"{query.upper()}%", year, limit),
        ).fetchall()
        return [row["hcpcs_code"] for row in rows]


def has_medicare_data(year: int) -> bool:
    """Check if Medicare data exists for a year."""
    try:
        with get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM medicare_rates WHERE year = ?", (year,)
            ).fetchone()[0]
        return count > 0
    except Exception:
        return False


def clear_medicare_data(year: int) -> None:
    """Clear all Medicare data for a year."""
    with get_connection() as conn:
        conn.execute("DELETE FROM medicare_rates WHERE year = ?", (year,))
        conn.execute("DELETE FROM localities WHERE year = ?", (year,))


def _row_to_medicare_rate(row) -> MedicareRate:
    """Convert database row to MedicareRate."""
    return MedicareRate(
        hcpcs_code=row["hcpcs_code"],
        carrier=row["carrier"],
        locality=row["locality"],
        non_facility_fee=Decimal(str(row["non_facility_fee"])),
        facility_fee=Decimal(str(row["facility_fee"])),
        year=row["year"],
        modifier=row["modifier"],
        state=row["state"],
        locality_name=row["locality_name"],
        status_code=row["status_code"],
    )
