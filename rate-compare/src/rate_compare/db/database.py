"""SQLite database connection management."""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from rate_compare.config import get_db_path, ensure_data_dir
from rate_compare.db.schema import create_tables


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection context manager."""
    ensure_data_dir()
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database with schema."""
    ensure_data_dir()
    with get_connection() as conn:
        create_tables(conn)
