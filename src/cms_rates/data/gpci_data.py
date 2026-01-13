"""Embedded GPCI data for 2025.

This provides fallback GPCI values when CMS files cannot be downloaded.
Data source: CMS 2025 Geographic Practice Cost Indices.
"""

# 2025 GPCI data: (carrier, locality, name, state, work_gpci, pe_gpci, mp_gpci)
GPCI_2025 = [
    # Alabama
    ("10112", "01", "Alabama", "AL", 1.000, 0.862, 0.590),
    # Alaska
    ("02102", "01", "Alaska", "AK", 1.500, 1.106, 0.754),
    # Arizona
    ("03102", "00", "Arizona", "AZ", 1.000, 0.970, 0.763),
    # Arkansas
    ("00520", "13", "Arkansas", "AR", 1.000, 0.853, 0.323),
    # California
    ("01182", "26", "Anaheim/Santa Ana, CA", "CA", 1.037, 1.217, 0.898),
    ("01182", "18", "Los Angeles, CA", "CA", 1.056, 1.155, 0.898),
    ("01182", "03", "Marin/Napa/Solano, CA", "CA", 1.043, 1.196, 0.539),
    ("01182", "07", "Oakland/Berkeley, CA", "CA", 1.062, 1.222, 0.539),
    ("01182", "05", "San Francisco, CA", "CA", 1.077, 1.399, 0.539),
    ("01182", "06", "San Mateo, CA", "CA", 1.077, 1.399, 0.539),
    ("01182", "09", "Santa Clara, CA", "CA", 1.074, 1.321, 0.539),
    ("01182", "17", "Ventura, CA", "CA", 1.028, 1.140, 0.718),
    ("01182", "99", "Rest of California", "CA", 1.014, 1.035, 0.718),
    # Colorado
    ("04102", "01", "Colorado", "CO", 1.000, 1.002, 0.678),
    # Connecticut
    ("13102", "00", "Connecticut", "CT", 1.050, 1.148, 0.901),
    # Delaware
    ("12102", "01", "Delaware", "DE", 1.020, 1.039, 0.749),
    # DC + Maryland/Virginia suburbs
    ("12102", "01", "DC + MD/VA Suburbs", "DC", 1.050, 1.165, 0.987),
    # Florida
    ("09102", "03", "Fort Lauderdale, FL", "FL", 1.000, 1.019, 1.393),
    ("09102", "04", "Miami, FL", "FL", 1.015, 1.058, 1.880),
    ("09102", "99", "Rest of Florida", "FL", 1.000, 0.948, 1.074),
    # Georgia
    ("10102", "01", "Atlanta, GA", "GA", 1.019, 1.042, 0.906),
    ("10102", "99", "Rest of Georgia", "GA", 1.000, 0.894, 0.906),
    # Hawaii/Guam
    ("01212", "01", "Hawaii/Guam", "HI", 1.000, 1.126, 0.768),
    # Idaho
    ("05130", "00", "Idaho", "ID", 1.000, 0.884, 0.474),
    # Illinois
    ("06102", "16", "Chicago, IL", "IL", 1.028, 1.092, 1.511),
    ("06102", "12", "East St. Louis, IL", "IL", 1.000, 0.925, 1.292),
    ("06102", "15", "Suburban Chicago, IL", "IL", 1.018, 1.073, 0.976),
    ("06102", "99", "Rest of Illinois", "IL", 1.000, 0.891, 0.657),
    # Indiana
    ("00630", "00", "Indiana", "IN", 1.000, 0.916, 0.441),
    # Iowa
    ("00826", "00", "Iowa", "IA", 1.000, 0.882, 0.503),
    # Kansas
    ("00650", "00", "Kansas", "KS", 1.000, 0.897, 0.508),
    ("00650", "02", "Kansas City, KS", "KS", 1.000, 0.960, 0.612),
    # Kentucky
    ("15102", "00", "Kentucky", "KY", 1.000, 0.869, 0.629),
    # Louisiana
    ("00528", "01", "New Orleans, LA", "LA", 1.000, 0.948, 0.950),
    ("00528", "99", "Rest of Louisiana", "LA", 1.000, 0.876, 0.778),
    # Maine
    ("31143", "03", "Maine", "ME", 1.000, 0.978, 0.563),
    # Maryland
    ("12102", "01", "Baltimore/Surr. Cntys, MD", "MD", 1.020, 1.039, 0.749),
    ("12102", "99", "Rest of Maryland", "MD", 1.000, 0.975, 0.876),
    # Massachusetts
    ("31143", "01", "Metropolitan Boston", "MA", 1.035, 1.237, 0.731),
    ("31143", "99", "Rest of Massachusetts", "MA", 1.013, 1.083, 0.731),
    # Michigan
    ("00953", "01", "Detroit, MI", "MI", 1.034, 1.019, 1.668),
    ("00953", "99", "Rest of Michigan", "MI", 1.000, 0.921, 0.988),
    # Minnesota
    ("00952", "00", "Minnesota", "MN", 1.000, 0.973, 0.414),
    # Mississippi
    ("00528", "00", "Mississippi", "MS", 1.000, 0.846, 0.478),
    # Missouri
    ("00523", "02", "Kansas City, MO", "MO", 1.000, 0.960, 0.612),
    ("00523", "01", "St. Louis, MO", "MO", 1.000, 0.943, 0.788),
    ("00523", "99", "Rest of Missouri", "MO", 1.000, 0.848, 0.509),
    # Montana
    ("03102", "04", "Montana", "MT", 1.000, 0.883, 0.597),
    # Nebraska
    ("00655", "00", "Nebraska", "NE", 1.000, 0.884, 0.343),
    # Nevada
    ("01182", "00", "Nevada", "NV", 1.005, 1.034, 1.090),
    # New Hampshire
    ("31143", "40", "New Hampshire", "NH", 1.000, 1.058, 0.721),
    # New Jersey
    ("12202", "01", "Northern NJ", "NJ", 1.046, 1.193, 0.881),
    ("12202", "99", "Rest of New Jersey", "NJ", 1.020, 1.086, 0.881),
    # New Mexico
    ("00521", "05", "New Mexico", "NM", 1.000, 0.887, 0.754),
    # New York
    ("14430", "01", "Manhattan, NY", "NY", 1.094, 1.488, 1.586),
    ("14430", "02", "NYC Suburbs/Long Island", "NY", 1.068, 1.251, 1.586),
    ("14430", "03", "Poughkeepsie/N NYC Suburbs", "NY", 1.011, 1.075, 0.720),
    ("14430", "04", "Queens, NY", "NY", 1.058, 1.228, 1.586),
    ("14430", "99", "Rest of New York", "NY", 1.000, 0.922, 0.520),
    # North Carolina
    ("11202", "00", "North Carolina", "NC", 1.000, 0.929, 0.524),
    # North Dakota
    ("00952", "01", "North Dakota", "ND", 1.000, 0.889, 0.459),
    # Ohio
    ("15202", "00", "Ohio", "OH", 1.000, 0.928, 0.819),
    # Oklahoma
    ("00522", "00", "Oklahoma", "OK", 1.000, 0.876, 0.374),
    # Oregon
    ("02202", "01", "Portland, OR", "OR", 1.007, 1.037, 0.418),
    ("02202", "99", "Rest of Oregon", "OR", 1.000, 0.949, 0.418),
    # Pennsylvania
    ("12302", "01", "Metropolitan Philadelphia", "PA", 1.030, 1.105, 0.840),
    ("12302", "99", "Rest of Pennsylvania", "PA", 1.000, 0.917, 0.614),
    # Puerto Rico
    ("09102", "05", "Puerto Rico", "PR", 0.879, 0.711, 0.241),
    # Rhode Island
    ("31143", "20", "Rhode Island", "RI", 1.021, 1.075, 0.711),
    # South Carolina
    ("11302", "01", "South Carolina", "SC", 1.000, 0.905, 0.310),
    # South Dakota
    ("00952", "02", "South Dakota", "SD", 1.000, 0.882, 0.370),
    # Tennessee
    ("10212", "35", "Tennessee", "TN", 1.000, 0.897, 0.519),
    # Texas
    ("00900", "09", "Austin, TX", "TX", 1.000, 1.001, 0.789),
    ("00900", "11", "Beaumont, TX", "TX", 1.000, 0.908, 0.986),
    ("00900", "20", "Brazoria, TX", "TX", 1.000, 0.990, 0.986),
    ("00900", "18", "Dallas, TX", "TX", 1.017, 1.049, 0.789),
    ("00900", "31", "Fort Worth, TX", "TX", 1.007, 0.997, 0.789),
    ("00900", "15", "Galveston, TX", "TX", 1.000, 0.986, 0.986),
    ("00900", "17", "Houston, TX", "TX", 1.023, 1.048, 0.986),
    ("00900", "99", "Rest of Texas", "TX", 1.000, 0.878, 0.789),
    # Utah
    ("03102", "09", "Utah", "UT", 1.000, 0.947, 0.536),
    # Vermont
    ("31143", "50", "Vermont", "VT", 1.000, 0.999, 0.423),
    # Virginia
    ("12102", "01", "Northern Virginia", "VA", 1.050, 1.165, 0.509),
    ("12102", "99", "Rest of Virginia", "VA", 1.000, 0.891, 0.467),
    # Virgin Islands
    ("09102", "10", "Virgin Islands", "VI", 1.000, 1.052, 0.925),
    # Washington
    ("02202", "02", "Seattle (King County), WA", "WA", 1.023, 1.106, 0.720),
    ("02202", "99", "Rest of Washington", "WA", 1.000, 0.973, 0.720),
    # West Virginia
    ("16102", "15", "West Virginia", "WV", 1.000, 0.834, 0.758),
    # Wisconsin
    ("00951", "00", "Wisconsin", "WI", 1.000, 0.925, 0.546),
    # Wyoming
    ("00655", "21", "Wyoming", "WY", 1.000, 0.909, 0.703),
]


def get_embedded_gpci_records(year: int):
    """Get embedded GPCI records as GPCIRecord objects.

    Args:
        year: Fee schedule year (used to tag records)

    Yields:
        GPCIRecord objects
    """
    from decimal import Decimal
    from cms_rates.models.gpci import GPCIRecord

    gpci_data = GPCI_2025  # Use 2025 data as fallback for all years

    for carrier, locality, name, state, work, pe, mp in gpci_data:
        yield GPCIRecord(
            carrier=carrier,
            locality=locality,
            locality_name=name,
            state=state,
            work_gpci=Decimal(str(work)),
            pe_gpci=Decimal(str(pe)),
            mp_gpci=Decimal(str(mp)),
            year=year,
        )
