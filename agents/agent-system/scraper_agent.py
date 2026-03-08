import json
import os
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

from agents.scraper_agent_core import ScraperRouter
from agents.browsing_agent_core import BaseBrowserAgent
from agents.utils.anti_bot_bypass import solve_captcha
from agents.utils.execution_tracer import tracer

_AGENT_KEY = "agent_5_scraper"

class ScraperAgent(BaseBrowserAgent):
    """
    search.json dosyasini dinleyen ve toplanmis linkleri
    scraper_agent_core.py icindeki siniflara yonelterek 'scrape.json'a basan Ajan.
    """
    
    def __init__(self):
        super().__init__("scraper-agent-v1")
        self.input_file = os.path.join("data", "search.json")
        self.output_file = os.path.join("data", "scrape.json")
        self.router = ScraperRouter()

    def _load_search_data(self) -> dict:
        if not os.path.exists(self.input_file):
            return {}
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[{self.agent_name}] search.json okuma hatasi: {e}")
            return {}
            
    def _load_scrape_data(self) -> dict:
        """Yeni sonuclari yazmadan once eski resultlari getirir (Deduplication icin)."""
        if not os.path.exists(self.output_file):
            return {"search_session_id": "", "scraped_pages": []}
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                 return json.load(f)
        except:
            return {"search_session_id": "", "scraped_pages": []}

    def _save_scrape_data(self, data: dict):
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def run(self):
        print(f"\n[{self.agent_name}] Scraping (Ham Veri Toplama) baslatiliyor...")
        tracer.log(_AGENT_KEY, "Scraping başladı")
        search_data = self._load_search_data()
        
        if not search_data or "target_pages" not in search_data:
             tracer.log(_AGENT_KEY, "target_pages bulunamadı (search.json eksik/boş)", "error")
             print(f"[{self.agent_name}] Islenecek target_pages bulunamadi (search.json eksik/bos).")
             return
             
        targets = search_data.get("target_pages", [])
        pipeline_type = search_data.get("pipeline", "Generic")
        session_id = search_data.get("session_id", "session_unassigned")
        original_query = search_data.get("original_query", "")
        
        print(f"[{self.agent_name}] Hedef {len(targets)} URL tespit edildi. Pipeline: {pipeline_type}")
        tracer.log(_AGENT_KEY, f"{len(targets)} hedef URL tespit edildi. Pipeline: {pipeline_type}")
        
        # Her aramada scrape.json dosyasini sifirla (ust uste ekleme yapmak yerine overwrite)
        scrape_json = {
            "search_session_id": session_id,
            "original_query": original_query,
            "scraped_pages": []
        }
        
        # Ayni calistirma (session) icerisindeki mukerrer linkleri engellemek icin bos liste ile basla
        existing_hashes = set()
        
        # Gelecekte eklenecek genel kaziyici ayarlari vs buralarda yapilabilir
        

        # Hedef sayisi sinirlamasi Source Discovery'de yapiliyor, burada hepsini isleyebiliriz.

        has_sahibinden = any("sahibinden.com" in str(t.get("url", "")).lower() for t in targets)

        async with async_playwright() as p:
            # Kullanıcı arka planda çalışmasını istediği için genelde headless, 
            # ancak Sahibinden için CDP öncelikli.
            browser = None
            context = None
            page = None
            using_cdp = False

            if has_sahibinden:
                try:
                    print(f"[{self.agent_name}] Sahibinden tespiti: CDP üzerinden bağlanılıyor...")
                    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                    contexts = browser.contexts
                    context = contexts[0] if contexts else await browser.new_context()
                    using_cdp = True
                except Exception as e:
                    print(f"[{self.agent_name}] CDP başarısız ({e}), headless devam ediliyor...")

            if not using_cdp:
                print(f"[{self.agent_name}] Headless tarayıcı başlatılıyor...")
                browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
                context = await self.configure_context(browser)
            
            async def _process_target(index, target, ctx):
                 url = target.get("url")
                 query_id = target.get("query_id", "q_unknown")
                 metadata = target.get("metadata", {})
                 
                 if not url or url.startswith("javascript") or url.startswith("#"):
                     return None
                 
                 print(f"[{self.agent_name}] ({index+1}/{len(targets)}) Kaziniyor: {url}")
                 active_scraper = self.router.route(pipeline_type, url)
                 
                 # CDP ise mevcut sayfayı veya yeni sayfayı kullan, değilse izole stealth page
                 new_page = await ctx.new_page() if using_cdp else await self.create_stealth_page(ctx)
                 
                 try:
                     await solve_captcha(new_page, self.agent_name)
                     scraped_result = await active_scraper.scrape(new_page, url, metadata)
                     
                     h = scraped_result.get("html_snapshot_hash")
                     scraped_result["query_id"] = query_id
                     scraped_result["scraped_at"] = datetime.now().isoformat() + "Z"
                     
                     extracted = scraped_result.get("extracted_entity", {})
                     scraped_result["profile_url"] = url
                     scraped_result["name"] = extracted.get("name")
                     scraped_result["title"] = extracted.get("title")
                     scraped_result["company"] = extracted.get("company")
                     scraped_result["location"] = extracted.get("location")
                     scraped_result["profile_link"] = url
                     
                     return {"result": scraped_result, "hash": h}
                 except Exception as e:
                     print(f"[{self.agent_name}] URL isleme hatasi ({url}): {e}")
                     return None
                 finally:
                     try:
                         await new_page.close()
                     except: pass

            # ─── İnsan Benzeri Sahibinden Kazıma (Sıralı + Beklemeli) ──────────────
            if has_sahibinden:
                sahibinden_targets = [t for t in targets if "sahibinden.com" in str(t.get("url", "")).lower()]
                other_targets = [t for t in targets if "sahibinden.com" not in str(t.get("url", "")).lower()]
                
                print(f"[{self.agent_name}] Sahibinden: {len(sahibinden_targets)} ilan SIRAYLA kazınacak (insan benzeri).")
                
                for index, target in enumerate(sahibinden_targets[:5]):
                    url = target.get("url")
                    query_id = target.get("query_id", "q_unknown")
                    metadata = target.get("metadata", {})
                    
                    if not url:
                        continue
                    
                    print(f"[{self.agent_name}] ({index+1}/5) Sahibinden ilan açılıyor: {url}")
                    
                    # CDP ise yeni sekme aç
                    if using_cdp:
                        new_page = await context.new_page()
                    else:
                        new_page = await self.create_stealth_page(context)
                    
                    try:
                        # Sayfayı yükle
                        await new_page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        
                        # İnsan benzeri: sayfanın tam yüklenmesini bekle
                        wait_sec = 3 + (index * 1.5)  # Her ilandan sonra biraz daha uzun bekle
                        await asyncio.sleep(wait_sec)
                        
                        # İnsan benzeri scroll: önce yavaşça aşağı, sonra yukarı
                        await new_page.evaluate("window.scrollTo({top: 300, behavior: 'smooth'})")
                        await asyncio.sleep(1.5)
                        await new_page.evaluate("window.scrollTo({top: 700, behavior: 'smooth'})")
                        await asyncio.sleep(2)
                        await new_page.evaluate("window.scrollTo({top: 1200, behavior: 'smooth'})")
                        await asyncio.sleep(1.5)
                        await new_page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                        await asyncio.sleep(1)
                        
                        active_scraper = self.router.route(pipeline_type, url)
                        scraped_result = await active_scraper.scrape(new_page, url, metadata)
                        
                        scraped_result["query_id"] = query_id
                        scraped_result["scraped_at"] = datetime.now().isoformat() + "Z"
                        scraped_result["profile_url"] = url
                        scraped_result["profile_link"] = url
                        
                        h = scraped_result.get("html_snapshot_hash")
                        if h and h in existing_hashes:
                            print(f"[{self.agent_name}] [ATLANDI] Hash zaten var.")
                        else:
                            if h: existing_hashes.add(h)
                            scrape_json["scraped_pages"].append(scraped_result)
                            print(f"[{self.agent_name}] ✓ İlan kazındı: {url[:80]}")
                        
                    except Exception as e:
                        print(f"[{self.agent_name}] Hata ({url}): {e}")
                    finally:
                        try:
                            await new_page.close()
                        except: pass
                    
                    # İlanlar ARASINDA insan benzeri bekleme (8-15sn rastgele)
                    if index < len(sahibinden_targets[:5]) - 1:
                        import random
                        delay = random.uniform(8, 15)
                        print(f"[{self.agent_name}] Sonraki ilana geçmeden {delay:.1f}sn bekleniyor...")
                        await asyncio.sleep(delay)
                
                # Diğer hedefleri paralel işle (Sahibinden olmayan)
                if other_targets:
                    print(f"[{self.agent_name}] Sahibinden dışı {len(other_targets)} URL paralel işlenecek.")
                    semaphore = asyncio.Semaphore(3)
                    async def _bound_other(i, t):
                        async with semaphore:
                            return await _process_target(i, t, context)
                    tasks = [_bound_other(i, t) for i, t in enumerate(other_targets)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for res in results:
                        if isinstance(res, Exception) or not res: continue
                        if res and res["result"]:
                            h = res["hash"]
                            if h and h in existing_hashes: continue
                            if h: existing_hashes.add(h)
                            scrape_json["scraped_pages"].append(res["result"])
            
            elif "Lokal" in pipeline_type or "Local Business" in pipeline_type:
                # Lokal Aramalar için sıralı işle
                print(f"[{self.agent_name}] Local Business: URL'ler sirayla islenecek.")
                for index, target in enumerate(targets[:6]):
                    res = await _process_target(index, target, context)
                    if res and res["result"]:
                        h = res["hash"]
                        if h and h in existing_hashes: continue
                        if h: existing_hashes.add(h)
                        scrape_json["scraped_pages"].append(res["result"])
            else:
                # Diğer pipeline'lar paralel
                print(f"[{self.agent_name}] Paralel kazıma başlatılıyor.")
                semaphore = asyncio.Semaphore(5)
                async def _bound_process(index, target):
                    async with semaphore:
                        return await _process_target(index, target, context)
                tasks = [_bound_process(i, t) for i, t in enumerate(targets)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception) or not res: continue
                    if res and res["result"]:
                        h = res["hash"]
                        if h and h in existing_hashes: continue
                        if h: existing_hashes.add(h)
                        scrape_json["scraped_pages"].append(res["result"])
                        
            if not using_cdp:
                await browser.close()
            
        self._save_scrape_data(scrape_json)
        total_scraped = len(scrape_json['scraped_pages'])
        print(f"[{self.agent_name}] Kazima tamamlandi. Basarili: {total_scraped} -> data/scrape.json")
        tracer.set_results(
            _AGENT_KEY,
            scrape_json["scraped_pages"],
            extra_meta={"pipeline": pipeline_type, "total_targets": len(targets)},
        )
        tracer.log(_AGENT_KEY, f"{total_scraped}/{len(targets)} URL başarıyla kazındı → scrape.json", "success")

    async def execute(self):
        await self.run()

if __name__ == "__main__":
    agent = ScraperAgent()
    asyncio.run(agent.execute())
