"""CMS data file parser."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator, Optional

from cms_rates.models.rvu import RVURecord
from cms_rates.models.gpci import GPCIRecord
from cms_rates.config import get_conversion_factor


def safe_decimal(value: str, default: Decimal = Decimal("0")) -> Decimal:
    """Safely convert a string to Decimal."""
    if not value or value.strip() in ("", "NA", "N/A", "."):
        return default
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return default


def normalize_column_name(name: str) -> str:
    """Normalize column name for consistent access."""
    return name.strip().upper().replace(" ", "_").replace("-", "_")


def find_header_row(file_path: Path) -> int:
    """Find the row number containing the column headers.

    CMS files often have several comment/title rows before the actual headers.
    Look for a row that starts with 'HCPCS'.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if line.strip().startswith("HCPCS"):
                return i
    return 0


def parse_rvu_file(file_path: Path, year: int) -> Iterator[RVURecord]:
    """Parse an RVU CSV file and yield RVURecord objects.

    Args:
        file_path: Path to the RVU CSV file
        year: Fee schedule year

    Yields:
        RVURecord objects
    """
    conversion_factor = Decimal(str(get_conversion_factor(year)))

    # Find the header row (skip title/comment rows)
    header_row = find_header_row(file_path)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Skip rows before the header
        for _ in range(header_row):
            next(f)

        reader = csv.reader(f, delimiter=",")

        # Skip header row
        headers = next(reader)

        # CMS RVU file column positions (0-indexed):
        # 0=HCPCS, 1=MOD, 2=DESCRIPTION, 3=STATUS CODE, 4=NOT USED FOR MEDICARE
        # 5=WORK RVU, 6=NON-FAC PE RVU, 7=NA IND, 8=FAC PE RVU, 9=NA IND
        # 10=MP RVU, 11=NON-FAC TOTAL, 12=FAC TOTAL, 13=PCTC IND, 14=GLOB DAYS
        # 24=CONV FACTOR
        COL_HCPCS = 0
        COL_MOD = 1
        COL_DESC = 2
        COL_STATUS = 3
        COL_WORK_RVU = 5
        COL_NONFAC_PE = 6
        COL_FAC_PE = 8
        COL_MP_RVU = 10
        COL_GLOB_DAYS = 14
        COL_CONV_FACTOR = 24

        for row in reader:
            if len(row) < 15:
                continue

            hcpcs = row[COL_HCPCS].strip()

            if not hcpcs:
                continue

            # Skip non-code rows (like section headers)
            if len(hcpcs) > 5 or not any(c.isalnum() for c in hcpcs):
                continue

            modifier = row[COL_MOD].strip() or None
            description = row[COL_DESC].strip()
            status_code = row[COL_STATUS].strip()

            work_rvu = safe_decimal(row[COL_WORK_RVU] if len(row) > COL_WORK_RVU else "0")
            non_fac_pe = safe_decimal(row[COL_NONFAC_PE] if len(row) > COL_NONFAC_PE else "0")
            fac_pe = safe_decimal(row[COL_FAC_PE] if len(row) > COL_FAC_PE else "0")
            mp_rvu = safe_decimal(row[COL_MP_RVU] if len(row) > COL_MP_RVU else "0")
            global_days = row[COL_GLOB_DAYS].strip() if len(row) > COL_GLOB_DAYS else None

            # Get conversion factor from file if available, otherwise use config
            if len(row) > COL_CONV_FACTOR and row[COL_CONV_FACTOR].strip():
                cf = safe_decimal(row[COL_CONV_FACTOR], conversion_factor)
            else:
                cf = conversion_factor

            yield RVURecord(
                hcpcs_code=hcpcs,
                modifier=modifier,
                description=description,
                status_code=status_code,
                work_rvu=work_rvu,
                non_facility_pe_rvu=non_fac_pe,
                facility_pe_rvu=fac_pe,
                malpractice_rvu=mp_rvu,
                conversion_factor=cf,
                global_days=global_days or None,
                year=year,
            )


def parse_gpci_file(file_path: Path, year: int) -> Iterator[GPCIRecord]:
    """Parse a GPCI CSV file and yield GPCIRecord objects.

    Args:
        file_path: Path to the GPCI CSV file
        year: Fee schedule year

    Yields:
        GPCIRecord objects
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Try to detect delimiter
        sample = f.read(4096)
        f.seek(0)

        delimiter = ","
        if sample.count("\t") > sample.count(","):
            delimiter = "\t"

        reader = csv.DictReader(f, delimiter=delimiter)

        # Normalize field names
        if reader.fieldnames:
            reader.fieldnames = [normalize_column_name(n) for n in reader.fieldnames]

        for row in reader:
            carrier = (
                row.get("CARRIER") or
                row.get("MAC") or
                row.get("CARRIER_NUM", "")
            ).strip()

            locality = (
                row.get("LOCALITY") or
                row.get("LOC") or
                row.get("LOCALITY_CODE", "")
            ).strip()

            if not carrier or not locality:
                continue

            locality_name = (
                row.get("LOCALITY_NAME") or
                row.get("LOCALITY_DESCRIPTION") or
                row.get("NAME", "")
            ).strip()

            state = (
                row.get("STATE") or
                row.get("STATE_CODE", "")
            ).strip()

            work_gpci = safe_decimal(
                row.get("WORK_GPCI") or
                row.get("PW_GPCI") or
                row.get("GPCI_WORK", "1.0")
            )

            pe_gpci = safe_decimal(
                row.get("PE_GPCI") or
                row.get("PRACTICE_EXPENSE_GPCI") or
                row.get("GPCI_PE", "1.0")
            )

            mp_gpci = safe_decimal(
                row.get("MP_GPCI") or
                row.get("MALPRACTICE_GPCI") or
                row.get("PLI_GPCI") or
                row.get("GPCI_MP", "1.0")
            )

            yield GPCIRecord(
                carrier=carrier,
                locality=locality,
                locality_name=locality_name,
                state=state,
                work_gpci=work_gpci,
                pe_gpci=pe_gpci,
                mp_gpci=mp_gpci,
                year=year,
            )
