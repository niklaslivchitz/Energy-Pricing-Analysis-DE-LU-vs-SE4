import sqlite3
from pathlib import Path

import pandas as pd

from src.entsoe_client import BALTIC_CABLE_CAPACITY_MW

DB_PATH = str(Path(__file__).resolve().parents[1] / "db" / "energy.db")

# TODO: pd.read_sql prices for DE_LU and SE_4 + cross_border_flows, align on timestamp,
# compute spread and utilization, bucket/compare.
