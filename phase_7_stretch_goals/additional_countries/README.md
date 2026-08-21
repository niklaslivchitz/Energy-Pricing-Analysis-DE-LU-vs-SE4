# Stretch: additional countries

See docs/project-brief.md Section 8. Since Phase 3's pipeline already reads
day-ahead price (A44) and generation-by-type (A75) the same way for every
ENTSO-E bidding zone, adding a country is:

1. Look up its bidding zone code (entsoe-py ships the mapping)
2. Add it to the zone list in common/entsoe_client.py and phase_3_etl_pipeline/pipeline.py
3. Re-run the pipeline — no schema change, no new parser

Countries with multiple bidding zones (Norway NO1-NO5, Italy, Denmark
DK1/DK2) need the same "one zone vs. all" judgment call Sweden already
required.
