"""Region to locality mapping service."""

from typing import Optional

from cms_rates.models.gpci import GPCIRecord
from cms_rates.data.storage import get_gpci, get_gpci_by_state, get_all_localities


# State name to abbreviation mapping
STATE_NAMES = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
    "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
    "PUERTO RICO": "PR", "VIRGIN ISLANDS": "VI", "GUAM": "GU",
}

# Reverse mapping
STATE_ABBREVS = {v: k for k, v in STATE_NAMES.items()}

# Default localities for states (carrier-locality codes)
# These represent the "Rest of State" or statewide localities
# Format: state_abbrev -> (carrier, locality, locality_name)
DEFAULT_LOCALITIES = {
    "AL": ("01182", "01", "Alabama"),
    "AK": ("02102", "01", "Alaska"),
    "AZ": ("03102", "00", "Arizona"),
    "AR": ("00520", "13", "Arkansas"),
    "CA": ("01182", "99", "Rest of California"),
    "CO": ("04102", "01", "Colorado"),
    "CT": ("13102", "00", "Connecticut"),
    "DE": ("12102", "01", "Delaware"),
    "DC": ("12102", "01", "DC + MD/VA Suburbs"),
    "FL": ("09102", "99", "Rest of Florida"),
    "GA": ("10102", "01", "Georgia"),
    "HI": ("01212", "01", "Hawaii/Guam"),
    "ID": ("05130", "00", "Idaho"),
    "IL": ("06102", "99", "Rest of Illinois"),
    "IN": ("00630", "00", "Indiana"),
    "IA": ("00826", "00", "Iowa"),
    "KS": ("00650", "00", "Kansas"),
    "KY": ("15102", "00", "Kentucky"),
    "LA": ("00528", "01", "Louisiana"),
    "ME": ("31143", "03", "Maine"),
    "MD": ("12102", "01", "Maryland"),
    "MA": ("31143", "01", "Massachusetts"),
    "MI": ("00953", "01", "Michigan"),
    "MN": ("00952", "00", "Minnesota"),
    "MS": ("00528", "00", "Mississippi"),
    "MO": ("00523", "99", "Rest of Missouri"),
    "MT": ("03102", "04", "Montana"),
    "NE": ("00655", "00", "Nebraska"),
    "NV": ("01182", "00", "Nevada"),
    "NH": ("31143", "40", "New Hampshire"),
    "NJ": ("12202", "01", "New Jersey"),
    "NM": ("00521", "05", "New Mexico"),
    "NY": ("14430", "99", "Rest of New York"),
    "NC": ("11202", "00", "North Carolina"),
    "ND": ("00952", "01", "North Dakota"),
    "OH": ("15202", "00", "Ohio"),
    "OK": ("00522", "00", "Oklahoma"),
    "OR": ("02202", "01", "Oregon"),
    "PA": ("12302", "99", "Rest of Pennsylvania"),
    "PR": ("09102", "05", "Puerto Rico"),
    "RI": ("31143", "20", "Rhode Island"),
    "SC": ("11302", "01", "South Carolina"),
    "SD": ("00952", "02", "South Dakota"),
    "TN": ("10212", "35", "Tennessee"),
    "TX": ("00900", "99", "Rest of Texas"),
    "UT": ("03102", "09", "Utah"),
    "VT": ("31143", "50", "Vermont"),
    "VA": ("12102", "99", "Rest of Virginia"),
    "VI": ("09102", "10", "Virgin Islands"),
    "WA": ("02202", "02", "Washington"),
    "WV": ("16102", "15", "West Virginia"),
    "WI": ("00951", "00", "Wisconsin"),
    "WY": ("00655", "21", "Wyoming"),
    "GU": ("01212", "01", "Guam"),
}


class RegionMapper:
    """Maps user region input to CMS localities."""

    def __init__(self, year: int):
        """Initialize the region mapper.

        Args:
            year: Fee schedule year for lookups
        """
        self.year = year

    def normalize_state(self, region: str) -> Optional[str]:
        """Convert state name or abbreviation to standard abbreviation.

        Args:
            region: State name or abbreviation

        Returns:
            2-letter state abbreviation, or None if not found
        """
        region = region.strip().upper()

        # Already an abbreviation?
        if len(region) == 2 and region in STATE_ABBREVS:
            return region

        # Full state name?
        if region in STATE_NAMES:
            return STATE_NAMES[region]

        return None

    def resolve_state(self, region: str) -> Optional[str]:
        """Resolve a region input to a state abbreviation.

        Args:
            region: State name, abbreviation, or locality code

        Returns:
            State abbreviation, or None if not recognized
        """
        region = region.strip()

        # Try as state name or abbreviation
        state_abbrev = self.normalize_state(region)
        if state_abbrev:
            return state_abbrev

        # Try as carrier-locality code (e.g., "01182-99")
        # Look up the state from GPCI data
        if "-" in region:
            parts = region.split("-")
            if len(parts) == 2:
                carrier, locality = parts[0].strip(), parts[1].strip()
                gpci = get_gpci(carrier, locality, self.year)
                if gpci:
                    return gpci.state

        return None

    def resolve_region(self, region: str) -> list[GPCIRecord]:
        """Resolve a region input to GPCI records.

        Args:
            region: State name, abbreviation, or locality code

        Returns:
            List of matching GPCIRecord objects
        """
        region = region.strip()

        # Try as state name or abbreviation
        state_abbrev = self.normalize_state(region)
        if state_abbrev:
            # First try to get from database
            localities = get_gpci_by_state(state_abbrev, self.year)
            if localities:
                return localities

            # Fall back to default locality
            if state_abbrev in DEFAULT_LOCALITIES:
                carrier, locality, name = DEFAULT_LOCALITIES[state_abbrev]
                gpci = get_gpci(carrier, locality, self.year)
                if gpci:
                    return [gpci]

        # Try as carrier-locality code (e.g., "01182-99")
        if "-" in region:
            parts = region.split("-")
            if len(parts) == 2:
                carrier, locality = parts[0].strip(), parts[1].strip()
                gpci = get_gpci(carrier, locality, self.year)
                if gpci:
                    return [gpci]

        return []

    def get_default_locality(self, state: str) -> Optional[GPCIRecord]:
        """Get the default/statewide locality for a state.

        Args:
            state: State name or abbreviation

        Returns:
            GPCIRecord for the default locality, or None
        """
        state_abbrev = self.normalize_state(state)
        if not state_abbrev:
            return None

        # Try to find "Rest of State" locality from database
        localities = get_gpci_by_state(state_abbrev, self.year)
        for loc in localities:
            if "rest of" in loc.locality_name.lower():
                return loc

        # Return first locality if no "Rest of" found
        if localities:
            return localities[0]

        # Fall back to hardcoded default
        if state_abbrev in DEFAULT_LOCALITIES:
            carrier, locality, name = DEFAULT_LOCALITIES[state_abbrev]
            return get_gpci(carrier, locality, self.year)

        return None

    def list_all_localities(self) -> list[GPCIRecord]:
        """Get all available localities.

        Returns:
            List of all GPCIRecord objects for the year
        """
        return get_all_localities(self.year)
