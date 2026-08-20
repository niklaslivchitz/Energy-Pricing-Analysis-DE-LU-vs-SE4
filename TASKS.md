# Task Tracker

Update this as we go — check items off, add notes inline. This is the first thing to read when
picking the project back up after a break.

## Phase 1 — Touch both APIs once
- [ ] Set up venv, `pip install -r requirements.txt`
- [ ] `phase1_explore/fetch_scb.py` — pull one SCB table via PxWebApi v2, into a DataFrame
- [ ] `phase1_explore/fetch_smard.py` — pull one SMARD series (pick day-ahead price, DE/LU, hourly)
- [ ] One Seaborn line chart per source (doesn't need to be pretty — just prove data flows end to end)
- [ ] Note here: which SCB table code did you use? _______
- [ ] Note here: which SMARD filter code did you use, and what does it mean? _______

## Phase 2 — First real analysis (single country)
- [ ] Pick renewable share vs. price volatility as the first question (per plan)
- [ ] Expand `fetch_smard.py` to pull generation-by-source alongside price
- [ ] Compute a simple volatility measure (rolling std of price) and plot against renewable share

## Phase 3 — ETL + SQLite
- [ ] Design shared schema: `timestamp, country, metric, value, unit` (adjust as needed)
- [ ] `phase3_etl/etl/extract.py` — wraps the Phase 1/2 fetch logic
- [ ] `phase3_etl/etl/transform.py` — normalizes into shared schema
- [ ] `phase3_etl/etl/load.py` — writes to SQLite (`data/energy.db`)
- [ ] Confirm both SE and DE data land in the same DB with consistent units/timestamps

## Phase 4 — Comparative analysis
- [ ] Day-ahead vs. intraday spread (centerpiece) — see PROJECT_PLAN.md for the full breakdown
- [ ] Spread vs. renewable share regression (`statsmodels.ols()`)
- [ ] Spread volatility clustering (rolling std, look for time-of-day/season patterns)
- [ ] Spread autocorrelation (`plot_acf()`)
- [ ] Household price trend, SE vs. DE (companion piece)
- [ ] Energy mix vs. price stability (intro/context section)

## Phase 5 — Polish
- [ ] One flagship interactive Plotly view
- [ ] (Optional) synthetic seasonal price curve as an add-on to the seasonal decomposition
- [ ] (Optional) Tableau Public static piece

## Phase 6 — Stretch (optional, do only if time allows)
- [ ] ENTSO-E API key registered (`.env` set up from `.env.example`)
- [ ] Cross-border flow module, same DB schema
- [ ] Scheduled pipeline (cron / GitHub Action) re-pulling SMARD + SCB daily

---
**Current focus:** _(fill in each session — e.g. "Phase 1, stuck on SCB JSON-stat shape")_
