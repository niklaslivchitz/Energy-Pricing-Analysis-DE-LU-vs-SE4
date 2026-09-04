"""
Phase 2: fetch the Phase 1 sample period once and cache it to disk
(data/processed/, long format matching db/schema.sql), so quality-checking
and first-analysis work below doesn't re-hit the ENTSO-E API every run.

Rough shape of the script (we'll do these one at a time):

Imports + constants (paths, the sample week's start/end, which zones)
A function that fetches+shapes prices into the (zone, timestamp, price_eur_mwh) frame
A function that fetches+shapes generation into long format (the .melt() + rename_axis("timestamp") + nett=True work from the notebook)
A function that fetches+shapes flows into (zone_from, zone_to, timestamp, flow_mw)
A main() that: makes sure data/processed/ exists, checks whether each target CSV already exists (skip if so — that's the "don't re-fetch" behavior you wanted), otherwise calls the fetch function and writes it

Step 1, your turn: set up the imports and constants. You'll need:

pandas, pathlib.Path
get_client from common.entsoe_client (same import you already use in the notebook)
a path pointing at data/processed/ — think about how to build this relative to the script's own location so it works no matter where you run it from (hint: Path(__file__).resolve() gives you the script's own path, and .parents[N] walks up N directories from there — how many levels up is repo root from phase_2_quality_and_first_analysis/?)
START/END timestamps — same week you used in the Phase 1 notebook, for consistency
the zone lists: which zones did you actually pull prices for vs. generation vs. flow pairs in the notebook? (they weren't all the same)
"""

from dotenv import load_dotenv
import os
from entsoe import EntsoePandasClient
import pandas as pd
from pathlib import Path

load_dotenv()  # reads .env and loads its variables into the environment.

client = EntsoePandasClient(api_key=os.environ["ENTSOE_API_KEY"])

#this defines the time period for which we want to fetch data - change for another period.

start = pd.Timestamp('2026-01-01', tz='Europe/Berlin')
end   = pd.Timestamp('2026-01-08', tz='Europe/Berlin')

#And then we call the pricing data, and transform it immediately in one function into the data frame form we well use for the database later:
def fetch_prices(start, end):
    de_prices = client.query_day_ahead_prices('DE_LU', start=start, end=end) #for germany
    se_prices = client.query_day_ahead_prices('SE_4', start=start, end=end) #and south sweden
    #we then convert the two series into dataframes with the right column names and concatenate them into a single dataframe:
    de_df = pd.DataFrame({"zone": "DE_LU", "timestamp": de_prices.index.astype(str), "price_eur_mwh": de_prices.values})
    se_df = pd.DataFrame({"zone": "SE_4", "timestamp": se_prices.index.astype(str), "price_eur_mwh": se_prices.values})
    prices_df = pd.concat([de_df, se_df], ignore_index=True)
    prices_df["timestamp"] = pd.to_datetime(prices_df["timestamp"], utc=True)
    return prices_df

#Here is a function that takes a generation dataframe and a zone name, and reshapes it into long format with the right column names for the database:

def to_long(gen_df, zone):
    long = (
        gen_df.rename_axis("timestamp")
        .reset_index()
        .melt(id_vars="timestamp", var_name="production_type", value_name="value_mw")
    )
    long["zone"] = zone
    return long[["zone", "timestamp", "production_type", "value_mw"]]

def fetch_generation(start, end):
    #we start with calling the data from de and se4, and we use the nett=True parameter to get the net generation (production minus consumption) for each production type:
    de_gen = client.query_generation('DE_LU', start=start, end=end, nett=True)
    se_gen = client.query_generation('SE_4', start=start, end=end, nett=True)
    #convert to long format
    de_long = to_long(de_gen, "DE_LU")
    se_long = to_long(se_gen, "SE_4")
    
    gen_df = pd.concat([de_long, se_long], ignore_index=True)
    gen_df["timestamp"] = pd.to_datetime(gen_df["timestamp"], utc=True)
    return gen_df

def fetch_flows(start, end):
    #we call the flow data for the de and se4, the final version of this code in stage 3 should probably take zones as arguments:
    de_se4_flow = client.query_crossborder_flows('DE_LU', 'SE_4', start=start, end=end)
    se4_de_flow = client.query_crossborder_flows('SE_4', 'DE_LU', start=start, end=end)
    #convert to dataframes with the right column names and concatenate them into a single dataframe:
    de_se4_df = pd.DataFrame({"zone_from": "DE_LU", "zone_to": "SE_4", "timestamp": de_se4_flow.index.astype(str), "flow_mw": de_se4_flow.values})
    se4_de_df = pd.DataFrame({"zone_from": "SE_4", "zone_to": "DE_LU", "timestamp": se4_de_flow.index.astype(str), "flow_mw": se4_de_flow.values})
    flows_df = pd.concat([de_se4_df, se4_de_df], ignore_index=True)
    flows_df["timestamp"] = pd.to_datetime(flows_df["timestamp"], utc=True)
    return flows_df

"""
prices_df = fetch_prices(start, end)
generation_df = fetch_generation(start, end)
flows_df = fetch_flows(start, end)

ok good, now we check that we got something reasonable
assert not prices_df.empty, "fetch_prices returned nothing"
assert not generation_df.empty, "fetch_generation returned nothing"
assert not flows_df.empty, "fetch_flows returned nothing"


for the next part we need to figure out where to store the data. We do project root/Data/processed, and we want to make sure that directory exists before we try to write to it. We also want to check whether the target CSV files already exist, and skip fetching if they do. Here's a main() function that does that:
"""


    
#lets define the path for the output directory, and the paths for the three CSV files we want to write:

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" #we use pathlib to make this run easier from git later

prices_path = OUT_DIR / "prices.csv"
generation_path = OUT_DIR / "generation.csv"
flows_path = OUT_DIR / "flows.csv"

def data_present(path):
    return path.exists() and path.stat().st_size > 0   

# now lets define the main() function that checks for the existence of the CSV files and fetches the data if they don't exist

def check_and_fetch():
    OUT_DIR.mkdir(parents=True, exist_ok=True)  # make sure the output directory exists
    if not data_present(prices_path):
        prices_df = fetch_prices(start, end)
        assert not prices_df.empty, "fetch_prices returned nothing"
        prices_df.to_csv(prices_path, index=False)
    else:
        print(f"{prices_path} already exists, skipping fetch.")
    
    if not data_present(generation_path):
        generation_df = fetch_generation(start, end)
        assert not generation_df.empty, "fetch_generation returned nothing"
        generation_df.to_csv(generation_path, index=False)
    else:
        print(f"{generation_path} already exists, skipping fetch.")
    
    if not data_present(flows_path):
        flows_df = fetch_flows(start, end)
        assert not flows_df.empty, "fetch_flows returned nothing"
        flows_df.to_csv(flows_path, index=False)
    else:
        print(f"{flows_path} already exists, skipping fetch.")

if __name__ == "__main__":
    check_and_fetch()