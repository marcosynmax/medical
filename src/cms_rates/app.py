"""Streamlit web app for CMS Rates lookup."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from cms_rates.config import get_default_year
from cms_rates.data.storage import has_data, init_database, search_by_description
from cms_rates.services.lookup import (
    RateLookup,
    InvalidCPTCodeError,
    CPTCodeNotFoundError,
    InvalidRegionError,
    DataNotFoundError,
)
from cms_rates.services.region_mapper import RegionMapper, STATE_NAMES


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

        # Calculation breakdown
        if show_breakdown:
            st.markdown("---")
            st.markdown("**Calculation Breakdown**")

            b = result.breakdown
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

# Check if data is available
year = get_default_year()
init_database()

if not has_data(year):
    st.error(f"⚠️ No data available for {year}. Please run the update command first:")
    st.code(f"PYTHONPATH=src python3 -m cms_rates update --year {year}")
    st.stop()

# Sidebar for options
st.sidebar.header("Options")
facility = st.sidebar.checkbox("Facility Rate", value=False, help="Check for facility setting, uncheck for non-facility")
show_breakdown = st.sidebar.checkbox("Show Calculation Breakdown", value=True)
show_all_localities = st.sidebar.checkbox("Show All Localities", value=False, help="Show rates for all localities in the selected state")

# Create tabs
tab1, tab2 = st.tabs(["🔍 Lookup by Code", "📝 Search by Description"])

# Create state options (shared)
states = sorted(STATE_NAMES.keys())
state_options = [f"{STATE_NAMES[s]} ({s})" for s in states]

# Tab 1: Lookup by Code
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        cpt_code = st.text_input(
            "CPT/HCPCS Code",
            value="99213",
            max_chars=5,
            help="Enter a 5-character CPT or HCPCS code (e.g., 99213, G0438)",
            key="cpt_input"
        )

    with col2:
        selected_state = st.selectbox(
            "State/Region",
            options=state_options,
            index=state_options.index("California (CA)") if "California (CA)" in state_options else 0,
            help="Select a state to look up rates",
            key="state_select_1"
        )
        region = selected_state.split("(")[1].replace(")", "").strip()

    if st.button("🔍 Look Up Rate", type="primary", use_container_width=True, key="lookup_btn"):
        try:
            lookup_service = RateLookup(year)
            results = lookup_service.lookup(
                cpt_code=cpt_code,
                region=region,
                facility=facility,
                all_localities=show_all_localities,
            )

            if results:
                display_results(results, show_breakdown, show_all_localities)

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

# Tab 2: Search by Description
with tab2:
    search_query = st.text_input(
        "Search Description",
        placeholder="e.g., office visit, x-ray, MRI, surgery",
        help="Enter keywords to search CPT code descriptions",
        key="search_input"
    )

    col1, col2 = st.columns(2)
    with col1:
        selected_state_search = st.selectbox(
            "State/Region for Pricing",
            options=state_options,
            index=state_options.index("California (CA)") if "California (CA)" in state_options else 0,
            help="Select a state to show rates",
            key="state_select_2"
        )
        region_search = selected_state_search.split("(")[1].replace(")", "").strip()

    with col2:
        max_results = st.slider("Max Results", min_value=10, max_value=100, value=25, key="max_results")

    if st.button("🔍 Search", type="primary", use_container_width=True, key="search_btn"):
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
                        else:
                            payment = "N/A"
                    except:
                        payment = "N/A"

                    data.append({
                        "Code": rvu.hcpcs_code,
                        "Description": rvu.description,
                        "Work RVU": f"{rvu.work_rvu:.2f}",
                        "Payment": payment,
                    })

                df = pd.DataFrame(data)

                # Make the code column clickable (store selection)
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Code": st.column_config.TextColumn("Code", width="small"),
                        "Description": st.column_config.TextColumn("Description", width="large"),
                        "Work RVU": st.column_config.TextColumn("Work RVU", width="small"),
                        "Payment": st.column_config.TextColumn("Payment", width="small"),
                    }
                )

                st.info("💡 Copy a code from the table and use the 'Lookup by Code' tab for detailed breakdown")
            else:
                st.warning(f"No CPT codes found matching '{search_query}'")
        else:
            st.warning("Please enter a search term")


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
st.sidebar.markdown("""
This tool looks up Medicare reimbursement rates from the
CMS Physician Fee Schedule.

**Data Year:** 2025

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
