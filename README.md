# Germany vs. Sweden Energy Market Analysis (ENTSO-E)

Full plan, rationale, and analysis design: `docs/project-brief.md`.

## TLDR:
This is a tech-stack-learning project pulling energy market data from ENTSO-E via their API, storing it, and running analyses on it.
The analytical focus is on price volatility as an effect of renewable energy generation share, as well as how German (DE-LU) day-ahead prices exert pressure on southern Swedish (SE4) prices via the Baltic Cable interconnector.

## Project Status
Phase 1 complete: Token is in place and works, API calls for pricing data for SE4 and DE-LU is go, as well as generation mix for SE4 and DE-LU. Details in the worksheet for Phase 1. 
Phase 2 complete - the fetch_and_cache.py script successfully pulls a week of testing data and stores it as csvs in /data/processed. Data quality is fine, transformations for analyses work fine. First pass of statistical analysis done, see notebook in the phase 2 folder.

## Structure — organized by build phase (see brief Section 10)

```
common/                                      Shared code used across phases (ENTSO-E client, pipeline helpers)
db/                                          SQLite schema
docs/                                        Project brief
phase_1_exploration/                         First manual pull: one zone, prove the mechanics work, rescope pull examples of all tables
phase_2_quality_and_first_analysis/          Naive ETL written, data quality pass done, first proof-of-concept statistical analyses.
phase_3_etl_pipeline/                        Formalize into fetch -> transform -> load, with logging/retry, also with rework of the folder structure planned.
phase_4_volatility_vs_renewables/            Core analysis 1
phase_5_transmission_price_pressure/         Core analysis 2 (DE <-> SE4, Baltic Cable)
phase_6_polish/                              Flagship interactive view, Tableau piece if time allows
phase_7_stretch_goals/                       Optional: synthetic curves, scheduled pipeline, more countries
sql/                                         Standalone queries reused across phases
outputs/figures/                             Exported charts
```

## Tech
- Python
- entsoe-py (ENTSO-E API client)
- pandas
- SQLite
- statsmodels (regressions for the two core analyses)
- scikit-learn
- seaborn + matplotlib
- plotly
- jupyter

## Quickstart
1. Register for ENTSO-E API access (brief Section 2), put the token in `.env`:
   ```
   ENTSOE_API_KEY=your-token-here
   ```
2. `pip install -r requirements.txt`
3. Start at `phase_1_exploration/`, work through phases in order — each one assumes the previous phase's output exists.
