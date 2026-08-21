# Stretch: synthetic seasonal price curves

See docs/project-brief.md Section 6. Not a core deliverable — attach this on
top of whichever Phase 4/5 analysis you run a seasonal decomposition for.

- `statsmodels.STL()` or `seasonal_decompose()` on a price series
- Refit the extracted seasonal component as a smooth curve (day-of-year /
  hour-of-day regression, or a Fourier series)
- Caveat to state explicitly in the writeup: this is a statistical proxy
  from spot data, not a market-derived forward curve.

Cost if included: roughly +1-3 days on top of the analysis it's attached to.
Skip entirely if time is short.
