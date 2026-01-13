"""Parser for CMS Physician Fee Schedule Payment Amount File (PFALL26A format)."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Optional

from cms_rates.models.payment import PaymentRecord, get_carrier_locality_info


def parse_payment_file(file_path: Path) -> Iterator[PaymentRecord]:
    """Parse a CMS Physician Fee Schedule Payment Amount file.

    Args:
        file_path: Path to the PFALL26A.txt file

    Yields:
        PaymentRecord objects for each valid record
    """
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip trailer record (starts with "TRL")
            if len(row) < 10 or row[0] == "TRL" or (len(row[0]) >= 3 and row[0][0:3] == "TRL"):
                continue

            try:
                record = parse_payment_row(row)
                if record:
                    yield record
            except (ValueError, IndexError) as e:
                # Skip malformed rows
                continue


def parse_payment_row(row: list[str]) -> Optional[PaymentRecord]:
    """Parse a single row from the payment file.

    Row format (CSV fields):
    0: Year (e.g., "2026")
    1: Carrier Number (e.g., "01112")
    2: Locality (e.g., "05")
    3: HCPCS Code (e.g., "99213")
    4: Modifier (e.g., "26", "TC", or blank)
    5: Non-Facility Fee (e.g., "0000090.16")
    6: Facility Fee (e.g., "0000067.89")
    7: Filler
    8: PCTC Indicator (0-9)
    9: Status Code (A, B, C, etc.)
    10: Multiple Surgery Indicator
    11-15: Additional fields (therapy reduction, OPPS, etc.)

    Args:
        row: List of CSV field values

    Returns:
        PaymentRecord or None if invalid
    """
    if len(row) < 10:
        return None

    year = row[0].strip()
    carrier = row[1].strip()
    locality = row[2].strip()
    hcpcs_code = row[3].strip()
    modifier = row[4].strip() if row[4].strip() else None
    non_facility_fee_str = row[5].strip()
    facility_fee_str = row[6].strip()
    pctc_indicator = row[8].strip() if len(row) > 8 else "0"
    status_code = row[9].strip() if len(row) > 9 else "A"
    multi_surgery = row[10].strip() if len(row) > 10 else "0"

    # Parse fee amounts (format: "0000090.16" = $90.16)
    try:
        non_facility_fee = Decimal(non_facility_fee_str) if non_facility_fee_str else Decimal("0")
        facility_fee = Decimal(facility_fee_str) if facility_fee_str else Decimal("0")
    except Exception:
        non_facility_fee = Decimal("0")
        facility_fee = Decimal("0")

    # Skip records with no fees (likely carrier-priced or excluded)
    if non_facility_fee == 0 and facility_fee == 0:
        return None

    try:
        year_int = int(year)
    except ValueError:
        return None

    return PaymentRecord(
        hcpcs_code=hcpcs_code,
        modifier=modifier,
        carrier=carrier,
        locality=locality,
        non_facility_fee=non_facility_fee,
        facility_fee=facility_fee,
        status_code=status_code,
        pctc_indicator=pctc_indicator,
        multiple_surgery_indicator=multi_surgery,
        year=year_int,
    )


def get_unique_localities(file_path: Path) -> dict[str, tuple[str, str]]:
    """Extract unique carrier/locality combinations with state info.

    Args:
        file_path: Path to the payment file

    Returns:
        Dict mapping carrier+locality to (state, locality_name)
    """
    localities = {}
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            carrier = row[1].strip()
            locality = row[2].strip()
            key = f"{carrier}-{locality}"
            if key not in localities:
                state, name = get_carrier_locality_info(carrier, locality)
                localities[key] = (state, name)
    return localities
