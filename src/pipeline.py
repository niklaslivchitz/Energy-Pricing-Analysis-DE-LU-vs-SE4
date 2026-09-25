"""
This is the ETL pipeline script for fetching and loading energy data into a SQLite database.
A bunch of supporting functions are defined in pipeline_utils.py, which is imported here.
Run from repo root: python -m src.pipeline
"""
from pathlib import Path

import pandas as pd

from src.entsoe_client import get_client, PRICE_ZONES, GENERATION_ZONES, FLOW_PAIRS
from src.pipeline_utils import fetch_with_retry, upsert_dataframe, get_engine, to_utc_str


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
EARLIEST_START = pd.Timestamp("2025-12-02", tz="Europe/Berlin") # First date ENTSO-E has 15-minute data for every series we pull (SE_4 generation switched last).


def init_db(engine):
    conn = engine.raw_connection()
    try:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            conn.executescript(f.read())
    finally:
        conn.close()

#For all the fetch_and_load functions, we will use the fetch_with_retry() function to handle retries. We find it in pipeline_utils.

def fetch_and_load_prices(client, engine, zone, start, end):
    """Fetch day-ahead prices for a given zone and load them into the database."""
    prices = fetch_with_retry(client.query_day_ahead_prices, zone, start=start, end=end)
    df = pd.DataFrame({
        "zone": zone,
        "timestamp": to_utc_str(prices.index),
        "price_eur_mwh": prices.values,
    })
    upsert_dataframe(df, "prices", ["zone", "timestamp"], engine)


def to_long(gen_df, zone):
    """This is a function that takes a generation dataframe and a zone name, and reshapes it into long format with the right column names for the database."""
    long = (
        gen_df.rename_axis("timestamp")
        .reset_index()
        .melt(id_vars="timestamp", var_name="production_type", value_name="value_mw")
    )
    long["zone"] = zone
    long["timestamp"] = to_utc_str(long["timestamp"])
    return long[["zone", "timestamp", "production_type", "value_mw"]]


def fetch_and_load_generation(client, engine, zone, start, end):
    """Fetch generation data for a given zone and load them into the database."""
    gen = fetch_with_retry(client.query_generation, zone, start=start, end=end, nett=True)
    df = to_long(gen, zone)
    upsert_dataframe(df, "generation", ["zone", "timestamp", "production_type"], engine)


def fetch_and_load_flows(client, engine, zone_from, zone_to, start, end):
    """Fetch cross-border flow data for a given pair of zones and load them into the database."""
    flows = fetch_with_retry(client.query_crossborder_flows, zone_from, zone_to, start=start, end=end)
    df = pd.DataFrame({
        "zone_from": zone_from,
        "zone_to": zone_to,
        "timestamp": to_utc_str(flows.index),
        "flow_mw": flows.values,
    })
    upsert_dataframe(df, "cross_border_flows", ["zone_from", "zone_to", "timestamp"], engine)


def run_pipeline(start, end):
    engine = get_engine()
    init_db(engine)
    client = get_client()
    for zone in PRICE_ZONES:
        print(f"Processing prices for zone: {zone}")
        fetch_and_load_prices(client, engine, zone, start, end)
    for zone in GENERATION_ZONES:
        print(f"Processing generation for zone: {zone}")
        fetch_and_load_generation(client, engine, zone, start, end)
    for zone_from, zone_to in FLOW_PAIRS:
        print(f"Processing flows for: {zone_from} -> {zone_to}")
        fetch_and_load_flows(client, engine, zone_from, zone_to, start, end)
    print("Pipeline run complete.")


if __name__ == "__main__":
    end = pd.Timestamp.now(tz="Europe/Berlin").normalize() #We pull data up to midnight today in Berlin time.
    start = max(end - pd.Timedelta(days=365), EARLIEST_START)  # Fetch data for the last year, but not before the earliest start date.
    print(f"Pulling {start} to {end}")
    run_pipeline(start, end)