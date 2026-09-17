"""
Shared logging, retry, and idempotent-upsert helpers for Phase 3 onward.

Phases 1-2 fetch manually and don't need this - it's deliberately introduced
at Phase 3 ("formalize into a pipeline") per the brief's build order, not
before, so the early exploration stays simple.

Adapted from a draft pipeline script, with one fix: the original used
`df.to_sql(..., if_exists='append')` against tables with a composite primary
key, which raises an IntegrityError on any overlapping re-run rather than
upserting. `upsert_dataframe()` below uses `INSERT OR REPLACE` instead, so
re-running the pipeline over a date range you've already fetched is safe.
"""
import logging
import sqlite3
import time

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def fetch_with_retry(fetch_func, *args, max_retries=3, retry_delay=5, **kwargs):
    """Generic retry wrapper for ENTSO-E API calls with backoff."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}: {fetch_func.__name__}")
            result = fetch_func(*args, **kwargs)
            logger.info(f"Fetched {len(result)} records")
            return result
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (attempt + 1)
                logger.info(f"Waiting {sleep_time}s before retry...")
                time.sleep(sleep_time)
            else:
                logger.error(f"All {max_retries} attempts failed for {fetch_func.__name__}")
                raise


def upsert_dataframe(df: pd.DataFrame, table_name: str, key_cols: list[str], db_path: str):
    """
    Idempotent upsert: INSERT OR REPLACE keyed on key_cols (must match the
    table's PRIMARY KEY in db/schema.sql). Safe to re-run over already-fetched
    date ranges - rows get overwritten, not duplicated or rejected.
    """
    if df.empty:
        logger.warning(f"Empty DataFrame for {table_name}, skipping upsert")
        return

    conn = sqlite3.connect(db_path)
    try:
        cols = list(df.columns)
        placeholders = ", ".join(["?"] * len(cols))
        col_list = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO {table_name} ({col_list}) VALUES ({placeholders})"
        conn.executemany(sql, df[cols].itertuples(index=False, name=None))
        conn.commit()
        logger.info(f"Upserted {len(df)} records into {table_name}")
    except Exception as e:
        logger.error(f"Failed to upsert into {table_name}: {e}")
        raise
    finally:
        conn.close()


def log_pipeline_run(db_path: str, run_id: str, zone: str, table_name: str,
                      records_processed: int, status: str, error_message: str = ""):
    """Write one row to pipeline_logs - lets you audit past runs from SQL directly."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO pipeline_logs (run_id, timestamp, zone, table_name, "
            "records_processed, status, error_message) VALUES (?, datetime('now'), ?, ?, ?, ?, ?)",
            (run_id, zone, table_name, records_processed, status, error_message),
        )
        conn.commit()
    finally:
        conn.close()
