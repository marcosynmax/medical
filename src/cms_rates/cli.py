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


if __name__ == "__main__":
    main()
