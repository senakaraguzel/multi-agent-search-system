from agents.source_planner_agent import SourcePlannerAgent
from agents.source_discovery_agent import SourceDiscoveryAgent
from agents.filtering_agent import FilteringAgent
from agents.utils.execution_tracer import tracer
import json
import asyncio
import sys

def main():
    # Windows konsolunda Turkce karakter hatalarini onlemek icin
    if sys.platform == 'win32':
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')

    print("\n==============================")
    print(" MULTI AGENT SEARCH SYSTEM ")
    print("==============================\n")

    # Kullanıcı sorgusu al
    user_query = input("Search query: ")

    # Yeni oturum için tracer'ı sıfırla
    tracer.reset()

    # Agent1 başlat
    planner = SourcePlannerAgent()

    print("\n[Agent1] Planning search...")

    result = planner.plan(user_query)

    print("\n[Agent1] Search Plan Created:\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n[+] data/search.json updated successfully.")

    # Agent2 başlat
    print("\n[Agent2] Executing Source Discovery...")
    agent2 = SourceDiscoveryAgent()
    agent2.run()

    # Agent 3 başlat
    from agents.browsing_agent import BrowsingAgentRouter
    print("\n[Agent3] Executing Browsing (URL fetching via Stealth Router)...")
    agent3 = BrowsingAgentRouter()
    agent3.run()

    # Agent 5 başlat (Scraping Modulu)
    from agents.scraper_agent import ScraperAgent
    print("\n[Agent5] Executing Scraping (Fetching raw data from targets)...")
    agent5 = ScraperAgent()
    asyncio.run(agent5.execute())

    # Agent 5.5: Google Comment Scraper
    from agents.google_comment_agent import GoogleCommentAgent
    print("\n[Agent5.5] Executing Google Comment Scraping (Extracting reviews if local business)...")
    agent5_5 = GoogleCommentAgent()
    agent5_5.run()

    # Agent 6: Veri Filtreleme & Yapilandirma (Result)
    print("\n[Agent6] Executing Filtering (Filtering and structuring scraped data)...")
    agent6 = FilteringAgent()
    agent6.execute()

    # Execution Trace kaydet (tüm ajanların izleri tek JSON'da)
    tracer.save(user_query, "data/sorgu_output.json")

    # Agent 7: Sunum Katmanı (Presentation)
    print("\n[Agent7] Arama tamamlandı! Sonuçları görmek için UI'ı açabilirsiniz.")
    print("         Backend : python -m agents.presentation_agent")
    print("         Frontend: cd ui && npm run dev")
    print("==============================\n")

if __name__ == "__main__":
    main()
