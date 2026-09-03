"""
Phase 2 (rescoped): fetch the same sample period used in Phase 1 and cache it
to disk, so quality-checking / first-analysis work doesn't re-hit the
ENTSO-E API every time this reruns.

Shapes each dataset to match db/schema.sql's long/tidy tables (prices,
generation, cross_border_flows) - see README's "Design note: long-format
generation table" for why. Phase 3's pipeline can later load these same
CSVs straight into SQLite without re-deriving the reshape.

Run: python phase_2_quality_and_first_analysis/fetch_and_cache.py
Re-fetch even if cached: python phase_2_quality_and_first_analysis/fetch_and_cache.py --force
"""
import sys
from pathlib import Path

import pandas as pd

from common.entsoe_client import get_client

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

# Same week used in phase_1_exploration/01_entsoe_exploration.ipynb
START = pd.Timestamp("2026-01-01", tz="Europe/Berlin")
END = pd.Timestamp("2026-01-08", tz="Europe/Berlin")

PRICE_ZONES = ["DE_LU", "SE_4", "SE_1"]
GENERATION_ZONES = ["DE_LU", "SE_4"]
FLOW_PAIRS = [("DE_LU", "SE_4"), ("SE_4", "DE_LU")]


def fetch_prices(client):
    frames = []
    for zone in PRICE_ZONES:
        prices = client.query_day_ahead_prices(zone, start=START, end=END)
        frames.append(pd.DataFrame({
            "zone": zone,
            "timestamp": prices.index.astype(str),
            "price_eur_mwh": prices.values,
        }))
    return pd.concat(frames, ignore_index=True)


def fetch_generation(client):
    frames = []
    for zone in GENERATION_ZONES:
        gen = client.query_generation(zone, start=START, end=END, nett=True)
        long = (
            gen.rename_axis("timestamp")
            .reset_index()
            .melt(id_vars="timestamp", var_name="production_type", value_name="value_mw")
        )
        long["zone"] = zone
        long["production_type"] = long["production_type"].str.lower().str.replace(" ", "_")
        long["timestamp"] = long["timestamp"].astype(str)
        frames.append(long[["zone", "timestamp", "production_type", "value_mw"]])
    return pd.concat(frames, ignore_index=True)


def fetch_flows(client):
    frames = []
    for zone_from, zone_to in FLOW_PAIRS:
        flow = client.query_crossborder_flows(zone_from, zone_to, start=START, end=END)
        frames.append(pd.DataFrame({
            "zone_from": zone_from,
            "zone_to": zone_to,
            "timestamp": flow.index.astype(str),
            "flow_mw": flow.values,
        }))
    return pd.concat(frames, ignore_index=True)


TARGETS = {
    "prices.csv": fetch_prices,
    "generation_long.csv": fetch_generation,
    "flows_long.csv": fetch_flows,
}


def main(force=False):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = get_client()

    for filename, fetch_fn in TARGETS.items():
        path = OUT_DIR / filename
        if path.exists() and not force:
            print(f"{filename} already cached, skipping (use --force to re-fetch)")
            continue
        df = fetch_fn(client)
        df.to_csv(path, index=False)
        print(f"Wrote {len(df)} rows to {path}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
