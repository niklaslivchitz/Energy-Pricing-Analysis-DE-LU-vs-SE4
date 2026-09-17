"""
Phase 4 - Core analysis 1: volatility vs. variable renewable (wind+solar) share.
See docs/project-brief.md Section 4.

Reads from db/energy.db (populated by Phase 3) - no API calls here.

variable_renewable_share = (wind + solar) / total_generation, per zone/hour
volatility = rolling std of price_eur_mwh (24h window), per zone

Regression: statsmodels.ols("volatility ~ variable_renewable_share + C(country)")
"""
import sqlite3
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf

DB_PATH = str(Path(__file__).resolve().parents[1] / "db" / "energy.db")

# TODO: pd.read_sql("SELECT * FROM prices", conn) and ("SELECT * FROM generation", conn),
# compute the two derived series, join into one DataFrame with a `country` column
# (DE_LU -> Germany, SE_* -> Sweden), then run the regression.
