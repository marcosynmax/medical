"""Payer rate data model for commercial/Medicaid rate comparison."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PayerRate:
    """Represents a payer-specific reimbursement rate for a CPT code."""

    hcpcs_code: str
    payer_name: str
    payer_type: str  # "commercial", "medicaid", "other"
    year: int
    modifier: Optional[str] = None
    state: Optional[str] = None
    facility_rate: Optional[Decimal] = None
    non_facility_rate: Optional[Decimal] = None
    percent_of_medicare: Optional[Decimal] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    source: Optional[str] = None

    def get_rate(self, facility: bool = False) -> Optional[Decimal]:
        """Get the rate for the specified setting.

        Args:
            facility: If True, return facility rate; otherwise non-facility

        Returns:
            Rate amount or None if not available
        """
        return self.facility_rate if facility else self.non_facility_rate

    def calculate_rate_from_medicare(
        self,
        medicare_rate: Decimal,
        facility: bool = False
    ) -> Optional[Decimal]:
        """Calculate rate based on percentage of Medicare.

        Args:
            medicare_rate: The Medicare rate for the same code/region
            facility: If True, calculate facility rate

        Returns:
            Calculated rate or stored rate
        """
        # If we have a direct rate, return it
        direct_rate = self.get_rate(facility)
        if direct_rate is not None:
            return direct_rate

        # Calculate from percentage of Medicare
        if self.percent_of_medicare is not None:
            return medicare_rate * (self.percent_of_medicare / Decimal("100"))

        return None
