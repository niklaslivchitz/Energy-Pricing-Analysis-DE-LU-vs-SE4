-- See docs/project-brief.md Section 7.
-- Composite primary keys enable idempotent INSERT OR REPLACE upserts
-- (see common/pipeline_utils.py) - re-running the pipeline over a date
-- range you've already fetched overwrites rather than duplicates or errors.

CREATE TABLE IF NOT EXISTS prices (
    zone TEXT,             -- 'DE_LU', 'SE_1', 'SE_2', 'SE_3', 'SE_4'
    timestamp TEXT,        -- ISO 8601, UTC
    price_eur_mwh REAL,
    PRIMARY KEY (zone, timestamp)
);

CREATE TABLE IF NOT EXISTS generation (
    zone TEXT,
    timestamp TEXT,
    production_type TEXT,  -- 'wind_onshore', 'wind_offshore', 'solar', 'hydro', 'nuclear', etc.
    value_mw REAL,
    PRIMARY KEY (zone, timestamp, production_type)
);

CREATE TABLE IF NOT EXISTS cross_border_flows (
    zone_from TEXT,
    zone_to TEXT,
    timestamp TEXT,
    flow_mw REAL,
    PRIMARY KEY (zone_from, zone_to, timestamp)
);

-- Pipeline run audit trail (Phase 3+). Optional but cheap, and useful once
-- the scheduled pipeline (Phase 7) is running unattended.
CREATE TABLE IF NOT EXISTS pipeline_logs (
    run_id TEXT,
    timestamp TEXT,
    zone TEXT,
    table_name TEXT,
    records_processed INTEGER,
    status TEXT,
    error_message TEXT
);
