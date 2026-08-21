# Task Tracker

Update this as we go — check items off, add notes inline. This is the first thing to read when
picking the project back up after a break.

**Core deliverable = Phases 1-5, Germany/SMARD only. Phase 6 (Sweden + cross-border) is optional.**

## Phase 1 — Touch SMARD once
- [ ] Set up venv, `pip install -r requirements.txt`
- [ ] `phase1_smard_explore/fetch_smard.py` — pull one SMARD series (day-ahead price, DE/LU, hourly)
- [ ] One Seaborn line chart (doesn't need to be pretty — just prove data flows end to end)
- [ ] Note here: which SMARD filter code did you use, and what does it mean? _______

## Phase 2 — First real DE analysis
- [ ] Pick renewable share vs. price volatility as the first question (per plan)
- [ ] Expand `fetch_smard.py` to pull generation-by-source alongside price
- [ ] Compute a simple volatility measure (rolling std of price) and plot against renewable share

## Phase 3 — ETL + SQLite
- [ ] Design/confirm shared schema: `timestamp, country, metric, value, unit, source` (see schema.sql — already multi-country-ready even though only DE lands in it for now)
- [ ] `phase3_etl/etl/extract.py` — wraps the Phase 1/2 SMARD fetch logic
- [ ] `phase3_etl/etl/transform.py` — normalizes into shared schema
- [ ] `phase3_etl/etl/load.py` — writes to SQLite (`data/energy.db`)

## Phase 4 — The centerpiece (all DE)
- [ ] Day-ahead vs. intraday spread — see PROJECT_PLAN.md for the full breakdown
- [ ] Spread vs. renewable share regression (`statsmodels.ols()`)
- [ ] Spread volatility clustering (rolling std, look for time-of-day/season patterns)
- [ ] Spread autocorrelation (`plot_acf()`)
- [ ] Seasonal decomposition of day-ahead prices

## Phase 5 — Polish
- [ ] One flagship interactive Plotly view
- [ ] (Optional) synthetic seasonal price curve as an add-on to the seasonal decomposition
- [ ] (Optional) Tableau Public static piece

## Phase 6 — Stretch, optional (Sweden + cross-border, bundled)
- [ ] `phase6_sweden_and_crossborder/fetch_scb.py` — one SCB table (household prices), via PxWebApi v2
- [ ] Nord Pool free day-ahead endpoint — `dataportal-api.nordpoolgroup.com/api/DayAheadPrices`, no auth needed
- [ ] ENTSO-E API key registered (`.env` set up from `.env.example`)
- [ ] Cross-border flow module, writing into the same DB schema from Phase 3
- [ ] Household price trend, SE vs. DE
- [ ] Energy mix vs. price stability, SE vs. DE

---
**Current focus:** _(fill in each session — e.g. "Phase 1, stuck on SMARD filter code")_
