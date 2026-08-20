"""
Phase 3, Load — write normalized DataFrames into the shared SQLite database.

Run schema.sql once (or call ensure_schema()) before the first load.
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent.parent / "data" / "energy.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


def ensure_schema(db_path: Path = DB_PATH):
    """Create the energy_data table if it doesn't exist yet."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def load(df: pd.DataFrame, db_path: Path = DB_PATH):
    """
    Append a normalized DataFrame to energy_data.
    Uses INSERT OR IGNORE against the UNIQUE constraint so re-running a fetch is safe
    (won't duplicate rows for a timestamp/country/metric/source you already have).
    """
    ensure_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        # TODO: pandas to_sql doesn't support "OR IGNORE" directly - either use
        # df.to_sql(..., if_exists="append") and dedupe after, or write rows manually
        # with executemany + "INSERT OR IGNORE INTO energy_data (...) VALUES (...)"
        raise NotImplementedError


if __name__ == "__main__":
    ensure_schema()
    print(f"Schema ready at {DB_PATH}")
