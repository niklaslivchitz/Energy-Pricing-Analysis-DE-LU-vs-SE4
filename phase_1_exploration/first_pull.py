"""
Phase 1: manual exploration.

Goal is NOT insight - it's just proving you can get real ENTSO-E data into
pandas and onto a chart at all. One zone (DE-LU), one week, one Seaborn chart.
No pipeline, no SQLite yet - those come in Phase 3.

Run: python phase_1_exploration/first_pull.py
"""
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

load_dotenv()  # load .env file for ENTSOE_API_KEY

from common.entsoe_client import get_client, ZONE_DE

client = get_client()
start = pd.Timestamp("2024-01-01", tz="Europe/Berlin")
end = pd.Timestamp("2024-01-08", tz="Europe/Berlin")

prices = client.query_day_ahead_prices(ZONE_DE, start=start, end=end)

sns.lineplot(x=prices.index, y=prices.values)
plt.title("DE-LU Day-Ahead Price, first week of Jan 2024")
plt.ylabel("EUR/MWh")
plt.savefig("outputs/figures/phase1_de_price_sample.png")
print(f"Pulled {len(prices)} hourly price points for {ZONE_DE}")

