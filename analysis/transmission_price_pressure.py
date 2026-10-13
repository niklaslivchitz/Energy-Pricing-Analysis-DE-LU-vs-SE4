"""
Baltic Cable analysis: do German (DE_LU) and southern Swedish (SE_4) prices drift
apart when the cable between them is full or out of service?

Reads prices, flows and outage records from the database, classifies every 15 minutes
as partly used, full or outage, and tests the price gap on daily values.
Writes tables to outputs/tables/cable/ and figures to outputs/figures/.

Run from the repo root: python -m analysis.transmission_price_pressure
"""

import matplotlib.pyplot as plt
import numpy as np  # used inside the log formula
import pandas as pd
import seaborn as sns
import statsmodels.formula.api as smf
from matplotlib.patches import Patch

from src.pipeline_utils import REPO_ROOT, get_engine

ZONE_DE = "DE_LU"
ZONE_SE = "SE_4"
RATED_MW_TO_SE = 600
RATED_MW_TO_DE = 615
FULL_UTILIZATION = 0.95      # at or above this share of available capacity counts as full
OBSERVED_CEILING_MW = 400    # flows this large count as full even where no outage record limits the cable
FULL_DAY_SHARE = 0.5         # a day is shaded as "full" if the cable was full at least this share of it
HAC_LAGS = 14

FIGURES_DIR = REPO_ROOT / "outputs" / "figures"
TABLES_DIR = REPO_ROOT / "outputs" / "tables" / "cable"

FORMULAS = {
    "state": "abs_spread ~ share_full + share_outage",
    "state_month_control": "abs_spread ~ share_full + share_outage + C(month)",
    "state_log": "np.log(abs_spread) ~ share_full + share_outage + C(month)",
    "direction": "price_spread ~ share_full_to_de + share_full_to_se + share_outage + C(month)",
}

def load_outages(engine, zone_from, zone_to):
    """Load the outage records for one direction of the cable and parse the times."""
    outages = pd.read_sql("SELECT * FROM transmission_outages", engine)
    outages["start_time"] = pd.to_datetime(outages["start_time"])
    outages["end_time"] = pd.to_datetime(outages["end_time"])
    return outages[(outages["zone_from"] == zone_from) & (outages["zone_to"] == zone_to)]

def capacity_series(outages, timestamps, full_capacity):
    """
    Available capacity per timestamp: the lowest available_mw among the active
    records covering it, and the full capacity where no record applies.
    """
    capacity = pd.Series(full_capacity, index=timestamps, dtype=float)
    active = outages[outages["doc_status"] != "Cancelled"]
    for _, record in active.iterrows():
        covered = (timestamps >= record["start_time"]) & (timestamps < record["end_time"])
        capacity[covered] = capacity[covered].clip(upper=record["available_mw"])
    return capacity

def load_prices(engine, zones):
    """Load day-ahead prices for the given zones and parse timestamps."""
    prices = pd.read_sql("SELECT * FROM prices", engine)
    prices["timestamp"] = pd.to_datetime(prices["timestamp"])
    return prices[prices["zone"].isin(zones)]

def load_flows(engine, zones):
    """Load cross-border flows between the given zones and parse timestamps."""
    flows = pd.read_sql("SELECT * FROM cross_border_flows", engine)
    flows["timestamp"] = pd.to_datetime(flows["timestamp"])
    return flows[flows["zone_from"].isin(zones) & flows["zone_to"].isin(zones)]

def build_cable_table(prices, flows, outages_to_de, outages_to_se):
    """
    One row per 15 minutes: both prices, the price gap, the net flow on the cable,
    the capacity available at that time, and the cable's state.
    The price gap is SE_4 minus DE_LU. Net flow is positive towards Germany.
    """
    prices_wide = prices.pivot(index="timestamp", columns="zone", values="price_eur_mwh")
    prices_wide = prices_wide.rename(columns={ZONE_DE: "price_de", ZONE_SE: "price_se4"})

    flows = flows.copy()
    flows["direction"] = flows["zone_from"] + "_to_" + flows["zone_to"]
    flows_wide = flows.pivot(index="timestamp", columns="direction", values="flow_mw")
    flows_wide = flows_wide.rename(columns={
        f"{ZONE_SE}_to_{ZONE_DE}": "flow_se_to_de",
        f"{ZONE_DE}_to_{ZONE_SE}": "flow_de_to_se",
    })

    cable = prices_wide.join(flows_wide, how="inner").reset_index()
    cable["price_spread"] = cable["price_se4"] - cable["price_de"]
    cable["abs_spread"] = cable["price_spread"].abs()
    cable["net_flow"] = cable["flow_se_to_de"] - cable["flow_de_to_se"]

    timestamps = pd.DatetimeIndex(cable["timestamp"])
    cable["capacity_to_de"] = capacity_series(outages_to_de, timestamps, RATED_MW_TO_DE).values
    cable["capacity_to_se"] = capacity_series(outages_to_se, timestamps, RATED_MW_TO_SE).values
    cable["capacity"] = cable["capacity_to_de"].where(cable["net_flow"] >= 0, cable["capacity_to_se"])
    cable["utilization"] = (cable["net_flow"].abs() / cable["capacity"]).where(cable["capacity"] > 0)

    cable["state"] = "partly used"
    is_full = (cable["utilization"] >= FULL_UTILIZATION) | (cable["net_flow"].abs() >= OBSERVED_CEILING_MW)
    cable.loc[is_full, "state"] = "full"
    cable.loc[cable["capacity"] == 0, "state"] = "outage"

    cable["direction"] = "none"
    cable.loc[cable["net_flow"] > 0, "direction"] = "towards Germany"
    cable.loc[cable["net_flow"] < 0, "direction"] = "towards Sweden"
    return cable

def build_daily_table(cable):
    """
    One row per day (UTC days): the mean price gap, signed and absolute, and the share
    of the day the cable spent in each state.
    """
    cable = cable.copy()
    cable["date"] = cable["timestamp"].dt.date
    cable["is_full"] = cable["state"] == "full"
    cable["is_outage"] = cable["state"] == "outage"
    cable["full_to_de"] = cable["is_full"] & (cable["direction"] == "towards Germany")
    cable["full_to_se"] = cable["is_full"] & (cable["direction"] == "towards Sweden")
    daily = (
        cable.groupby("date")
        .agg(
            abs_spread=("abs_spread", "mean"),
            price_spread=("price_spread", "mean"),
            share_full=("is_full", "mean"),
            share_outage=("is_outage", "mean"),
            share_full_to_de=("full_to_de", "mean"),
            share_full_to_se=("full_to_se", "mean"),
        )
        .reset_index()
    )
    daily["month"] = pd.to_datetime(daily["date"]).dt.month
    return daily

def fit_model(table, formula):
    """
    Fit an OLS regression with HAC standard errors.
    HAC because consecutive days are not independent (outages last for weeks) and the
    spread is not constant.
    """
    return smf.ols(formula, data=table).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})


def coefficients_table(result):
    """The regression's coefficients, standard errors, p-values and 95% confidence interval as one table."""
    table = result.conf_int()
    table.columns = ["ci_low", "ci_high"]
    table["coef"] = result.params
    table["std_err"] = result.bse
    table["p_value"] = result.pvalues
    table.index.name = "term"
    return table.reset_index()

def plot_spread_over_time(daily):
    """Daily price gap over time, with outage days and mostly-full days shaded."""
    fig, ax = plt.subplots(figsize=(14, 5))
    sns.lineplot(data=daily, x="date", y="abs_spread", color="black", ax=ax)
    for _, day in daily.iterrows():
        if day["share_outage"] >= 0.99:
            color = "grey"
        elif day["share_full"] >= FULL_DAY_SHARE:
            color = "orange"
        else:
            continue
        ax.axvspan(day["date"], day["date"] + pd.Timedelta(days=1), color=color, alpha=0.3, linewidth=0)
    ax.legend(handles=[
        Patch(color="grey", alpha=0.3, label="Cable out of service"),
        Patch(color="orange", alpha=0.3, label="Cable full for most of the day"),
    ])
    ax.set_title(f"Daily price gap between {ZONE_SE} and {ZONE_DE}, by cable state")
    ax.set_xlabel("")
    ax.set_ylabel("Mean price gap (EUR/MWh)")
    fig.savefig(FIGURES_DIR / "cable_spread_over_time.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def plot_spread_vs_flow(cable):
    """Signed price gap against net flow at 15 minutes, coloured by state, in-service intervals only."""
    running = cable[cable["state"] != "outage"]
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(data=running, x="net_flow", y="price_spread", hue="state", alpha=0.1, s=8, ax=ax)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)
    legend = ax.get_legend()
    if legend is not None:
        for handle in legend.legend_handles:
            handle.set_alpha(1)  # type: ignore
    ax.set_title("Price gap vs flow on the Baltic Cable, in service only")
    ax.set_xlabel("Net flow (MW), positive = towards Germany")
    ax.set_ylabel(f"{ZONE_SE} price minus {ZONE_DE} price (EUR/MWh)")
    fig.savefig(FIGURES_DIR / "cable_spread_vs_flow.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def plot_spread_by_state(cable):
    """Box plot of the price gap in each cable state, without the extreme points."""
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=cable, x="state", y="abs_spread", order=["partly used", "full", "outage"], showfliers=False, ax=ax)
    ax.set_title("Price gap by cable state")
    ax.set_xlabel("")
    ax.set_ylabel(f"Price gap between {ZONE_SE} and {ZONE_DE} (EUR/MWh)")
    fig.savefig(FIGURES_DIR / "cable_spread_by_state.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def main():
    """
    Runs the whole cable analysis: builds the 15-minute and daily tables, saves the summary
    tables and regression results to outputs/tables/cable/, and the figures to outputs/figures/.
    """
    engine = get_engine()
    prices = load_prices(engine, [ZONE_DE, ZONE_SE])
    flows = load_flows(engine, [ZONE_DE, ZONE_SE])
    outages_to_se = load_outages(engine, ZONE_DE, ZONE_SE)
    outages_to_de = load_outages(engine, ZONE_SE, ZONE_DE)

    cable = build_cable_table(prices, flows, outages_to_de, outages_to_se)
    daily = build_daily_table(cable)
    print(cable.groupby("state").size())
    print(daily.head())

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    daily.to_csv(TABLES_DIR / "daily_spread_and_cable_state.csv", index=False)

    state_summary = cable.groupby("state")["abs_spread"].describe()
    print(state_summary)
    state_summary.to_csv(TABLES_DIR / "abs_spread_by_state.csv")

    full = cable[cable["state"] == "full"].copy()
    direction_summary = full.groupby("direction")["price_spread"].describe()
    print(direction_summary)
    direction_summary.to_csv(TABLES_DIR / "spread_by_direction_when_full.csv")

    full["hour"] = full["timestamp"].dt.tz_convert("Europe/Berlin").dt.hour  # timestamps are UTC, the midday pattern is local
    full_by_hour = full.groupby(["hour", "direction"]).size().unstack()
    print(full_by_hour)
    full_by_hour.to_csv(TABLES_DIR / "full_intervals_by_hour.csv")

    coefficient_tables = []
    summaries = []
    for name, formula in FORMULAS.items():
        result = fit_model(daily, formula)
        print(name)
        print(result.summary())
        table = coefficients_table(result)
        table.insert(0, "zone", f"{ZONE_DE}-{ZONE_SE}")
        table.insert(0, "model", name)
        coefficient_tables.append(table)
        summaries.append(f"{name}\n{result.summary().as_text()}")

    pd.concat(coefficient_tables).to_csv(TABLES_DIR / "regression_coefficients.csv", index=False)
    (TABLES_DIR / "regression_summaries.txt").write_text("\n\n".join(summaries))

    plot_spread_over_time(daily)
    plot_spread_vs_flow(cable)
    plot_spread_by_state(cable)


if __name__ == "__main__":
    main()

