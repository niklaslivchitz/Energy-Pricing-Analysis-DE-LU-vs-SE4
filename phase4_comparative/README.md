# Phase 4 — Comparative analysis (SE vs DE)

Requires Phase 3's SQLite db to exist (data/energy.db). See TASKS.md for the checklist:
day-ahead/intraday spread (centerpiece), household price trend, energy mix vs. stability.

Query the db with pandas: `pd.read_sql(query, conn)` — not pd.read_csv. That's the point of Phase 3.
