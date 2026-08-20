"""
Phase 1, Step A — pull ONE table from SCB (Statistiska Centralbyrån) and get it into pandas.

Goal for this file: prove the mechanics work end to end. Not analysis yet.

Background (see PROJECT_PLAN.md for more):
- Use PxWebApi v2 (the v1 endpoint sunsets end of 2026 — don't build against it).
- No API key needed.
- Response format is JSON-stat: a nested structure with `dimension` (what each axis of the
  data means, e.g. region/year/category) and `value` (a flat array of numbers you have to
  reconstruct against the dimensions). This shape is the main learning curve here, not the
  HTTP call itself.

Suggested first table: something under Energipriser (energy prices) - e.g. household
electricity price by year. Pick ONE narrow table first; you can always widen it later.

Docs to check when you get here:
- https://www.scb.se/en/services/open-data-api/api-for-the-statistical-database/
  (has the v2 base URL and a table-browsing UI to find table IDs)
"""

import requests
import pandas as pd

# TODO: replace with the real v2 base URL + table path once you've found your table via
# SCB's table browser (the table ID goes in the path, e.g. .../TAB/EN0110/EN0110A/...)
SCB_V2_BASE_URL = "https://api.scb.se/OV0104/v2beta1/api/v2"  # confirm exact base against docs


def fetch_table(table_path: str, query: dict) -> dict:
    """
    Fetch a single table from SCB PxWebApi v2.

    Args:
        table_path: the table's path/id within the SCB catalog (found via their table browser)
        query: the PxWebApi v2 query body — which dimensions/values you want

    Returns:
        Raw JSON-stat response as a dict.
    """
    # TODO: build the actual request. v2 typically wants a POST with a JSON query body
    # rather than v1's GET-with-query-string style — confirm against current docs.
    raise NotImplementedError("Fill this in once you've picked a table and read the v2 query format.")


def json_stat_to_dataframe(json_stat: dict) -> pd.DataFrame:
    """
    Convert a JSON-stat response into a tidy pandas DataFrame.

    This is the fiddly part: JSON-stat stores `value` as a flat array and `dimension` as a
    dict describing what each position in that array means. You need to reconstruct the
    full index (e.g. region x year x category) before you can attach the values.

    Tip: the `pyjstat` library (pip install pyjstat) can do this conversion for you if you'd
    rather not hand-roll the dimension unpacking - worth trying before writing this by hand.
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    # TODO: once fetch_table + json_stat_to_dataframe work, this should end with:
    #   df = json_stat_to_dataframe(fetch_table(...))
    #   print(df.head())
    #   df.to_csv("../data/scb_sample.csv", index=False)
    pass
