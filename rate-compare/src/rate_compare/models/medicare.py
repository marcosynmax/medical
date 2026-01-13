"""Medicare rate data model."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class MedicareRate:
    """Represents a Medicare rate from the CMS Payment Amount File."""

    hcpcs_code: str
    carrier: str
    locality: str
    non_facility_fee: Decimal
    facility_fee: Decimal
    year: int
    modifier: Optional[str] = None
    state: Optional[str] = None
    locality_name: Optional[str] = None
    status_code: Optional[str] = None

    @property
    def carrier_locality(self) -> str:
        """Return combined carrier-locality code."""
        return f"{self.carrier}-{self.locality}"


# Carrier to state mapping (extracted from CMS documentation)
CARRIER_STATE_MAP = {
    "01112": "CA",  # California - Northern
    "01182": "CA",  # California - Southern
    "01212": "HI",  # Hawaii
    "02102": "AK",  # Alaska
    "02202": "OR",  # Oregon
    "02302": "OR",  # Oregon
    "02402": "WA",  # Washington
    "03102": "AZ",  # Arizona
    "04102": "CO",  # Colorado
    "04212": "NM",  # New Mexico
    "04312": "OK",  # Oklahoma
    "04412": "TX",  # Texas
    "05130": "ID",  # Idaho
    "05302": "MO",  # Missouri
    "05440": "MT",  # Montana
    "06102": "IL",  # Illinois
    "07102": "AR",  # Arkansas
    "07202": "LA",  # Louisiana
    "08102": "IN",  # Indiana
    "08202": "MI",  # Michigan
    "09102": "FL",  # Florida
    "10102": "GA",  # Georgia
    "10212": "TN",  # Tennessee
    "11102": "AL",  # Alabama
    "11202": "NC",  # North Carolina
    "11302": "SC",  # South Carolina
    "12102": "DC",  # DC/Maryland/Virginia
    "12202": "DE",  # Delaware
    "12302": "MD",  # Maryland
    "12402": "NJ",  # New Jersey
    "12502": "PA",  # Pennsylvania
    "13102": "CT",  # Connecticut
    "13202": "NY",  # New York - Downstate
    "13282": "NY",  # New York - Upstate
    "13292": "NY",  # New York
    "14112": "ME",  # Maine
    "14212": "MA",  # Massachusetts
    "14312": "NH",  # New Hampshire
    "14412": "RI",  # Rhode Island
    "14512": "VT",  # Vermont
    "15102": "KY",  # Kentucky
    "15202": "OH",  # Ohio
    "15302": "WV",  # West Virginia
    "16102": "WV",  # West Virginia
    "00510": "KS",  # Kansas
    "00511": "NE",  # Nebraska
    "00520": "AR",  # Arkansas
    "00521": "NM",  # New Mexico
    "00522": "OK",  # Oklahoma
    "00523": "MO",  # Missouri
    "00528": "MS",  # Mississippi
    "00542": "UT",  # Utah
    "00630": "IN",  # Indiana
    "00650": "KS",  # Kansas
    "00655": "NE",  # Nebraska
    "00826": "IA",  # Iowa
    "00900": "TX",  # Texas
    "00951": "WI",  # Wisconsin
    "00952": "MN",  # Minnesota
    "00953": "MI",  # Michigan
    "31143": "MA",  # Massachusetts/New England
}

# Carrier/Locality to state and name mapping
CARRIER_LOCALITY_MAP = {
    # Alabama
    "1011200": ("AL", "ALABAMA"),
    # Alaska
    "0210201": ("AK", "ALASKA"),
    # Arizona
    "0310200": ("AZ", "ARIZONA"),
    # Arkansas
    "0710213": ("AR", "ARKANSAS"),
    # California
    "0111205": ("CA", "SAN FRANCISCO, CA"),
    "0111209": ("CA", "SANTA CLARA, CA"),
    "0111254": ("CA", "BAKERSFIELD, CA"),
    "0111255": ("CA", "CHICO, CA"),
    "0111256": ("CA", "FRESNO, CA"),
    "0111263": ("CA", "SACRAMENTO, CA"),
    "0111265": ("CA", "SAN JOSE, CA"),
    "0111267": ("CA", "SANTA ROSA, CA"),
    "0118217": ("CA", "VENTURA, CA"),
    "0118218": ("CA", "LOS ANGELES, CA"),
    "0118271": ("CA", "EL CENTRO, CA"),
    "0118272": ("CA", "SAN DIEGO, CA"),
    # Colorado
    "0410201": ("CO", "COLORADO"),
    # Connecticut
    "1310200": ("CT", "CONNECTICUT"),
    # DC/Maryland/Virginia
    "1210201": ("DC", "DC/MD/VA SUBURBS"),
    # Florida
    "0910203": ("FL", "FORT LAUDERDALE, FL"),
    "0910204": ("FL", "MIAMI, FL"),
    "0910299": ("FL", "REST OF FLORIDA"),
    # Georgia
    "1010201": ("GA", "ATLANTA, GA"),
    "1010299": ("GA", "REST OF GEORGIA"),
    # Hawaii
    "0121201": ("HI", "HAWAII"),
    # Illinois
    "0610216": ("IL", "CHICAGO, IL"),
    "0610212": ("IL", "EAST ST. LOUIS, IL"),
    "0610299": ("IL", "REST OF ILLINOIS"),
    # New York
    "1320201": ("NY", "MANHATTAN, NY"),
    "1320202": ("NY", "NYC SUBURBS/LONG I., NY"),
    "1328299": ("NY", "REST OF NEW YORK"),
    # Texas
    "0441209": ("TX", "BRAZORIA, TX"),
    "0441211": ("TX", "DALLAS, TX"),
    "0441215": ("TX", "GALVESTON, TX"),
    "0441218": ("TX", "HOUSTON, TX"),
    "0441220": ("TX", "BEAUMONT, TX"),
    "0441228": ("TX", "FORT WORTH, TX"),
    "0441231": ("TX", "AUSTIN, TX"),
    "0441299": ("TX", "REST OF TEXAS"),
}


def get_state_from_carrier(carrier: str) -> Optional[str]:
    """Get state abbreviation from carrier code."""
    return CARRIER_STATE_MAP.get(carrier)


def get_locality_info(carrier: str, locality: str) -> tuple[Optional[str], str]:
    """Get state and locality name from carrier/locality codes.

    Returns:
        Tuple of (state, locality_name)
    """
    key = f"{carrier}{locality}"
    if key in CARRIER_LOCALITY_MAP:
        return CARRIER_LOCALITY_MAP[key]

    # Try with different key formats
    for map_key, value in CARRIER_LOCALITY_MAP.items():
        if carrier in map_key and locality in map_key:
            return value

    # Fallback to carrier state lookup
    state = get_state_from_carrier(carrier)
    return (state, f"Locality {locality}")
