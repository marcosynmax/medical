"""Core lookup service for CMS rate queries."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from cms_rates.config import get_default_year
from cms_rates.data.storage import get_rvu, has_data
from cms_rates.models.rvu import RVURecord
from cms_rates.models.gpci import GPCIRecord
from cms_rates.services.region_mapper import RegionMapper
from cms_rates.services.calculator import PaymentCalculator, CalculationBreakdown


class LookupError(Exception):
    """Base exception for lookup errors."""
    pass


class InvalidCPTCodeError(LookupError):
    """Invalid CPT/HCPCS code format."""
    pass


class CPTCodeNotFoundError(LookupError):
    """CPT code not found in fee schedule."""
    pass


class InvalidRegionError(LookupError):
    """Region input could not be resolved."""
    pass


class DataNotFoundError(LookupError):
    """Required data not downloaded."""
    pass


@dataclass
class LookupResult:
    """Result of a rate lookup."""

    code: str
    modifier: Optional[str]
    description: str
    year: int
    facility: bool
    locality_name: str
    carrier_locality: str
    state: str
    payment_amount: Decimal
    breakdown: CalculationBreakdown
    rvu: RVURecord
    gpci: GPCIRecord


class RateLookup:
    """Main service for looking up CMS reimbursement rates."""

    def __init__(self, year: Optional[int] = None):
        """Initialize the lookup service.

        Args:
            year: Fee schedule year (default: current year)
        """
        self.year = year or get_default_year()
        self.region_mapper = RegionMapper(self.year)
        self.calculator = PaymentCalculator()

    def validate_cpt_code(self, code: str) -> str:
        """Validate and normalize a CPT/HCPCS code.

        Args:
            code: CPT or HCPCS code

        Returns:
            Normalized code (uppercase)

        Raises:
            InvalidCPTCodeError: If code format is invalid
        """
        code = code.strip().upper()

        # CPT codes are 5 digits, HCPCS Level II are 1 letter + 4 digits
        if len(code) != 5:
            raise InvalidCPTCodeError(
                f"Invalid code format '{code}'. Expected 5 characters (e.g., 99213 or G0438)"
            )

        # Check format: either all digits or letter + 4 digits
        if not (code.isdigit() or (code[0].isalpha() and code[1:].isdigit())):
            raise InvalidCPTCodeError(
                f"Invalid code format '{code}'. Expected numeric CPT or alphanumeric HCPCS"
            )

        return code

    def lookup(
        self,
        cpt_code: str,
        region: str,
        facility: bool = False,
        modifier: Optional[str] = None,
        all_localities: bool = False,
    ) -> list[LookupResult]:
        """Look up reimbursement rates for a CPT code and region.

        Args:
            cpt_code: CPT or HCPCS code
            region: State name, abbreviation, or locality code
            facility: If True, return facility rates; otherwise non-facility
            modifier: Optional modifier code
            all_localities: If True, return rates for all localities in region

        Returns:
            List of LookupResult objects (one per locality)

        Raises:
            InvalidCPTCodeError: If CPT code format is invalid
            CPTCodeNotFoundError: If CPT code not found in fee schedule
            InvalidRegionError: If region cannot be resolved
            DataNotFoundError: If data not downloaded for the year
        """
        # Check if data is available
        if not has_data(self.year):
            raise DataNotFoundError(
                f"Data for {self.year} not found. Run 'cms-rates update --year {self.year}' to download."
            )

        # Validate CPT code
        code = self.validate_cpt_code(cpt_code)

        # Get RVU data
        rvu = get_rvu(code, self.year, modifier)
        if not rvu:
            raise CPTCodeNotFoundError(
                f"CPT code {code} not found in {self.year} fee schedule."
            )

        # Resolve region to localities
        localities = self.region_mapper.resolve_region(region)
        if not localities:
            raise InvalidRegionError(
                f"Region '{region}' not recognized. "
                "Use state name (California), abbreviation (CA), or locality code (01182-99)."
            )

        # If not all_localities, just use the first (default) locality
        if not all_localities:
            localities = [localities[0]]

        # Calculate payment for each locality
        results = []
        for gpci in localities:
            breakdown = self.calculator.calculate(rvu, gpci, facility)
            results.append(LookupResult(
                code=rvu.hcpcs_code,
                modifier=rvu.modifier,
                description=rvu.description,
                year=self.year,
                facility=facility,
                locality_name=gpci.locality_name,
                carrier_locality=gpci.carrier_locality,
                state=gpci.state,
                payment_amount=breakdown.payment_amount,
                breakdown=breakdown,
                rvu=rvu,
                gpci=gpci,
            ))

        return results
