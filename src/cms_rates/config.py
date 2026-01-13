"""Configuration management for CMS Rates."""

import os
from pathlib import Path
from datetime import datetime


def get_data_dir() -> Path:
    """Get the data directory for CMS files and database."""
    if env_dir := os.environ.get("CMS_RATES_DATA_DIR"):
        return Path(env_dir)
    return Path.home() / ".cms-rates"


def get_db_path() -> Path:
    """Get the path to the SQLite database."""
    return get_data_dir() / "cms_rates.db"


def get_downloads_dir() -> Path:
    """Get the directory for downloaded CMS files."""
    return get_data_dir() / "downloads"


def ensure_data_dirs() -> None:
    """Create data directories if they don't exist."""
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_downloads_dir().mkdir(parents=True, exist_ok=True)


def get_current_year() -> int:
    """Get the current year for default fee schedule."""
    return datetime.now().year


def get_default_year() -> int:
    """Get the default year, can be overridden by environment variable."""
    if env_year := os.environ.get("CMS_RATES_DEFAULT_YEAR"):
        return int(env_year)
    # Default to 2026 (latest available data)
    return 2026


# CMS data source URLs
CMS_BASE_URL = "https://www.cms.gov/medicare/payment/fee-schedules/physician"
CMS_RVU_FILES_URL = f"{CMS_BASE_URL}/pfs-relative-value-files"

# Conversion factor for 2025 (updated annually by CMS)
CONVERSION_FACTORS = {
    2024: 32.7442,
    2025: 32.3465,
    2026: 32.3465,  # Placeholder, update when announced
}


def get_conversion_factor(year: int) -> float:
    """Get the conversion factor for a given year."""
    return CONVERSION_FACTORS.get(year, CONVERSION_FACTORS[2025])
