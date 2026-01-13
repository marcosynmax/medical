"""Parser for custom CSV fee schedules."""

import csv
from decimal import Decimal
from io import StringIO
from typing import Iterator, Optional

from rate_compare.models.payer import PayerRate


def parse_payer_csv(
    csv_content: str,
    payer_name: str,
    payer_type: str,
    year: int,
    code_column: str = "hcpcs_code",
    fee_column: Optional[str] = "fee",
    facility_fee_column: Optional[str] = None,
    allowed_amount_column: Optional[str] = None,
    modifier_column: Optional[str] = None,
    state_column: Optional[str] = None,
    default_state: Optional[str] = None,
    source: Optional[str] = None,
) -> Iterator[PayerRate]:
    """Parse a CSV file with payer rates.

    Args:
        csv_content: CSV content as string
        payer_name: Name of the payer
        payer_type: Type ('commercial', 'medicaid', 'other')
        year: Fee schedule year
        code_column: Column name for HCPCS code
        fee_column: Column name for non-facility fee
        facility_fee_column: Column name for facility fee (optional)
        allowed_amount_column: Column name for allowed amount (optional, used as non-facility fee)
        modifier_column: Column name for modifier (optional)
        state_column: Column name for state (optional)
        default_state: Default state if not in CSV
        source: Source description

    Yields:
        PayerRate objects
    """
    reader = csv.DictReader(StringIO(csv_content))

    for row in reader:
        try:
            hcpcs_code = row.get(code_column, "").strip().upper()
            if not hcpcs_code:
                continue

            # Parse fees - allowed amount takes precedence if provided
            if allowed_amount_column:
                allowed_amount = _parse_decimal(row.get(allowed_amount_column))
                non_fac_fee = allowed_amount
            else:
                non_fac_fee = _parse_decimal(row.get(fee_column)) if fee_column else None

            fac_fee = _parse_decimal(row.get(facility_fee_column)) if facility_fee_column else None

            # Skip if no fees
            if non_fac_fee is None and fac_fee is None:
                continue

            # Get optional fields
            modifier = row.get(modifier_column, "").strip() if modifier_column else None
            modifier = modifier if modifier else None

            state = row.get(state_column, "").strip().upper() if state_column else None
            state = state if state else default_state

            yield PayerRate(
                hcpcs_code=hcpcs_code,
                payer_name=payer_name,
                payer_type=payer_type,
                year=year,
                modifier=modifier,
                state=state,
                non_facility_fee=non_fac_fee,
                facility_fee=fac_fee,
                source=source,
            )

        except Exception:
            continue


def _parse_decimal(value: Optional[str]) -> Optional[Decimal]:
    """Parse a string to Decimal, returning None on failure."""
    if not value:
        return None
    try:
        # Remove currency symbols and whitespace
        cleaned = value.strip().replace("$", "").replace(",", "")
        if not cleaned:
            return None
        return Decimal(cleaned)
    except Exception:
        return None


def detect_csv_columns(csv_content: str) -> list[str]:
    """Detect column names from CSV content."""
    reader = csv.DictReader(StringIO(csv_content))
    return list(reader.fieldnames or [])
