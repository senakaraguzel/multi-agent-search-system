import sys
import json
import os
import traceback

# UTF-8 çıktısı
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
from agents.browsing_agent import BrowsingAgent
from agents.scraper_agent import ScraperAgent

DATA_DIR = "data"
URLS_FILE  = os.path.join(DATA_DIR, "listing_urls.json")
DETAILS_FILE = os.path.join(DATA_DIR, "listing_details.json")

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python main.py <query> [max_scrolls]", flush=True)
        sys.exit(1)

    query       = sys.argv[1]
    max_scrolls = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    os.makedirs(DATA_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page    = context.new_page()

        try:
            # ── Aşama 1: Arama & URL Toplama ──────────────────────────────
            print("PHASE:searching", flush=True)

            browsing = BrowsingAgent(page)
            success  = browsing.search(query)

            if not success:
                print("ERROR:Arama başarısız oldu.", flush=True)
                sys.exit(1)

            urls = browsing.collect_urls(max_scrolls=max_scrolls)

            with open(URLS_FILE, "w", encoding="utf-8") as f:
                json.dump(urls, f, ensure_ascii=False, indent=2)

            print(f"URLS_FOUND:{len(urls)}", flush=True)

            if not urls:
                print("ERROR:Hiç URL bulunamadı.", flush=True)
                sys.exit(1)

            # ── Aşama 2: Scraping ──────────────────────────────────────────
            print("PHASE:extracting", flush=True)

            scraper = ScraperAgent(page, URLS_FILE)
            results = scraper.scrape_listings()

            with open(DETAILS_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)

            print(f"RESULTS_COUNT:{len(results)}", flush=True)
            print("PHASE:done", flush=True)

        except Exception as e:
            print(f"ERROR:{e}", flush=True)
            traceback.print_exc()
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    main()
