"""
Phase 3, Transform — reshape raw source-specific DataFrames into the shared schema
(timestamp, country, metric, value, unit, source) defined in schema.sql.

This is where SCB's and SMARD's very different native shapes converge into one common format.
Keep each function narrow: one source in, one normalized DataFrame out.
"""

import pandas as pd

SCHEMA_COLUMNS = ["timestamp", "country", "metric", "value", "unit", "source"]


def normalize_scb(df: pd.DataFrame, metric: str, unit: str) -> pd.DataFrame:
    """
    Reshape a raw SCB DataFrame into the shared schema.
    TODO: map SCB's actual column names (depends on which table you pulled) to timestamp/value.
    """
    raise NotImplementedError


def normalize_smard(df: pd.DataFrame, metric: str, unit: str) -> pd.DataFrame:
    """
    Reshape a raw SMARD DataFrame into the shared schema.
    TODO: SMARD timestamps come back as unix ms - make sure they're converted to ISO UTC here,
    not left as raw ints, so everything lines up with SCB's timestamps downstream.
    """
    raise NotImplementedError


def validate_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Sanity check before loading: right columns, no null timestamps, known country codes."""
    missing = set(SCHEMA_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df["timestamp"].isnull().any():
        raise ValueError("Found null timestamps - fix upstream before loading.")
    if not set(df["country"].unique()) <= {"SE", "DE"}:
        raise ValueError(f"Unexpected country codes: {df['country'].unique()}")
    return df
