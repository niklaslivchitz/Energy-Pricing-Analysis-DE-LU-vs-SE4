-- Shared schema for the SQLite landing zone (Phase 3+).
-- One normalized table for everything, rather than separate SE/DE tables — this is what makes
-- cross-country joins in Phase 4 trivial (just filter/group by `country`).

CREATE TABLE IF NOT EXISTS energy_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,      -- ISO 8601, always UTC — convert at load time, not query time
    country     TEXT NOT NULL,      -- 'SE' or 'DE'
    metric      TEXT NOT NULL,      -- e.g. 'day_ahead_price', 'intraday_price', 'wind_generation'
    value       REAL,
    unit        TEXT,               -- e.g. 'EUR/MWh', 'MW'
    source      TEXT,               -- 'SCB', 'SMARD', 'DESTATIS' — keep provenance visible
    UNIQUE(timestamp, country, metric, source)
);

CREATE INDEX IF NOT EXISTS idx_energy_data_lookup
    ON energy_data (country, metric, timestamp);

-- Query patterns this schema is meant to support (Phase 4):
--   SELECT * FROM energy_data WHERE country = 'DE' AND metric IN ('day_ahead_price', 'intraday_price')
--   -- then pivot in pandas to compute the spread column
--
--   SELECT country, AVG(value) FROM energy_data WHERE metric = 'household_price' GROUP BY country
