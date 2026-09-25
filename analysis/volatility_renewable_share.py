import sqlite3
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf

DB_PATH = str(Path(__file__).resolve().parents[1] / "db" / "energy.db")

# TODO: pd.read_sql("SELECT * FROM prices", conn) and ("SELECT * FROM generation", conn),
# compute the two derived series, join into one DataFrame with a `country` column
# (DE_LU -> Germany, SE_* -> Sweden), then run the regression.
