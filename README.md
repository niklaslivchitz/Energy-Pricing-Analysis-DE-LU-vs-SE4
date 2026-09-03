# Germany vs. Sweden Energy Market Analysis (ENTSO-E)

Full plan, rationale, and analysis design: `docs/project-brief.md`.

##TLDR - This is a skeleton of the project to be filled in a modular fashion as progress goes along.

## Project Status
Phase 1 complete: Token is in place and works, API calls for pricing data for SE4 and DE-LU is go, as well as generation mix for SE4 and DE-LU. Details in the worksheet for Phase 1. 

## Structure — organized by build phase (see brief Section 10)

```
common/                                      Shared code used across phases (ENTSO-E client, pipeline helpers)
db/                                          SQLite schema
docs/                                        Project brief
phase_1_exploration/                         First manual pull: one zone, prove the mechanics work, rescope pull examples of all tables
phase_2_quality_and_first_analysis/          rescope - eyeball analysis of the data, quality check, first analysis attempt. Possibly also pyscript.
phase_3_etl_pipeline/                        Formalize into fetch -> transform -> load, with logging/retry
phase_4_volatility_vs_renewables/            Core analysis 1
phase_5_transmission_price_pressure/         Core analysis 2 (DE <-> SE4, Baltic Cable)
phase_6_polish/                              Flagship interactive view, Tableau piece if time allows
phase_7_stretch_goals/                       Optional: synthetic curves, scheduled pipeline, more countries
sql/                                         Standalone queries reused across phases
outputs/figures/                             Exported charts
```

## Design note: long-format `generation` table

'generation' need to be pivoted. Why? From the call we get one column per energy generation type per time stamp.
In the SQLite database, this would lead to differing columns per country (sweden has no lignite eg) and a lot of NULL values.
To avoid this we povot into a long format, which one row per time stamp, zone and energy type combination.
More rows, but no nulls - missing entries for a country now means rows left out.

As a bonus calculations basically becomes GROUP BY aggregates instead of column arithmetic.

Reguires some fiddling with pivots with the .melt method.

