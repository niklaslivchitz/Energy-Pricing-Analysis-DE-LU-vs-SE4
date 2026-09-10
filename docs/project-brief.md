# Project Brief v3: Germany vs. Sweden — ENTSO-E-Only Build

**Status:** Single-source (ENTSO-E) build, in progress. Phase 1 rescoped and complete — see Section 10.
**Core question:** How does renewable variability relate to price volatility, and how does cross-border transmission capacity between Germany and Sweden shape price convergence/divergence?

---

## 1. Why ENTSO-E only

Originally scoped as a two-source build (SCB for Sweden, SMARD for Germany), but neither exposed a stable intraday price series, which was the original centerpiece. ENTSO-E is the only source giving both countries' day-ahead prices and generation-by-source in one consistent schema, with a stable free API and cheap extensibility to more countries later (a bidding-zone lookup, not a new integration).

---

## 2. Data source: ENTSO-E Transparency Platform

**Access:** Register at transparency.entsoe.eu, then email `transparency@entsoe.eu` requesting RESTful API access (subject: "Restful API access"). Not instant — budget a day or few for the token to come back. Once issued, it's a stable long-lived token.

**Client library:** Use `entsoe-py` (or its maintained fork `python-entsoe`) rather than parsing raw XML by hand. It wraps the IEC 62325 market documents and hands back pandas Series/DataFrames indexed by timestamp — ready to load into SQLite.

**Rate limits:** 400 requests/minute per token. A daily scheduled pull across a handful of zones and series is a non-issue at this volume, even backfilling months of history in one run.

**Datasets you need:**
| Document | What it gives you | entsoe-py method (approx.) |
|---|---|---|
| Day-ahead prices (A44) | Hourly price, EUR/MWh, per bidding zone | `query_day_ahead_prices()` |
| Actual generation per production type (A75) | Hourly generation by source (wind, solar, hydro, nuclear, etc.) per zone | `query_generation()` |
| Cross-border physical flows | Hourly flow between two zones | `query_crossborder_flows()` |
| (Optional) Net transfer capacity / scheduled exchanges | Available/allocated cross-border capacity | `query_net_position()` or similar |

**Bidding zones:**
- Germany: `DE-LU` — single zone, no ambiguity.
- Sweden: split into **SE1–SE4**. For the renewable-share/volatility analysis, decide whether to use one reference zone, an average, or all four (worth pulling all four since it's the same cost per extra zone). For the DE–SE transmission analysis specifically, **use SE4** — see below.

**Eyeballing the data before building:** transparency.entsoe.eu itself renders this data as charts/tables, no key required. Day-ahead prices: Dashboard → Markets → Day-ahead Prices. Generation mix: Dashboard → Generation → Actual Generation per Production Type. Both let you export a CSV sample directly from the browser.

---

## 3. Physical reality check: the DE–SE interconnection

Worth confirming before designing the transmission analysis, since it determines what's actually observable:

- **Baltic Cable** — an existing, operational ~600 MW HVDC link connecting **SE4** (southern Sweden) and Germany, run by Baltic Cable AB (Statkraft). This is the real physical channel your flow/price-pressure analysis will be measuring.
- **Hansa PowerBridge** — a proposed second, larger (700 MW) DE–SE link — **was rejected by the Swedish government in 2024** over concerns it would import volatility from the German market into southern Sweden. It is not being built. So historical and current cross-border capacity between the two countries stays capped at Baltic Cable's ~600 MW for the whole analysis period — don't design around a link that doesn't exist.

This is exactly why **SE4** (not SE3 or a national average) is the right Swedish zone for the transmission-specific analysis: it's the zone Baltic Cable physically connects to.

---

## 4. Core analysis 1 — Volatility vs. renewable share

**Question:** Does a higher share of variable renewables (wind + solar) associate with higher day-ahead price volatility, and does this differ between Germany (wind/solar-heavy) and Sweden (hydro/nuclear-heavy)?

**Methodological note worth stating explicitly in the writeup:** define "renewable share" as **wind + solar specifically**, not all renewables. Hydro (dominant in Sweden) is dispatchable and grid-stabilizing — lumping it in with wind/solar would blur the actual hypothesis, which is about *variable, weather-driven* generation, not renewables in general. This distinction is itself a small finding worth calling out.

**Steps:**
1. Pull hourly day-ahead price and generation-by-source for DE-LU and each Swedish zone.
2. Compute `variable_renewable_share = (wind + solar) / total_generation` per hour, per zone.
3. Compute a volatility measure — rolling standard deviation of price (e.g. 24-hour window) is the simplest, defensible choice.
4. Regress volatility (or `|price change|`) against `variable_renewable_share`, using `statsmodels.ols()` — e.g. `volatility ~ variable_renewable_share + C(country)` to test whether the relationship differs by country, not just whether it exists.
5. Compare the fitted relationship for DE vs. SE — the expected story (higher variable-renewable share → higher volatility, more pronounced in DE than SE) is a clean, testable hypothesis with a real physical explanation behind it (hydro's flexibility dampens what wind/solar variability would otherwise do to price).
6. Optional extension: rolling volatility clustering — does it concentrate around solar ramp times (dawn/dusk) more in DE than SE? `statsmodels.graphics.tsaplots.plot_acf()` for autocorrelation, one line.
7. **Within-day spread (added 2026-09-10):** compute per-day peak-hour minus off-peak-hour price spread, per zone. Standard, cheap, and directly relevant — confirmed via literature (mean and std are consistently higher in peak-hour electricity prices than off-peak across markets) — and likely to show a concrete DE-vs-SE contrast on its own: Germany's solar-driven midday price dip ("duck curve") should show up much more sharply than Sweden's flatter, hydro/nuclear-smoothed profile. Uses data already being pulled, no new source needed.

**Methodology note (decided 2026-09-10):** considered but deliberately excluding **jump/continuous volatility decomposition** (bipower-variation-based separation of realized volatility into a smooth "continuous" component and discrete "jumps," with formal jump-significance testing — the Barndorff-Nielsen & Shephard framework, which does show up in electricity-market literature specifically, e.g. Nord Pool and Japan spot market studies). It's a real, verified technique, not a made-up idea — but it's meaningfully heavier (realized-variation math, jump test statistics, significance-threshold judgment calls) than this project's core question needs. Worth a one-line mention by name in the final writeup as a "known more rigorous approach, out of scope here," to signal domain awareness without taking on the implementation cost. The simple rolling-std volatility measure (step 3) plus the peak/off-peak spread (step 7) are sufficient to answer the actual hypothesis.

**Why this is a good centerpiece candidate:** single-country data per test (no cross-source joins needed for this piece), directly testable hypothesis, real mechanism to explain the result either way, and reuses exactly the two ENTSO-E datasets you're already pulling.

**Phase 2 exploratory finding (2026-09-10, provisional):** the sample-week first-look came back the *opposite* sign from the hypothesis above. Spearman correlation between `variable_renewable_share` and 24h rolling price volatility, computed in `phase_2_quality_and_first_analysis/phase_2_quality_analysis.ipynb`: **DE_LU ≈ −0.50, SE_4 ≈ −0.57**. More renewables associated with *lower* volatility in this sample, not higher.

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

**Framing note:** this is a much more concrete, physically-grounded version of the original brief's "cross-border flow story," and it no longer needs a 2–3 country reconciliation — it's two zones you already have from the same source.

**Methodology refinement (decided 2026-09-10, from Phase 2's first eyeballed look):**

- **Analyze both flow directions separately, not pooled.** Build a signed `net_flow = flow(SE_4→DE_LU) − flow(DE_LU→SE_4)` and split the sample by its sign before doing anything else with it. The two directions are opposite-sign effects, not two halves of one story: when `SE_4→DE_LU` is capped, Sweden's price is held *down* (can't export its surplus into the pricier German market — this is the dominant, more frequent direction in the sample: nonzero 42.4% of the time, mean 80.7 MW, vs. `DE_LU→SE_4`'s 24.6%/43.4 MW, consistent with Sweden being the structurally cheaper zone). When `DE_LU→SE_4` is capped, Sweden's price is held *up* instead (blocked from cheap German imports, e.g. during a German wind glut). Pooling both directions without splitting would average these opposite effects together and wash out both — analyze each direction on its own subset.
- **The ~600 MW nameplate capacity is not the right divisor for `flow_utilization`.** Checked directly: in the Phase 2 sample week, physical flow plateaus around 216 MW (`SE_4→DE_LU`) and ~204 MW (`DE_LU→SE_4`) — well under the Baltic Cable's rated 600 MW. Test-pulled `entsoe-py`'s `query_net_transfer_capacity_dayahead()` and `query_offered_capacity()` for this border/period to check for an explicit allocated-capacity figure — both returned `NoMatchingDataError` (this border may not publish those document types, being a merchant/privately-owned HVDC link rather than a standard TSO-to-TSO interconnector; or it's just not published for this specific sample period, unclear which without a longer pull). `query_scheduled_exchanges()` *does* work for this border and its plateau (max exactly 216 MW / ~204 MW) matches the physical flow plateau almost exactly — a strong empirical proxy for the effective operating limit even without an explicit capacity document. **Until a real allocated-capacity series is confirmed available (worth re-testing in Phase 3 with a longer date range), use the observed per-period max flow (or the `query_scheduled_exchanges()` plateau) as the `flow_utilization` denominator instead of a flat 600 constant** — dividing by 600 would systematically understate utilization and miss real congestion events that are actually happening well below nameplate capacity.
- **Test statistically, not just by eyeballing a plot.** Bucket congestion via a `flow_utilization` threshold (e.g. `>0.9`) and compare `price_spread` between congested/uncongested groups with `scipy.stats.mannwhitneyu` (non-parametric — power prices are spiky/non-normal, a t-test's assumptions don't hold) rather than eyeballing a box plot alone. Also fit the continuous version already listed as optional in step 6 above — `statsmodels.OLS(spread ~ flow_utilization)` — for a slope/R²/p-value rather than just a two-bucket difference. Caveat that matters for credibility: 15-minute data is heavily autocorrelated, so naive OLS/Mann-Whitney standard errors overstate the evidence (effective independent sample size is much smaller than row count). Phase 2's informal pass can run the naive test with this caveat stated explicitly; this formal Phase 5 version should use HAC-robust standard errors (`statsmodels`, `cov_type='HAC'`, `maxlags` ~96 for a 24h dependency horizon) before trusting any p-value.

---

## 6. Reserve option — synthetic seasonal price curves

Not a core deliverable; an optional add-on if time allows and you want to nod toward your futures/forward-curve background specifically.

- **What it is:** after doing a seasonal decomposition (`statsmodels.STL()` or `seasonal_decompose()`) on either country's day-ahead price series, take the extracted seasonal component and refit it as a smooth continuous curve — regression on day-of-year/hour-of-day terms, or a Fourier series. The fitted curve becomes a "synthetic seasonal price curve": what a naive forward curve would look like if built from historical spot patterns instead of actual traded futures.
- **Where it could plug in:** as a small extension on top of whichever core analysis you do a seasonal decomposition for — not a separate standalone piece. Natural candidates:
  - Applied to DE-LU day-ahead prices, then compared against the same fitted curve for SE4 — do the two countries' seasonal price shapes differ (e.g. Germany's solar-driven midday dip vs. Sweden's winter-heating-driven peak)?
  - Applied on top of the renewable-share analysis: fit separate synthetic curves for high- vs. low-renewable-share periods, to visualize how the shape of the "typical price day" changes with generation mix.
- **Caveat to state explicitly in the writeup:** this is a statistical proxy built from spot data, not a market-derived forward curve (which would require actual traded futures prices). Being upfront about that distinction is itself a good signal on a portfolio piece — it shows you know the difference between the spot and futures markets, which is exactly the domain credibility you're trying to demonstrate.
- **Cost if included:** roughly +1–3 days on top of whichever core analysis it's attached to, per the original brief's modular estimates — skip it entirely if time is short, since both core analyses stand on their own without it.

---

## 7. Updated SQLite schema

Single source simplifies this considerably versus the original two-agency plan — one normalized shape covers everything:

```sql
CREATE TABLE prices (
    zone TEXT,           -- 'DE-LU', 'SE1', 'SE2', 'SE3', 'SE4'
    timestamp TEXT,       -- ISO 8601, UTC
    price_eur_mwh REAL
);

CREATE TABLE generation (
    zone TEXT,
    timestamp TEXT,
    production_type TEXT, -- 'wind_onshore', 'wind_offshore', 'solar', 'hydro', 'nuclear', etc.
    value_mw REAL
);

CREATE TABLE cross_border_flows (
    zone_from TEXT,
    zone_to TEXT,
    timestamp TEXT,
    flow_mw REAL
);
```

pandas reads from these via `pd.read_sql(query, conn)` for the volatility/regression work and the spread/utilization calculations in Section 5. Adding a country later just means more rows in the same three tables — no schema change.

---

## 8. Adding countries later

Deliberately easy by design of this pivot: since day-ahead price and generation-by-type are the same ENTSO-E document types across every zone, adding e.g. France or the Netherlands means:
- Look up the bidding zone code (`entsoe-py` ships the country → EIC code mapping already)
- Add it to the fetch script's zone list
- No new schema, no new parser, no new auth

Per-zone judgment calls repeat (some countries split into multiple bidding zones — Norway NO1–NO5, Italy, Denmark DK1/DK2), and historical depth varies slightly by zone, but neither is a structural problem. This is also what makes the original brief's "cross-border flow story" stretch goal much more approachable now — flow-between-zones uses the same query pattern with two zone codes instead of one.

---

## 9. Scheduled pipeline (optional, Section 6 of original brief)

If you want the live-refresh nice-to-have:
- ENTSO-E's rate limit (400 req/min) is a non-issue for a daily scheduled pull.
- The one real setup cost is the API-key email registration — one-time, do it early since turnaround isn't instant.
- **GitHub Actions runners are stateless** — your SQLite file won't persist between scheduled runs unless the workflow commits the updated `.db` file back to the repo at the end of each run. Simplest fix for this project's scope; worth deciding upfront so it's not a surprise later.

---

## 10. Rough build order

1. **Phase 1 — manual exploration (rescoped, complete):** get API access, then prove the mechanics work for all three data shapes at once — day-ahead prices (DE-LU, SE4, SE1), generation-by-source (DE-LU, SE4, reshaped wide→long), and cross-border physical flows (DE-LU↔SE4, both directions) — for one sample week, in `phase_1_exploration/01_entsoe_exploration.ipynb`. Sweden's price/generation pulls, originally slated for Phase 2, happened here instead since there was no reason to wait.
2. **Phase 2 — quality check + first analysis (rescoped from "expand to Sweden," now redundant per above):** cache the sample pull to disk (`data/processed/`, long-format CSVs matching Section 7's schema) so this and later phases stop re-hitting the API on every run; eyeball data quality (missing timestamps, resolution mismatches — note the API returns 15-min intervals, not hourly as earlier assumed — plausibility of generation values); first informal look at `variable_renewable_share` for both countries before the formal regression in Phase 4.
3. **Phase 3 — formalize into SQLite:** refactor into fetch → transform → load functions writing into the schema in Section 7, reusing the reshape logic and cached CSVs from Phase 2 rather than re-deriving it. Lands directly in `src/` (see folder-structure note below), not a `phase_3_etl_pipeline/` folder.
4. **Phase 4 — Analysis 1 (volatility vs. renewable share):** the more self-contained of the two core analyses — good to do first. Lands in `analysis/`.
5. **Phase 5 — Analysis 2 (DE–SE transmission price pressure):** pull cross-border flow data, join against the price tables already in SQLite. Lands in `analysis/`.
6. **Phase 6 — polish:** flagship Plotly interactive view; Tableau piece if time allows.
7. **Phase 7 (optional/stretch):** synthetic curves (Section 6); scheduled pipeline (Section 9); additional countries (Section 8).

**Folder structure going forward (decided 2026-09-04):** Phase 1/2's `phase_1_exploration/` and `phase_2_quality_and_first_analysis/` were genuinely exploratory scaffolding — no reason to preserve them as real project structure; they get dropped once no longer needed (git history keeps every version, so no separate archive copy is needed). Phase 3 onward is the *permanent* code, so it lands directly in its final home instead of another disposable `phase_N_*/` folder:
- `src/` — the ETL pipeline (current `common/` + `phase_3_etl_pipeline/pipeline.py` collapse into here)
- `analysis/` — the two core analyses (current `phase_4_.../` + `phase_5_.../` collapse into here)
- `db/`, `data/`, `docs/`, `sql/`, `outputs/` — unchanged

A curated EDA notebook may get added under `notebooks/` in Phase 6 as a portfolio piece, but that's a deliberate late addition, not a preserved copy of the Phase 1 exploration notebook.

**Git workflow for Phase 3 (decided 2026-09-04):** Phases 1–2 committed straight to `main`, which is fine for low-stakes, easily-redone exploratory work. Phase 3 is bigger and more disruptive (the folder reorg above, plus building out the real fetch → transform → load pipeline) and should go through a feature branch instead — partly practical (keeps `main` working throughout), partly a deliberate portfolio signal that the standard branch/PR workflow is understood. Plan: branch off `main` (e.g. `phase-3-pipeline`), do the reorg and pipeline work there, push, open a PR (`gh pr create`) with a real description, self-review the diff on GitHub, merge via **squash and merge**, then delete the branch.

**Time estimate (rough):** single-source, two-country, two-analysis scope — likely comparable to or slightly faster than the original brief's "SE + DE comparison, no ETL/SQL" tier (Section 10 of the original: 2–3.5 weeks solo / 1–1.5 weeks with Claude Code for core-only), since ENTSO-E's uniform schema removes most of the reconciliation overhead that was driving the original estimates up. Add the usual SQL/pipeline formalization time from the original brief's modular table if you want the full ETL layer.
