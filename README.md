# Germany vs. Sweden Energy Market Analysis (ENTSO-E)

Full plan, rationale, and analysis design: `docs/project-brief.md`.

##TLDR - This is a skeleton of the project to be filled in a modular fashion as progress goes along.

## Structure — organized by build phase (see brief Section 10)

```
common/                        Shared code used across phases (ENTSO-E client, pipeline helpers)
db/                             SQLite schema
docs/                           Project brief
phase_1_exploration/            First manual pull: one zone, prove the mechanics work
phase_2_sweden_expansion/       Add SE1-SE4, compute renewable share for both countries
phase_3_etl_pipeline/           Formalize into fetch -> transform -> load, with logging/retry
phase_4_volatility_vs_renewables/   Core analysis 1
phase_5_transmission_price_pressure/ Core analysis 2 (DE <-> SE4, Baltic Cable)
phase_6_polish/                 Flagship interactive view, Tableau piece if time allows
phase_7_stretch_goals/          Optional: synthetic curves, scheduled pipeline, more countries
sql/                             Standalone queries reused across phases
outputs/figures/                 Exported charts
```

## Quickstart
1. Register for ENTSO-E API access (brief Section 2), put the token in `.env`:
   ```
   ENTSOE_API_KEY=your-token-here
   ```
2. `pip install -r requirements.txt`
3. Start at `phase_1_exploration/`, work through phases in order — each one assumes the previous phase's output exists.
