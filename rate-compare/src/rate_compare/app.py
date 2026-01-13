"""Medicare Rate Comparison Tool - Streamlit Web GUI."""

import streamlit as st
import pandas as pd
from pathlib import Path
from decimal import Decimal

from rate_compare.config import DEFAULT_YEAR, STATES
from rate_compare.db.database import init_db
from rate_compare.services.lookup import (
    import_medicare_data,
    get_medicare_rate,
    get_medicare_rates_by_state,
    get_localities_by_state,
    search_medicare_codes,
    has_medicare_data,
    clear_medicare_data,
    get_all_states,
)
from rate_compare.services.compare import (
    import_payer_data,
    get_payers,
    compare_rates,
    delete_payer,
    clear_payer_data,
)
from rate_compare.parsers.csv_parser import parse_payer_csv, detect_csv_columns


# Initialize database
init_db()

# Page config
st.set_page_config(
    page_title="Medicare Rate Comparison",
    page_icon="🏥",
    layout="wide",
)

st.title("Medicare Rate Comparison Tool")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Rate Lookup",
    "⚖️ Rate Comparison",
    "📥 Import Data",
    "⚙️ Manage Payers"
])


# ============================================================================
# Tab 1: Rate Lookup
# ============================================================================
with tab1:
    st.header("Medicare Rate Lookup")

    col1, col2 = st.columns([1, 3])

    with col1:
        year = st.selectbox("Year", [2026, 2025, 2024], key="lookup_year")

        if not has_medicare_data(year):
            st.warning(f"No Medicare data for {year}. Import data in the 'Import Data' tab.")
        else:
            # Get available states
            states = get_all_states(year)
            if not states:
                states = STATES

            state = st.selectbox("State", states, key="lookup_state")
            cpt_code = st.text_input("CPT/HCPCS Code", placeholder="99213", key="lookup_code")
            facility = st.checkbox("Facility Rate", key="lookup_facility")

            if st.button("Look Up Rate", type="primary"):
                if cpt_code:
                    # Get all rates for this code in the state
                    rates = get_medicare_rates_by_state(cpt_code, state, year)

                    if rates:
                        with col2:
                            st.subheader(f"Rates for {cpt_code} in {state}")
                            st.caption(f"{'Facility' if facility else 'Non-Facility'} rates for {year}")

                            # Build grid data
                            data = []
                            for rate in rates:
                                fee = rate.facility_fee if facility else rate.non_facility_fee
                                data.append({
                                    "Locality": rate.locality_name,
                                    "Carrier-Locality": rate.carrier_locality,
                                    "Non-Facility": f"${rate.non_facility_fee:.2f}",
                                    "Facility": f"${rate.facility_fee:.2f}",
                                    "Payment": f"${fee:.2f}",
                                })

                            df = pd.DataFrame(data)
                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Locality": st.column_config.TextColumn("Locality", width="medium"),
                                    "Carrier-Locality": st.column_config.TextColumn("Code", width="small"),
                                    "Non-Facility": st.column_config.TextColumn("Non-Facility", width="small"),
                                    "Facility": st.column_config.TextColumn("Facility", width="small"),
                                    "Payment": st.column_config.TextColumn("Selected", width="small"),
                                }
                            )

                            # Summary stats
                            fees = [rate.facility_fee if facility else rate.non_facility_fee for rate in rates]
                            st.write(f"**{len(rates)} localities** | Min: ${min(fees):.2f} | Max: ${max(fees):.2f} | Avg: ${sum(fees)/len(fees):.2f}")
                    else:
                        with col2:
                            st.error(f"Code {cpt_code} not found in {year} fee schedule for {state}.")
                else:
                    st.warning("Please enter a CPT code.")


# ============================================================================
# Tab 2: Rate Comparison
# ============================================================================
with tab2:
    st.header("Compare Rates")

    col1, col2 = st.columns([1, 3])

    with col1:
        year = st.selectbox("Year", [2026, 2025, 2024], key="compare_year")

        if not has_medicare_data(year):
            st.warning(f"No Medicare data for {year}.")
        else:
            states = get_all_states(year)
            if not states:
                states = STATES

            state = st.selectbox("State", states, key="compare_state")
            cpt_code = st.text_input("CPT/HCPCS Code", placeholder="99213", key="compare_code")
            facility = st.checkbox("Facility Rates", key="compare_facility")

            if st.button("Compare Rates", type="primary"):
                if cpt_code:
                    comparisons = compare_rates(cpt_code, state, year, facility)

                    if comparisons:
                        with col2:
                            st.subheader(f"Rate Comparison for {cpt_code} in {state}")

                            # Build comparison table
                            data = []
                            for comp in comparisons:
                                fee = comp.facility_fee if facility else comp.non_facility_fee
                                data.append({
                                    "Payer": comp.payer_name,
                                    "Type": comp.payer_type.title(),
                                    "Non-Facility": f"${comp.non_facility_fee:.2f}" if comp.non_facility_fee else "-",
                                    "Facility": f"${comp.facility_fee:.2f}" if comp.facility_fee else "-",
                                    "% of Medicare": f"{comp.percent_of_medicare:.1f}%" if comp.percent_of_medicare else "-",
                                })

                            df = pd.DataFrame(data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        with col2:
                            st.info(f"No rates found for {cpt_code} in {state}.")
                else:
                    st.warning("Please enter a CPT code.")


# ============================================================================
# Tab 3: Import Data
# ============================================================================
with tab3:
    st.header("Import Data")

    import_type = st.radio(
        "Import Type",
        ["Medicare Data (CMS)", "Custom Payer (CSV)"],
        horizontal=True
    )

    if import_type == "Medicare Data (CMS)":
        st.subheader("Import CMS Medicare Data")
        st.write("Upload a CMS Payment Amount File (PFALL26A format).")

        uploaded_file = st.file_uploader(
            "Choose CMS file",
            type=["txt", "csv"],
            key="cms_upload"
        )

        year = st.selectbox("Year", [2026, 2025, 2024], key="import_cms_year")
        clear_existing = st.checkbox("Clear existing data for this year", key="cms_clear")

        if uploaded_file is not None:
            if st.button("Import Medicare Data", type="primary"):
                # Save uploaded file temporarily
                temp_path = Path("/tmp") / uploaded_file.name
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(count):
                    progress_bar.progress(min(count / 1000000, 1.0))
                    status_text.text(f"Imported {count:,} records...")

                try:
                    count = import_medicare_data(
                        temp_path,
                        year=year,
                        clear_existing=clear_existing,
                        progress_callback=update_progress,
                    )
                    progress_bar.progress(1.0)
                    st.success(f"Successfully imported {count:,} Medicare rates for {year}!")
                except Exception as e:
                    st.error(f"Import failed: {e}")
                finally:
                    temp_path.unlink(missing_ok=True)

    else:  # Custom Payer CSV
        st.subheader("Import Custom Payer Rates")
        st.write("Upload a CSV file with payer fee schedule data.")

        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=["csv"],
            key="payer_upload"
        )

        if uploaded_file is not None:
            # Read and preview CSV
            csv_content = uploaded_file.getvalue().decode("utf-8")
            columns = detect_csv_columns(csv_content)

            if columns:
                st.write("**CSV Columns Detected:**", ", ".join(columns))

                # Preview data
                preview_df = pd.read_csv(uploaded_file)
                uploaded_file.seek(0)  # Reset file position
                st.write("**Preview (first 5 rows):**")
                st.dataframe(preview_df.head(), use_container_width=True, hide_index=True)

                st.subheader("Configure Import")

                col1, col2 = st.columns(2)

                with col1:
                    payer_name = st.text_input("Payer Name", placeholder="Blue Cross TX")
                    payer_type = st.selectbox("Payer Type", ["commercial", "medicaid", "other"])
                    year = st.selectbox("Year", [2026, 2025, 2024], key="import_payer_year")

                with col2:
                    code_column = st.selectbox("HCPCS Code Column", columns)
                    fee_column = st.selectbox("Non-Facility Fee Column", columns)
                    facility_column = st.selectbox(
                        "Facility Fee Column (optional)",
                        ["(none)"] + columns
                    )
                    state_column = st.selectbox(
                        "State Column (optional)",
                        ["(none)"] + columns
                    )

                default_state = st.text_input("Default State (if not in CSV)", placeholder="TX")

                if st.button("Import Payer Data", type="primary"):
                    if not payer_name:
                        st.error("Please enter a payer name.")
                    else:
                        try:
                            records = parse_payer_csv(
                                csv_content,
                                payer_name=payer_name,
                                payer_type=payer_type,
                                year=year,
                                code_column=code_column,
                                fee_column=fee_column,
                                facility_fee_column=facility_column if facility_column != "(none)" else None,
                                state_column=state_column if state_column != "(none)" else None,
                                default_state=default_state if default_state else None,
                                source=uploaded_file.name,
                            )
                            count = import_payer_data(records)
                            st.success(f"Successfully imported {count:,} rates for {payer_name}!")
                        except Exception as e:
                            st.error(f"Import failed: {e}")


# ============================================================================
# Tab 4: Manage Payers
# ============================================================================
with tab4:
    st.header("Manage Payers")

    year = st.selectbox("Year", [2026, 2025, 2024], key="manage_year")

    payers = get_payers(year)

    if payers:
        st.subheader(f"Imported Payers ({year})")

        # Build payer table
        payer_data = []
        for payer in payers:
            payer_data.append({
                "Payer Name": payer["payer_name"],
                "Type": payer["payer_type"].title(),
                "Records": f"{payer['record_count']:,}",
                "States": payer["states"],
                "First Import": payer["first_import"][:10] if payer["first_import"] else "-",
            })

        df = pd.DataFrame(payer_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Delete payer
        st.subheader("Delete Payer")
        payer_names = [p["payer_name"] for p in payers]
        payer_to_delete = st.selectbox("Select payer to delete", payer_names)

        if st.button("Delete Payer", type="secondary"):
            deleted = delete_payer(payer_to_delete, year)
            st.success(f"Deleted {deleted:,} records for {payer_to_delete}.")
            st.rerun()
    else:
        st.info(f"No custom payers imported for {year}.")

    # Clear all data section
    st.divider()
    st.subheader("Clear Data")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Clear All Medicare Data", type="secondary"):
            clear_medicare_data(year)
            st.success(f"Cleared all Medicare data for {year}.")
            st.rerun()

    with col2:
        if st.button("Clear All Payer Data", type="secondary"):
            clear_payer_data(year)
            st.success(f"Cleared all payer data for {year}.")
            st.rerun()


# Footer
st.divider()
st.caption("Medicare Rate Comparison Tool v1.0")
