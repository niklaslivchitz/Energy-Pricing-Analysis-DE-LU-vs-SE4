# Phase 6 — Sweden + cross-border (stretch, optional, bundled)

Only start this once Phases 1-5 are solid and you have time left over. This phase is one bundle,
not two separate stretch goals — both pieces need a second country to mean anything:

- **fetch_scb.py** — one SCB table (household electricity prices), via PxWebApi v2. No auth.
- **Nord Pool free day-ahead endpoint** — `dataportal-api.nordpoolgroup.com/api/DayAheadPrices`,
  no auth, unofficial/undocumented but community-verified (Home Assistant's integration uses it).
  Day-ahead only — Nord Pool intraday is a paid product, not worth pursuing here.
- **ENTSO-E** — needs a free API key (.env, see .env.example). Unlocks the cross-border flow story.

All of it writes into the same schema Phase 3 already defined (see phase3_etl/schema.sql) —
that's what makes this a genuine plug-in rather than a parallel project.

The actual value of including Sweden isn't a second spread analysis (SE doesn't have free
intraday data to make that possible) — it's the cross-comparison exercise itself: reconciling
SCB's and SMARD's very different formats/units/timestamps into one coherent picture.
