import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

import state_utils

#set variables
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
CATALOG_URL = "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items"


#define helper functions
def get_file_name(url):
    return url.rsplit("/", 1)[-1]

def to_snake_case(name):
    # step 1: lowercase
    name = name.lower()
    # step 2: replace runs of non-alphanumeric characters with "_"
    name = re.sub(r"[^a-z0-9]+", "_", name)
    # step 3: strip leading/trailing "_"
    name = name.strip("_")
    return name

def process_dataset(item):
    #Download one dataset, snake_case its columns, write it to OUTPUT_DIR.
    url = item["distribution"][0]["downloadURL"]
    file_name = get_file_name(url)
    df = pd.read_csv(url, dtype=str)
    df.columns = [to_snake_case(c) for c in df.columns]
    df.to_csv(OUTPUT_DIR / file_name, index=False)

#define main function
def main():
    state = state_utils.load_state()

    # fetch the dataset catalog (one metadata record per dataset) 
    # raises on 4xx/5xx instead of failing silently later
    response = requests.get(CATALOG_URL, timeout=60)
    response.raise_for_status()

    # parse the JSON body into Python objects
    data = response.json()

    # get the data items that are hospitals
    hospital_items = [i for i in data if "Hospitals" in i["theme"]]

    # build the dataframe based on the source 'columns' in hospital_items
    hospitals_df = pd.DataFrame(hospital_items)

    # turn the keyword array into its own dataframe with the unique identifier as the key
    dataset_keywords = hospitals_df[["identifier", "keyword"]].explode("keyword")

    # output the dataframes for inspection
    hospitals_df.to_csv(OUTPUT_DIR / "hospital_catalog.csv", index=False)
    dataset_keywords.to_csv(OUTPUT_DIR / "dataset_keywords.csv", index=False)

    # decide what needs work: new datasets, or ones whose 'modified' date changed
    to_process = [
        i for i in hospital_items
        if state.get(i["identifier"]) != i["modified"]
    ]
    print(f"{len(to_process)} to download, {len(hospital_items) - len(to_process)} unchanged")

    # download in parallel; only this main thread touches 'state'
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_dataset, item): item for item in to_process}

        for future in as_completed(futures):
            item = futures[future]
            identifier = item["identifier"]
            try:
                future.result()                          # re-raises any error from the worker
                state[identifier] = item["modified"]     # record success only
                print(f"downloaded: {identifier}")
            except Exception as e:
                print(f"FAILED {identifier}: {e}")

    state_utils.save_state(state)

if __name__ == "__main__":
    main()