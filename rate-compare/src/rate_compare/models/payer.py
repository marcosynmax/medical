"""Payer rate data model."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PayerRate:
    """Represents a rate from a commercial payer or Medicaid."""

    hcpcs_code: str
    payer_name: str
    payer_type: str  # 'commercial', 'medicaid', 'other'
    year: int
    modifier: Optional[str] = None
    state: Optional[str] = None
    non_facility_fee: Optional[Decimal] = None
    facility_fee: Optional[Decimal] = None
    percent_of_medicare: Optional[Decimal] = None
    effective_date: Optional[str] = None
    source: Optional[str] = None


# Valid payer types
PAYER_TYPES = ["commercial", "medicaid", "other"]
