"""Database module."""

from rate_compare.db.database import get_connection, init_db
from rate_compare.db.schema import create_tables

__all__ = ["get_connection", "init_db", "create_tables"]
