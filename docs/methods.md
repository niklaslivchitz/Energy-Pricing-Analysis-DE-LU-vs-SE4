# Methods and decisions

How the data is collected, stored and analysed, and why it is done this way. The results
themselves are in the [README](../README.md) and the regenerated
[findings report](../outputs/report.md).

## Data

**Source.** All the raw data comes from the ENTSO-E Transparency Platform, through its REST API and
the `entsoe-py` library. It is the great source that publishes a wide variety of european energy data with frequent time stamps.

**What is pulled.**

| Data | Zones | Resolution |
|---|---|---|
| Day-ahead prices | DE-LU, SE1 to SE4 | 15 minutes |
| Generation by production type | DE-LU, SE4 | 15 minutes |
| Physical flows on the Baltic Cable | DE-LU to SE4, both directions | 15 minutes |
| Outage and maintenance records for the cable | both directions | one row per record |

SE4 is the Swedish side because it is the zone the Baltic Cable connects to, and the market in Sweden with the highest prices.

**The time window.** A rolling year up to the last complete day (midnight, Berlin time), but
never earlier than 2 December 2025. Each series switched from hourly to 15-minute data on a
different date, and 2 December is the first day all of them are at 15 minutes.

## Pipeline and database

- **Fetch, transform, load,** one function per data type, in `src/pipeline.py`. A failed fetch
  is retried a few times, and then stops the run instead of skipping data quietly.
- **SQLite through SQLAlchemy.** One file, no server. SQLAlchemy makes sure that a switch to another
  database would be relatively plug and play.
- **Reruns are safe.** Prices, generation and flows are written with an upsert
  (`INSERT ... ON CONFLICT DO UPDATE`): an existing row is updated, not duplicated. This matters
  because ENTSO-E revises actual generation and flows after first publishing them.
- **The outage table is reloaded, not upserted.** Outage records get corrected after the fact,
  including their start and end times, and withdrawn records disappear. An upsert can't remove
  rows the source no longer sends, so each run deletes a cable direction's records and loads the
  current set.
- **The database stores data in a long format**: To future proof changes in categorization, the data
  is pivoted into a long format for storage, and pivoted back wide for analysis.
- **Timestamps are stored in UTC, as text in one fixed format.** The database compares
  timestamps as text, so the same moment always has to be written the same way.
- **Key columns are `NOT NULL`,** otherwise SQLite would accept empty keys and duplicates.
- **One command runs everything:** `python run_all.py` runs the pipeline, both analyses and the
  findings report, in that order.

## Analysis 1: wind, solar and volatility

- **Shares of the zone's own generation,** of wind and solar as a share of total generation,
  per 15 minutes and averaged per day. Wind and solar are kept apart: combined they show almost
  nothing, because they pull in opposite directions.
  Hydro is not counted as variable renewable: it can be run on demand.
- **Negative pumped storage is set to zero** before adding up total generation. Pumping uses
  power; it isn't generation.
- **Volatility = the standard deviation of the 96 prices within a day.** A 24-hour rolling
  window was tried first, but neighbouring windows share 95 of their 96 values, which gives
  trails of near-identical points instead of separate observations.
- **Tests,** per zone, on daily values:
  - Spearman rank correlation, which a few extreme days can't dominate.
  - Linear regression of the price swing on the solar and wind share, with HAC standard errors
    (7 days of lags). Neighbouring days resemble each other, which makes ordinary p-values too
    confident.
  - Two robustness checks: the same model with the month as a control (is it just the season?),
    and on the logarithm of the price swing (is it a few extreme days?).
  - One model over both zones with a separate slope per zone, to test whether the zones differ.

## Analysis 2: the Baltic Cable

- **Net flow** = flow towards Germany minus flow towards Sweden.
- **The cable's capacity comes from ENTSO-E's outage records,** turned into one value per 15
  minutes: the lowest available capacity among the active records covering that moment. The
  rated 600 MW was never available in the data window, so dividing by 600 would have made the
  cable look rarely full.
- **Three states per 15 minutes:**
  - *out of service*: available capacity zero;
  - *full*: flow at 95% or more of the available capacity, or 400 MW or more. The second rule
    catches a limit of about 430 MW from mid-September that the outage records don't show;
  - *partly used*: everything else.
- **Tests on daily values:** the average price gap of a day against the share of the day the
  cable was full and out of service, with HAC standard errors (14 days of lags, because outages
  last for weeks), with and without month controls, and on the logarithm of the gap. A second
  model splits "full" by direction and uses the signed gap.
- **The outages as a natural experiment.** A full cable is partly a result of a price gap: power
  flows from the cheap side until the prices meet or the cable is full. An outage happens for
  technical reasons, so comparing outage time with in-service time in the same months is the
  fairer test of what the cable does.

## Findings report

`analysis/findings_report.py` reads the result tables and writes the conclusions with the current
numbers into `outputs/report.md`. The wording follows fixed rules:

- A p-value below **α = 0.05** counts as a clear effect.
- Correlations below 0.3 in size read as "almost no link", below 0.6 as "moderate", above as
  "strong".
- A check "holds" if it is clear and points the same way as the main test.
- The conclusion combines the main test and both checks into one of four verdicts: holds up,
  treat with caution, tentative, no evidence.

## Dashboard

The Tableau Public dashboard reads CSV files the analysis scripts export, because Tableau Public
can't read SQLite. The 15-minute exports carry a local-time column without a time zone offset,
since Tableau handles offsets poorly and the daily patterns only make sense in local time. These
large exports are kept out of git. The dashboard is refreshed by hand: rerun the scripts, refresh
the data in Tableau, republish.

## Limits

- **About ten months of data,** without October and November until December 2026. Future runs limit to 12 months.
- **Shares are of local generation only.** SE4 imports much of its power from the rest of Sweden, so its own shares say
  less about its prices.
- **Associations, not proof of cause.**
- **The cable comparison measures the gap between the two prices,** not which side's price moves.
- **Other connections exist.** SE4 is also linked to Denmark, Poland and Lithuania, and Germany to
  Denmark. They aren't in the data yet.
- **Some limits on the cable are missing from the outage records,** for example on 5 October,
  when the flow sat at about 300 MW with a gap of over 100 €/MWh. Such intervals count as
  "partly used", which makes the difference between the states look smaller, not larger.
- **Daily values use UTC days.** The first day in the daily tables holds only the first hour of
  2 December, local time, which still falls on 1 December in UTC.
