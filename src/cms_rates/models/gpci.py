"""GPCI (Geographic Practice Cost Index) data model."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class GPCIRecord:
    """Represents a GPCI record for a specific locality."""

    carrier: str
    locality: str
    locality_name: str
    state: str
    work_gpci: Decimal
    pe_gpci: Decimal
    mp_gpci: Decimal
    year: int

    @property
    def carrier_locality(self) -> str:
        """Return combined carrier-locality code."""
        return f"{self.carrier}-{self.locality}"
