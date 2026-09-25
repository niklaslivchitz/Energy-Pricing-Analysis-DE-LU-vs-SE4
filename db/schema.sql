-- See docs/project-brief.md Section 7.
-- Composite primary keys enable idempotent upserts (INSERT ... ON CONFLICT DO
-- UPDATE, see upsert_dataframe() in src/pipeline_utils.py) - re-running the
-- pipeline over a date range you've already fetched updates rows instead of
-- duplicating them or erroring.
-- Key columns are NOT NULL because SQLite allows NULLs in composite primary
-- keys, and NULLs never count as equal - a NULL key would slip past the upsert
-- and duplicate on every run.
-- Timestamps are stored as UTC text, 'YYYY-MM-DD HH:MM:SS+00:00' (see to_utc_str()).

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
