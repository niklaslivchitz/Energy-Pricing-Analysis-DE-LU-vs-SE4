# Project Brief v3

**Status:** Test data pulled and tentatively analyzed, the full project is go to build. The ETL pipeline is done, pulling and storing generation, transmission and pricing data for SE4 and DE-LU, in a modular fashion (more markets are easy to add without touching the database). SQLite is up and running.
**Core question:** How does renewable variability relate to price volatility in Germany, and how does cross-border transmission capacity between Germany and Sweden shape price convergence/divergence?

---

## 2. Data source: ENTSO-E Transparency Platform

**Access:** Register at transparency.entsoe.eu, then email `transparency@entsoe.eu` requesting RESTful API access (subject: "Restful API access").

**Client library:** Use `entsoe-py`

**Rate limits:** 400 requests/minute per token. Should be a non-issue for this project.

**Datasets:**
| Document | What it gives | entsoe-py method (approx.) |
|---|---|---|
| Day-ahead prices (A44) | 15-min price, EUR/MWh, per bidding zone | `query_day_ahead_prices()` |
| Actual generation per production type (A75) | 15-min generation by source (wind, solar, hydro, nuclear, etc.) per zone | `query_generation(..., nett=True)` |
| Cross-border physical flows | 15-min flow between two zones, one direction per query | `query_crossborder_flows()` |
| (Optional, not pulled yet) Transfer capacity / scheduled exchanges | Cross-border capacity and planned commercial exchange | `query_net_transfer_capacity_weekahead()`, `query_scheduled_exchanges()` |

**Resolution note (checked against the API 2026-09-25):** current data comes at 15-minute resolution, not hourly as this brief originally assumed. The switch happened at different dates per data type:

| Data | Hourly until | 15-min from |
|---|---|---|
| Day-ahead prices (DE_LU, SE_4) | 2025-09-30 | 2025-10-01 (the SDAC switch to 15-min products) |
| Cross-border flows (DE_LU↔SE_4) | 2025-09-29 | 2025-09-30 |
| Generation DE_LU | — | 15-min throughout |
| Generation SE_4 | 2025-12-01 | 2025-12-02 |

**Decision (2026-09-25): a rolling one-year window with a floor at 2025-12-02,** the first date with 15-min data for every series.
- **`end`** = today's Berlin midnight.
- **`start`** = the later of `end − 365 days` and 2025-12-02.

What this means over time:
- **Until December 2026,** the floor applies: about 10 months of uniformly 15-min data. October and November are missing, so the seasonal cycle is incomplete. The write-up should state this when discussing seasonal effects, if the analysis runs on data from before then.
- **From December 2026,** the rolling year takes over automatically, with no code change: a full, uniform year with a complete seasonal cycle.
- **All three tables are always uniformly 15-min,** so neither the pipeline nor the analyses need resolution handling.
- **Alternative considered and rejected:** a full rolling year stored at native resolution, with Analysis 1 resampled to hourly. It gives a complete seasonal cycle today, but every analysis would have to handle mixed resolution.

**Bidding zones:**
- Germany: `DE-LU` — single zone, no ambiguity.
- Sweden: split into **SE1–SE4**. For the renewable-share/volatility analysis, decide whether to use one reference zone, an average, or all four (worth pulling all four since it's the same cost per extra zone). For the DE–SE transmission analysis specifically, **use SE4** — see below.

---

## 3. Physical reality check: the DE–SE interconnection

Worth confirming before designing the transmission analysis, since it determines what's actually observable:

- **Baltic Cable** — an existing, operational ~600 MW HVDC link connecting **SE4** (southern Sweden) and Germany, run by Baltic Cable AB (Statkraft). This is the real physical channel your flow/price-pressure analysis will be measuring.
- **Hansa PowerBridge** — a proposed second, larger (700 MW) DE–SE link — **was rejected by the Swedish government in 2024** over concerns it would import volatility from the German market into southern Sweden.

This is exactly why **SE4** (not SE3 or a national average) is the right Swedish zone for the transmission-specific analysis: it's the zone Baltic Cable physically connects to. Lets leave the analysis of swedish internal transmission to another day.

---

## 4. Core analysis 1 — Volatility vs. renewable share

**Question:** Does a higher share of variable renewables (wind + solar) associate with higher day-ahead price volatility, and does this differ between Germany (wind/solar-heavy) and Sweden (hydro/nuclear-heavy)?

**Methodological note worth stating explicitly in the writeup:** define "renewable share" as **wind + solar specifically**, not all renewables. Hydro (dominant in Sweden) is dispatchable and grid-stabilizing — lumping it in with wind/solar would be confounding the issue, which is about *variable, weather-driven* generation, not renewables in general.

**Steps:**
1. Pull hourly day-ahead price and generation-by-source for DE-LU and each Swedish zone.
2. Compute `variable_renewable_share = (wind + solar) / total_generation` per hour, per zone.
3. Compute a volatility measure — rolling standard deviation of price (e.g. 24-hour window) is the simplest, defensible choice. Also the standard measure in the Energy sector in practice.
4. Regress volatility (or `|price change|`) against `variable_renewable_share`, using `statsmodels.ols()` — e.g. `volatility ~ variable_renewable_share + C(country)` to test whether the relationship differs by country, not just whether it exists.
5. Compare the fitted relationship for DE vs. SE — the expected story (higher variable-renewable share → higher volatility, more pronounced in DE than SE) is a clean, testable hypothesis with a real physical explanation behind it.
6. Optional extension: rolling volatility clustering — does it concentrate around solar ramp times (dawn/dusk) more in DE than SE? `statsmodels.graphics.tsaplots.plot_acf()` for autocorrelation, one line.
7. **Within-day spread (added 2026-09-10):** compute per-day peak-hour minus off-peak-hour price spread, per zone. Standard, cheap, and directly relevant — confirmed via literature (mean and std are consistently higher in peak-hour electricity prices than off-peak across markets) — and likely to show a concrete DE-vs-SE contrast on its own: Germany's solar-driven midday price dip ("duck curve") should show up much more sharply than Sweden's flatter, hydro/nuclear-smoothed profile. Uses data already being pulled, no new source needed.


**Phase 2 exploratory finding (2026-09-10, provisional):** the sample-week first-look came back the *opposite* sign from the hypothesis above. Spearman correlation between `variable_renewable_share` and 24h rolling price volatility, computed in the Phase 2 exploration notebook (`archive/phase_2_quality_and_first_analysis/phase_2_quality_analysis.ipynb`, now local-only and in git history): **DE_LU ≈ −0.50, SE_4 ≈ −0.57**. More renewables associated with *lower* volatility in this sample, not higher.

Followed up in the same notebook with an OLS regression (`rolling_volatility ~ renewables_share * C(zone)`), fit twice to check whether the naive correlation could be trusted: once with default standard errors, once with Newey-West (HAC, 96 lags) robust standard errors. The HAC fit was chosen because the naive fit's Durbin-Watson statistic came back at 0.004 — a strong sign of residual autocorrelation, consistent with the rolling window's overlapping observations. Under the naive fit, every term looked significant (p<0.001). Under the HAC-robust fit: the `renewables_share` main effect held up (p=0.014) — a real, if less overwhelming, negative relationship — but the country-specific terms (SE_4's baseline difference and its slope-interaction with renewables_share) were not significant (p=0.449 and p=0.969 respectively). As recorded in the notebook: the two countries don't appear to behave differently here, but there probably is a genuine negative relationship between renewable share and volatility.

**Caveats before treating this as a settled result:** one sample week only — this could reflect that week's particular weather/demand pattern rather than a stable relationship; needs Phase 3's longer historical pull to confirm it holds. This is a correlation/regression finding, not a causal claim — no mechanism has been established. The autocorrelation problem the HAC correction addresses (from the rolling window's overlapping observations) means even the HAC p-value should be read as indicative rather than definitive on a sample this small.

---

## 5. Core analysis 2 — Transmission price pressure, Germany ↔ Sweden

**Question:** Does the DE–SE price spread widen when the Baltic Cable is running at or near its ~600 MW capacity (congestion), and converge when flow is comfortably below capacity (market coupling working as intended)?

This is standard price-coupling logic: interconnected markets should converge toward the same price when transfer capacity isn't binding; when the link saturates, the two markets decouple and the spread reflects the congestion cost.

**Steps:**
1. Pull day-ahead prices for DE-LU and **SE4** specifically.
2. Pull cross-border physical flow (DE↔SE4) for the same period.
3. Compute `price_spread = price_SE4 − price_DE-LU` per hour.
4. Compute `flow_utilization = |actual_flow| / ~600 MW` (Baltic Cable's rated capacity) per hour.
5. Compare `price_spread` distribution when `flow_utilization` is near 1 (congested) vs. well below (uncongested) — a simple bucketed comparison (box plot or distribution overlay) tells the core story before any regression.
6. Optional: regress `|price_spread|` against `flow_utilization` directly for a continuous version of the same relationship.
7. Optional: check flow direction — does Sweden mostly export to Germany, or does it vary seasonally (e.g. with German wind output)? This adds a narrative layer about *when* each country needs the other.


**Methodology refinement (decided 2026-09-10, from Phase 2's first eyeballed look):**

- **Analyze both flow directions separately, not pooled.** Build a signed `net_flow = flow(SE_4→DE_LU) − flow(DE_LU→SE_4)` and split the sample by its sign before doing anything else with it. The two directions are opposite-sign effects, not two halves of one story: when `SE_4→DE_LU` is capped, Sweden's price is held *down* (can't export its surplus into the pricier German market — this is the dominant, more frequent direction in the sample: nonzero 42.4% of the time, mean 80.7 MW, vs. `DE_LU→SE_4`'s 24.6%/43.4 MW, consistent with Sweden being the structurally cheaper zone). When `DE_LU→SE_4` is capped, Sweden's price is held *up* instead (blocked from cheap German imports, e.g. during a German wind glut). Pooling both directions without splitting would average these opposite effects together and wash out both — analyze each direction on its own subset.
- **The ~600 MW nameplate capacity is not the right divisor for `flow_utilization`.** Checked directly: in the Phase 2 sample week, physical flow plateaus around 216 MW (`SE_4→DE_LU`) and ~204 MW (`DE_LU→SE_4`) — well under the Baltic Cable's rated 600 MW. Test-pulled `entsoe-py`'s `query_net_transfer_capacity_dayahead()` and `query_offered_capacity()` for this border/period to check for an explicit allocated-capacity figure — both returned `NoMatchingDataError` (this border may not publish those document types, being a merchant/privately-owned HVDC link rather than a standard TSO-to-TSO interconnector; or it's just not published for this specific sample period, unclear which without a longer pull). `query_scheduled_exchanges()` *does* work for this border and its plateau (max exactly 216 MW / ~204 MW) matches the physical flow plateau almost exactly — a strong empirical proxy for the effective operating limit even without an explicit capacity document. **Until a real allocated-capacity series is confirmed available (worth re-testing in Phase 3 with a longer date range), use the observed per-period max flow (or the `query_scheduled_exchanges()` plateau) as the `flow_utilization` denominator instead of a flat 600 constant** — dividing by 600 would systematically understate utilization and miss real congestion events that are actually happening well below nameplate capacity.
- **Capacity re-test (2026-09-25), deferred for now:** re-probed the capacity endpoints for DE_LU↔SE_4 on 2026-09-15. Day-ahead NTC, daily offered capacity and intraday offered capacity still return `NoMatchingDataError`. A likely reason, not verified: the Nordic region moved to flow-based market coupling in late 2024, which doesn't produce a simple per-border NTC. **Week-ahead and month-ahead NTC do return data**, one value per period: 600 MW DE→SE4 and 615 MW SE4→DE, essentially nameplate. `query_scheduled_exchanges(dayahead=True)` returns 15-min schedules. Physical flows in the September test week peak around **420–433 MW**, so the ~217 MW plateau in the January sample was a temporary reduction (maintenance or grid constraints), not a permanent cap. The effective limit varies over time. Options for defining congestion, to decide at the start of Analysis 2: (a) utilization against week-ahead NTC; (b) price-based congestion (in coupled markets, equal DE_LU/SE_4 prices mean the cable isn't binding, but this is circular if the question is whether the spread widens under congestion); (c) an empirical rolling-max capacity estimate. Capacity data isn't pulled yet. Because the pipeline's upsert is idempotent, it can be added as a fourth table later and backfilled.
- **Test statistically, not just by eyeballing a plot.** Bucket congestion via a `flow_utilization` threshold (e.g. `>0.9`) and compare `price_spread` between congested/uncongested groups with `scipy.stats.mannwhitneyu` (non-parametric — power prices are spiky/non-normal, a t-test's assumptions don't hold) rather than eyeballing a box plot alone. Also fit the continuous version already listed as optional in step 6 above — `statsmodels.OLS(spread ~ flow_utilization)` — for a slope/R²/p-value rather than just a two-bucket difference. Caveat that matters for credibility: 15-minute data is heavily autocorrelated, so naive OLS/Mann-Whitney standard errors overstate the evidence (effective independent sample size is much smaller than row count). Phase 2's informal pass can run the naive test with this caveat stated explicitly; this formal Phase 5 version should use HAC-robust standard errors (`statsmodels`, `cov_type='HAC'`, `maxlags` ~96 for a 24h dependency horizon) before trusting any p-value.

---

## 6. Reserve option — synthetic seasonal price curves

Not a core deliverable; an optional add-on if time allows .

- **What it is:** after doing a seasonal decomposition (`statsmodels.STL()` or `seasonal_decompose()`) on either country's day-ahead price series, take the extracted seasonal component and refit it as a smooth continuous curve — regression on day-of-year/hour-of-day terms, or a Fourier series. The fitted curve becomes a "synthetic seasonal price curve": what a naive forward curve would look like if built from historical spot patterns instead of actual traded futures.
- **Where it could plug in:** as a small extension on top of whichever core analysis you do a seasonal decomposition for — not a separate standalone piece. Natural candidates:
  - Applied to DE-LU day-ahead prices, then compared against the same fitted curve for SE4 — do the two countries' seasonal price shapes differ (e.g. Germany's solar-driven midday dip vs. Sweden's winter-heating-driven peak)?
  - Applied on top of the renewable-share analysis: fit separate synthetic curves for high- vs. low-renewable-share periods, to visualize how the shape of the "typical price day" changes with generation mix.
- **Caveat to state explicitly in the writeup:** this is a statistical proxy built from spot data, not a market-derived forward curve (which would require actual traded futures prices). Being upfront about that distinction is itself a good signal on a portfolio piece — it shows you know the difference between the spot and futures markets, which is exactly the domain credibility you're trying to demonstrate.
- **Cost if included:** roughly +1–3 days on top of whichever core analysis it's attached to, per the original brief's modular estimates — skip it entirely if time is short, since both core analyses stand on their own without it.

---

## 7. Updated SQLite schema

Single source is simple and nice. The live version is `db/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS prices (
    zone TEXT NOT NULL,             -- 'DE_LU', 'SE_1', 'SE_2', 'SE_3', 'SE_4'
    timestamp TEXT NOT NULL,
    price_eur_mwh REAL,
    PRIMARY KEY (zone, timestamp)
);

CREATE TABLE IF NOT EXISTS generation (
    zone TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    production_type TEXT NOT NULL,  -- ENTSO-E labels, e.g. 'Wind Onshore', 'Solar', 'Hydro Pumped Storage'
    value_mw REAL,
    PRIMARY KEY (zone, timestamp, production_type)
);

CREATE TABLE IF NOT EXISTS cross_border_flows (
    zone_from TEXT NOT NULL,
    zone_to TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    flow_mw REAL,
    PRIMARY KEY (zone_from, zone_to, timestamp)
);
```

**Design decisions (2026-09-24):**
- **Composite primary keys** make loading idempotent. The pipeline upserts with `INSERT ... ON CONFLICT DO UPDATE`, so re-running over an already-loaded range updates rows instead of duplicating them. This is verified: two runs over the same week give identical row counts.
- **One timestamp format everywhere:** UTC text, `'YYYY-MM-DD HH:MM:SS+00:00'`, produced by `to_utc_str()` in `src/pipeline_utils.py`. ENTSO-E returns local time (CET/CEST), and prices and generation came back with different offsets in the Phase 2 sample. Because keys and joins compare text, the same instant must always produce the same string.
- **`NOT NULL` on key columns:** SQLite allows NULLs in composite primary keys and never treats two NULLs as equal, so a NULL key would slip past the upsert and duplicate on every run. Value columns stay nullable, so a missing value is stored as missing.
- **Raw ENTSO-E production type labels** instead of snake_case. Analysis 1 only needs to know which labels count as wind/solar, and that list can live in the analysis code.

pandas reads from these via `pd.read_sql(query, engine)`, using the shared SQLAlchemy engine from `get_engine()` in `src/pipeline_utils.py`, for the volatility/regression work and the spread/utilization calculations in Section 5. Adding a country later just means more rows in the same three tables — no schema change.

---

## 8. Adding countries later

Easy by design: since day-ahead price and generation-by-type are the same ENTSO-E document types across every zone, adding e.g. France or the Netherlands means:
- Look up the bidding zone code (`entsoe-py` ships the country → EIC code mapping already)
- Add it to the fetch script's zone list
- No new schema, no new parser

---

## 9. Scheduled pipeline

Demonstrate how to build the fetch/pipeline script into a local cron entry (Linux/Mac) or, since this project's
dev environment is Windows, Windows Task Scheduler. This is just to mention scheduling in case of portfolio.

The fun version should I have way too much time on my hands is to migrate the project to a cloud based server and schedule it there.

---

## 10. Rough build order

1. **Phase 1 — manual exploration (complete):** get API access, then prove the mechanics work for all three data shapes at once — day-ahead prices (DE-LU, SE4, SE1), generation-by-source (DE-LU, SE4, reshaped wide→long), and cross-border physical flows (DE-LU↔SE4, both directions) — for one sample week, in `phase_1_exploration/01_entsoe_exploration.ipynb`.
2. **Phase 2 — quality check + first analysis (complete):** cache the sample pull to disk (`data/processed/`, long-format CSVs matching Section 7's schema) so this and later phases stop re-hitting the API on every run; eyeball data quality (missing timestamps, resolution mismatches — note the API returns 15-min intervals, not hourly as earlier assumed — plausibility of generation values); first informal look at `variable_renewable_share` for both countries before the formal regression in Phase 4.
3. **Phase 3 — formalize into SQLite (in progress):** refactor into fetch → transform → load functions writing into the schema in Section 7, reusing the reshape logic from Phase 2. Lands directly in `src/` (see folder-structure note below), not a `phase_3_etl_pipeline/` folder.
   - **Done so far:** `src/pipeline.py` fetches, reshapes and upserts prices for all five zones, generation for DE_LU and SE_4, and flows for DE_LU↔SE_4 in both directions. Run it from the repo root with `python -m src.pipeline`.
   - **Implementation decisions (2026-09-24/25):**
     - **SQLAlchemy** (`create_engine("sqlite:///...")`) instead of stdlib `sqlite3`, for consistency with other ETL work and flexibility in the DB.
     - **Failures stop the run** instead of being skipped and recorded.
     - **`.env` loaded via `python-dotenv`** in `src/entsoe_client.py`.
     - **Zone scopes as named lists** in `src/entsoe_client.py`: `PRICE_ZONES` (all five), `GENERATION_ZONES` (DE_LU, SE_4) and `FLOW_PAIRS` (DE_LU↔SE_4).
4. **Phase 4 — Analysis 1 (volatility vs. renewable share):** the more self-contained of the two core analyses — good to do first. Lands in `analysis/`.
5. **Phase 5 — Analysis 2 (DE–SE transmission price pressure):** pull cross-border flow data, join against the price tables already in SQLite. Lands in `analysis/`.
6. **Phase 6 — polish:** flagship Plotly interactive view; Tableau piece if time allows.
7. **Phase 7 (optional/stretch):** synthetic curves (Section 6); scheduled pipeline (Section 9); additional countries (Section 8).

**Git workflow for Phase 3 (decided 2026-09-04):** Phases 1–2 committed straight to `main`, which is fine for easily-redone exploratory work. Phase 3 is bigger and more disruptive (the folder reorg above, plus building out the real FTL pipeline) and should go through a feature branch instead.
