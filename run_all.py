"""
Runs the whole project in order: the pipeline (fetches from ENTSO-E into the database),
the two analyses, and the findings report.

Run from the repo root: python run_all.py
"""
from analysis import findings_report, transmission_price_pressure, volatility_renewable_share
from src import pipeline


def main():
    pipeline.main()
    volatility_renewable_share.main()
    transmission_price_pressure.main()
    findings_report.main()


if __name__ == "__main__":
    main()