# Project Brief v2: Germany vs. Sweden — ENTSO-E-Only Build

**Status:** Revised from original SCB+SMARD brief after evaluating data availability. Pivoted to a single-source (ENTSO-E) build.
**Core question:** How does renewable variability relate to price volatility, and how does cross-border transmission capacity between Germany and Sweden shape price convergence/divergence?

---

## 1. Why ENTSO-E only

Original plan paired SCB (Sweden) with SMARD (Germany). Investigating the actual data availability surfaced two problems:

- **Neither SMARD nor Energy-Charts (Fraunhofer ISE) exposes a documented, stable intraday continuous price series.** SMARD's full filter list (from its `openapi.yaml`) only has day-ahead-style "Marktpreis" codes — no intraday. Energy-Charts' officially documented API is day-ahead only; the intraday series that appears on their website is only reachable via undocumented internal chart files or a paid third-party reseller. This killed the original "day-ahead vs. intraday divergence" centerpiece as scoped.
- **ENTSO-E has the same day-ahead-only limitation** (continuous intraday trading doesn't clear at one price per interval, so there's no equivalent document type), but it's the *only* source that gives you **both countries' day-ahead prices and generation-by-source in one consistent schema**, with a stable free API.

Trade-off accepted: you lose some of the "reconciling messy multi-agency data" portfolio flex from the original plan. You gain a much simpler pipeline (one auth step, one XML shape, one SQLite schema) and — importantly — **cheap extensibility**: adding a third country later is a bidding-zone lookup, not a new integration.

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

**Why this is a good centerpiece candidate:** single-country data per test (no cross-source joins needed for this piece), directly testable hypothesis, real mechanism to explain the result either way, and reuses exactly the two ENTSO-E datasets you're already pulling.

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

1. **Phase 1 — manual exploration:** get API access, pull one week of DE-LU day-ahead prices and generation via `entsoe-py`, into pandas, one Seaborn chart. Goal is just proving the mechanics work.
2. **Phase 2 — expand to Sweden:** add SE1–SE4 price and generation pulls. Compute `variable_renewable_share` for both countries.
3. **Phase 3 — formalize into SQLite:** refactor manual scripts into fetch → transform → load functions writing into the schema in Section 7.
4. **Phase 4 — Analysis 1 (volatility vs. renewable share):** the more self-contained of the two core analyses — good to do first.
5. **Phase 5 — Analysis 2 (DE–SE transmission price pressure):** pull cross-border flow data, join against the price tables already in SQLite.
6. **Phase 6 — polish:** flagship Plotly interactive view; Tableau piece if time allows.
7. **Phase 7 (optional/stretch):** synthetic curves (Section 6); scheduled pipeline (Section 9); additional countries (Section 8).

**Time estimate (rough):** single-source, two-country, two-analysis scope — likely comparable to or slightly faster than the original brief's "SE + DE comparison, no ETL/SQL" tier (Section 10 of the original: 2–3.5 weeks solo / 1–1.5 weeks with Claude Code for core-only), since ENTSO-E's uniform schema removes most of the reconciliation overhead that was driving the original estimates up. Add the usual SQL/pipeline formalization time from the original brief's modular table if you want the full ETL layer.
