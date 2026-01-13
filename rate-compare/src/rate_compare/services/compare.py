"""Rate comparison service."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator, Optional

from rate_compare.db.database import get_connection, init_db
from rate_compare.models.payer import PayerRate
from rate_compare.services.lookup import get_medicare_rates_by_state


def import_payer_data(records: Iterator[PayerRate]) -> int:
    """Import payer rates into database.

    Args:
        records: Iterator of PayerRate objects

    Returns:
        Number of records imported
    """
    init_db()
    count = 0

    with get_connection() as conn:
        for record in records:
            conn.execute(
                """
                INSERT INTO payer_rates
                (hcpcs_code, modifier, payer_name, payer_type, state,
                 non_facility_fee, facility_fee, percent_of_medicare,
                 effective_date, source, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.hcpcs_code,
                    record.modifier,
                    record.payer_name,
                    record.payer_type,
                    record.state,
                    float(record.non_facility_fee) if record.non_facility_fee else None,
                    float(record.facility_fee) if record.facility_fee else None,
                    float(record.percent_of_medicare) if record.percent_of_medicare else None,
                    record.effective_date,
                    record.source,
                    record.year,
                ),
            )
            count += 1

    return count


def get_payer_rate(
    hcpcs_code: str,
    payer_name: str,
    state: Optional[str],
    year: int,
    modifier: Optional[str] = None,
) -> Optional[PayerRate]:
    """Get rate for a specific payer."""
    with get_connection() as conn:
        if state:
            row = conn.execute(
                """
                SELECT * FROM payer_rates
                WHERE hcpcs_code = ? AND payer_name = ? AND state = ? AND year = ?
                AND (modifier = ? OR modifier IS NULL)
                LIMIT 1
                """,
                (hcpcs_code.upper(), payer_name, state.upper(), year, modifier),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM payer_rates
                WHERE hcpcs_code = ? AND payer_name = ? AND year = ?
                AND (modifier = ? OR modifier IS NULL)
                LIMIT 1
                """,
                (hcpcs_code.upper(), payer_name, year, modifier),
            ).fetchone()

        if row:
            return _row_to_payer_rate(row)
    return None


def get_payers(year: int) -> list[dict]:
    """Get list of all payers with record counts."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT payer_name, payer_type, COUNT(*) as count,
                   COUNT(DISTINCT state) as states,
                   MIN(created_at) as first_import
            FROM payer_rates
            WHERE year = ?
            GROUP BY payer_name, payer_type
            ORDER BY payer_name
            """,
            (year,),
        ).fetchall()

        return [
            {
                "payer_name": row["payer_name"],
                "payer_type": row["payer_type"],
                "record_count": row["count"],
                "states": row["states"],
                "first_import": row["first_import"],
            }
            for row in rows
        ]


def delete_payer(payer_name: str, year: int) -> int:
    """Delete all rates for a payer.

    Returns:
        Number of records deleted
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM payer_rates WHERE payer_name = ? AND year = ?",
            (payer_name, year),
        )
        return cursor.rowcount


def clear_payer_data(year: int) -> None:
    """Clear all payer data for a year."""
    with get_connection() as conn:
        conn.execute("DELETE FROM payer_rates WHERE year = ?", (year,))


@dataclass
class RateComparison:
    """Comparison result for a single payer."""

    payer_name: str
    payer_type: str
    non_facility_fee: Optional[Decimal]
    facility_fee: Optional[Decimal]
    percent_of_medicare: Optional[float]


def compare_rates(
    hcpcs_code: str,
    state: str,
    year: int,
    facility: bool = False,
) -> list[RateComparison]:
    """Compare Medicare rate with all payer rates.

    Args:
        hcpcs_code: HCPCS/CPT code
        state: State abbreviation
        year: Fee schedule year
        facility: If True, use facility rates

    Returns:
        List of RateComparison objects (Medicare first, then payers)
    """
    results = []

    # Get Medicare rate
    medicare_rates = get_medicare_rates_by_state(hcpcs_code, state, year)
    if medicare_rates:
        medicare = medicare_rates[0]  # Use first locality
        medicare_fee = medicare.facility_fee if facility else medicare.non_facility_fee

        results.append(RateComparison(
            payer_name="Medicare (CMS)",
            payer_type="government",
            non_facility_fee=medicare.non_facility_fee,
            facility_fee=medicare.facility_fee,
            percent_of_medicare=100.0,
        ))
    else:
        medicare_fee = None

    # Get payer rates
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM payer_rates
            WHERE hcpcs_code = ? AND (state = ? OR state IS NULL) AND year = ?
            ORDER BY payer_name
            """,
            (hcpcs_code.upper(), state.upper(), year),
        ).fetchall()

        for row in rows:
            payer = _row_to_payer_rate(row)
            payer_fee = payer.facility_fee if facility else payer.non_facility_fee

            # Calculate percent of Medicare
            pct = None
            if payer.percent_of_medicare:
                pct = float(payer.percent_of_medicare)
            elif medicare_fee and payer_fee and medicare_fee > 0:
                pct = float(payer_fee / medicare_fee * 100)

            results.append(RateComparison(
                payer_name=payer.payer_name,
                payer_type=payer.payer_type,
                non_facility_fee=payer.non_facility_fee,
                facility_fee=payer.facility_fee,
                percent_of_medicare=pct,
            ))

    return results


def _row_to_payer_rate(row) -> PayerRate:
    """Convert database row to PayerRate."""
    return PayerRate(
        hcpcs_code=row["hcpcs_code"],
        payer_name=row["payer_name"],
        payer_type=row["payer_type"],
        year=row["year"],
        modifier=row["modifier"],
        state=row["state"],
        non_facility_fee=Decimal(str(row["non_facility_fee"])) if row["non_facility_fee"] else None,
        facility_fee=Decimal(str(row["facility_fee"])) if row["facility_fee"] else None,
        percent_of_medicare=Decimal(str(row["percent_of_medicare"])) if row["percent_of_medicare"] else None,
        effective_date=row["effective_date"],
        source=row["source"],
    )
