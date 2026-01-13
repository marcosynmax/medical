"""CMS data file downloader."""

import zipfile
from pathlib import Path
from typing import Optional

import httpx
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

from cms_rates.config import get_downloads_dir, ensure_data_dirs


# CMS PFS RVU file URLs (these are the actual download locations)
# Note: CMS updates these quarterly - URLs follow pattern PPRRVU{YY}{Q}.zip
# where YY is 2-digit year and Q is quarter (A=Q1, B=Q2, C=Q3, D=Q4)
CMS_RVU_URL_TEMPLATE = (
    "https://www.cms.gov/files/zip/rvu{year}{quarter}.zip"
)

# GPCI files are typically in the same location
CMS_GPCI_URL_TEMPLATE = (
    "https://www.cms.gov/files/zip/cy{year}-gpci-file.zip"
)


def download_file(url: str, dest_path: Path, show_progress: bool = True) -> bool:
    """Download a file from URL to destination path.

    Args:
        url: URL to download from
        dest_path: Destination file path
        show_progress: Whether to show download progress

    Returns:
        True if download successful, False otherwise
    """
    ensure_data_dirs()

    try:
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))

                if show_progress and total > 0:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        DownloadColumn(),
                    ) as progress:
                        task = progress.add_task(f"Downloading {dest_path.name}", total=total)
                        with open(dest_path, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=8192):
                                f.write(chunk)
                                progress.update(task, advance=len(chunk))
                else:
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
        return True
    except httpx.HTTPError as e:
        print(f"Error downloading {url}: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Optional[Path] = None) -> list[Path]:
    """Extract a ZIP file and return list of extracted files.

    Args:
        zip_path: Path to ZIP file
        extract_to: Directory to extract to (default: same as zip file)

    Returns:
        List of extracted file paths
    """
    if extract_to is None:
        extract_to = zip_path.parent

    extracted_files = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            zf.extract(name, extract_to)
            extracted_files.append(extract_to / name)

    return extracted_files


def download_rvu_file(year: int, quarter: str = "a") -> Optional[Path]:
    """Download RVU file for a specific year and quarter.

    Args:
        year: 4-digit year (e.g., 2025)
        quarter: Quarter letter (a, b, c, or d)

    Returns:
        Path to downloaded/extracted CSV file, or None if failed
    """
    year_2digit = str(year)[-2:]
    url = CMS_RVU_URL_TEMPLATE.format(year=year_2digit, quarter=quarter.lower())

    downloads_dir = get_downloads_dir()
    zip_path = downloads_dir / f"rvu{year_2digit}{quarter.lower()}.zip"

    print(f"Downloading RVU file for {year} Q{quarter.upper()}...")
    if not download_file(url, zip_path):
        # Try alternative URL patterns
        alt_url = f"https://www.cms.gov/files/zip/rvu{year_2digit}.zip"
        if not download_file(alt_url, zip_path):
            return None

    print("Extracting files...")
    extracted = extract_zip(zip_path)

    # Find the CSV file (usually PPRRVU{YY}.csv or similar)
    for f in extracted:
        if f.suffix.lower() == ".csv" and "rvu" in f.name.lower():
            return f
        if f.suffix.lower() == ".txt" and "rvu" in f.name.lower():
            return f

    # Return first CSV if no specific match
    for f in extracted:
        if f.suffix.lower() in (".csv", ".txt"):
            return f

    return None


def download_gpci_file(year: int) -> Optional[Path]:
    """Download GPCI file for a specific year.

    Args:
        year: 4-digit year (e.g., 2025)

    Returns:
        Path to downloaded/extracted CSV file, or None if failed
    """
    url = CMS_GPCI_URL_TEMPLATE.format(year=year)

    downloads_dir = get_downloads_dir()
    zip_path = downloads_dir / f"gpci{year}.zip"

    print(f"Downloading GPCI file for {year}...")
    if not download_file(url, zip_path):
        return None

    print("Extracting files...")
    extracted = extract_zip(zip_path)

    # Find the CSV file
    for f in extracted:
        if f.suffix.lower() == ".csv" and "gpci" in f.name.lower():
            return f

    # Return first CSV if no specific match
    for f in extracted:
        if f.suffix.lower() in (".csv", ".txt"):
            return f

    return None
