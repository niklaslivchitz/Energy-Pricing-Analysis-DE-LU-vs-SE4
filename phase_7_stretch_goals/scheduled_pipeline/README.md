# Stretch: scheduled pipeline

See docs/project-brief.md Section 9 (rescoped 2026-09-11).

Data (`db/*.db`, `data/raw/`, `data/processed/`) is gitignored, so a GitHub Actions
job with nothing to commit back to isn't useful — dropped that approach. Instead,
this is **documented local scheduling instructions**: how to run the fetch/pipeline
script unattended via cron (Linux/Mac) or Windows Task Scheduler, rather than a
live automated job. Doc TBD.
