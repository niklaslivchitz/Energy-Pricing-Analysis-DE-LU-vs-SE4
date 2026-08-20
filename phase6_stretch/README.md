# Phase 6 — Stretch (optional)

Only start this if Phases 1-5 are solid and you have time left over.
- ENTSO-E plug-in: same schema as Phase 3 (see schema.sql), same energy_data table, new source='ENTSOE'.
- Scheduled pipeline: cron or GitHub Action re-running phase3_etl daily.
Needs ENTSOE_API_KEY set in .env (copy from .env.example).
