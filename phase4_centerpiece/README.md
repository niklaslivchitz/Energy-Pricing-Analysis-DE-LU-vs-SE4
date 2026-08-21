# Phase 4 — The centerpiece (all DE)

Requires Phase 3's SQLite db to exist (data/energy.db). See TASKS.md for the checklist:
day-ahead/intraday spread (the main event), renewable-share regression, volatility clustering,
autocorrelation, seasonal decomposition.

Query the db with pandas: `pd.read_sql(query, conn)` — not pd.read_csv. That's the point of Phase 3.
