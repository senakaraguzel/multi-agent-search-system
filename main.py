import sys
import os
import json

from agents.HeaderGenerator import HeaderGenerator
from agents.browsing_agent import BrowsingAgent
from agents.scraper_agent import ScraperAgent


def main():

    print("\n==============================")
    print(" SAHIBINDEN AI AGENT SYSTEM ")
    print("==============================\n")


    # 1️⃣ Query alma (UI veya Terminal)

    if len(sys.argv) > 1:

        user_query = sys.argv[1]

        print("UI Query:", user_query)

    else:

        user_query = input("Arama giriniz: ")


    if not user_query:

        print("❌ Boş sorgu")

        return


    # 2️⃣ HeaderGenerator (Dynamic Headers)

    print("\n--- 🧠 HeaderGenerator ---")

    header_generator = HeaderGenerator()
    
    # We still need QueryParser to parse the search criteria to pass to BrowsingAgent
    from utils.query_parser import QueryParser
    query_parser = QueryParser()
    
    header_data = header_generator.generate_headers(user_query)
    domain = header_data["domain"]
    metadata_headers = header_data["headers"]
    
    parsed_data = query_parser.parse(user_query, domain=domain)

    print("\nDomain:", domain)
    print("Parsed Data:")
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))

    # Domain ve header bilgisini kaydet (api_server.py okuyacak)
    search_metadata = {
        "domain": domain,
        "headers": metadata_headers
    }
    with open("search_metadata.json", "w", encoding="utf-8") as f:
        json.dump(search_metadata, f, indent=2, ensure_ascii=False)

    print("✅ search_metadata.json kaydedildi")



    # 3️⃣ BrowsingAgent

    print("\n--- 🌐 BrowsingAgent ---")

    browsing_agent = BrowsingAgent()


    try:

        browsing_agent.open_site()

    except Exception as e:

        print("❌ Tarayıcı açılamadı:", e)

        return



    # Query text — parsed_data'dan oluştur
    # QueryParser "query" alanı döndürmüyor; city/district/rooms/listing_type'tan inşa et

    parts = []

    if domain in ["araba", "vasita"]:
        marka = parsed_data.get("marka")
        if marka:
            parts.append(marka)
        seri = parsed_data.get("seri")
        if seri:
            parts.append(seri)
        model = parsed_data.get("model")
        if model:
            parts.append(model)
        yil_min = parsed_data.get("yil_min")
        if yil_min:
            parts.append(str(yil_min))
    else:
        district = parsed_data.get("district") or parsed_data.get("city")
        if district:
            parts.append(district)
    
        rooms = parsed_data.get("rooms")
        if rooms:
            parts.append(rooms)
    
        listing_type = parsed_data.get("listing_type")
        if listing_type:
            parts.append(listing_type)

    # Parçalar yoksa orijinal kullanıcı sorgusunu kullan
    query_text = " ".join(parts) if parts else user_query

    if not query_text:
        print("❌ Query üretilemedi")
        return

    print("\n🔍 Arama Yapılıyor:", query_text)

    browsing_agent.search_with_query(query_text)



    # Filtre uygula

    print("\n⚙️ Filtreler uygulanıyor")


    browsing_agent.apply_filters(parsed_data)



    # URL toplama

    print("\n📄 URL toplama başlıyor")


    listing_urls = browsing_agent.collect_urls_from_pages(

        max_pages=1

    )


    if not listing_urls:

        print("❌ URL bulunamadı")

        return


    print(f"\n✅ {len(listing_urls)} URL bulundu")



    # 4️⃣ ScraperAgent

    print("\n--- 🕵️ ScraperAgent ---")


    scraper = ScraperAgent(
        browsing_agent.page,
        metadata_headers
    )


    final_data = scraper.scrape_listings()



    if final_data:

        print("\n====================")

        print("✅ İşlem tamamlandı")

        print("Toplam ilan:", len(final_data))

        print("listing_urls.json kaydedildi")

        print("listing_details.json kaydedildi")

        print("====================")

    else:

        print("❌ Scraper veri çekemedi")



    browsing_agent.close()



if __name__ == "__main__":

    main()