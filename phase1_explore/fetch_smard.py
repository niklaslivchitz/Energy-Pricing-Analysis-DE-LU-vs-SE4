"""
Phase 1, Step B — pull ONE series from SMARD (Bundesnetzagentur) and get it into pandas.

Goal for this file: prove the mechanics work end to end. Not analysis yet.

Background (see PROJECT_PLAN.md for more):
- No API key needed - plain GET requests.
- URL shape: smard.de/app/chart_data/{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json
- The `{filter}` numeric codes are NOT self-explanatory (they don't map obviously to
  "day-ahead price" etc). Use the community-documented reference instead of guessing:
    - https://smard.api.bund.dev
    - https://github.com/bundesAPI/smard-api
  Find the filter code for "Day-ahead prices, DE/LU" there before writing this.
- SMARD's chart_data endpoint is a two-step fetch:
    1. Fetch the "index" file for a filter/region/resolution to get available timestamps
    2. Fetch the actual data file for the timestamp(s) you want

Suggested first series: Day-ahead price, DE/LU bidding zone, hourly resolution.
"""

import requests
import pandas as pd

SMARD_BASE_URL = "https://www.smard.de/app/chart_data"

# TODO: look up the real filter code for "day-ahead price, DE/LU" via smard.api.bund.dev
DAY_AHEAD_PRICE_FILTER = None  # e.g. 4169 - CONFIRM, don't guess
REGION = "DE-LU"
RESOLUTION = "hour"


def fetch_available_timestamps(filter_code: int, region: str = REGION, resolution: str = RESOLUTION) -> list:
    """
    Step 1: fetch the index of available data timestamps for a given filter/region/resolution.
    URL shape: {SMARD_BASE_URL}/{filter}/{region}/index_{resolution}.json
    """
    # TODO
    raise NotImplementedError


def fetch_series(filter_code: int, timestamp: int, region: str = REGION, resolution: str = RESOLUTION) -> dict:
    """
    Step 2: fetch the actual data for one timestamp chunk.
    URL shape: {SMARD_BASE_URL}/{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json
    Returns raw JSON: typically {"series": [[unix_ms, value], ...]}.
    """
    # TODO
    raise NotImplementedError


def series_to_dataframe(raw_json: dict) -> pd.DataFrame:
    """Convert SMARD's [[unix_ms, value], ...] series into a tidy DataFrame with a real datetime."""
    # TODO: pd.to_datetime(..., unit="ms") on the first column
    raise NotImplementedError


if __name__ == "__main__":
    # TODO: once the filter code is confirmed and the three functions above work, this should
    # end with something like:
    #   timestamps = fetch_available_timestamps(DAY_AHEAD_PRICE_FILTER)
    #   df = series_to_dataframe(fetch_series(DAY_AHEAD_PRICE_FILTER, timestamps[-1]))
    #   print(df.head())
    #   df.to_csv("../data/smard_sample.csv", index=False)
    pass
