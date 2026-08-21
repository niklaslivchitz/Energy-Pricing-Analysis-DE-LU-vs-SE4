"""
Shared ENTSO-E client setup. Used from every phase from Phase 1 onward.

Reads ENTSOE_API_KEY from environment (.env). See docs/project-brief.md
Section 2 for registration steps and rate limit notes (400 req/min - a
non-issue at this project's scale, see the retry pacing in
common/pipeline_utils.py for why we still throttle a little anyway).
"""
import os
from entsoe import EntsoePandasClient


def get_client() -> EntsoePandasClient:
    api_key = os.environ.get("ENTSOE_API_KEY")
    if not api_key:
        raise RuntimeError("ENTSOE_API_KEY not set. Add it to your .env file.")
    return EntsoePandasClient(api_key=api_key)


# Bidding zones used across this project (brief Sections 2-3)
ZONE_DE = "DE_LU"
ZONES_SE = ["SE_1", "SE_2", "SE_3", "SE_4"]
BALTIC_CABLE_CAPACITY_MW = 600  # DE <-> SE4 physical link, see brief Section 3
