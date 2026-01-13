"""Parser for CMS Physician Fee Schedule Payment Amount files (PFALL26A format)."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Optional

from rate_compare.models.medicare import MedicareRate, get_locality_info


def parse_cms_file(file_path: Path, year: int = 2026) -> Iterator[MedicareRate]:
    """Parse a CMS Payment Amount file.

    Args:
        file_path: Path to the PFALL26A format file
        year: Fee schedule year

    Yields:
        MedicareRate objects
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip trailer records and short rows
            if len(row) < 10 or row[0].startswith("TRL"):
                continue

            record = _parse_row(row, year)
            if record:
                yield record


def _parse_row(row: list[str], year: int) -> Optional[MedicareRate]:
    """Parse a single row into a MedicareRate.

    CSV Format:
    0: Year
    1: Carrier (5 digits)
    2: Locality (2 digits)
    3: HCPCS Code
    4: Modifier
    5: Non-Facility Fee
    6: Facility Fee
    7: Filler
    8: PCTC Indicator
    9: Status Code
    """
    try:
        # Extract fields
        carrier = row[1].strip()
        locality = row[2].strip()
        hcpcs_code = row[3].strip()
        modifier = row[4].strip() if row[4].strip() else None
        non_fac_fee = _parse_fee(row[5])
        fac_fee = _parse_fee(row[6])
        status_code = row[9].strip() if len(row) > 9 else None

        # Skip records with zero fees
        if non_fac_fee == Decimal("0") and fac_fee == Decimal("0"):
            return None

        # Get state and locality name
        state, locality_name = get_locality_info(carrier, locality)

        return MedicareRate(
            hcpcs_code=hcpcs_code,
            carrier=carrier,
            locality=locality,
            non_facility_fee=non_fac_fee,
            facility_fee=fac_fee,
            year=year,
            modifier=modifier,
            state=state,
            locality_name=locality_name,
            status_code=status_code,
        )

    except (IndexError, ValueError):
        return None


def _parse_fee(fee_str: str) -> Decimal:
    """Parse fee string like '0000098.25' to Decimal."""
    try:
        return Decimal(fee_str.strip())
    except Exception:
        return Decimal("0")
