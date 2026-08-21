"""
Phase 2: expand the manual pull to Sweden's four bidding zones (SE1-SE4),
and compute variable_renewable_share (wind+solar / total generation) for
both countries - see docs/project-brief.md Section 4 for why hydro is
excluded from that definition.

Still manual/one-off at this stage, same as Phase 1 - the ETL formalization
happens in Phase 3.

Run: python phase_2_sweden_expansion/fetch_sweden_zones.py
"""
import pandas as pd

from common.entsoe_client import get_client, ZONE_DE, ZONES_SE

client = get_client()
start = pd.Timestamp("2024-01-01", tz="Europe/Berlin")
end = pd.Timestamp("2024-01-08", tz="Europe/Berlin")

all_prices = {}
for zone in [ZONE_DE] + ZONES_SE:
    all_prices[zone] = client.query_day_ahead_prices(zone, start=start, end=end)
    print(f"{zone}: {len(all_prices[zone])} hourly points")

# TODO: pull generation per zone via client.query_generation(), compute
# variable_renewable_share = (wind_onshore + wind_offshore + solar) / total,
# and do a first eyeball comparison DE vs SE before Phase 3 formalizes this.
