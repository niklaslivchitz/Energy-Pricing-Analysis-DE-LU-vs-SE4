"""
Shared ENTSO-E client setup and bidding zone constants.
It might be unnecessary to have a separate file for this, but it now exists for learning purposes.
"""
import os

from dotenv import load_dotenv
from entsoe import EntsoePandasClient # type: ignore

load_dotenv()  # reads .env and loads its variables into the environment


def get_client() -> EntsoePandasClient:
    api_key = os.environ.get("ENTSOE_API_KEY")
    if not api_key:
        raise RuntimeError("ENTSOE_API_KEY not set. Add it to your .env file.")
    return EntsoePandasClient(api_key=api_key)


# Bidding zones used across this project. Modifying this will change the data fetched. The database easily handles more zones, but the analysis code is written for these specific zones.
ZONE_DE = "DE_LU"
ZONE_SE4 = "SE_4"
ZONES_SE = ["SE_1", "SE_2", "SE_3", "SE_4"]

# What gets fetched for which zone
PRICE_ZONES = [ZONE_DE] + ZONES_SE         # all five: cheap, one request per zone
GENERATION_ZONES = [ZONE_DE, ZONE_SE4]     # the two zones Analysis 1 compares
FLOW_PAIRS = [                             # Baltic Cable, both directions
    (ZONE_DE, ZONE_SE4),
    (ZONE_SE4, ZONE_DE),
]
BALTIC_CABLE_CAPACITY_MW = 600  # DE <-> SE4 physical link, in practice run seems to be capped at 200 something SE->DE, but I cannot find why. ENTSO-E data shows 600 MW as the max, so we use that for now.
