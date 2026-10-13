"""
Findings report: reads the result tables of both analyses and writes the findings
as sentences with the current numbers to outputs/report.md.

Run from the repo root, after both analysis scripts: python -m analysis.findings_report
"""
import pandas as pd

from src.pipeline_utils import REPO_ROOT

ALPHA = 0.05  # p-values below this count as a clear effect
VOLATILITY_DIR = REPO_ROOT / "outputs" / "tables" / "volatility"
CABLE_DIR = REPO_ROOT / "outputs" / "tables" / "cable"
REPORT_PATH = REPO_ROOT / "outputs" / "report.md"


def get_term(coefficients, model, zone, term):
    """One row of a coefficient table, picked by model, zone and term."""
    match = coefficients[
        (coefficients["model"] == model) & (coefficients["zone"] == zone) & (coefficients["term"] == term)
    ]
    return match.iloc[0]


def effect_words(row):
    """'a clear effect' or 'no detectable effect', depending on the p-value."""
    if row["p_value"] < ALPHA:
        return "a clear effect"
    return "no detectable effect"


def main():
    volatility = pd.read_csv(VOLATILITY_DIR / "regression_coefficients.csv")
    solar = get_term(volatility, "base", "DE_LU", "solar_share")
    print(
        f"In DE_LU, 10 percentage points more solar goes with {solar['coef'] / 10:.1f} EUR/MWh "
        f"more daily volatility ({effect_words(solar)}, p = {solar['p_value']:.3f})."
    )


if __name__ == "__main__":
    main()