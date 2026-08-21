# Stretch: scheduled pipeline

See docs/project-brief.md Section 9. The actual GitHub Actions workflow
lives at `.github/workflows/scheduled_pipeline.yml` (has to live there for
GitHub to pick it up — kept as a stub here just so it shows up alongside the
other stretch goals in this phase-ordered structure).

To activate: uncomment the `schedule` trigger in that file, set
`ENTSOE_API_KEY` as a repo secret. Note GitHub Actions runners are stateless,
so the workflow commits db/energy.db back to the repo at the end of each run.
