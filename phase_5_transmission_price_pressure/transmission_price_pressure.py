"""
Phase 5 - Core analysis 2: DE-SE4 transmission price pressure via the
Baltic Cable. See docs/project-brief.md Section 5.

Reads from db/energy.db (populated by Phase 3) - no API calls here.

price_spread = price_SE4 - price_DE_LU
flow_utilization = abs(flow_mw) / BALTIC_CABLE_CAPACITY_MW (600 MW)

Compare price_spread distribution when flow_utilization is near 1 (congested)
vs. well below (uncongested).
"""
import sqlite3
from pathlib import Path

import pandas as pd

from common.entsoe_client import BALTIC_CABLE_CAPACITY_MW

DB_PATH = str(Path(__file__).resolve().parents[1] / "db" / "energy.db")

# TODO: pd.read_sql prices for DE_LU and SE_4 + cross_border_flows (see sql/queries.sql
# for the join pattern), align on timestamp, compute spread and utilization, bucket/compare.
