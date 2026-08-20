"""
Phase 1, Step C — one Seaborn chart per source. This is the finish line for Phase 1.

Not trying to answer a question yet - just confirming: real data, from both APIs, in a plot.
Once this runs, Phase 1 is done and you move to phase2_single_country/.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from fetch_scb import fetch_table, json_stat_to_dataframe
from fetch_smard import fetch_available_timestamps, fetch_series, series_to_dataframe, DAY_AHEAD_PRICE_FILTER


def plot_scb(df: pd.DataFrame):
    # TODO: adjust column names once you know what your chosen SCB table actually returns
    sns.lineplot(data=df, x="year", y="value")
    plt.title("SCB sample series")
    plt.show()


def plot_smard(df: pd.DataFrame):
    sns.lineplot(data=df, x="timestamp", y="value")
    plt.title("SMARD day-ahead price sample")
    plt.show()


if __name__ == "__main__":
    # TODO: wire these up once fetch_scb.py and fetch_smard.py are working
    pass
