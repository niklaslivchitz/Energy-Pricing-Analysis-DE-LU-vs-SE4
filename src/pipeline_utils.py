"""
Shared, project-agnostic helpers for the ETL pipeline and the analysis scripts:
database engine, API retry, idempotent upsert, and timestamp massage.
"""
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine # pyright: ignore[reportCallIssue]

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = REPO_ROOT / "db" / "energy.db"


def get_engine(db_path: Path = DEFAULT_DB_PATH) -> Engine:
    """SQLAlchemy engine for the SQLite file."""
    return create_engine(f"sqlite:///{db_path}")


def to_utc_str(timestamps) -> pd.Index:
    """
    Timestamps should be in UTC, lets make it happen.
    Input must be timezone-aware (entsoe-py's always is) - tz_convert raises on naive timestamps.
    """
    return pd.DatetimeIndex(timestamps).tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S+00:00")


def fetch_with_retry(fetch_func, *args, max_retries=3, retry_delay=5,
                     no_retry=(), **kwargs):
    """
    Retry wrapper.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return fetch_func(*args, **kwargs)
        except no_retry:
            raise
        except Exception as e:
            print(f"Attempt {attempt}/{max_retries} of {fetch_func.__name__} failed: {e}")
            if attempt == max_retries:
                raise
            time.sleep(retry_delay * attempt)


def upsert_dataframe(df: pd.DataFrame, table_name: str, key_cols: list[str], engine: Engine):
    """
    Idempotent upsert, i.e. update or insert. Re-running over an already-loaded range updates rows.
    """

    cols = list(df.columns)
    value_cols = [c for c in cols if c not in key_cols]

    #and below the actual SQL statement that does the upsert. We later pass it to conn.execute().
    sql = text(
        f"INSERT INTO {table_name} ({', '.join(cols)}) "
        f"VALUES ({', '.join(':' + c for c in cols)}) "
        f"ON CONFLICT ({', '.join(key_cols)}) DO UPDATE SET "
        + ", ".join(f"{c} = excluded.{c}" for c in value_cols)
    )

    #Here NaNs gets rewritten to None so that we can insert them into the database as NULLs.
    records = df.astype(object).where(df.notna(), None).to_dict("records")

    with engine.begin() as conn:
        conn.execute(sql, records) # pyright: ignore
    print(f"Upserted {len(df)} rows into {table_name}")