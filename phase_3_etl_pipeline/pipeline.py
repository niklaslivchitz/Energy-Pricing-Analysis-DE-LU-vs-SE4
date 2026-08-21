"""
Phase 3: formalize Phases 1-2 into a proper fetch -> transform -> load
pipeline writing into SQLite, with the logging/retry/idempotency helpers
from common/pipeline_utils.py.

This is the "halfway point" per the brief's build order - once this runs
cleanly for all five zones (DE-LU + SE1-SE4), Phases 4-5 read from
db/energy.db instead of re-fetching from the API each time.

Run: python phase_3_etl_pipeline/pipeline.py
"""
import sqlite3
import uuid
from pathlib import Path

import pandas as pd

from common.entsoe_client import get_client, ZONE_DE, ZONES_SE
from common.pipeline_utils import fetch_with_retry, upsert_dataframe, log_pipeline_run, logger

DB_PATH = str(Path(__file__).resolve().parents[1] / "db" / "energy.db")
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def fetch_and_load_prices(client, zone, start, end, run_id):
    try:
        prices = fetch_with_retry(client.query_day_ahead_prices, zone, start=start, end=end)
        df = pd.DataFrame({
            "zone": zone,
            "timestamp": prices.index.astype(str),
            "price_eur_mwh": prices.values,
        })
        upsert_dataframe(df, "prices", ["zone", "timestamp"], DB_PATH)
        log_pipeline_run(DB_PATH, run_id, zone, "prices", len(df), "success")
    except Exception as e:
        log_pipeline_run(DB_PATH, run_id, zone, "prices", 0, "failed", str(e))
        logger.error(f"Skipping {zone} prices after retries exhausted: {e}")


# TODO: fetch_and_load_generation() and fetch_and_load_flows(), same pattern -
# fetch_with_retry -> reshape to long format -> upsert_dataframe -> log_pipeline_run.
# See phase_1/phase_2 scripts for the raw entsoe-py calls to reshape from.


def run_pipeline(start, end):
    init_db()
    client = get_client()
    run_id = str(uuid.uuid4())
    for zone in [ZONE_DE] + ZONES_SE:
        logger.info(f"Processing zone: {zone}")
        fetch_and_load_prices(client, zone, start, end, run_id)
    logger.info("Pipeline run complete.")


if __name__ == "__main__":
    run_pipeline(
        start=pd.Timestamp("2024-01-01", tz="Europe/Berlin"),
        end=pd.Timestamp("2024-01-08", tz="Europe/Berlin"),
    )
