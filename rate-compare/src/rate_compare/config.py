"""Configuration settings for Rate Compare."""

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Get the data directory for database and downloads."""
    if env_dir := os.environ.get("RATE_COMPARE_DATA_DIR"):
        return Path(env_dir)
    return Path.home() / ".rate-compare"


def get_db_path() -> Path:
    """Get the path to the SQLite database."""
    return get_data_dir() / "rate_compare.db"


def ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    get_data_dir().mkdir(parents=True, exist_ok=True)


# Default year for Medicare data
DEFAULT_YEAR = 2026

# State abbreviations
STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "PR",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "VI", "WA",
    "WV", "WI", "WY", "GU"
]
