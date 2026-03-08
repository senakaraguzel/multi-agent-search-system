from utils import fetch_listings, process_listings
from config import SEARCH_PARAMS

def run_pipeline():
    raw_data = fetch_listings(SEARCH_PARAMS)
    cleaned_data = process_listings(raw_data)
    print("Pipeline tamamlandı!")

if __name__ == "__main__":
    run_pipeline()
