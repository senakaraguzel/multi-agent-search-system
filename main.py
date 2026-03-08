import asyncio
import json
import os
from agents.url_agent import URLAgent
from agents.scraping_agent import ScrapingAgent
from agents.scoring_agent import ScoringAgent
from agents.llm_agent import LLMAgent

async def main():
    print("=== Okul Puanlama Takımı ===")
    
    url_agent = URLAgent(headless=False) # Görsel takip için False
    scraping_agent = ScrapingAgent(headless=False) # Görsel takip için False
    scoring_agent = ScoringAgent()
    llm_agent = LLMAgent()
    
    try:
        while True:
            school_name = input("\nLütfen puanlanacak okulun adını girin (Çıkış için 'q'): ").strip()
            if school_name.lower() == 'q':
                break
                
            position = input("Adayın başvuracağı pozisyonu girin (örn: AI Engineer): ").strip()
            if not position:
                position = "Genel"

            employer_name = input("İlan veren şirketin adını girin (örn: Google, Aselsan, Trendyol): ").strip()
            if not employer_name:
                employer_name = "Bilinmeyen Şirket"

            cv = {"name": "Aday", "education": [{"school_name": school_name, "department": position}]}
            job_post = {"employer": employer_name, "position": position}

            # 0. LLM Analizi
            print(f"[{employer_name}] LLM üzerinden şirket ve okul lokasyonu analiz ediliyor...")
            llm_res = await llm_agent.analyze_company_and_school(job_post, cv)

            # 1. URL BULMA
            print(f"[{school_name}] THE URL'si araştırılıyor...")
            url_res = await url_agent.run(school_name)
            
            if url_res["status"] != "success":
                print(f"(!) HATA: URL bulunamadı: {url_res.get('message', 'Bilinmeyen hata')}")
                continue
                
            the_url = url_res["url"]
            print(f"(+) URL Bulundu: {the_url}")
            
            # 2. SCRAPING
            print(f"[{school_name}] Veriler çekiliyor...")
            scrape_res = await scraping_agent.run({
                "school_name": school_name,
                "the_url": the_url
            })
            
            if scrape_res["status"] not in ["success", "partial"]:
                print(f"(!) HATA: Scraping başarısız.")
                continue

            # 3. SCORING
            print(f"[{school_name}] Puanlanıyor (Pozisyon: {position})...")
            score_res = scoring_agent.run({
                "cv": cv,
                "job_post": job_post,
                "position": position,
                "scraped_data": scrape_res,
                "llm_data": llm_res
            })
            
            # SONUÇLARI BİRLEŞTİR VE KAYDET
            data_to_save = {
                "cv_info": cv,
                "job_post": job_post,
                "llm_data": llm_res,
                "url_data": url_res,
                "scrape_data": scrape_res,
                "score_data": score_res
            }
            
            # Dosyaya ekle (append-like logic)
            file_path = "university_data.json"
            all_data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        all_data = json.load(f)
                except:
                    all_data = []
            
            all_data.append(data_to_save)
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
                
            print(f"\n(+) İŞLEM TAMAMLANDI!")
            print(f"--- SONUÇ ---")
            print(f"Okul: {school_name}")
            print(f"Dünya Sıralaması (Mid): {scrape_res['world_rank']['mid'] if scrape_res['world_rank'] else 'N/A'}")
            print(f"Final Puan (20 üzerinden): {score_res['score_out_of_20']}")
            print(f"Dayanak: {score_res['basis']}")
            print(f"--------------")
            print(f"Sonuçlar '{file_path}' dosyasına kaydedildi.")
            
    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    asyncio.run(main())
