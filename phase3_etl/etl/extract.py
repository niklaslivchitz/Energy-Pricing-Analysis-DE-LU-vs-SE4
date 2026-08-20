"""
Phase 3, Extract — thin wrappers around the Phase 1/2 fetch logic.

Don't rewrite fetch logic here. By this point fetch_scb.py / fetch_smard.py already work from
Phase 1 — this module just calls them and hands raw data to transform.py. If you find yourself
duplicating fetch logic instead of importing it, stop and import it instead.
"""

# TODO: once Phase 1 scripts are solid, import them, e.g.:
# import sys
# sys.path.append("../../phase1_explore")
# from fetch_scb import fetch_table, json_stat_to_dataframe
# from fetch_smard import fetch_available_timestamps, fetch_series, series_to_dataframe


def extract_scb(table_path: str, query: dict):
    """Return a raw pandas DataFrame from SCB, unchanged (no schema normalization here)."""
    raise NotImplementedError


def extract_smard(filter_code: int, timestamp: int):
    """Return a raw pandas DataFrame from SMARD, unchanged (no schema normalization here)."""
    raise NotImplementedError
