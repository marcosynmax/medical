"""RVU (Relative Value Unit) data model."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class RVURecord:
    """Represents an RVU record from the CMS Physician Fee Schedule."""

    hcpcs_code: str
    modifier: Optional[str]
    description: str
    status_code: str
    work_rvu: Decimal
    non_facility_pe_rvu: Decimal
    facility_pe_rvu: Decimal
    malpractice_rvu: Decimal
    conversion_factor: Decimal
    global_days: Optional[str]
    year: int

    @property
    def total_non_facility_rvu(self) -> Decimal:
        """Calculate total RVUs for non-facility setting."""
        return self.work_rvu + self.non_facility_pe_rvu + self.malpractice_rvu

    @property
    def total_facility_rvu(self) -> Decimal:
        """Calculate total RVUs for facility setting."""
        return self.work_rvu + self.facility_pe_rvu + self.malpractice_rvu
