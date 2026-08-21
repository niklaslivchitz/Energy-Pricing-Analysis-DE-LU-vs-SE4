-- Standalone queries reused across phase_4/phase_5 analysis scripts.

-- Phase 5: hourly price spread between DE-LU and SE4
-- SELECT a.timestamp,
--        a.price_eur_mwh AS price_de,
--        b.price_eur_mwh AS price_se4,
--        b.price_eur_mwh - a.price_eur_mwh AS spread
-- FROM prices a
-- JOIN prices b ON a.timestamp = b.timestamp
-- WHERE a.zone = 'DE_LU' AND b.zone = 'SE_4';

-- Phase 3: audit recent pipeline runs
-- SELECT * FROM pipeline_logs ORDER BY timestamp DESC LIMIT 20;
