from utils import fetch_data, process_data
from config import DEFAULT_LOCATION

def run_pipeline():
    raw_data = fetch_data(query=DEFAULT_LOCATION)
    cleaned_data = process_data(raw_data)
    print("Pipeline tamamlandı!")

if __name__ == "__main__":
    run_pipeline()
