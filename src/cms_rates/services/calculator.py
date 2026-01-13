"""Payment calculation service."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from cms_rates.models.rvu import RVURecord
from cms_rates.models.gpci import GPCIRecord


@dataclass
class CalculationBreakdown:
    """Breakdown of payment calculation components."""

    work_rvu: Decimal
    pe_rvu: Decimal
    mp_rvu: Decimal
    work_gpci: Decimal
    pe_gpci: Decimal
    mp_gpci: Decimal
    work_adjusted: Decimal
    pe_adjusted: Decimal
    mp_adjusted: Decimal
    total_adjusted_rvu: Decimal
    conversion_factor: Decimal
    payment_amount: Decimal


class PaymentCalculator:
    """Calculates Medicare payment amounts using the CMS formula."""

    def calculate(
        self,
        rvu: RVURecord,
        gpci: GPCIRecord,
        facility: bool = False,
    ) -> CalculationBreakdown:
        """Calculate the Medicare payment amount.

        Formula:
        Payment = [(Work_RVU × Work_GPCI) + (PE_RVU × PE_GPCI) + (MP_RVU × MP_GPCI)] × CF

        Args:
            rvu: RVU record for the CPT code
            gpci: GPCI record for the locality
            facility: If True, use facility PE RVU; otherwise use non-facility

        Returns:
            CalculationBreakdown with full calculation details
        """
        # Select appropriate PE RVU based on setting
        pe_rvu = rvu.facility_pe_rvu if facility else rvu.non_facility_pe_rvu

        # Calculate adjusted RVUs
        work_adjusted = rvu.work_rvu * gpci.work_gpci
        pe_adjusted = pe_rvu * gpci.pe_gpci
        mp_adjusted = rvu.malpractice_rvu * gpci.mp_gpci

        # Sum adjusted RVUs
        total_adjusted = work_adjusted + pe_adjusted + mp_adjusted

        # Apply conversion factor
        payment = total_adjusted * rvu.conversion_factor

        # Round to 2 decimal places
        payment = payment.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return CalculationBreakdown(
            work_rvu=rvu.work_rvu,
            pe_rvu=pe_rvu,
            mp_rvu=rvu.malpractice_rvu,
            work_gpci=gpci.work_gpci,
            pe_gpci=gpci.pe_gpci,
            mp_gpci=gpci.mp_gpci,
            work_adjusted=work_adjusted.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            pe_adjusted=pe_adjusted.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            mp_adjusted=mp_adjusted.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            total_adjusted_rvu=total_adjusted.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            conversion_factor=rvu.conversion_factor,
            payment_amount=payment,
        )
