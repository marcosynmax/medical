"""Streamlit web app for CMS Rates lookup."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from cms_rates.config import get_default_year, ensure_data_dirs
from cms_rates.data.storage import (
    has_data,
    has_payment_data,
    init_database,
    search_by_description,
    clear_rvu_data,
    clear_gpci_data,
    insert_rvu_records,
    insert_gpci_records,
    get_gpci_by_state,
    get_payer_rates,
    get_all_payers,
    insert_payer_rate,
    delete_payer_rates,
    get_payment_localities_by_state,
)
from cms_rates.data.downloader import download_rvu_file
from cms_rates.data.parser import parse_rvu_file
from cms_rates.data.gpci_data import get_embedded_gpci_records
from cms_rates.services.lookup import (
    RateLookup,
    InvalidCPTCodeError,
    CPTCodeNotFoundError,
    InvalidRegionError,
    DataNotFoundError,
)
from cms_rates.services.region_mapper import RegionMapper, STATE_NAMES
from cms_rates.models.payer import PayerRate
from decimal import Decimal


@st.cache_resource
def load_data(year: int) -> bool:
    """Download and load CMS data if not present. Cached to run only once."""
    ensure_data_dirs()
    init_database()

    # Check if payment amount data exists (preferred for 2026+)
    if has_payment_data(year):
        return True

    # Always ensure GPCI data is loaded (use embedded data)
    gpci_loaded = False
    try:
        from cms_rates.data.storage import get_connection
        with get_connection() as conn:
            gpci_count = conn.execute(
                "SELECT COUNT(*) FROM gpci WHERE year = ?", (year,)
            ).fetchone()[0]
            gpci_loaded = gpci_count > 0
    except:
        gpci_loaded = False

    if not gpci_loaded:
        clear_gpci_data(year)
        insert_gpci_records(get_embedded_gpci_records(year))

    # Check if RVU data exists
    if has_data(year):
        return True

    # Download RVU file
    rvu_file = download_rvu_file(year, "a")
    if not rvu_file:
        # Even if RVU download fails, we have GPCI data
        return False

    # Import RVU data
    clear_rvu_data(year)
    insert_rvu_records(parse_rvu_file(rvu_file, year))

    return True


def get_locality_options_for_state(state: str, year: int) -> list:
    """Get list of locality options for a state. Returns serializable dicts."""

    # First try to get localities from payment data (2026+)
    if has_payment_data(year):
        payment_localities = get_payment_localities_by_state(state, year)
        if payment_localities:
            return [
                {
                    "name": loc.get("locality_name") or f"Locality {loc['locality']}",
                    "carrier": loc["carrier"],
                    "locality": loc["locality"],
                    "label": f"{loc.get('locality_name') or 'Locality ' + loc['locality']} ({loc['carrier']}-{loc['locality']})"
                }
                for loc in payment_localities
            ]

    # Hardcoded locality data to ensure it always works
    LOCALITIES: dict = {
        "AL": [("10112", "01", "Alabama")],
        "AK": [("02102", "01", "Alaska")],
        "AZ": [("03102", "00", "Arizona")],
        "AR": [("00520", "13", "Arkansas")],
        "CA": [
            ("01182", "26", "Anaheim/Santa Ana, CA"),
            ("01182", "18", "Los Angeles, CA"),
            ("01182", "03", "Marin/Napa/Solano, CA"),
            ("01182", "07", "Oakland/Berkeley, CA"),
            ("01182", "05", "San Francisco, CA"),
            ("01182", "06", "San Mateo, CA"),
            ("01182", "09", "Santa Clara, CA"),
            ("01182", "17", "Ventura, CA"),
            ("01182", "99", "Rest of California"),
        ],
        "CO": [("04102", "01", "Colorado")],
        "CT": [("13102", "00", "Connecticut")],
        "DE": [("12102", "01", "Delaware")],
        "DC": [("12102", "01", "DC + MD/VA Suburbs")],
        "FL": [
            ("09102", "03", "Fort Lauderdale, FL"),
            ("09102", "04", "Miami, FL"),
            ("09102", "99", "Rest of Florida"),
        ],
        "GA": [
            ("10102", "01", "Atlanta, GA"),
            ("10102", "99", "Rest of Georgia"),
        ],
        "HI": [("01212", "01", "Hawaii/Guam")],
        "ID": [("05130", "00", "Idaho")],
        "IL": [
            ("06102", "16", "Chicago, IL"),
            ("06102", "12", "East St. Louis, IL"),
            ("06102", "15", "Suburban Chicago, IL"),
            ("06102", "99", "Rest of Illinois"),
        ],
        "IN": [("00630", "00", "Indiana")],
        "IA": [("00826", "00", "Iowa")],
        "KS": [
            ("00650", "00", "Kansas"),
            ("00650", "02", "Kansas City, KS"),
        ],
        "KY": [("15102", "00", "Kentucky")],
        "LA": [
            ("00528", "01", "New Orleans, LA"),
            ("00528", "99", "Rest of Louisiana"),
        ],
        "ME": [("31143", "03", "Maine")],
        "MD": [
            ("12102", "01", "Baltimore/Surr. Cntys, MD"),
            ("12102", "99", "Rest of Maryland"),
        ],
        "MA": [
            ("31143", "01", "Metropolitan Boston"),
            ("31143", "99", "Rest of Massachusetts"),
        ],
        "MI": [
            ("00953", "01", "Detroit, MI"),
            ("00953", "99", "Rest of Michigan"),
        ],
        "MN": [("00952", "00", "Minnesota")],
        "MS": [("00528", "00", "Mississippi")],
        "MO": [
            ("00523", "02", "Kansas City, MO"),
            ("00523", "01", "St. Louis, MO"),
            ("00523", "99", "Rest of Missouri"),
        ],
        "MT": [("03102", "04", "Montana")],
        "NE": [("00655", "00", "Nebraska")],
        "NV": [("01182", "00", "Nevada")],
        "NH": [("31143", "40", "New Hampshire")],
        "NJ": [
            ("12202", "01", "Northern NJ"),
            ("12202", "99", "Rest of New Jersey"),
        ],
        "NM": [("00521", "05", "New Mexico")],
        "NY": [
            ("14430", "01", "Manhattan, NY"),
            ("14430", "02", "NYC Suburbs/Long Island"),
            ("14430", "03", "Poughkeepsie/N NYC Suburbs"),
            ("14430", "04", "Queens, NY"),
            ("14430", "99", "Rest of New York"),
        ],
        "NC": [("11202", "00", "North Carolina")],
        "ND": [("00952", "01", "North Dakota")],
        "OH": [("15202", "00", "Ohio")],
        "OK": [("00522", "00", "Oklahoma")],
        "OR": [
            ("02202", "01", "Portland, OR"),
            ("02202", "99", "Rest of Oregon"),
        ],
        "PA": [
            ("12302", "01", "Metropolitan Philadelphia"),
            ("12302", "99", "Rest of Pennsylvania"),
        ],
        "PR": [("09102", "05", "Puerto Rico")],
        "RI": [("31143", "20", "Rhode Island")],
        "SC": [("11302", "01", "South Carolina")],
        "SD": [("00952", "02", "South Dakota")],
        "TN": [("10212", "35", "Tennessee")],
        "TX": [
            ("04412", "31", "Austin, TX"),
            ("04412", "20", "Beaumont, TX"),
            ("04412", "09", "Brazoria, TX"),
            ("04412", "11", "Dallas, TX"),
            ("04412", "28", "Fort Worth, TX"),
            ("04412", "15", "Galveston, TX"),
            ("04412", "18", "Houston, TX"),
            ("04412", "99", "Rest of Texas"),
        ],
        "UT": [("03102", "09", "Utah")],
        "VT": [("31143", "50", "Vermont")],
        "VA": [
            ("12102", "01", "Northern Virginia"),
            ("12102", "99", "Rest of Virginia"),
        ],
        "VI": [("09102", "10", "Virgin Islands")],
        "WA": [
            ("02202", "02", "Seattle (King County), WA"),
            ("02202", "99", "Rest of Washington"),
        ],
        "WV": [("16102", "15", "West Virginia")],
        "WI": [("00951", "00", "Wisconsin")],
        "WY": [("00655", "21", "Wyoming")],
    }

    localities_data = LOCALITIES.get(state, [])
    return [
        {
            "name": loc[2],
            "carrier": loc[0],
            "locality": loc[1],
            "label": f"{loc[2]} ({loc[0]}-{loc[1]})"
        }
        for loc in localities_data
    ]


def ensure_gpci_data(year: int):
    """Ensure GPCI data is loaded. Called on every render to guarantee data exists."""
    try:
        from cms_rates.data.storage import get_connection
        with get_connection() as conn:
            gpci_count = conn.execute(
                "SELECT COUNT(*) FROM gpci WHERE year = ?", (year,)
            ).fetchone()[0]
            if gpci_count == 0:
                clear_gpci_data(year)
                insert_gpci_records(get_embedded_gpci_records(year))
    except:
        pass  # Fallback will handle it


def render_region_selector(key_prefix: str, year: int):
    """Render state and locality selection dropdowns.

    Returns:
        tuple: (region, locality_name, all_localities_flag)
    """
    # Ensure GPCI data exists before rendering
    ensure_gpci_data(year)

    # STATE_NAMES maps full name -> abbreviation, e.g., "CALIFORNIA" -> "CA"
    # Create options as "CA - California" for better display
    state_abbrevs = sorted(STATE_NAMES.values())
    state_name_lookup = {v: k.title() for k, v in STATE_NAMES.items()}  # CA -> California
    state_options = [f"{abbr} - {state_name_lookup[abbr]}" for abbr in state_abbrevs]

    # State selection - default to Texas
    default_state = "TX - Texas"
    default_state_index = state_options.index(default_state) if default_state in state_options else 0

    selected_state = st.selectbox(
        "State",
        options=state_options,
        index=default_state_index,
        help="Select a state",
        key=f"{key_prefix}_state"
    )
    state_code = selected_state.split(" - ")[0].strip()

    # Get localities for selected state
    localities = get_locality_options_for_state(state_code, year)

    # Always show locality dropdown
    if localities:
        locality_labels = [loc["label"] for loc in localities]

        # Build options list
        if len(localities) > 1:
            options = ["All localities in " + state_code] + locality_labels
        else:
            options = locality_labels

        # Default to Houston if Texas is selected, otherwise first option
        default_locality_index = 0
        if state_code == "TX":
            for i, label in enumerate(options):
                if "Houston" in label:
                    default_locality_index = i
                    break

        selected_locality = st.selectbox(
            "Locality",
            options=options,
            index=default_locality_index,
            help=f"Select a locality ({len(localities)} available)",
            key=f"{key_prefix}_locality"
        )

        if selected_locality.startswith("All localities"):
            return state_code, None, True
        else:
            # Find the selected locality
            for loc in localities:
                if loc["label"] == selected_locality:
                    carrier_locality = f"{loc['carrier']}-{loc['locality']}"
                    return carrier_locality, loc["name"], False
            # Fallback to first locality
            loc = localities[0]
            return f"{loc['carrier']}-{loc['locality']}", loc["name"], False
    else:
        # No localities - show placeholder dropdown
        st.selectbox(
            "Locality",
            options=["No localities available"],
            disabled=True,
            key=f"{key_prefix}_locality"
        )
        return state_code, None, False


def display_results(results, show_breakdown, show_all_localities):
    """Display lookup results."""
    for i, result in enumerate(results):
        if show_all_localities and len(results) > 1:
            st.subheader(f"📍 {result.locality_name}")
        else:
            st.subheader(f"💰 Reimbursement Rate")

        # Main result card
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Payment Amount", f"${result.payment_amount:.2f}")

        with col2:
            setting = "Facility" if result.facility else "Non-Facility"
            st.metric("Setting", setting)

        with col3:
            st.metric("Year", result.year)

        # Code details
        st.markdown("---")
        st.markdown(f"**Code:** {result.code}")
        st.markdown(f"**Description:** {result.description}")
        st.markdown(f"**Locality:** {result.locality_name} ({result.carrier_locality})")

        # Calculation breakdown (only show if we have RVU data)
        if show_breakdown:
            b = result.breakdown
            # Check if this is pre-calculated (no RVU data) or calculated
            has_rvu_data = b.total_adjusted_rvu > 0

            if has_rvu_data:
                st.markdown("---")
                st.markdown("**Calculation Breakdown**")

                breakdown_data = {
                    "Component": ["Work", "Practice Expense", "Malpractice", "**Total**"],
                    "RVU": [f"{b.work_rvu:.2f}", f"{b.pe_rvu:.2f}", f"{b.mp_rvu:.2f}", ""],
                    "GPCI": [f"{b.work_gpci:.3f}", f"{b.pe_gpci:.3f}", f"{b.mp_gpci:.3f}", ""],
                    "Adjusted": [f"{b.work_adjusted:.4f}", f"{b.pe_adjusted:.4f}", f"{b.mp_adjusted:.4f}", f"**{b.total_adjusted_rvu:.4f}**"],
                }

                df = pd.DataFrame(breakdown_data)
                st.table(df)

                st.markdown(f"**Conversion Factor:** ${b.conversion_factor:.4f}")
                st.markdown(f"**Formula:** {b.total_adjusted_rvu:.4f} × ${b.conversion_factor:.4f} = **${b.payment_amount:.2f}**")
            else:
                st.markdown("---")
                st.info("💡 This rate is a pre-calculated CMS payment amount (no RVU breakdown available).")

        if show_all_localities and i < len(results) - 1:
            st.markdown("---")
            st.markdown("")


# Page config
st.set_page_config(
    page_title="CMS Rates Lookup",
    page_icon="🏥",
    layout="wide",
)

# Title
st.title("🏥 CMS Medicare Reimbursement Rate Lookup")
st.markdown("Look up Medicare Physician Fee Schedule rates by CPT code and region")

# Load data (auto-downloads if not present)
year = get_default_year()

with st.spinner(f"Loading CMS data for {year}... (first load may take a minute)"):
    data_loaded = load_data(year)

if not data_loaded:
    st.warning(f"⚠️ RVU data download in progress or failed for {year}. Some features may be limited. Try refreshing in a minute.")

# Sidebar for options
st.sidebar.header("Options")
facility = st.sidebar.checkbox("Facility Rate", value=False, help="Check for facility setting, uncheck for non-facility")
show_breakdown = st.sidebar.checkbox("Show Calculation Breakdown", value=True)
show_all_localities = st.sidebar.checkbox("Show All Localities", value=False, help="Show rates for all localities in the selected state")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Single Code Lookup", "📋 Multi-Code Lookup", "📝 Search by Description", "📊 Rate Comparison"])

# Tab 1: Single Code Lookup
with tab1:
    cpt_code = st.text_input(
        "CPT/HCPCS Code",
        value="99213",
        max_chars=5,
        help="Enter a 5-character CPT or HCPCS code (e.g., 99213, G0438)",
        key="cpt_input"
    )

    region, locality_name, all_locs = render_region_selector("single", year)

    if st.button("🔍 Look Up Rate", type="primary", key="lookup_btn"):
        try:
            lookup_service = RateLookup(year)
            results = lookup_service.lookup(
                cpt_code=cpt_code,
                region=region,
                facility=facility,
                all_localities=all_locs or show_all_localities,
            )

            if results:
                display_results(results, show_breakdown, all_locs or show_all_localities)

        except InvalidCPTCodeError as e:
            st.error(f"❌ Invalid CPT Code: {e}")
        except CPTCodeNotFoundError as e:
            st.error(f"❌ CPT Code Not Found: {e}")
        except InvalidRegionError as e:
            st.error(f"❌ Invalid Region: {e}")
        except DataNotFoundError as e:
            st.error(f"❌ Data Not Found: {e}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# Tab 2: Multi-Code Lookup
with tab2:
    st.markdown("Enter multiple CPT codes to look up rates for all of them at once.")

    cpt_codes_input = st.text_area(
        "CPT/HCPCS Codes (one per line or comma-separated)",
        value="99213\n99214\n99215",
        height=150,
        help="Enter multiple CPT codes, one per line or separated by commas",
        key="multi_cpt_input"
    )

    region_multi, locality_name_multi, all_locs_multi = render_region_selector("multi", year)

    if st.button("🔍 Look Up All Rates", type="primary", key="multi_lookup_btn"):
        # Parse the input - handle newlines and commas
        raw_codes = cpt_codes_input.replace(",", "\n").split("\n")
        cpt_codes = [code.strip() for code in raw_codes if code.strip()]

        if not cpt_codes:
            st.warning("Please enter at least one CPT code")
        else:
            lookup_service = RateLookup(year)
            all_results = []
            errors = []

            # Create a summary table
            summary_data = []

            for code in cpt_codes:
                try:
                    results = lookup_service.lookup(
                        cpt_code=code,
                        region=region_multi,
                        facility=facility,
                        all_localities=all_locs_multi,
                    )
                    if results:
                        # If all localities, take first one for summary
                        result = results[0]
                        all_results.append(result)
                        summary_data.append({
                            "Code": result.code,
                            "Description": result.description,
                            "Locality": result.locality_name,
                            "Payment": f"${result.payment_amount:.2f}",
                            "Work RVU": f"{result.breakdown.work_rvu:.2f}" if result.breakdown.work_rvu > 0 else "N/A",
                            "Setting": "Facility" if result.facility else "Non-Facility",
                        })
                except Exception as e:
                    errors.append(f"{code}: {e}")

            if summary_data:
                st.success(f"Found rates for {len(summary_data)} codes")

                # Calculate total
                total_payment = sum(r.payment_amount for r in all_results)

                # Display summary table
                df = pd.DataFrame(summary_data)
                st.dataframe(df, hide_index=True)

                # Show total
                st.markdown(f"### 💰 Total Payment: **${total_payment:.2f}**")

                # Detailed breakdown expander
                if show_breakdown:
                    with st.expander("📊 View Detailed Breakdown"):
                        display_results(all_results, show_breakdown, False)

            if errors:
                with st.expander(f"⚠️ {len(errors)} errors"):
                    for error in errors:
                        st.error(error)

# Tab 3: Search by Description
with tab3:
    search_query = st.text_input(
        "Search Description",
        placeholder="e.g., office visit, x-ray, MRI, surgery",
        help="Enter keywords to search CPT code descriptions",
        key="search_input"
    )

    region_search, locality_name_search, all_locs_search = render_region_selector("search", year)

    max_results = st.slider("Max Results", min_value=10, max_value=100, value=25, key="max_results")

    if st.button("🔍 Search", type="primary", key="search_btn"):
        if search_query:
            results = search_by_description(search_query, year, limit=max_results)

            if results:
                st.success(f"Found {len(results)} matching CPT codes")

                # Create a dataframe for display
                lookup_service = RateLookup(year)

                data = []
                for rvu in results:
                    try:
                        # Get the rate for this code
                        rate_results = lookup_service.lookup(
                            cpt_code=rvu.hcpcs_code,
                            region=region_search,
                            facility=facility,
                        )
                        if rate_results:
                            payment = f"${rate_results[0].payment_amount:.2f}"
                            locality = rate_results[0].locality_name
                        else:
                            payment = "N/A"
                            locality = "N/A"
                    except:
                        payment = "N/A"
                        locality = "N/A"

                    data.append({
                        "Code": rvu.hcpcs_code,
                        "Description": rvu.description,
                        "Locality": locality,
                        "Work RVU": f"{rvu.work_rvu:.2f}" if rvu.work_rvu > 0 else "N/A",
                        "Payment": payment,
                    })

                df = pd.DataFrame(data)

                # Display results table
                st.dataframe(
                    df,
                    hide_index=True,
                    column_config={
                        "Code": st.column_config.TextColumn("Code", width="small"),
                        "Description": st.column_config.TextColumn("Description", width="medium"),
                        "Locality": st.column_config.TextColumn("Locality", width="medium"),
                        "Work RVU": st.column_config.TextColumn("Work RVU", width="small"),
                        "Payment": st.column_config.TextColumn("Payment", width="small"),
                    }
                )

                st.info("💡 Copy a code from the table and use the 'Lookup by Code' tab for detailed breakdown")
            else:
                st.warning(f"No CPT codes found matching '{search_query}'")
        else:
            st.warning("Please enter a search term")

# Tab 4: Rate Comparison
with tab4:
    st.markdown("Compare Medicare rates with commercial insurers and Medicaid across different payers.")

    compare_cpt = st.text_input(
        "CPT/HCPCS Code",
        value="99213",
        max_chars=5,
        help="Enter a CPT or HCPCS code to compare rates",
        key="compare_cpt_input"
    )

    region_compare, locality_name_compare, all_locs_compare = render_region_selector("compare", year)

    if st.button("📊 Compare Rates", type="primary", key="compare_btn"):
        try:
            lookup_service = RateLookup(year)
            medicare_results = lookup_service.lookup(
                cpt_code=compare_cpt,
                region=region_compare,
                facility=facility,
            )

            if medicare_results:
                medicare_result = medicare_results[0]
                medicare_rate = medicare_result.payment_amount
                state = medicare_result.state

                # Get payer rates for this code
                payer_rates = get_payer_rates(compare_cpt, year, state=state)

                # Build comparison data
                comparison_data = [{
                    "Payer": "Medicare (CMS)",
                    "Type": "Government",
                    "Rate": f"${float(medicare_rate):.2f}",
                    "% of Medicare": "100.0%",
                    "rate_value": float(medicare_rate),
                }]

                for pr in payer_rates:
                    rate = pr.calculate_rate_from_medicare(medicare_rate, facility)
                    if rate is not None:
                        pct = (float(rate) / float(medicare_rate)) * 100 if medicare_rate > 0 else 0
                        comparison_data.append({
                            "Payer": pr.payer_name,
                            "Type": pr.payer_type.title(),
                            "Rate": f"${float(rate):.2f}",
                            "% of Medicare": f"{pct:.1f}%",
                            "rate_value": float(rate),
                        })

                # Display results
                st.subheader(f"Rate Comparison for CPT {compare_cpt}")
                st.markdown(f"**Region:** {medicare_result.locality_name} ({state})")
                st.markdown(f"**Setting:** {'Facility' if facility else 'Non-Facility'}")
                st.markdown("---")

                # Create DataFrame for display
                df = pd.DataFrame(comparison_data)
                display_df = df[["Payer", "Type", "Rate", "% of Medicare"]]

                # Display as styled table
                st.dataframe(
                    display_df,
                    hide_index=True,
                    column_config={
                        "Payer": st.column_config.TextColumn("Payer", width="medium"),
                        "Type": st.column_config.TextColumn("Type", width="small"),
                        "Rate": st.column_config.TextColumn("Rate", width="small"),
                        "% of Medicare": st.column_config.TextColumn("% of Medicare", width="small"),
                    }
                )

                # Visual chart
                if len(comparison_data) > 1:
                    st.markdown("---")
                    st.markdown("### Rate Comparison Chart")

                    chart_data = pd.DataFrame({
                        "Payer": [d["Payer"] for d in comparison_data],
                        "Rate": [d["rate_value"] for d in comparison_data],
                    })
                    st.bar_chart(chart_data.set_index("Payer"))

                if len(comparison_data) == 1:
                    st.info("No payer rates found for this code/region. Use the sidebar to add payer rates.")

        except (InvalidCPTCodeError, CPTCodeNotFoundError, InvalidRegionError, DataNotFoundError) as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error: {e}")

    # Payer management section
    st.markdown("---")
    st.markdown("### Manage Payer Rates")

    with st.expander("Add New Payer Rate"):
        col1, col2 = st.columns(2)

        with col1:
            new_cpt = st.text_input("CPT Code", max_chars=5, key="new_payer_cpt")
            new_payer = st.text_input("Payer Name", key="new_payer_name", placeholder="e.g., Blue Cross, Medi-Cal")
            new_type = st.selectbox("Payer Type", ["commercial", "medicaid", "other"], key="new_payer_type")

        with col2:
            new_state = st.text_input("State (optional)", max_chars=2, key="new_payer_state", placeholder="e.g., CA")
            rate_method = st.radio("Rate Method", ["Fixed Rate", "% of Medicare"], key="rate_method")

            if rate_method == "Fixed Rate":
                new_rate = st.number_input("Non-Facility Rate ($)", min_value=0.0, step=1.0, key="new_payer_rate")
                new_fac_rate = st.number_input("Facility Rate ($) (optional)", min_value=0.0, step=1.0, key="new_payer_fac_rate")
                new_pct = None
            else:
                new_rate = None
                new_fac_rate = None
                new_pct = st.number_input("% of Medicare", min_value=0.0, max_value=500.0, value=100.0, step=5.0, key="new_payer_pct")

        if st.button("Add Payer Rate", key="add_payer_btn"):
            if not new_cpt or not new_payer:
                st.error("CPT Code and Payer Name are required")
            elif rate_method == "Fixed Rate" and not new_rate and not new_fac_rate:
                st.error("At least one rate is required")
            elif rate_method == "% of Medicare" and not new_pct:
                st.error("Percentage is required")
            else:
                try:
                    payer_rate = PayerRate(
                        hcpcs_code=new_cpt.upper(),
                        payer_name=new_payer,
                        payer_type=new_type,
                        year=year,
                        state=new_state.upper() if new_state else None,
                        non_facility_rate=Decimal(str(new_rate)) if new_rate else None,
                        facility_rate=Decimal(str(new_fac_rate)) if new_fac_rate else None,
                        percent_of_medicare=Decimal(str(new_pct)) if new_pct else None,
                        source="Web UI",
                    )
                    insert_payer_rate(payer_rate)
                    st.success(f"Added rate for {new_cpt} from {new_payer}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding rate: {e}")

    # Upload fee schedule
    with st.expander("Upload Fee Schedule (CSV)"):
        st.markdown("Upload a CSV file containing CPT codes and reimbursement rates.")

        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            key="fee_schedule_upload",
            help="CSV should contain at minimum a CPT code column and a rate column"
        )

        if uploaded_file is not None:
            try:
                # Read CSV
                import io
                df_upload = pd.read_csv(uploaded_file)

                st.markdown(f"**Found {len(df_upload)} rows and {len(df_upload.columns)} columns**")

                # Column mapping
                col1, col2 = st.columns(2)

                with col1:
                    upload_payer = st.text_input(
                        "Payer Name",
                        key="upload_payer_name",
                        placeholder="e.g., Blue Cross, Medi-Cal"
                    )
                    upload_type = st.selectbox(
                        "Payer Type",
                        ["commercial", "medicaid", "other"],
                        key="upload_payer_type"
                    )
                    upload_state = st.text_input(
                        "State (optional)",
                        max_chars=2,
                        key="upload_payer_state",
                        placeholder="e.g., CA"
                    )

                with col2:
                    columns = list(df_upload.columns)
                    code_col = st.selectbox(
                        "CPT Code Column",
                        columns,
                        key="upload_code_col"
                    )
                    rate_col = st.selectbox(
                        "Rate Column (Non-Facility)",
                        ["(none)"] + columns,
                        key="upload_rate_col"
                    )
                    allowed_col = st.selectbox(
                        "Allowed Amount Column (optional)",
                        ["(none)"] + columns,
                        key="upload_allowed_col",
                        help="If specified, used as non-facility rate when Rate Column is empty"
                    )
                    fac_rate_col = st.selectbox(
                        "Facility Rate Column (optional)",
                        ["(none)"] + columns,
                        key="upload_fac_rate_col"
                    )

                # Preview data
                st.markdown("**Preview (first 10 rows):**")
                preview_cols = [code_col]
                if rate_col != "(none)":
                    preview_cols.append(rate_col)
                if allowed_col != "(none)":
                    preview_cols.append(allowed_col)
                if fac_rate_col != "(none)":
                    preview_cols.append(fac_rate_col)
                st.dataframe(df_upload[preview_cols].head(10), hide_index=True)

                # Import button
                if st.button("Import Fee Schedule", key="import_fee_schedule_btn", type="primary"):
                    if not upload_payer:
                        st.error("Payer Name is required")
                    elif rate_col == "(none)" and allowed_col == "(none)" and fac_rate_col == "(none)":
                        st.error("At least one rate column must be selected")
                    else:
                        imported = 0
                        errors = 0

                        for _, row in df_upload.iterrows():
                            try:
                                cpt_code = str(row[code_col]).strip()
                                if not cpt_code:
                                    continue

                                # Parse rate from Rate Column
                                non_fac_rate = None
                                if rate_col != "(none)":
                                    rate_str = str(row[rate_col]).replace('$', '').replace(',', '').strip()
                                    non_fac_rate = Decimal(rate_str) if rate_str and rate_str != 'nan' else None

                                # Parse allowed amount (use as non-facility rate if rate is empty)
                                if allowed_col != "(none)" and non_fac_rate is None:
                                    allowed_str = str(row[allowed_col]).replace('$', '').replace(',', '').strip()
                                    non_fac_rate = Decimal(allowed_str) if allowed_str and allowed_str != 'nan' else None

                                # Parse facility rate if specified
                                fac_rate = None
                                if fac_rate_col != "(none)":
                                    fac_str = str(row[fac_rate_col]).replace('$', '').replace(',', '').strip()
                                    fac_rate = Decimal(fac_str) if fac_str and fac_str != 'nan' else None

                                if non_fac_rate is None and fac_rate is None:
                                    continue

                                payer_rate = PayerRate(
                                    hcpcs_code=cpt_code.upper(),
                                    payer_name=upload_payer,
                                    payer_type=upload_type,
                                    year=year,
                                    state=upload_state.upper() if upload_state else None,
                                    non_facility_rate=non_fac_rate,
                                    facility_rate=fac_rate,
                                    source=f"Uploaded: {uploaded_file.name}",
                                )
                                insert_payer_rate(payer_rate)
                                imported += 1
                            except Exception:
                                errors += 1

                        if imported > 0:
                            st.success(f"Successfully imported {imported} rates for '{upload_payer}'")
                        if errors > 0:
                            st.warning(f"Skipped {errors} rows due to invalid data")
                        if imported > 0:
                            st.rerun()

            except Exception as e:
                st.error(f"Error reading CSV: {e}")

    # Show existing payers
    with st.expander("View Existing Payers"):
        payers = get_all_payers(year)
        if payers:
            payers_df = pd.DataFrame(payers)
            payers_df.columns = ["Payer Name", "Type", "State", "# Rates"]
            st.dataframe(payers_df, hide_index=True)
        else:
            st.info("No payer rates in database yet.")


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8em;">
    Data source: CMS Physician Fee Schedule |
    Payment = [(Work RVU × Work GPCI) + (PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × Conversion Factor
</div>
""", unsafe_allow_html=True)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown(f"""
This tool looks up Medicare reimbursement rates from the
CMS Physician Fee Schedule.

**Data Year:** {year}

**Conversion Factor:** $32.3465
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick CPT Codes")
st.sidebar.markdown("""
- `99213` - Office visit, established
- `99214` - Office visit, moderate
- `99215` - Office visit, high
- `99203` - Office visit, new patient
- `99385` - Preventive visit 18-39
- `99395` - Preventive visit 40-64
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### Search Tips")
st.sidebar.markdown("""
Try searching for:
- `office visit`
- `x-ray`
- `MRI`
- `CT scan`
- `surgery`
- `injection`
""")
