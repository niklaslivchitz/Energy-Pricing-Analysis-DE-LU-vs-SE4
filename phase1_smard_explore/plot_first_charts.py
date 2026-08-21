"""
Phase 1 — one Seaborn chart from SMARD. This is the finish line for Phase 1.

Not trying to answer a question yet - just confirming: real data, from the API, in a plot.
Once this runs, Phase 1 is done and you move to phase2_de_analysis/.

(SCB/Sweden fetching lives in phase6_sweden_and_crossborder/ now — Sweden is a stretch goal,
not part of the core Phase 1-5 build. See PROJECT_PLAN.md for why.)
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from fetch_smard import fetch_available_timestamps, fetch_series, series_to_dataframe, DAY_AHEAD_PRICE_FILTER


def plot_smard(df: pd.DataFrame):
    sns.lineplot(data=df, x="timestamp", y="value")
    plt.title("SMARD day-ahead price sample")
    plt.show()


if __name__ == "__main__":
    # TODO: wire this up once fetch_smard.py is working
    #   timestamps = fetch_available_timestamps(DAY_AHEAD_PRICE_FILTER)
    #   df = series_to_dataframe(fetch_series(DAY_AHEAD_PRICE_FILTER, timestamps[-1]))
    #   plot_smard(df)
    pass
