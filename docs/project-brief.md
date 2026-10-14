# Project Brief v3

**Status:** Test data pulled and tentatively analyzed, the full project is go to build. The ETL pipeline is done, pulling and storing generation, transmission and pricing data for SE4 and DE-LU. It's built so more markets are easy to add without touching the database. SQLite is up and running. Analysis 1 (price swings vs. wind and solar) is done, see Section 4. Analysis 2 (the cable) is done, see Section 5. Next: the findings report and the Tableau dashboard.
**Core question:** How does the share of wind and solar power relate to how much prices jump around, in Germany and Sweden? And how does the cable between Germany and Sweden affect whether their prices move together or apart?

---

## 1. Why ENTSO-E

Only source that gives both countries' prices and generation in the same format, with a free API. Adding more countries later is just a zone code.

---

## 2. Data source: ENTSO-E Transparency Platform

**Access:** Register at transparency.entsoe.eu, then email `transparency@entsoe.eu` asking for API access (subject: "Restful API access").

**Python library:** `entsoe-py`

**Rate limits:** 400 requests/minute per key. Not an issue for this project.

**Datasets:**
| Data | What it gives | entsoe-py function |
|---|---|---|
| Day-ahead prices | Price in EUR/MWh every 15 min, per zone | `query_day_ahead_prices()` |
| Actual generation per type | MW produced every 15 min by each source (wind, solar, hydro, nuclear, etc.) per zone | `query_generation(..., nett=True)` |
| Cross-border flows | MW flowing between two zones every 15 min, one direction per call | `query_crossborder_flows()` |
| Cable outages and maintenance (added 2026-10-13) | One record per outage: start, end, and how many MW the cable could still carry | `query_unavailability_transmission()` |
| (Optional, not pulled) Planned exchange | The planned trade over the cable | `query_scheduled_exchanges()` |

**15-minute data (checked 2026-09-25):** the data comes in 15-minute steps, not hourly like this brief first assumed. Each data type switched from hourly to 15-min on a different date:

| Data | Hourly until | 15-min from |
|---|---|---|
| Day-ahead prices (DE_LU, SE_4) | 2025-09-30 | 2025-10-01 (the European day-ahead market switched to 15-min then) |
| Cross-border flows (DE_LU↔SE_4) | 2025-09-29 | 2025-09-30 |
| Generation DE_LU | — | 15-min the whole time |
| Generation SE_4 | 2025-12-01 | 2025-12-02 |

**Decision (2026-09-25): pull the last year, but never earlier than 2025-12-02.** That's the first date where everything is 15-min.
- **`end`** = today at midnight, Berlin time.
- **`start`** = whichever is later: one year before `end`, or 2025-12-02.

What this means over time:
- **Until December 2026** we get about 10 months. October and November are missing, so we don't see a full year of seasons yet. Mention this in the write-up if seasons come up.
- **From December 2026** it's a full year automatically, no code change needed.
- **Everything is always 15-min,** so we never have to mix hourly and 15-min data.
- **Other option we dropped:** pull a full year and store the older part as hourly. Gives all seasons now, but every analysis would have to deal with two different time steps.

**Price zones:**
- Germany: `DE-LU`, one zone.
- Sweden: split into **SE1–SE4**. Prices are pulled for all four (cheap), generation and flows only for **SE4**, the zone the Baltic Cable connects to — see below.

---

## 3. Reality check: the cable between Germany and Sweden

- **Baltic Cable:** an existing ~600 MW power cable between **SE4** (southern Sweden) and Germany, run by Baltic Cable AB (Statkraft). This is what the flow analysis measures.
- **Hansa PowerBridge:** a planned second, bigger (700 MW) cable. **The Swedish government said no in 2024,** worried it would bring German price swings into southern Sweden.

That's why **SE4** is the right Swedish zone for the cable analysis: it's the zone the Baltic Cable actually plugs into. Lets leave the analysis of swedish internal transmission to another day.

---

## 4. Core analysis 1 — Price swings vs. wind and solar share

**Question:** When wind and solar make up more of the power mix, do prices jump around more? And is that different in Germany (lots of wind/solar) and Sweden (lots of hydro/nuclear)?

**Note for the write-up:** "renewable share" here means **wind + solar only**, not all renewables. Hydro (big in Sweden) can be turned up and down on demand and actually calms the grid. Counting it with wind and solar would mix two different things. The question is about weather-driven power.

**Steps:**
1. Load prices and generation for DE-LU and SE4 from the database (15-min).
2. Compute `variable_renewable_share = (wind + solar) / total_generation` for every 15 min, per zone.
3. Measure how much prices jump around: the standard deviation of the price over the last 24 hours (96 values), recalculated every 15 min. A common and simple measure in the energy sector.
4. Regression with `statsmodels`: `volatility ~ variable_renewable_share + C(country)`, to test both whether there is a relationship and whether it differs between the countries.
5. Compare Germany and Sweden. The expected result: more wind/solar → more price swings, stronger in Germany than Sweden. There's a real physical reason behind this, so it's a clean thing to test.
6. Optional: do the price swings bunch up around sunrise and sunset (when solar ramps up and down), more in Germany than Sweden?
7. **Daily price gap (added 2026-09-10):** per day, the price at the most expensive hours minus the cheapest hours, per zone. Simple and likely to show a clear DE vs. SE difference: Germany's midday price dip from solar ("duck curve") should be much sharper than Sweden's flatter prices. Uses data we already have.

**Result (2026-10-09, data from 2025-12-02 to 2026-10-05):** done in `analysis/volatility_renewable_share.py`. Tables are in `outputs/tables/`, charts in `outputs/figures/`.

What changed from the steps above:
- **One value per day instead of a rolling window.** Volatility is the standard deviation of the 96 prices within a day, and the shares are daily averages. The rolling 24-hour windows overlap almost completely, so they gave trails instead of separate observations.
- **Wind and solar are split.** The combined share showed almost nothing (correlation +0.25 in DE_LU, −0.05 in SE_4), because wind and solar work in opposite directions and cancel out.
- **Negative pumped storage is set to zero** before summing total generation. Pumping uses power, it isn't generation.

What came out (regressions with HAC standard errors, 7 daily lags):
- **Solar goes with bigger price swings in Germany.** Correlation +0.74. 10 percentage points more solar goes with about 18 EUR/MWh more volatility (p < 0.001). Still there with the month as a control (about 23 EUR/MWh) and with the logarithm of volatility, so it isn't just the season or a few extreme days.
- **Wind shows no effect in Germany** once solar is in the model (p = 0.86). The −0.34 correlation for wind comes from windy days being less sunny.
- **In SE_4 the solar effect is a third as big, and it's gone with the month as a control** (p = 0.75), so there it was the season. Within a month, windier days in SE_4 have calmer prices (about 3.4 EUR/MWh less per 10 points of wind, p = 0.002).
- **The difference between the zones is real** for solar (p < 0.001 in the pooled model), not for wind (p = 0.24).
- **The mechanism shows in the average day:** prices dip at 13:00 local time in both zones. Germany averages about 43 EUR/MWh at 13:00 and 166 at 20:00.

Two things that weren't expected:
- **SE_4 has the higher wind and solar share** (71% of what it generates, against 47% in Germany). The question above assumed the opposite. Sweden's hydro and nuclear are further north; SE_4 itself generates little, mostly wind, and imports much of its power. So its local share explains less of its price (R² 0.17 against 0.49 for Germany).
- **SE_4 has the same midday price dip as Germany,** with almost no solar of its own. The dip comes in over the cables, which is where Analysis 2 picks up.

Limits: about ten months of data with no November, the share is of local generation only, and these are relationships in the data, not proof of cause.

**Earlier first look from the Phase 2 sample week (2026-09-10, replaced by the result above):** the result came out the *opposite* way from the hypothesis. The correlation between wind/solar share and price swings was **DE_LU ≈ −0.50, SE_4 ≈ −0.57**: more wind and solar went with *calmer* prices, not wilder ones. (Done in the Phase 2 notebook, `archive/phase_2_quality_and_first_analysis/phase_2_quality_analysis.ipynb`, local only now and still in git history.)

Then ran a regression on the same data, twice:
- **Normal regression:** everything looked highly significant (p < 0.001).
- **Corrected regression (HAC standard errors):** needed because the 24-hour windows overlap, so each value is almost the same as the one before it. That makes a normal regression far too confident. The Durbin-Watson test showed this clearly (0.004, where ~2 would be fine).

After the correction:
- **Wind/solar share still mattered** (p = 0.014): a real, but weaker, negative relationship.
- **The country differences did not** (p = 0.449 and p = 0.969): Germany and Sweden don't seem to behave differently.

**Why it didn't hold:** it was one January week, when almost all of the wind and solar share is wind. The full data shows the negative link belongs to wind, and solar goes the other way.

---

## 5. Core analysis 2 — Does the cable keep German and Swedish prices together?

**Question:** Do German and SE4 prices drift apart when the Baltic Cable is full, and stay together when it has room to spare?

The logic: when a cable connects two markets, power flows from the cheap side to the expensive side until the prices match. That only works while the cable has spare room. Once it's full, the prices can drift apart.

**Steps:**
1. Load DE-LU and **SE4** prices from the database.
2. Load the cable flows (DE↔SE4) for the same period.
3. Compute `price_spread = price_SE4 − price_DE-LU` every 15 min.
4. Compute `flow_utilization = |flow| / capacity` every 15 min, i.e. how full the cable is. The capacity comes from the outage records, see the result below.
5. Compare the price gap when the cable is (nearly) full vs. when it isn't. A box plot shows the main story before any statistics.
6. Optional: a regression of `|price_spread|` on `flow_utilization`.
7. Optional: which way does power mostly flow, and does it change with the seasons (e.g. with German wind)? Shows *when* each country needs the other.

**Methodology notes (from the Phase 2 first look, 2026-09-10):**

- **Look at the two flow directions separately.** They have opposite effects:
  - **Sweden → Germany cable full:** Sweden can't sell its cheap power to Germany, so the Swedish price stays *low*. This is the common direction (flowing 42.4% of the time in the sample, 80.7 MW on average), which makes sense since Sweden is usually cheaper.
  - **Germany → Sweden cable full:** Sweden can't buy cheap German power (e.g. on very windy days in Germany), so the Swedish price stays *high* (24.6% of the time, 43.4 MW on average).

  Mixing both directions would cancel the two effects out. So: compute `net_flow = flow(SE_4→DE_LU) − flow(DE_LU→SE_4)` and split the data by whether it's positive or negative.
- **(Older note, replaced by the re-test below.) Dividing by 600 MW is probably wrong.** In the January sample week, the flow never went above ~216 MW (SE→DE) and ~204 MW (DE→SE), way under the cable's 600 MW. ENTSO-E didn't return an official "allowed capacity" number for this cable for that week. The planned exchange (`query_scheduled_exchanges()`) did work, and topped out at the same ~216 / ~204 MW. Idea at the time: use the highest observed flow as the capacity instead of 600.
- **Capacity re-test (2026-09-25), parked for now:** tested again for 2026-09-15.
  - **No daily capacity numbers** for this cable. A guess (not checked): the Nordic market changed how it hands out cable capacity in late 2024, so there's no simple number per cable anymore.
  - **Weekly and monthly capacity numbers do exist,** but they're basically just the max: 600 MW DE→SE4, 615 MW SE4→DE.
  - **15-min planned exchange** is available (`query_scheduled_exchanges(dayahead=True)`).
  - **The flow went up to 420–433 MW in September,** so the ~217 MW limit in January was temporary (maintenance or grid problems), not permanent. The real limit changes over time.

  Options for deciding when the cable counts as "full", to pick when Analysis 2 starts:
  - (a) flow compared to the weekly capacity numbers;
  - (b) the prices themselves: if DE and SE4 prices are exactly equal, the cable wasn't full. Catch: that's circular if the question is whether full cables cause price gaps;
  - (c) estimate the limit from the data, e.g. the highest flow in each week.

  Capacity data isn't pulled yet. It can be added later as a fourth table, and old data filled in, without breaking anything.
- **Test with statistics, not just a plot.**
  - Split into "full" / "not full" (e.g. `flow_utilization > 0.9`) and compare the price gap with a Mann-Whitney U test (`scipy.stats.mannwhitneyu`). Power prices have extreme spikes, so a t-test isn't a good fit.
  - Also run the regression from step 6, `spread ~ flow_utilization`, for a slope and p-value.
  - Same catch as Analysis 1: each 15-min value is very similar to the one before, so normal p-values look much better than they really are. Use the corrected version (`cov_type='HAC'`, `maxlags` ~96 = 24 hours) before trusting a p-value.

**Result (2026-10-13, data from 2025-12-02 to 2026-10-12):** done in `analysis/transmission_price_pressure.py`. Tables are in `outputs/tables/cable/`, charts in `outputs/figures/` (names start with `cable_`).

What changed from the steps above:
- **Three states instead of "full / not full".** Every 15 minutes the cable is out of service (39% of the time), full (39%) or partly used (23%).
- **"Full" is measured against the capacity that was available at the time,** taken from the outage records, not against 600 MW. Flows of 400 MW and more also count as full.
- **The test runs on daily values,** like in Analysis 1: the average price gap of the day against the share of the day the cable was full or out. HAC standard errors with 14 daily lags, because outages last for weeks.

What came out:
- **With spare room on the cable, the two prices are almost the same.** The typical (median) gap is 1.9 EUR/MWh. With the cable full it is 22.7, with the cable out 15.8.
- **A day with the cable full all day has a gap about 40 EUR/MWh bigger** than a day with spare room all day (month as a control, p < 0.001, between 28 and 53).
- **A day with the cable out has a gap about 36 EUR/MWh bigger** (between 27 and 46). So a full cable separates the two markets about as much as a missing one.
- **Still there with the logarithm of the gap,** so it isn't a few extreme days.
- **Direction, full towards Germany:** Sweden is cheaper, typically by 27 EUR/MWh. Clear in the daily test as well (about 45 EUR/MWh, p < 0.001). This is the common direction, 3.5 times as often as the other.
- **Direction, full towards Sweden:** Sweden is more expensive, typically by 12 EUR/MWh. The daily test has the right sign but can't tell it from zero (p = 0.22). It happens mostly between 11:00 and 14:00, so it lasts a few hours and disappears in a daily average.
- **The link to Analysis 1:** the cable fills towards Sweden around midday, when German solar pushes the German price down, and towards Germany in the evening and at night.
- **With the cable out, Sweden is the cheaper side** (about 21 EUR/MWh on average). It's the zone that would have been exporting.

Limits:
- **About ten months, two long outages.** There are 119 outage days, but they come from very few separate events. July and August are outage only, so for those months the outage and the season can't be told apart.
- **Some limits are not in the outage records.** On 5 October the flow sat at about 300 MW with a gap of over 100 EUR/MWh, and that counts as "partly used". This makes the difference between the groups look smaller, not bigger.
- **The cable state explains part of the gap, not all of it** (R² 0.17 without and 0.37 with the month). The rest is how different the two markets are on a given day.
- See the note on the other connections below for how to word the result.

**Notes on method and wording (2026-10-13):**

- **The capacity question is answered: use the outage records.** ENTSO-E publishes outages and maintenance for the cable (`query_unavailability_transmission()` in `entsoe-py`), each with a start, an end and the capacity that was still available. Turned into one value per 15 minutes, that gives the capacity to divide the flow by. This replaces options (a) to (c) above.
- **The cable was never at its full 600 MW in our data.**
  - 4 Nov 2025 to 19 Apr 2026: a fault limited it to about 204 MW towards Sweden and 216 MW towards Germany. So the ~217 MW plateau was a full cable.
  - 20 Apr to about 22 May 2026, and 22 Jun to 14 Sep 2026: completely out of service.
  - After 14 Sep 2026: about 420 to 430 MW. The outage records mostly don't show this limit, so flows of 400 MW and more are counted as full as well (the highest flow in the data is 433 MW).
- **Three states instead of two:** out of service (40% of the time), full (39%), partly used (21%).
- **The other connections matter for how to word the result.** SE4 is also connected to eastern Denmark, Poland and Lithuania, and Germany to both Danish zones. So the two markets are not cut off from each other when the Baltic Cable is down.
  - What the data shows: when this cable is full or out, the price gap is large. With spare room, the gap almost disappears.
  - What it doesn't show: that this one cable is what keeps the prices together. A full cable is partly a *result* of a price gap, not only a cause: power is sent from the cheap side to the expensive side until the prices meet or the cable is full.
  - More likely: when the gap is big enough to fill the Baltic Cable, the other routes are full in the same direction too. The whole border region is congested, and this cable is the one we measure.
  - The outage comparison is the stronger evidence, because unplanned outages don't happen because of prices. Still, nobody knows what the gap would have been on those days with the cable working.
- **Open question for later:** add the SE4 connections to Denmark, Poland and Lithuania (`FLOW_PAIRS`) and the eastern Danish price zone, and check whether those are also at their limits when the gap is large. Not part of this analysis.

---

## 6. Reserve option — typical price curves by season

Not a core part; an optional add-on if time allows.

- **What it is:** split the price series into trend, seasonal pattern and noise (`statsmodels` `STL()` or `seasonal_decompose()`). Then fit a smooth curve to the seasonal part. That gives a "typical price curve": roughly what a futures price curve would look like if you built it from past prices instead of real futures trades.
- **Where it could fit:** as a small extra on top of one of the core analyses, not on its own. For example:
  - Compare the typical price curve for DE-LU and SE4: do Germany (solar dip at midday) and Sweden (winter heating peak) have different shapes?
  - Fit separate curves for days with a lot vs. a little wind/solar, to show how the "typical price day" changes with the power mix.
- **Say this in the write-up:** it's built from past spot prices, not from real futures prices. Being clear about that difference is a good signal in a portfolio.
- **Cost:** roughly +1–3 days. Skip it if time is short, both core analyses work without it.

---

## 7. SQLite database

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

CREATE TABLE IF NOT EXISTS transmission_outages (
    zone_from TEXT NOT NULL,
    zone_to TEXT NOT NULL,
    mrid TEXT NOT NULL,             -- ENTSO-E's ID for the outage record
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    available_mw REAL,              -- capacity still available during the record
    business_type TEXT,             -- 'Planned maintenance' or 'Unplanned outage'
    doc_status TEXT,                -- 'Cancelled' or empty
    PRIMARY KEY (zone_from, zone_to, mrid, start_time, end_time)
);
```

**The fourth table (added 2026-10-13):** `transmission_outages` is different from the other three. Its rows are periods, not one value per 15 minutes, and ENTSO-E changes and cancels records after the fact. So the pipeline doesn't update row by row here: on every run it deletes the rows for a pair of zones and loads the current set (about 130 records per direction). The analysis turns the periods into one capacity value per 15 minutes.

**Design decisions (2026-09-24):**
- **Rerunning the pipeline is safe.** Each table has a primary key made of several columns (e.g. zone + timestamp). When a row with the same key already exists, the pipeline updates it instead of adding a copy (`INSERT ... ON CONFLICT DO UPDATE`, an "upsert"). Checked: two runs over the same week give the same row counts.
- **All timestamps in UTC, in one format:** `'YYYY-MM-DD HH:MM:SS+00:00'`, made by `to_utc_str()` in `src/pipeline_utils.py`. ENTSO-E sends German/Swedish local time, and prices and generation came back with different time offsets in the Phase 2 sample. The database compares timestamps as text, so the same moment always has to be written exactly the same way.
- **Key columns can't be empty (`NOT NULL`).** SQLite would otherwise allow an empty zone or timestamp, and those don't count as duplicates of each other, so the same row would get added again on every run. Value columns can be empty, so missing data stays visible as missing.
- **Production types keep ENTSO-E's names** (e.g. `Wind Onshore`) instead of being renamed. Analysis 1 only needs a list of which names count as wind/solar, and that list can live in the analysis code.

pandas reads from these tables with `pd.read_sql(query, engine)`, using the shared database connection from `get_engine()` in `src/pipeline_utils.py`. Adding a country later just means more rows in the same tables, no new tables needed.

---

## 8. Adding countries later

Easy by design: every zone uses the same ENTSO-E data types, so adding e.g. France or the Netherlands means:
- Look up the zone code (`entsoe-py` already has them)
- Add it to the zone lists in `src/entsoe_client.py`
- No new tables, no new code for reading the data

---

## 9. Scheduled pipeline

Show how to run the pipeline automatically every day: with cron (Linux/Mac) or, since this project is built on Windows, Windows Task Scheduler. This is just to mention scheduling in case of portfolio.

The fun version should I have way too much time on my hands is to migrate the project to a cloud based server and schedule it there. That idea now lives in Section 11, as part of the forecasting service.

---

## 10. Rough build order

1. **Phase 1 — manual exploration (complete):** get API access, then check that pulling works for all three data types — prices (DE-LU, SE4, SE1), generation (DE-LU, SE4, reshaped from one column per source into one row per source), and cable flows (DE-LU↔SE4, both directions) — for one sample week, in `archive/phase_1_exploration/01_entsoe_exploration.ipynb` (local only now).
2. **Phase 2 — quality check + first analysis (complete):** save the sample week as CSVs (`data/processed/`, local archive only now) so we don't hit the API on every run; check data quality (missing timestamps, 15-min instead of hourly, realistic generation numbers); first look at the wind/solar share for both countries before the real regression in Phase 4.
3. **Phase 3 — proper pipeline into SQLite (complete):** turn the exploration code into fetch → transform → load functions that write into the tables in Section 7. Lives in `src/`.
   - **Done:** `src/pipeline.py` fetches, reshapes and saves prices for all five zones, generation for DE_LU and SE_4, and flows for DE_LU↔SE_4 in both directions. Run it from the repo root with `python -m src.pipeline`. Full pull from 2025-12-02 done and checked: no missing days, no empty values, reruns don't duplicate. Merged to `main` via PR #1.
   - **Decisions (2026-09-24/25):**
     - **SQLAlchemy** instead of Python's built-in `sqlite3`, same as in other ETL work, and it makes switching databases easier later.
     - **If a fetch fails, the run stops** instead of skipping it quietly.
     - **The API key is loaded from `.env`** with `python-dotenv`, in `src/entsoe_client.py`.
     - **Which zones get pulled for what** is set by three lists in `src/entsoe_client.py`: `PRICE_ZONES` (all five), `GENERATION_ZONES` (DE_LU, SE_4) and `FLOW_PAIRS` (DE_LU↔SE_4).
4. **Phase 4 — Analysis 1 (price swings vs. wind/solar share) (complete):** `analysis/volatility_renewable_share.py`, run from the repo root with `python -m analysis.volatility_renewable_share`. It writes the charts, the regression tables and the CSVs for Tableau to `outputs/`. Results in Section 4.
5. **Phase 5 — Analysis 2 (the cable and DE–SE prices) (complete):** `analysis/transmission_price_pressure.py`, run from the repo root with `python -m analysis.transmission_price_pressure`. Joins prices, flows and the outage records. The pipeline got a fourth table for the outage records along the way (Section 7). Results in Section 5.
   - **Done along the way:** both scripts save the regression numbers (coefficients, p-values, confidence intervals) as one CSV per analysis, `regression_coefficients.csv`, next to the text summaries. The findings report needs them. Each analysis has its own folder under `outputs/tables/`.
   - **Right after it:** the findings report script (decided 2026-10-09, in scope). Details in Section 11.
6. **Phase 6 — Tableau dashboard + polish:** a Tableau Public dashboard is the main deliverable (required, not optional). It reads the CSVs the analysis scripts write to `outputs/tables/`. The charts inside the analyses are made with seaborn and matplotlib; Plotly was planned for them at first and isn't used.
7. **Phase 7 — Data management layer (decided 2026-10-09, in scope):** data dictionary, quality checks on every load, lineage, licence and retention notes. Details in Section 11.
8. **Phase 8 (optional extras):** typical price curves (Section 6); scheduled pipeline (Section 9); more countries (Section 8).
9. **Later, as its own repository:** a forecasting service that runs every day (Section 11). Not started until everything above is finished.

**Git workflow (decided 2026-09-04):** Phases 1–2 went straight to `main`, fine for quick exploration work. From Phase 3 on, bigger work goes through its own branch and a pull request.

---

## 11. After the two analyses (decided 2026-10-09)

The project as it stands is aimed at a data analyst role. The findings report rounds that off, and the two additions after it aim the project at other roles as well. Order: cable analysis, findings report, Tableau dashboard, data management layer, then the forecasting service.

### Findings report (in this repository)

A script that reads the result tables in `outputs/tables/` and writes the findings out as sentences with the current numbers in them. One output file (`outputs/report.md`, or an HTML page with the charts in it), made new on every run.

- **Numbers filled in:** e.g. "10 percentage points more solar goes with 17.9 EUR/MWh more daily volatility in DE_LU."
- **Simple rules pick the wording:** p below 0.05 gives "a clear effect", otherwise "no detectable effect".
- **Comparisons:** e.g. whether the solar effect is still there with the month as a control.

Why: the README quotes numbers from one date, and they go out of date as soon as the pipeline runs again. With the report, the README describes the project and links to the report for the current numbers.

What it can't do: it only says what there is a sentence and a rule for. It won't notice anything new. Finding things stays a job for a person looking at the tables.

How it fits with the rest: the analysis scripts compute and save, the report script puts the results into words, and the Tableau dashboard is the interactive version for people who won't open the repository. Plotly is not this step, it only draws charts.

Needs first: the regression numbers as CSV (see Section 10, Phase 5). The text summaries are made for reading, not for a script to pick numbers out of.

### Data management layer (in this repository)

Shows that the data is documented and can be trusted. Mostly documentation plus one checks script.

- **Data dictionary:** every table and column, with its unit, where it comes from and its time zone.
- **Quality checks after every load:** 96 rows per day, no gaps, no empty values, no values outside a sensible range. Results get stored in their own table, so there's a record of every run.
- **Lineage:** which script fills which table and writes which output file.
- **Licence and retention notes:** ENTSO-E data is CC-BY 4.0 (checked 2026-09-11); what is kept, where, and what isn't published.
- **What scales to other zones and what doesn't (reviewed 2026-10-14):** write this up for readers who want to reuse the code.
  - **Scales as it is:** the database (every table has zone columns), the pipeline (loops over the lists in `src/entsoe_client.py`), the volatility analysis (follows `GENERATION_ZONES`, skips fuel types a zone doesn't report, stops with an error if a zone has no matching prices), and the volatility part of the findings report.
  - **Needs a check when adding zones:** `EARLIEST_START` in `src/pipeline.py` is the date SE4 generation switched to 15 minutes; other zones may have switched on other dates or not at all. A flow pair with no outage records in the window would stop the pipeline run, because a failed fetch stops the run.
  - **Doesn't scale, on purpose:** the cable analysis and the cable part of the findings report. They are about the Baltic Cable only, with their own zone constants, capacities, column names and labels. Making them work for any list of cables would only pay off together with the open question in Section 5 (the SE4 links to Denmark, Poland and Lithuania).

Write the dictionary and the lineage after the cable analysis, because that analysis may add a capacity table. The quality checks can come earlier.

### Forecasting service (its own repository, later)

Data engineering and data science in one project: a pipeline that runs by itself every day, makes a prediction for tomorrow, and later checks how good that prediction was.

Each daily run:
1. **Pull** yesterday's actual prices and generation, plus the day-ahead forecasts for wind, solar and demand that ENTSO-E publishes.
2. **Predict** tomorrow's price swings (or the size of the midday dip) from those forecasts.
3. **Store** the prediction with the date it was made.
4. **Score** yesterday's prediction against what really happened, and add it to a running accuracy record.

Why it's worth doing: predictions written down before the outcome is known can't be adjusted afterwards, and a chart of the accuracy over weeks shows that.

What it needs that this project doesn't have yet:
- **Somewhere to run every day** (a small cloud server with cron, or a scheduled GitHub Actions job).
- **A hosted database** in place of the SQLite file. SQLAlchemy makes the switch easier; `init_db` is written for SQLite and would need changing.
- **Logging and tests,** so a failed night run leaves a trace.
- **A model with a fair test:** train on earlier months, test on later ones, and compare with a simple baseline like "tomorrow is the same as today".

Why its own repository: GitHub doesn't allow forking your own repository into the same account, and this repository should stay a finished analysis with fixed findings. The service starts as a copy of this one.

Known limit: about ten months of data is thin for a forecasting model. Say so in the write-up.
