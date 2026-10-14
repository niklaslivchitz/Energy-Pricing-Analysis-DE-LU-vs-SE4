"""
Findings report: reads the result tables of both analyses and writes the findings
as plain sentences with the current numbers to outputs/report.md.

The README and the brief describe one fixed period in hand-written words. This report
is regenerated from whatever the tables currently hold, and is meant as a key for reading
the correlations, p-values and checks without a statistics background.

Run from the repo root, after both analysis scripts: python -m analysis.findings_report
"""
import pandas as pd

from src.pipeline_utils import REPO_ROOT

ALPHA = 0.05  # p-values below this count as a clear effect
VOLATILITY_DIR = REPO_ROOT / "outputs" / "tables" / "volatility"
CABLE_DIR = REPO_ROOT / "outputs" / "tables" / "cable"
FIGURES_DIR = REPO_ROOT / "outputs" / "figures"
REPORT_PATH = REPO_ROOT / "outputs" / "report.md"

SHARES = ["solar_share", "wind_share"]

METHOD_SPEARMAN = "Spearman rank correlation on daily values"
METHOD_REGRESSION = "linear regression on daily values, with standard errors corrected for day-to-day dependence (HAC)"
METHOD_MONTH = "the same regression with the calendar month added as a control"
METHOD_LOG = "the same regression on the logarithm of the outcome, which shrinks extreme days"
METHOD_STATE = "median price gap over all 15-minute intervals in each cable state"

HOW_TO_READ = [
    "## How to read this",
    "",
    "- **Correlation** runs from -1 to +1. Near 0 means no link; near +1 or -1 means the two move closely together or opposite."
    " Spearman's version compares rankings, so a few extreme days cannot dominate it.",
    "- **Regression** estimates how much one thing changes when another changes, holding the other inputs equal.",
    f"- **p-value:** the chance of seeing an effect this large if there were none. Below {ALPHA} counts as a clear effect here.",
    "- **HAC correction:** neighbouring days resemble each other, which makes ordinary p-values too confident. The correction accounts for that.",
    "- **The two checks** test whether a result is really the season, or really a handful of extreme days.",
    "- None of this proves that one thing causes the other.",
    "",
]


def image_lines(filename, caption):
    """Markdown for one chart from outputs/figures/, linked relative to the report. Skipped if the chart is missing."""
    if not (FIGURES_DIR / filename).exists():
        return []
    return [f"![{caption}](figures/{filename})", f"*{caption}*", ""]


def date_range_text(daily):
    """
    'Data from ... to ...' in local (Berlin) days. The daily tables use UTC days, and the data starts
    at local midnight, which is still the evening before in UTC. So the first UTC date only holds
    that last hour or two and is skipped.
    """
    dates = sorted(daily["date"].unique())
    return f"Data from {dates[1]} to {dates[-1]}."


def get_term(coefficients, model, zone, term):
    """Getting data out of the coefficient table. One row of a coefficient table, picked by model, zone and term."""
    match = coefficients[
        (coefficients["model"] == model) & (coefficients["zone"] == zone) & (coefficients["term"] == term)
    ]
    return match.iloc[0]


def p_text(p_value):
    """A p-value as text: 'p < 0.001' for very small values, otherwise three decimals."""
    if p_value < 0.001:
        return "p < 0.001"
    return f"p = {p_value:.3f}"


def strength_words(rho):
    """A correlation as words, e.g. 'a strong positive link'."""
    if abs(rho) < 0.3:
        return "almost no link"
    strength = "a moderate" if abs(rho) < 0.6 else "a strong"
    direction = "positive" if rho > 0 else "negative"
    return f"{strength} {direction} link"


def clear_words(row):
    """'a clear effect' or 'not distinguishable from zero', with the p-value."""
    if row["p_value"] < ALPHA:
        return f"a clear effect, {p_text(row['p_value'])}"
    return f"not distinguishable from zero, {p_text(row['p_value'])}"


def holds_up(base, check):
    """True if a check still shows a clear effect in the same direction as the main test."""
    same_direction = (base["coef"] > 0) == (check["coef"] > 0)
    return check["p_value"] < ALPHA and same_direction


def verdict(clear, holds_month, holds_log):
    """The plain-language conclusion from the main test and the two checks."""
    if clear and holds_month and holds_log:
        return "This holds up. It is clear in the main test and survives both checks."
    if clear and not holds_month:
        return (
            "Treat with caution. It is clear in the main test but disappears once the season is "
            "accounted for, so it may just reflect the time of year."
        )
    if clear:
        return "Mostly holds. It is clear in the main test and survives the season check, but depends on a few extreme days."
    if holds_month:
        return "Tentative. It is not clear in the main test, but shows up once the season is accounted for."
    return "No evidence of an effect."


def share_finding(coefficients, spearman, zone, share):
    """The text lines for one share (e.g. 'solar_share') in one zone."""
    rho = spearman.loc[(zone, "volatility"), share]
    base = get_term(coefficients, "base", zone, share)
    month = get_term(coefficients, "month_control", zone, share)
    log = get_term(coefficients, "log", zone, share)
    clear = base["p_value"] < ALPHA
    holds_month = holds_up(base, month)
    holds_log = holds_up(base, log)

    conclusion = verdict(clear, holds_month, holds_log)
    if abs(rho) >= 0.3 and not clear and not holds_month:
        conclusion += " The link in the first line is indirect: it goes away once the other share is taken into account."

    label = share.replace("_", " ")
    return [
        f"### {label.capitalize()} in {zone}",
        "",
        f"- **Do they move together?** There is {strength_words(rho)} between {label} and daily price "
        f"volatility (correlation {rho:.2f}). *Method: {METHOD_SPEARMAN}.*",
        f"- **How big, and could it be chance?** 10 percentage points more {label} goes with "
        f"{base['coef'] / 10:+.1f} EUR/MWh daily volatility ({clear_words(base)}). *Method: {METHOD_REGRESSION}.*",
        f"- **With the season removed:** {'still there' if holds_month else 'not there'} ({p_text(month['p_value'])}). *Method: {METHOD_MONTH}.*",
        f"- **Without the extreme days:** {'still there' if holds_log else 'not there'} ({p_text(log['p_value'])}). *Method: {METHOD_LOG}.*",
        f"- **Conclusion:** {conclusion}",
        "",
    ]


def volatility_section():
    """The report section for the renewables and price volatility analysis."""
    coefficients = pd.read_csv(VOLATILITY_DIR / "regression_coefficients.csv")
    spearman = pd.read_csv(VOLATILITY_DIR / "spearman_by_zone.csv", index_col=[0, 1])
    daily = pd.read_csv(VOLATILITY_DIR / "daily_volatility_and_shares.csv")
    zones = sorted(daily["zone"].unique())

    lines = [
        "## Wind, solar and price volatility",
        "",
        f"{date_range_text(daily)} Volatility is the standard deviation "
        "of the 15-minute prices within a day. Shares are shares of the zone's own generation.",
        "",
    ]
    for zone in zones:
        rho = spearman.loc[(zone, "volatility"), "renewables_share"]
        lines.append(
            f"- **Wind and solar combined, {zone}:** {strength_words(rho)} with daily volatility "
            f"(correlation {rho:.2f}). The two are looked at separately below, because they can pull in opposite directions."
        )
    lines.append("")
    for zone in zones:
        for share in SHARES:
            lines += share_finding(coefficients, spearman, zone, share)

    lines += image_lines(
        "volatility_vs_solar_share_fit.png",
        "Each dot is one day. The lines are fitted on solar share alone, one per zone; a steeper line means a bigger solar effect.",
    )
    lines += image_lines(
        "volatility_vs_solar_share_by_month.png",
        "The same, one panel per month. This is what the season check looks at: does the pattern hold within a month?",
    )
    lines += image_lines(
        "price_by_hour.png",
        "The average price at each hour of the day. The midday dip is when solar output peaks.",
    )

    # The pooled model compares every other zone against the first (alphabetical order),
    # in terms named like 'solar_share:C(zone)[T.SE_4]'.
    lines += ["### Do the zones differ?", ""]
    for share in SHARES:
        label = share.replace("_", " ")
        for other_zone in zones[1:]:
            row = get_term(coefficients, "pooled", "all", f"{share}:C(zone)[T.{other_zone}]")
            lines.append(
                f"- **{label.capitalize()}, {other_zone} compared with {zones[0]}:** the effect differs by "
                f"{row['coef'] / 10:+.1f} EUR/MWh per 10 percentage points ({clear_words(row)}). "
                f"*Method: one regression over all zones, with a separate slope per zone.*"
            )
    lines.append("")
    return lines


def cable_state_finding(coefficients, state_summary, zone, term, state, state_words):
    """The text lines for one cable state ('full' or 'outage'), compared with a partly used cable."""
    gap = state_summary.loc[state, "50%"]
    gap_spare = state_summary.loc["partly used", "50%"]
    share_of_time = state_summary.loc[state, "count"] / state_summary["count"].sum()
    base = get_term(coefficients, "state", zone, term)
    month = get_term(coefficients, "state_month_control", zone, term)
    log = get_term(coefficients, "state_log", zone, term)
    holds_month = holds_up(base, month)
    holds_log = holds_up(base, log)

    return [
        f"### Cable {state_words}",
        "",
        f"- **First look:** the typical price gap is {gap:.1f} EUR/MWh with the cable {state_words}, against "
        f"{gap_spare:.1f} with spare room. The cable is in this state {share_of_time:.0%} of the time. *Method: {METHOD_STATE}.*",
        f"- **How big, and could it be chance?** On a day spent entirely in this state, the price gap differs by "
        f"{base['coef']:+.1f} EUR/MWh from a day with spare room throughout ({clear_words(base)}). "
        f"*Method: {METHOD_REGRESSION}.*",
        f"- **With the season removed:** {'still there' if holds_month else 'not there'} ({p_text(month['p_value'])}). *Method: {METHOD_MONTH}.*",
        f"- **Without the extreme days:** {'still there' if holds_log else 'not there'} ({p_text(log['p_value'])}). *Method: {METHOD_LOG}, month control included.*",
        f"- **Conclusion:** {verdict(base['p_value'] < ALPHA, holds_month, holds_log)}",
        "",
    ]


def cable_direction_lines(coefficients, direction_summary, full_by_hour, zone):
    """The text lines on which way the cable is full, and what that does to the price gap."""
    terms = {"towards Germany": "share_full_to_de", "towards Sweden": "share_full_to_se"}
    lines = [
        "### Which way the cable is full",
        "",
        "The price gap here is the Swedish price minus the German price, so a negative number means Sweden is cheaper.",
        "",
    ]
    for direction, term in terms.items():
        gap = direction_summary.loc[direction, "50%"]
        count = direction_summary.loc[direction, "count"]
        peak_hour = full_by_hour[direction].idxmax()
        row = get_term(coefficients, "direction", zone, term)
        lines += [
            f"- **Full {direction}:** the typical gap is {gap:+.1f} EUR/MWh ({count:.0f} intervals, most often around "
            f"{peak_hour}:00 local time). *Method: median over the 15-minute intervals with the cable full in this direction.*",
            f"  In the daily test, a day spent entirely full in this direction shifts the gap by {row['coef']:+.1f} EUR/MWh "
            f"({clear_words(row)}). *Method: {METHOD_REGRESSION}, month control included.*",
        ]
    lines.append("")
    return lines


def cable_section():
    """The report section for the Baltic Cable analysis."""
    coefficients = pd.read_csv(CABLE_DIR / "regression_coefficients.csv")
    state_summary = pd.read_csv(CABLE_DIR / "abs_spread_by_state.csv", index_col=0)
    direction_summary = pd.read_csv(CABLE_DIR / "spread_by_direction_when_full.csv", index_col=0)
    full_by_hour = pd.read_csv(CABLE_DIR / "full_intervals_by_hour.csv", index_col=0)
    daily = pd.read_csv(CABLE_DIR / "daily_spread_and_cable_state.csv")
    zone = coefficients["zone"].iloc[0]

    lines = [
        "## The Baltic Cable and the price gap",
        "",
        f"{date_range_text(daily)} Every 15 minutes the cable is out of service, "
        "full, or partly used. The price gap is the difference between the Swedish (SE_4) and German (DE_LU) price.",
        "",
    ]
    lines += image_lines(
        "cable_spread_over_time.png",
        "The daily price gap. Grey: cable out of service. Orange: cable full for most of the day. White: spare room for most of the day.",
    )
    lines += cable_state_finding(coefficients, state_summary, zone, "share_full", "full", "full")
    lines += cable_state_finding(coefficients, state_summary, zone, "share_outage", "outage", "out of service")
    lines += image_lines(
        "cable_spread_by_state.png",
        "The price gap in each cable state. The box holds the middle half of all 15-minute intervals, the line in it is the median.",
    )
    lines += cable_direction_lines(coefficients, direction_summary, full_by_hour, zone)
    lines += image_lines(
        "cable_spread_vs_flow.png",
        "Each dot is 15 minutes with the cable in service. With spare room the gap sits near zero; full towards Germany it is below zero, full towards Sweden above.",
    )
    lines += [
        "Keep in mind: the two zones are also connected through other countries, and a full cable is partly a "
        "result of a price gap, not only a cause. The outage periods are the stronger evidence.",
        "",
    ]
    return lines


def main():
    lines = [
        "# Findings report",
        "",
        "Generated by `analysis/findings_report.py` from the tables in `outputs/tables/`. It always reflects the "
        "latest run of the two analyses. The README and the project brief describe one fixed period in more detail.",
        "",
    ]
    lines += HOW_TO_READ
    lines += volatility_section()
    lines += cable_section()
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
