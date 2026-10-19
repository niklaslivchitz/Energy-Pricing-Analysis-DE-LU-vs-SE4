
"""
This is the main analytical engine for the renewable share and price volatility analysis.
It loads the data from the database, computes the daily volatility and renewable shares, fits regression models, and saves the results to files.
Run the script from repo root with `python -m analysis.volatility_renewable_share`.
"""

import numpy as np  # used inside the log formula
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns

from src.entsoe_client import GENERATION_ZONES
from src.pipeline_utils import get_engine, REPO_ROOT

FIGURES_DIR = REPO_ROOT / "outputs" / "figures"
TABLES_DIR = REPO_ROOT / "outputs" / "tables" / "volatility"

# ENTSO-E production type names that count as wind and as solar. Types a zone doesn't report are skipped.
WIND_TYPES = ["Wind Onshore", "Wind Offshore"]
SOLAR_TYPES = ["Solar"]

ZONE_FORMULAS = {
    "base": "volatility ~ solar_share + wind_share",
    "month_control": "volatility ~ solar_share + wind_share + C(month)",
    "log": "np.log(volatility) ~ solar_share + wind_share",
}
POOLED_FORMULA = "volatility ~ (solar_share + wind_share) * C(zone)"

def load_prices(engine, zones):
    """Load day-ahead prices for the given zones and parse timestamps."""
    prices = pd.read_sql("SELECT * FROM prices", engine)
    prices["timestamp"] = pd.to_datetime(prices["timestamp"])
    return prices[prices["zone"].isin(zones)]

def load_generation(engine, zones):
    """Load the generation for the given zones and parse timestamps."""
    generation = pd.read_sql("SELECT * FROM generation", engine)
    generation["timestamp"] = pd.to_datetime(generation["timestamp"])
    return generation[generation["zone"].isin(zones)]

def compute_shares(generation):
    """Wind, solar and combined share of total generation, per zone and timestamp."""
    wide = generation.pivot(
        index=["zone", "timestamp"], columns="production_type", values="value_mw"
    ).clip(lower=0)
    production_cols = wide.columns.tolist()
    wide = wide.reset_index()
    total = wide[production_cols].sum(axis=1)
    wind_cols = [c for c in WIND_TYPES if c in wide.columns]
    solar_cols = [c for c in SOLAR_TYPES if c in wide.columns]
    wide["wind_share"] = wide[wind_cols].sum(axis=1) / total
    wide["solar_share"] = wide[solar_cols].sum(axis=1) / total
    wide["renewables_share"] = wide["wind_share"] + wide["solar_share"]
    return wide[["zone", "timestamp", "wind_share", "solar_share", "renewables_share"]]

    
def build_daily_table(prices, shares):
    """
    One row per zone per day (UTC days).
    Volatility is the standard deviation of the 15-minute prices within the day,
    price_gap is the day's highest minus lowest price, shares are daily means.
    """
    merged = prices.merge(shares, on=["zone", "timestamp"], validate="one_to_one")
    merged["date"] = merged["timestamp"].dt.date
    daily = (
        merged.groupby(["zone", "date"])
        .agg(
            volatility=("price_eur_mwh", "std"),
            price_max=("price_eur_mwh", "max"),
            price_min=("price_eur_mwh", "min"),
            wind_share=("wind_share", "mean"),
            solar_share=("solar_share", "mean"),
            renewables_share=("renewables_share", "mean"),
        )
        .reset_index()
    )
    daily["price_gap"] = daily["price_max"] - daily["price_min"]
    daily["month"] = pd.to_datetime(daily["date"]).dt.month
    return daily

def build_hourly_table(prices):
    """One row per zone per hour of day: the mean price at that hour, in local (Berlin) time."""
    prices = prices.copy()
    prices["hour"] = prices["timestamp"].dt.tz_convert("Europe/Berlin").dt.hour  # timestamps are UTC, the midday dip is local
    return prices.groupby(["zone", "hour"])["price_eur_mwh"].mean().reset_index()

def fit_model(table, formula):
    """
    Fit an OLS regression with HAC standard errors.
    HAC because consecutive days are not independent (weather persists) and the spread
    is not constant; 7 lags lets the correction reach one week back.
    """
    return smf.ols(formula, data=table).fit(cov_type="HAC", cov_kwds={"maxlags": 7})

def plot_daily_volatility(daily):
    """Time series of daily price volatility, one line per zone."""
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.lineplot(data=daily, x="date", y="volatility", hue="zone", ax=ax)
    ax.set_title("Daily price volatility")
    ax.set_xlabel("")
    ax.set_ylabel("Std of price within the day (EUR/MWh)")
    fig.savefig(FIGURES_DIR / "volatility_daily.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_volatility_vs_share(daily, share_column):
    """Scatter of daily volatility against one share column, e.g. 'solar_share'."""
    label = share_column.replace("_", " ")
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(data=daily, x=share_column, y="volatility", hue="zone", alpha=0.6, ax=ax)
    ax.set_title(f"Daily price volatility vs {label}")
    ax.set_xlabel(f"{label.capitalize()} of generation (daily mean)")
    ax.set_ylabel("Std of price within the day (EUR/MWh)")
    fig.savefig(FIGURES_DIR / f"volatility_vs_{share_column}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_solar_fit(daily):
    """Volatility against solar share with one fitted line per zone (solar-only OLS, no HAC)."""
    g = sns.lmplot(
        data=daily, x="solar_share", y="volatility", hue="zone",
        height=6, aspect=1.6, ci=None, scatter_kws={"alpha": 0.5},
    )
    g.set_axis_labels("Solar share of generation (daily mean)", "Std of price within the day (EUR/MWh)")
    g.ax.set_title("Daily price volatility vs solar share, with fitted lines")
    g.savefig(FIGURES_DIR / "volatility_vs_solar_share_fit.png", dpi=150, bbox_inches="tight")
    plt.close(g.figure)


def plot_solar_fit_by_month(daily):
    """The solar fit split into one panel per month, to show the pattern within seasons."""
    g = sns.lmplot(
        data=daily, x="solar_share", y="volatility", hue="zone", col="month", col_wrap=4,
        height=3, ci=None, scatter_kws={"alpha": 0.5},
    )
    g.set_axis_labels("Solar share (daily mean)", "Std of price within the day (EUR/MWh)")
    g.savefig(FIGURES_DIR / "volatility_vs_solar_share_by_month.png", dpi=150, bbox_inches="tight")
    plt.close(g.figure)


def plot_price_by_hour(hourly):
    """Average price at each hour of the day, one line per zone."""
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=hourly, x="hour", y="price_eur_mwh", hue="zone", marker="o", ax=ax)
    ax.set_title("Average day-ahead price by hour of day")
    ax.set_xlabel("Hour of day (local time)")
    ax.set_ylabel("Mean price (EUR/MWh)")
    fig.savefig(FIGURES_DIR / "price_by_hour.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def coefficients_table(result):
    """The regression's coefficients, standard errors, p-values and 95% confidence interval as one table."""
    table = result.conf_int()
    table.columns = ["ci_low", "ci_high"]
    table["coef"] = result.params
    table["std_err"] = result.bse
    table["p_value"] = result.pvalues
    table.index.name = "term"
    return table.reset_index()

def main():
    """
    This runs the whole analysis, saving the daily and hourly tables, the Spearman correlations and the regression results to text files, and the plots to image files.
    """
    engine = get_engine()
    prices = load_prices(engine, GENERATION_ZONES)
    generation = load_generation(engine, GENERATION_ZONES)

    shares = compute_shares(generation)
    daily = build_daily_table(prices, shares)
    missing = set(GENERATION_ZONES) - set(daily["zone"])
    if missing:
        # the merge in build_daily_table keeps only zones with both prices and generation
        raise ValueError(f"No matching prices and generation for {sorted(missing)}. Check PRICE_ZONES and GENERATION_ZONES in src/entsoe_client.py.")
    hourly = build_hourly_table(prices)

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    daily.to_csv(TABLES_DIR / "daily_volatility_and_shares.csv", index=False)

    # Exports for the Tableau dashboard. Local time without an offset, because Tableau handles offsets poorly.
    prices_shares = prices.merge(shares, on=["zone", "timestamp"], validate="one_to_one")
    prices_shares.insert(2, "timestamp_local", prices_shares["timestamp"].dt.tz_convert("Europe/Berlin").dt.strftime("%Y-%m-%d %H:%M:%S"))
    prices_shares.sort_values(["zone", "timestamp"], inplace=True)
    prices_shares.to_csv(TABLES_DIR / "prices_shares_15min.csv", index=False)

    mix = generation.copy()
    mix["date_local"] = mix["timestamp"].dt.tz_convert("Europe/Berlin").dt.date
    mix["energy_mwh"] = mix["value_mw"].clip(lower=0) * 0.25  # MW held for 15 minutes = MW x 0.25 h; pumping counts as zero, as in the shares
    generation_mix = mix.groupby(["zone", "date_local", "production_type"])["energy_mwh"].sum().reset_index()
    generation_mix.to_csv(TABLES_DIR / "generation_mix_daily.csv", index=False)

    spearman = daily.groupby("zone")[["volatility", "solar_share", "wind_share", "renewables_share"]].corr(method="spearman")
    print(spearman)
    spearman.to_csv(TABLES_DIR / "spearman_by_zone.csv")

    coefficient_tables = []
    summaries = []

    for zone in GENERATION_ZONES:
        zone_daily = daily[daily["zone"] == zone]
        for name, formula in ZONE_FORMULAS.items():
            result = fit_model(zone_daily, formula)
            print(zone, name)
            print(result.summary())
            table = coefficients_table(result)
            table.insert(0, "zone", zone)
            table.insert(0, "model", name)
            coefficient_tables.append(table)
            summaries.append(f"{name} / {zone}\n{result.summary().as_text()}")

    # Fit a pooled model across all zones, with interaction terms for zone.
    result = fit_model(daily, POOLED_FORMULA)
    table = coefficients_table(result)
    table.insert(0, "zone", "all")
    table.insert(0, "model", "pooled")
    coefficient_tables.append(table)
    summaries.append(f"pooled / all\n{result.summary().as_text()}") #we save the summaries to a text file for easy reading, but the coefficients to a CSV for easier analysis

    pd.concat(coefficient_tables).to_csv(TABLES_DIR / "regression_coefficients.csv", index=False)
    (TABLES_DIR / "regression_summaries.txt").write_text("\n\n".join(summaries))

    plot_daily_volatility(daily)
    plot_volatility_vs_share(daily, "solar_share")
    plot_volatility_vs_share(daily, "wind_share")
    plot_solar_fit(daily)
    plot_solar_fit_by_month(daily)
    plot_price_by_hour(hourly)


if __name__ == "__main__":
    main()