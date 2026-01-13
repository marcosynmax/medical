"""Payment Amount data model for CMS Physician Fee Schedule."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PaymentRecord:
    """Represents a payment amount record from the CMS Physician Fee Schedule Payment File."""

    hcpcs_code: str
    modifier: Optional[str]
    carrier: str
    locality: str
    non_facility_fee: Decimal
    facility_fee: Decimal
    status_code: str
    pctc_indicator: str
    multiple_surgery_indicator: str
    year: int

    @property
    def carrier_locality(self) -> str:
        """Return combined carrier-locality code."""
        return f"{self.carrier}{self.locality}"


# Carrier/Locality mapping from CMS PF26PAR.pdf Attachment A
# Format: carrier+locality code -> (state, locality_name)
CARRIER_LOCALITY_MAP = {
    # Alabama
    "101120000": ("AL", "ALABAMA"),
    # Georgia
    "102120101": ("GA", "ATLANTA, GA"),
    "102129999": ("GA", "REST OF GEORGIA"),
    # Arkansas
    "071021313": ("AR", "ARKANSAS"),
    # New Mexico
    "042120505": ("NM", "NEW MEXICO"),
    # Oklahoma
    "043120000": ("OK", "OKLAHOMA"),
    # Missouri
    "053020101": ("MO", "METROPOLITAN ST. LOUIS, MO"),
    "053020202": ("MO", "METROPOLITAN KANSAS CITY, MO"),
    "053029999": ("MO", "REST OF MISSOURI"),
    # Louisiana
    "072020101": ("LA", "NEW ORLEANS, LA"),
    "072029999": ("LA", "REST OF LOUISIANA"),
    # Delaware
    "121020101": ("DE", "DELAWARE"),
    # DC
    "122020101": ("DC", "DC + MD/VA SUBURBS"),
    # Florida
    "091020303": ("FL", "FORT LAUDERDALE, FL"),
    "091020404": ("FL", "MIAMI, FL"),
    "091029999": ("FL", "REST OF FLORIDA"),
    # Indiana
    "081020000": ("IN", "INDIANA"),
    # Iowa
    "051020000": ("IA", "IOWA"),
    # Kansas
    "052020000": ("KS", "KANSAS"),
    # Nebraska
    "054020000": ("NE", "NEBRASKA"),
    # Kentucky
    "151020000": ("KY", "KENTUCKY"),
    # Montana
    "032020101": ("MT", "MONTANA"),
    # New York
    "132829999": ("NY", "REST OF NEW YORK"),
    "132020101": ("NY", "MANHATTAN, NY"),
    "132020202": ("NY", "NYC SUBURBS/LONG I., NY"),
    "132020303": ("NY", "POUGHKPSIE/N NYC SUBURBS, NY"),
    "132920404": ("NY", "QUEENS, NY"),
    # New Jersey
    "124020101": ("NJ", "NORTHERN NJ"),
    "124029999": ("NJ", "REST OF NEW JERSEY"),
    # North Dakota
    "033020101": ("ND", "NORTH DAKOTA"),
    # South Dakota
    "034020202": ("SD", "SOUTH DAKOTA"),
    # Wyoming
    "036022121": ("WY", "WYOMING"),
    # Washington
    "024020202": ("WA", "SEATTLE (KING CNTY), WA"),
    "024029999": ("WA", "REST OF WASHINGTON"),
    # Alaska
    "021020101": ("AK", "ALASKA"),
    # Arizona
    "031020000": ("AZ", "ARIZONA"),
    # Nevada
    "013120000": ("NV", "NEVADA"),
    # Colorado
    "041120101": ("CO", "COLORADO"),
    # Hawaii
    "012120101": ("HI", "HAWAII/GUAM"),
    # Oregon
    "023020101": ("OR", "PORTLAND, OR"),
    "023029999": ("OR", "REST OF OREGON"),
    # Pennsylvania
    "125020101": ("PA", "METROPOLITAN PHILADELPHIA, PA"),
    "125029999": ("PA", "REST OF PENNSYLVANIA"),
    # Rhode Island
    "144120101": ("RI", "RHODE ISLAND"),
    # South Carolina
    "112020101": ("SC", "SOUTH CAROLINA"),
    # Texas
    "044120909": ("TX", "BRAZORIA, TX"),
    "044121111": ("TX", "DALLAS, TX"),
    "044121515": ("TX", "GALVESTON, TX"),
    "044121818": ("TX", "HOUSTON, TX"),
    "044122020": ("TX", "BEAUMONT, TX"),
    "044122828": ("TX", "FORT WORTH, TX"),
    "044123131": ("TX", "AUSTIN, TX"),
    "044129999": ("TX", "REST OF TEXAS"),
    # Maryland
    "123020101": ("MD", "BALTIMORE/SURR. CNTYS, MD"),
    "123029999": ("MD", "REST OF MARYLAND"),
    # Utah
    "035020909": ("UT", "UTAH"),
    # Wisconsin
    "063020000": ("WI", "WISCONSIN"),
    # Illinois
    "061021212": ("IL", "EAST ST. LOUIS, IL"),
    "061021515": ("IL", "SUBURBAN CHICAGO, IL"),
    "061021616": ("IL", "CHICAGO, IL"),
    "061029999": ("IL", "REST OF ILLINOIS"),
    # Michigan
    "082020101": ("MI", "DETROIT, MI"),
    "082029999": ("MI", "REST OF MICHIGAN"),
    # Puerto Rico/Virgin Islands
    "092022020": ("PR", "PUERTO RICO"),
    "092025050": ("VI", "VIRGIN ISLANDS"),
    # California (Southern - CA2)
    "011821717": ("CA", "VENTURA, CA"),
    "011821818": ("CA", "LOS ANGELES, CA"),
    "011822626": ("CA", "ANAHEIM/SANTA ANA, CA"),
    "011827171": ("CA", "EL CENTRO, CA"),
    "011827272": ("CA", "SAN DIEGO - CARLSBAD, CA"),
    "011827373": ("CA", "SAN LUIS OBISPO-PASO ROBLES, CA"),
    "011827474": ("CA", "SANTA MARIA-SANTA BARBARA, CA"),
    "011827575": ("CA", "REST OF CALIFORNIA (SOUTH)"),
    # Idaho
    "022020000": ("ID", "IDAHO"),
    # Tennessee
    "103123535": ("TN", "TENNESSEE"),
    # North Carolina
    "115020000": ("NC", "NORTH CAROLINA"),
    # Connecticut
    "131020000": ("CT", "CONNECTICUT"),
    # Minnesota
    "062020000": ("MN", "MINNESOTA"),
    # Mississippi
    "073020000": ("MS", "MISSISSIPPI"),
    # Virginia
    "113020000": ("VA", "VIRGINIA"),
    # Ohio
    "152020000": ("OH", "OHIO"),
    # West Virginia
    "114021616": ("WV", "WEST VIRGINIA"),
    # California (Northern - CA1)
    "011120505": ("CA", "SAN FRANCISCO, CA"),
    "011120606": ("CA", "SAN MATEO, CA"),
    "011120707": ("CA", "OAKLAND/BERKELEY, CA"),
    "011120909": ("CA", "SANTA CLARA, CA"),
    "011125151": ("CA", "NAPA, CA"),
    "011125252": ("CA", "MARIN COUNTY, CA"),
    "011125353": ("CA", "VALLEJO-FAIRFIELD, CA"),
    "011125454": ("CA", "BAKERSFIELD, CA"),
    "011125555": ("CA", "CHICO, CA"),
    "011125656": ("CA", "FRESNO, CA"),
    "011125757": ("CA", "HANFORD-CORCORAN, CA"),
    "011125858": ("CA", "MADERA, CA"),
    "011125959": ("CA", "MERCED, CA"),
    "011126060": ("CA", "MODESTO, CA"),
    "011126161": ("CA", "REDDING, CA"),
    "011126262": ("CA", "RIVERSIDE-SAN BERNARDINO, CA"),
    "011126363": ("CA", "SACRAMENTO-ROSEVILLE, CA"),
    "011126464": ("CA", "SALINAS, CA"),
    "011126565": ("CA", "SAN JOSE-SUNNYVALE, CA"),
    "011126666": ("CA", "SANTA CRUZ-WATSONVILLE, CA"),
    "011126767": ("CA", "SANTA ROSA, CA"),
    "011126868": ("CA", "STOCKTON-LODI, CA"),
    "011126969": ("CA", "VISALIA-PORTERVILLE, CA"),
    "011127070": ("CA", "YUBA CITY, CA"),
    # Maine
    "141120303": ("ME", "SOUTHERN MAINE"),
    "141129999": ("ME", "REST OF MAINE"),
    # Massachusetts
    "142120101": ("MA", "METROPOLITAN BOSTON"),
    "142129999": ("MA", "REST OF MASSACHUSETTS"),
    # New Hampshire
    "143124040": ("NH", "NEW HAMPSHIRE"),
    # Vermont
    "145125050": ("VT", "VERMONT"),
}


def get_carrier_locality_info(carrier: str, locality: str) -> tuple[str, str]:
    """Get state and locality name from carrier and locality codes.

    Args:
        carrier: 5-digit carrier code
        locality: 2-digit locality code

    Returns:
        Tuple of (state, locality_name), or ("XX", "UNKNOWN") if not found
    """
    # Try exact match first
    key = f"{carrier}{locality}"
    if key in CARRIER_LOCALITY_MAP:
        return CARRIER_LOCALITY_MAP[key]

    # Try with padding variations
    for map_key, value in CARRIER_LOCALITY_MAP.items():
        if map_key.startswith(carrier) and map_key.endswith(locality):
            return value

    # Fallback: determine state from carrier patterns
    carrier_state_map = {
        "01112": "CA",  # California Northern
        "01182": "CA",  # California Southern
        "01011": "AL",  # Alabama
        "01021": "GA",  # Georgia
        "07102": "AR",  # Arkansas
        "04212": "NM",  # New Mexico
        "04312": "OK",  # Oklahoma
        "05302": "MO",  # Missouri
        "07202": "LA",  # Louisiana
        "12102": "DE",  # Delaware
        "12202": "DC",  # DC
        "09102": "FL",  # Florida
        "08102": "IN",  # Indiana
        "05102": "IA",  # Iowa
        "05202": "KS",  # Kansas
        "05402": "NE",  # Nebraska
        "15102": "KY",  # Kentucky
        "03202": "MT",  # Montana
        "13282": "NY",  # New York 1
        "13202": "NY",  # New York 2
        "13292": "NY",  # New York 3
        "12402": "NJ",  # New Jersey
        "03302": "ND",  # North Dakota
        "03402": "SD",  # South Dakota
        "03602": "WY",  # Wyoming
        "02402": "WA",  # Washington
        "02102": "AK",  # Alaska
        "03102": "AZ",  # Arizona
        "01312": "NV",  # Nevada
        "04112": "CO",  # Colorado
        "01212": "HI",  # Hawaii
        "02302": "OR",  # Oregon
        "12502": "PA",  # Pennsylvania
        "14412": "RI",  # Rhode Island
        "11202": "SC",  # South Carolina
        "04412": "TX",  # Texas
        "12302": "MD",  # Maryland
        "03502": "UT",  # Utah
        "06302": "WI",  # Wisconsin
        "06102": "IL",  # Illinois
        "08202": "MI",  # Michigan
        "09202": "PR",  # Puerto Rico/VI
        "02202": "ID",  # Idaho
        "10312": "TN",  # Tennessee
        "11502": "NC",  # North Carolina
        "13102": "CT",  # Connecticut
        "06202": "MN",  # Minnesota
        "07302": "MS",  # Mississippi
        "11302": "VA",  # Virginia
        "15202": "OH",  # Ohio
        "11402": "WV",  # West Virginia
        "14112": "ME",  # Maine
        "14212": "MA",  # Massachusetts
        "14312": "NH",  # New Hampshire
        "14512": "VT",  # Vermont
    }

    state = carrier_state_map.get(carrier, "XX")
    return (state, f"Locality {locality}")
