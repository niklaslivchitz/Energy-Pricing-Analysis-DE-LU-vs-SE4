# Project Plan (condensed)

Full original brief lives in your project files as `energy-data-project-brief.md` — this is the
working summary so you don't have to re-read the whole thing every session.

**Pivot from the original brief:** the brief assumed a symmetric SE + DE comparison from the
start. In practice, SCB (Sweden) only has end-consumer prices, not exchange/spot prices — the
actual Nordic exchange, Nord Pool, has free day-ahead data but intraday is a paid product. SMARD
(Germany) is the only source with both day-ahead AND intraday free and keyless. So the project
now builds the full core (Phases 1-5) around Germany/SMARD alone, and packages Sweden (SCB +
Nord Pool day-ahead) together with the cross-border flow story (needs ENTSO-E) as one bundled
stretch module — since both need a second country to be meaningful anyway. See README.md for
the folder-level version of this.

## The core story

**Centerpiece: day-ahead vs. intraday price divergence.**
`spread = intraday_price − day_ahead_price` per delivery hour. This is spread/basis analysis,
not forward-curve analysis — day-ahead is electricity's de facto spot price, intraday is the
continuous correction window as forecasts (especially wind/solar) improve. Divergence ≈ realized
forecast-error risk premium, which ties directly back to your bundled-contract pricing background.

Follow-on questions that fall out of the centerpiece naturally (not separate projects):
- Spread magnitude vs. renewable share / hour-of-day (`statsmodels.ols()`)
- Spread volatility clustering over time (rolling std — dawn/dusk solar ramps? seasonal?)
- Autocorrelation of the spread (`plot_acf()`)

Secondary/companion angles, core build (DE only, no second country needed):
- Seasonal decomposition of day-ahead prices (`STL()` / `seasonal_decompose()`)
- **Optional add-on:** refit the extracted seasonal component as a synthetic seasonal price curve
  (regression on day-of-year/hour terms, or Fourier series) — explicitly labeled as a statistical
  proxy, not a real forward curve, since real forward curves need actual futures data.

Stretch angles, Phase 6 only (need Sweden data / ENTSO-E):
- Household price trend, SE vs. DE (most accessible, least technical — good companion piece)
- Energy mix vs. price stability (hydro/nuclear SE vs. wind/solar/lignite DE — storytelling intro)
- Cross-border flow story (needs ENTSO-E) — does DE import cheap Nordic hydro/wind during low
  German wind, and does that show up as intraday price convergence between the two markets?
- Aligning SCB's and SMARD's very different formats/units/timestamps into one schema is itself
  part of the value here — the cross-comparison exercise, not a second spread analysis, is the
  actual point of including Sweden at all.

**Where NOT to use regression:** don't try to forecast next-day prices as if it'll actually work —
energy prices are non-linear/regime-dependent and a simple linear model will visibly underperform.
If you want a forecasting angle, frame it explicitly as a naive baseline that shows its own limits.

## Data sources

### Core (Phases 1–5) — Germany only

| Source | Covers | Auth | Format | Notes |
|---|---|---|---|---|
| SMARD | DE day-ahead/intraday prices, generation by source, load, hourly, back to 2015 | None | JSON | Numeric filter codes are opaque — use `smard.api.bund.dev` / `bundesAPI/smard-api` as the reference |
| Destatis GENESIS-Online | DE annual/macro energy balance | None | Tabular | German-language labels, less granular — background/context only |

### Stretch (Phase 6) — Sweden + cross-border

| Source | Covers | Auth | Format | Notes |
|---|---|---|---|---|
| SCB PxWebApi **v2** | Sweden end-consumer prices + energy balance | None | JSON-stat | v1 sunsets end of 2026 — build on v2 only. No spot/exchange prices available here. |
| Nord Pool (free endpoint) | SE day-ahead spot prices | None (unofficial, undocumented) | JSON | `dataportal-api.nordpoolgroup.com/api/DayAheadPrices` — no auth, community-verified via Home Assistant's integration. Day-ahead only; intraday is a paid Nord Pool product (~€3-5.5k/yr redistribution), not worth pursuing for a portfolio piece. Not officially supported — don't build the scheduled/live pipeline on it without a fallback. |
| ENTSO-E Transparency | Pan-EU prices/flows | Free API key (email signup) | XML | Needed for the cross-border flow story specifically |

## Build order (matches the folder structure)

1. **Phase 1 — touch SMARD once.** One series, into pandas, one Seaborn chart. Goal is just
   proving the mechanics work, not insight yet.
2. **Phase 2 — first real DE analysis.** Price volatility vs. renewable share is the suggested
   first target — single source, no cross-source joining needed.
3. **Phase 3 — formalize into ETL + SQLite.** Refactor working scripts into fetch → transform →
   load, writing into a local SQLite db with a shared schema (`timestamp, country, metric, value,
   unit`). Schema is deliberately multi-country-ready even though only DE data lands in it for
   now — that's what makes Phase 6 a genuine plug-in later instead of a rebuild.
4. **Phase 4 — the centerpiece.** Day-ahead vs. intraday spread analysis and its direct
   follow-ons (all DE): magnitude vs. renewable share, volatility clustering, autocorrelation.
   Seasonal decomposition too, as its own item.
5. **Phase 5 — polish.** One flagship interactive Plotly view; static Tableau piece if time allows
   (Tableau's cost is fixed regardless of Python skill — it's GUI-driven, Claude helps least there).
6. **Phase 6 — stretch, optional, bundled.** Sweden module (SCB + Nord Pool day-ahead) AND
   ENTSO-E cross-border flow story, done together — both need a second country to be meaningful,
   and both write into the same schema Phase 3 already defined.

## Why the ETL/SQL layer isn't scope creep

DA vs. DS distinction that matters to employers: DS = predictive modeling, DA = getting messy
real data into a queryable/visualizable state. Fetch → clean → load into SQLite is squarely DA
("data plumbing"), and SQL is one of the most commonly requested DA skills in job postings — the
overlap strengthens the DA framing rather than diluting it.

## Time budget (with an assistant driving alongside you, non-agentic)

| Scope | Estimate |
|---|---|
| Core only (Phases 1–2, no SQL/ETL/Tableau) | 1–1.5 weeks |
| + SQL (Phase 3, no scheduled pipeline) | 1.5–2 weeks |
| + ETL formalized (Section 7/8 as written) | 2–3 weeks |
| + Tableau piece | +2–4 days on top |
| + scheduled pipeline (Phase 6) | +1–2 days on top |
| Full build, everything | 3–4.5 weeks |

**Protect Phase 4** (the comparative analysis — the actual insight deliverable) if time gets tight.
Phase 3's ETL refactor is the biggest optional time sink relative to what it adds; it's valuable
for the SQL story but skippable if you need to cut scope.

## Libraries — plug-and-play, no hand-rolled math

- `statsmodels` — `seasonal_decompose()`/`STL()` for decomposition, `ols()` with formula strings
  for regression-with-dummies (e.g. `price ~ renewable_share + C(month)`), `plot_acf()` for
  autocorrelation.
- `scikit-learn`'s `LinearRegression` — simpler API for plain trend/renewable-share regressions
  where you don't need statsmodels' p-values/confidence intervals.
- Skip SageMath — built for symbolic math, not applied stats on messy real data; not the right
  tool here even though it's tempting given your background.
