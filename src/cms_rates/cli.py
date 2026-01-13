"""Command-line interface for CMS Rates."""

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from cms_rates import __version__
from cms_rates.config import get_default_year, ensure_data_dirs
from cms_rates.data.downloader import download_rvu_file, download_gpci_file
from cms_rates.data.parser import parse_rvu_file, parse_gpci_file
from cms_rates.data.storage import (
    init_database,
    clear_rvu_data,
    clear_gpci_data,
    insert_rvu_records,
    insert_gpci_records,
    has_data,
    insert_payer_rate,
    get_payer_rates,
    get_all_payers,
    delete_payer_rates,
    clear_payment_amounts,
    insert_payment_records,
    has_payment_data,
    get_payment_localities,
)
from cms_rates.services.lookup import (
    RateLookup,
    LookupResult,
    InvalidCPTCodeError,
    CPTCodeNotFoundError,
    InvalidRegionError,
    DataNotFoundError,
)
from cms_rates.services.region_mapper import RegionMapper

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """CMS Rates - Medicare Physician Fee Schedule Lookup Tool.

    Look up Medicare reimbursement rates by CPT code and geographic region.
    """
    pass


@main.command()
@click.argument("cpt_codes", nargs=-1, required=True)
@click.option("--region", "-r", required=True, help="State name, abbreviation, or locality code")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option("--facility", "-f", is_flag=True, help="Show facility rate (default: non-facility)")
@click.option("--modifier", "-m", default=None, help="Modifier code (TC, 26, etc.)")
@click.option(
    "--format", "-o", "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format"
)
@click.option("--all-localities", is_flag=True, help="Show rates for all localities in region")
@click.option("--verbose", "-v", is_flag=True, help="Show calculation breakdown")
def lookup(
    cpt_codes: tuple,
    region: str,
    year: Optional[int],
    facility: bool,
    modifier: Optional[str],
    output_format: str,
    all_localities: bool,
    verbose: bool,
):
    """Look up Medicare reimbursement rates for one or more CPT codes.

    CPT_CODES: One or more 5-digit CPT or HCPCS codes (e.g., 99213 99214 99215)

    Examples:

        cms-rates lookup 99213 -r CA

        cms-rates lookup 99213 99214 99215 -r California

        cms-rates lookup 99213 -r CA --facility

        cms-rates lookup 99213 99214 -r TX --format json

        cms-rates lookup 99213 -r CA --all-localities
    """
    year = year or get_default_year()
    all_results = []

    lookup_service = RateLookup(year)

    for cpt_code in cpt_codes:
        try:
            results = lookup_service.lookup(
                cpt_code=cpt_code,
                region=region,
                facility=facility,
                modifier=modifier,
                all_localities=all_localities,
            )
            all_results.extend(results)
        except (InvalidCPTCodeError, CPTCodeNotFoundError, InvalidRegionError, DataNotFoundError) as e:
            console.print(f"[red]Error for {cpt_code}:[/red] {e}")
            continue

    if not all_results:
        console.print("[yellow]No results found.[/yellow]")
        sys.exit(1)

    if output_format == "json":
        output_json(all_results)
    elif output_format == "csv":
        output_csv(all_results)
    else:
        output_table(all_results, verbose)


def output_table(results: list[LookupResult], verbose: bool = False):
    """Output results as a rich table."""
    for result in results:
        setting = "Facility" if result.facility else "Non-Facility"

        # Header panel
        console.print(Panel(
            f"Medicare Physician Fee Schedule - CPT {result.code}",
            style="bold blue"
        ))

        # Basic info table
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column("Field", style="cyan")
        info_table.add_column("Value")

        info_table.add_row("Code:", result.code)
        if result.modifier:
            info_table.add_row("Modifier:", result.modifier)
        info_table.add_row("Description:", result.description)
        info_table.add_row("Year:", str(result.year))
        info_table.add_row("Setting:", setting)
        info_table.add_row("Locality:", f"{result.locality_name} ({result.carrier_locality})")
        info_table.add_row("Payment:", f"[bold green]${result.payment_amount:.2f}[/bold green]")

        console.print(info_table)

        if verbose:
            console.print()
            breakdown_table = Table(title="Calculation Breakdown", box=None)
            breakdown_table.add_column("Component", style="cyan")
            breakdown_table.add_column("RVU", justify="right")
            breakdown_table.add_column("GPCI", justify="right")
            breakdown_table.add_column("Adjusted", justify="right")

            b = result.breakdown
            breakdown_table.add_row("Work", f"{b.work_rvu:.2f}", f"{b.work_gpci:.3f}", f"{b.work_adjusted:.4f}")
            breakdown_table.add_row("Practice Expense", f"{b.pe_rvu:.2f}", f"{b.pe_gpci:.3f}", f"{b.pe_adjusted:.4f}")
            breakdown_table.add_row("Malpractice", f"{b.mp_rvu:.2f}", f"{b.mp_gpci:.3f}", f"{b.mp_adjusted:.4f}")
            breakdown_table.add_row("", "", "", "────────")
            breakdown_table.add_row("Total Adjusted RVU", "", "", f"{b.total_adjusted_rvu:.4f}")

            console.print(breakdown_table)
            console.print(f"\nConversion Factor: ${b.conversion_factor:.4f}")
            console.print(f"Final Payment: ${b.total_adjusted_rvu:.4f} × ${b.conversion_factor:.4f} = [bold green]${b.payment_amount:.2f}[/bold green]")

        console.print()


def output_json(results: list[LookupResult]):
    """Output results as JSON."""
    output = []
    for result in results:
        output.append({
            "code": result.code,
            "modifier": result.modifier,
            "description": result.description,
            "year": result.year,
            "setting": "facility" if result.facility else "non_facility",
            "locality": {
                "name": result.locality_name,
                "carrier_locality": result.carrier_locality,
                "state": result.state,
            },
            "payment_amount": float(result.payment_amount),
            "rvu": {
                "work": float(result.breakdown.work_rvu),
                "practice_expense": float(result.breakdown.pe_rvu),
                "malpractice": float(result.breakdown.mp_rvu),
            },
            "gpci": {
                "work": float(result.breakdown.work_gpci),
                "practice_expense": float(result.breakdown.pe_gpci),
                "malpractice": float(result.breakdown.mp_gpci),
            },
            "conversion_factor": float(result.breakdown.conversion_factor),
        })

    print(json.dumps(output if len(output) > 1 else output[0], indent=2))


def output_csv(results: list[LookupResult]):
    """Output results as CSV."""
    print("code,modifier,description,year,setting,locality,state,payment_amount")
    for result in results:
        setting = "facility" if result.facility else "non_facility"
        desc = result.description.replace(",", ";")
        print(f"{result.code},{result.modifier or ''},{desc},{result.year},{setting},{result.locality_name},{result.state},{result.payment_amount:.2f}")


@main.command()
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year to download")
@click.option("--quarter", "-q", default="a", help="Quarter (a, b, c, d)")
def update(year: Optional[int], quarter: str):
    """Download or update CMS fee schedule data.

    Downloads the RVU and GPCI files from CMS.gov and imports them into the local database.

    Examples:

        cms-rates update

        cms-rates update --year 2025

        cms-rates update --year 2025 --quarter b
    """
    year = year or get_default_year()

    console.print(f"[cyan]Updating CMS data for {year}...[/cyan]")
    ensure_data_dirs()
    init_database()

    # Download RVU file
    console.print("\n[yellow]Step 1/4:[/yellow] Downloading RVU file...")
    rvu_file = download_rvu_file(year, quarter)
    if not rvu_file:
        console.print("[red]Failed to download RVU file.[/red]")
        console.print("You may need to download manually from:")
        console.print("https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files")
        sys.exit(1)

    console.print(f"[green]Downloaded:[/green] {rvu_file.name}")

    # Download GPCI file
    console.print("\n[yellow]Step 2/4:[/yellow] Downloading GPCI file...")
    gpci_file = download_gpci_file(year)
    if not gpci_file:
        console.print("[yellow]Warning: Could not download GPCI file.[/yellow]")
        console.print("GPCI data may be included in the RVU file or require manual download.")

    # Parse and import RVU data
    console.print("\n[yellow]Step 3/4:[/yellow] Importing RVU data...")
    clear_rvu_data(year)
    rvu_count = insert_rvu_records(parse_rvu_file(rvu_file, year))
    console.print(f"[green]Imported {rvu_count:,} RVU records[/green]")

    # Parse and import GPCI data
    console.print("\n[yellow]Step 4/4:[/yellow] Importing GPCI data...")
    clear_gpci_data(year)

    if gpci_file:
        gpci_count = insert_gpci_records(parse_gpci_file(gpci_file, year))
        console.print(f"[green]Imported {gpci_count:,} GPCI records from CMS file[/green]")
    else:
        # Use embedded GPCI data as fallback
        from cms_rates.data.gpci_data import get_embedded_gpci_records
        gpci_count = insert_gpci_records(get_embedded_gpci_records(year))
        console.print(f"[green]Imported {gpci_count:,} GPCI records (embedded data)[/green]")

    console.print(f"\n[bold green]Data update complete for {year}![/bold green]")


@main.command("list-localities")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option("--state", "-s", default=None, help="Filter by state abbreviation")
def list_localities(year: Optional[int], state: Optional[str]):
    """List all available CMS localities.

    Examples:

        cms-rates list-localities

        cms-rates list-localities --state CA
    """
    year = year or get_default_year()

    if not has_data(year):
        console.print(f"[red]No data available for {year}.[/red]")
        console.print(f"Run 'cms-rates update --year {year}' to download data.")
        sys.exit(1)

    mapper = RegionMapper(year)
    localities = mapper.list_all_localities()

    if state:
        localities = [loc for loc in localities if loc.state.upper() == state.upper()]

    if not localities:
        console.print(f"[yellow]No localities found{' for state ' + state if state else ''}.[/yellow]")
        return

    table = Table(title=f"CMS Localities ({year})")
    table.add_column("State", style="cyan")
    table.add_column("Carrier-Locality", style="green")
    table.add_column("Name")
    table.add_column("Work GPCI", justify="right")
    table.add_column("PE GPCI", justify="right")
    table.add_column("MP GPCI", justify="right")

    for loc in localities:
        table.add_row(
            loc.state,
            loc.carrier_locality,
            loc.locality_name,
            f"{loc.work_gpci:.3f}",
            f"{loc.pe_gpci:.3f}",
            f"{loc.mp_gpci:.3f}",
        )

    console.print(table)
    console.print(f"\nTotal: {len(localities)} localities")


@main.command()
@click.argument("cpt_code")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
def info(cpt_code: str, year: Optional[int]):
    """Show information about a CPT code without pricing.

    Examples:

        cms-rates info 99213

        cms-rates info G0438
    """
    year = year or get_default_year()

    from cms_rates.data.storage import get_rvu

    if not has_data(year):
        console.print(f"[red]No data available for {year}.[/red]")
        console.print(f"Run 'cms-rates update --year {year}' to download data.")
        sys.exit(1)

    rvu = get_rvu(cpt_code.upper(), year)
    if not rvu:
        console.print(f"[red]CPT code {cpt_code} not found in {year} fee schedule.[/red]")
        sys.exit(1)

    console.print(Panel(f"CPT Code Information - {rvu.hcpcs_code}", style="bold blue"))

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Code:", rvu.hcpcs_code)
    if rvu.modifier:
        table.add_row("Modifier:", rvu.modifier)
    table.add_row("Description:", rvu.description)
    table.add_row("Status:", rvu.status_code)
    table.add_row("Global Days:", rvu.global_days or "N/A")
    table.add_row("", "")
    table.add_row("Work RVU:", f"{rvu.work_rvu:.2f}")
    table.add_row("Non-Facility PE RVU:", f"{rvu.non_facility_pe_rvu:.2f}")
    table.add_row("Facility PE RVU:", f"{rvu.facility_pe_rvu:.2f}")
    table.add_row("Malpractice RVU:", f"{rvu.malpractice_rvu:.2f}")
    table.add_row("", "")
    table.add_row("Total Non-Facility RVU:", f"{rvu.total_non_facility_rvu:.2f}")
    table.add_row("Total Facility RVU:", f"{rvu.total_facility_rvu:.2f}")
    table.add_row("Conversion Factor:", f"${rvu.conversion_factor:.4f}")

    console.print(table)


@main.command()
@click.argument("query")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option("--limit", "-l", type=int, default=25, help="Maximum number of results")
@click.option(
    "--format", "-o", "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format"
)
def search(query: str, year: Optional[int], limit: int, output_format: str):
    """Search for CPT codes by description.

    QUERY: Keywords to search in CPT descriptions

    Examples:

        cms-rates search "office visit"

        cms-rates search "x-ray" --limit 50

        cms-rates search "MRI" --format json
    """
    year = year or get_default_year()

    from cms_rates.data.storage import search_by_description

    if not has_data(year):
        console.print(f"[red]No data available for {year}.[/red]")
        console.print(f"Run 'cms-rates update --year {year}' to download data.")
        sys.exit(1)

    results = search_by_description(query, year, limit=limit)

    if not results:
        console.print(f"[yellow]No CPT codes found matching '{query}'[/yellow]")
        return

    if output_format == "json":
        import json
        output = []
        for rvu in results:
            output.append({
                "code": rvu.hcpcs_code,
                "modifier": rvu.modifier,
                "description": rvu.description,
                "work_rvu": float(rvu.work_rvu),
                "non_facility_pe_rvu": float(rvu.non_facility_pe_rvu),
                "facility_pe_rvu": float(rvu.facility_pe_rvu),
                "malpractice_rvu": float(rvu.malpractice_rvu),
            })
        print(json.dumps(output, indent=2))

    elif output_format == "csv":
        print("code,modifier,description,work_rvu,non_fac_pe_rvu,fac_pe_rvu,mp_rvu")
        for rvu in results:
            desc = rvu.description.replace(",", ";")
            print(f"{rvu.hcpcs_code},{rvu.modifier or ''},{desc},{rvu.work_rvu:.2f},{rvu.non_facility_pe_rvu:.2f},{rvu.facility_pe_rvu:.2f},{rvu.malpractice_rvu:.2f}")

    else:
        table = Table(title=f"Search Results for '{query}' ({len(results)} found)")
        table.add_column("Code", style="cyan")
        table.add_column("Description")
        table.add_column("Work RVU", justify="right")
        table.add_column("Non-Fac PE", justify="right")
        table.add_column("Fac PE", justify="right")
        table.add_column("MP RVU", justify="right")

        for rvu in results:
            table.add_row(
                rvu.hcpcs_code,
                rvu.description[:50] + "..." if len(rvu.description) > 50 else rvu.description,
                f"{rvu.work_rvu:.2f}",
                f"{rvu.non_facility_pe_rvu:.2f}",
                f"{rvu.facility_pe_rvu:.2f}",
                f"{rvu.malpractice_rvu:.2f}",
            )

        console.print(table)


@main.command("add-payer-rate")
@click.argument("cpt_code")
@click.argument("payer_name")
@click.option("--rate", "-r", type=float, help="Non-facility reimbursement rate")
@click.option("--facility-rate", "-fr", type=float, help="Facility reimbursement rate")
@click.option("--percent-medicare", "-p", type=float, help="Rate as percentage of Medicare (e.g., 120 for 120%)")
@click.option("--state", "-s", help="State abbreviation (leave empty for national rate)")
@click.option("--type", "-t", "payer_type", type=click.Choice(["commercial", "medicaid", "other"]), default="commercial", help="Payer type")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option("--modifier", "-m", help="Modifier code")
@click.option("--source", help="Data source description")
def add_payer_rate(
    cpt_code: str,
    payer_name: str,
    rate: Optional[float],
    facility_rate: Optional[float],
    percent_medicare: Optional[float],
    state: Optional[str],
    payer_type: str,
    year: Optional[int],
    modifier: Optional[str],
    source: Optional[str],
):
    """Add a payer-specific reimbursement rate.

    CPT_CODE: The CPT or HCPCS code

    PAYER_NAME: Name of the insurance payer (e.g., "Blue Cross CA", "Medi-Cal")

    Examples:

        cms-rates add-payer-rate 99213 "Blue Cross CA" --rate 115.50 --state CA

        cms-rates add-payer-rate 99213 "Aetna" --percent-medicare 120 --type commercial

        cms-rates add-payer-rate 99213 "Medi-Cal" --rate 72.00 --state CA --type medicaid
    """
    from decimal import Decimal
    from cms_rates.models.payer import PayerRate

    year = year or get_default_year()

    if not rate and not facility_rate and not percent_medicare:
        console.print("[red]Error: Must specify --rate, --facility-rate, or --percent-medicare[/red]")
        sys.exit(1)

    init_database()

    payer_rate = PayerRate(
        hcpcs_code=cpt_code.upper(),
        payer_name=payer_name,
        payer_type=payer_type,
        year=year,
        modifier=modifier.upper() if modifier else None,
        state=state.upper() if state else None,
        non_facility_rate=Decimal(str(rate)) if rate else None,
        facility_rate=Decimal(str(facility_rate)) if facility_rate else None,
        percent_of_medicare=Decimal(str(percent_medicare)) if percent_medicare else None,
        source=source,
    )

    record_id = insert_payer_rate(payer_rate)
    console.print(f"[green]Added payer rate for {cpt_code} from {payer_name} (ID: {record_id})[/green]")

    # Show the added rate
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("CPT Code:", cpt_code.upper())
    table.add_row("Payer:", payer_name)
    table.add_row("Type:", payer_type)
    table.add_row("State:", state.upper() if state else "National")
    if rate:
        table.add_row("Non-Facility Rate:", f"${rate:.2f}")
    if facility_rate:
        table.add_row("Facility Rate:", f"${facility_rate:.2f}")
    if percent_medicare:
        table.add_row("% of Medicare:", f"{percent_medicare:.0f}%")
    table.add_row("Year:", str(year))

    console.print(table)


@main.command()
@click.argument("cpt_code")
@click.option("--region", "-r", required=True, help="State name, abbreviation, or locality code")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option("--facility", "-f", is_flag=True, help="Show facility rates (default: non-facility)")
@click.option("--modifier", "-m", help="Modifier code")
@click.option(
    "--format", "-o", "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format"
)
def compare(
    cpt_code: str,
    region: str,
    year: Optional[int],
    facility: bool,
    modifier: Optional[str],
    output_format: str,
):
    """Compare Medicare rates with other payers for a CPT code.

    CPT_CODE: The CPT or HCPCS code to compare

    Examples:

        cms-rates compare 99213 -r CA

        cms-rates compare 99213 -r California --facility

        cms-rates compare 99213 -r TX --format json
    """
    from decimal import Decimal

    year = year or get_default_year()

    if not has_data(year) and not has_payment_data(year):
        console.print(f"[red]No CMS data available for {year}.[/red]")
        console.print(f"Run 'cms-rates update --year {year}' or 'cms-rates import-payment-file' to load data.")
        sys.exit(1)

    # Get Medicare rate first
    lookup_service = RateLookup(year)
    try:
        medicare_results = lookup_service.lookup(
            cpt_code=cpt_code,
            region=region,
            facility=facility,
            modifier=modifier,
        )
    except (InvalidCPTCodeError, CPTCodeNotFoundError, InvalidRegionError, DataNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not medicare_results:
        console.print(f"[red]No Medicare rate found for {cpt_code} in {region}[/red]")
        sys.exit(1)

    medicare_result = medicare_results[0]
    medicare_rate = medicare_result.payment_amount

    # Get payer rates
    state = medicare_result.state
    payer_rates = get_payer_rates(cpt_code, year, state=state, modifier=modifier)

    # Build comparison data
    comparison_data = [{
        "payer": "Medicare (CMS)",
        "type": "government",
        "rate": float(medicare_rate),
        "percent_medicare": 100.0,
    }]

    for pr in payer_rates:
        rate = pr.calculate_rate_from_medicare(medicare_rate, facility)
        if rate is not None:
            pct = (float(rate) / float(medicare_rate)) * 100 if medicare_rate > 0 else 0
            comparison_data.append({
                "payer": pr.payer_name,
                "type": pr.payer_type,
                "rate": float(rate),
                "percent_medicare": pct,
            })

    if output_format == "json":
        output = {
            "cpt_code": cpt_code,
            "region": region,
            "state": state,
            "locality": medicare_result.locality_name,
            "year": year,
            "setting": "facility" if facility else "non_facility",
            "rates": comparison_data,
        }
        print(json.dumps(output, indent=2))

    elif output_format == "csv":
        print("payer,type,rate,percent_of_medicare")
        for item in comparison_data:
            print(f"{item['payer']},{item['type']},{item['rate']:.2f},{item['percent_medicare']:.1f}")

    else:
        setting = "Facility" if facility else "Non-Facility"
        console.print(Panel(
            f"Rate Comparison - CPT {cpt_code} ({setting})\n"
            f"Region: {medicare_result.locality_name} ({state})",
            style="bold blue"
        ))

        table = Table()
        table.add_column("Payer", style="cyan")
        table.add_column("Type")
        table.add_column("Rate", justify="right", style="green")
        table.add_column("% of Medicare", justify="right")

        for item in comparison_data:
            pct_style = ""
            if item["percent_medicare"] > 100:
                pct_style = "green"
            elif item["percent_medicare"] < 100:
                pct_style = "red"

            table.add_row(
                item["payer"],
                item["type"],
                f"${item['rate']:.2f}",
                f"[{pct_style}]{item['percent_medicare']:.1f}%[/{pct_style}]" if pct_style else f"{item['percent_medicare']:.1f}%",
            )

        console.print(table)

        if len(comparison_data) == 1:
            console.print("\n[yellow]No payer rates found for this code/region.[/yellow]")
            console.print("Use 'cms-rates add-payer-rate' to add payer rates.")


@main.command("list-payers")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option(
    "--format", "-o", "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format"
)
def list_payers(year: Optional[int], output_format: str):
    """List all payers with rates in the database.

    Examples:

        cms-rates list-payers

        cms-rates list-payers --year 2025

        cms-rates list-payers --format json
    """
    year_filter = year or get_default_year()

    payers = get_all_payers(year_filter)

    if not payers:
        console.print(f"[yellow]No payer rates found for {year_filter}.[/yellow]")
        console.print("Use 'cms-rates add-payer-rate' to add payer rates.")
        return

    if output_format == "json":
        print(json.dumps(payers, indent=2))
    else:
        table = Table(title=f"Payers in Database ({year_filter})")
        table.add_column("Payer Name", style="cyan")
        table.add_column("Type")
        table.add_column("State")
        table.add_column("# Rates", justify="right")

        for p in payers:
            table.add_row(
                p["payer_name"],
                p["payer_type"],
                p["state"] or "National",
                str(p["rate_count"]),
            )

        console.print(table)
        console.print(f"\nTotal: {len(payers)} payer entries")


@main.command("import-payer-rates")
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--payer", "-p", required=True, help="Payer name for imported rates")
@click.option("--type", "-t", "payer_type", type=click.Choice(["commercial", "medicaid", "other"]), default="medicaid", help="Payer type")
@click.option("--state", "-s", help="State for all imported rates (if not in CSV)")
@click.option("--year", "-y", type=int, default=None, help="Fee schedule year")
@click.option("--code-column", default="code", help="CSV column name for CPT code")
@click.option("--rate-column", default="rate", help="CSV column name for rate")
@click.option("--facility-column", help="CSV column name for facility rate")
@click.option("--source", help="Data source description")
@click.option("--dry-run", is_flag=True, help="Show what would be imported without importing")
def import_payer_rates(
    csv_file: str,
    payer: str,
    payer_type: str,
    state: Optional[str],
    year: Optional[int],
    code_column: str,
    rate_column: str,
    facility_column: Optional[str],
    source: Optional[str],
    dry_run: bool,
):
    """Import payer rates from a CSV file.

    CSV_FILE: Path to the CSV file to import

    The CSV should have at minimum a CPT code column and a rate column.
    Column names can be customized with options.

    Examples:

        cms-rates import-payer-rates medicaid_rates.csv --payer "Medi-Cal" --state CA

        cms-rates import-payer-rates rates.csv --payer "BCBS" --code-column "CPT" --rate-column "Amount"

        cms-rates import-payer-rates data.csv --payer "Aetna" --dry-run
    """
    import csv
    from decimal import Decimal, InvalidOperation
    from pathlib import Path
    from cms_rates.models.payer import PayerRate
    from cms_rates.data.storage import insert_payer_rates

    year = year or get_default_year()

    # Read CSV file
    csv_path = Path(csv_file)
    rates_to_import = []
    errors = []

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        # Check required columns exist
        if code_column not in reader.fieldnames:
            console.print(f"[red]Error: Column '{code_column}' not found in CSV[/red]")
            console.print(f"Available columns: {', '.join(reader.fieldnames)}")
            sys.exit(1)

        if rate_column not in reader.fieldnames:
            console.print(f"[red]Error: Column '{rate_column}' not found in CSV[/red]")
            console.print(f"Available columns: {', '.join(reader.fieldnames)}")
            sys.exit(1)

        for row_num, row in enumerate(reader, start=2):
            cpt_code = row.get(code_column, '').strip()
            rate_str = row.get(rate_column, '').strip()

            if not cpt_code:
                continue

            # Parse rate
            try:
                # Remove currency symbols and commas
                rate_str = rate_str.replace('$', '').replace(',', '')
                non_facility_rate = Decimal(rate_str) if rate_str else None
            except InvalidOperation:
                errors.append(f"Row {row_num}: Invalid rate '{rate_str}' for {cpt_code}")
                continue

            # Parse facility rate if column specified
            facility_rate = None
            if facility_column and facility_column in row:
                fac_str = row.get(facility_column, '').strip()
                try:
                    fac_str = fac_str.replace('$', '').replace(',', '')
                    facility_rate = Decimal(fac_str) if fac_str else None
                except InvalidOperation:
                    pass  # Ignore facility rate errors

            # Get state from row or default
            row_state = row.get('state', '').strip() or state

            rate = PayerRate(
                hcpcs_code=cpt_code.upper(),
                payer_name=payer,
                payer_type=payer_type,
                year=year,
                state=row_state.upper() if row_state else None,
                non_facility_rate=non_facility_rate,
                facility_rate=facility_rate,
                source=source or f"Imported from {csv_path.name}",
            )
            rates_to_import.append(rate)

    if errors:
        console.print(f"[yellow]Warnings during parsing:[/yellow]")
        for err in errors[:10]:  # Show first 10 errors
            console.print(f"  {err}")
        if len(errors) > 10:
            console.print(f"  ... and {len(errors) - 10} more")
        console.print()

    if not rates_to_import:
        console.print("[red]No valid rates found in CSV file[/red]")
        sys.exit(1)

    console.print(f"Found {len(rates_to_import)} rates to import for '{payer}'")

    if dry_run:
        console.print("\n[yellow]Dry run - showing first 10 rates:[/yellow]")
        table = Table()
        table.add_column("CPT", style="cyan")
        table.add_column("State")
        table.add_column("Non-Fac Rate", justify="right")
        table.add_column("Fac Rate", justify="right")

        for rate in rates_to_import[:10]:
            table.add_row(
                rate.hcpcs_code,
                rate.state or "N/A",
                f"${rate.non_facility_rate:.2f}" if rate.non_facility_rate else "-",
                f"${rate.facility_rate:.2f}" if rate.facility_rate else "-",
            )

        console.print(table)
        if len(rates_to_import) > 10:
            console.print(f"\n... and {len(rates_to_import) - 10} more")
        return

    # Import rates
    init_database()
    count = insert_payer_rates(iter(rates_to_import))
    console.print(f"[green]Successfully imported {count} rates for '{payer}'[/green]")


@main.command("import-payment-file")
@click.argument("payment_file", type=click.Path(exists=True))
@click.option("--year", "-y", type=int, default=2026, help="Fee schedule year")
@click.option("--clear", "-c", is_flag=True, help="Clear existing payment data before import")
def import_payment_file(
    payment_file: str,
    year: int,
    clear: bool,
):
    """Import CMS Payment Amount File (PFALL26A format).

    PAYMENT_FILE: Path to the CMS payment file (e.g., PFALL26AR.txt)

    This imports pre-calculated payment amounts by carrier/locality from the
    CMS Physician Fee Schedule Payment Amount File.

    Examples:

        cms-rates import-payment-file PFALL26AR.txt

        cms-rates import-payment-file PFALL26AR.txt --year 2026 --clear
    """
    from pathlib import Path
    from cms_rates.data.payment_parser import parse_payment_file, get_unique_localities
    from cms_rates.models.payment import get_carrier_locality_info

    file_path = Path(payment_file)

    console.print(f"[cyan]Importing CMS Payment Amount File for {year}...[/cyan]")
    ensure_data_dirs()
    init_database()

    # Build locality lookup
    console.print("[yellow]Step 1/3:[/yellow] Analyzing localities...")
    localities = get_unique_localities(file_path)
    console.print(f"  Found {len(localities)} unique carrier/locality combinations")

    # Build state lookup from carrier/locality mappings
    state_lookup = {}
    for key, (state, name) in localities.items():
        state_lookup[key] = (state, name)

    # Also use the built-in mapping for better coverage
    for key in localities:
        carrier, locality = key.split("-")
        state, name = get_carrier_locality_info(carrier, locality)
        if state != "XX":  # Override with built-in mapping if available
            state_lookup[key] = (state, name)

    if clear:
        console.print("\n[yellow]Step 2/3:[/yellow] Clearing existing data...")
        clear_payment_amounts(year)
        console.print(f"  Cleared payment data for {year}")
    else:
        console.print("\n[yellow]Step 2/3:[/yellow] Keeping existing data...")

    console.print("\n[yellow]Step 3/3:[/yellow] Importing payment records...")
    console.print("  This may take a few minutes for large files...")

    count = insert_payment_records(parse_payment_file(file_path), state_lookup)

    console.print(f"\n[bold green]Successfully imported {count:,} payment records![/bold green]")
    console.print(f"  Year: {year}")
    console.print(f"  Localities: {len(localities)}")


@main.command("delete-payer")
@click.argument("payer_name")
@click.option("--year", "-y", type=int, help="Only delete rates for specific year")
@click.option("--state", "-s", help="Only delete rates for specific state")
@click.option("--confirm", "-c", is_flag=True, help="Skip confirmation prompt")
def delete_payer(
    payer_name: str,
    year: Optional[int],
    state: Optional[str],
    confirm: bool,
):
    """Delete payer rates from the database.

    PAYER_NAME: Name of the payer to delete rates for

    Examples:

        cms-rates delete-payer "Blue Cross CA"

        cms-rates delete-payer "Medi-Cal" --state CA

        cms-rates delete-payer "Old Payer" --confirm
    """
    if not confirm:
        msg = f"Delete all rates for '{payer_name}'"
        if year:
            msg += f" (year {year})"
        if state:
            msg += f" (state {state})"
        msg += "?"

        if not click.confirm(msg):
            console.print("[yellow]Cancelled.[/yellow]")
            return

    count = delete_payer_rates(payer_name, year=year, state=state)

    if count > 0:
        console.print(f"[green]Deleted {count} rate(s) for '{payer_name}'[/green]")
    else:
        console.print(f"[yellow]No rates found for '{payer_name}'[/yellow]")


if __name__ == "__main__":
    main()
