import asyncio
import json
import random
import re
from playwright.async_api import async_playwright

class ScrapingAgent:
    def __init__(self, headless=False):
        self.agent_name = "browsing_scraping_agent"
        self.headless = headless

    def normalize_rank(self, rank_str):
        """
        THE sitesindeki farklı ranking formatlarını {min, max, mid} sözlüğü olarak döner.
        Örn: "120th" -> {min: 120, max: 120, mid: 120}
        "201–250" -> {min: 201, max: 250, mid: 225}
        "1001+" -> {min: 1001, max: 1001, mid: 1001}
        """
        if not rank_str:
            return None
        
        # Temizleme
        rank_str = rank_str.strip().replace('=', '').replace('th', '')
        
        # Aralık varsa (– veya - işareti)
        range_match = re.search(r"(\d+)[–-](\d+)", rank_str)
        if range_match:
            val1 = int(range_match.group(1))
            val2 = int(range_match.group(2))
            return {
                "min": val1,
                "max": val2,
                "mid": (val1 + val2) // 2
            }
            
        # '+' varsa
        if '+' in rank_str:
            num_match = re.search(r"(\d+)", rank_str)
            val = int(num_match.group(1)) if num_match else None
            return {"min": val, "max": val, "mid": val} if val else None
            
        # Düz sayı
        num_match = re.search(r"(\d+)", rank_str)
        if num_match:
            val = int(num_match.group(1))
            return {"min": val, "max": val, "mid": val}
            
        return None

    async def human_scroll(self, page):
        """Daha yavaş ve duraksamalı insan benzeri kaydırma simülasyonu."""
        print(f"[{self.agent_name}] Sayfa inceleniyor (yavaş kaydırma)...")
        # Sayfanın en altına kadar yavaş yavaş in
        total_height = await page.evaluate("document.body.scrollHeight")
        current_pos = 0
        while current_pos < total_height:
            scroll_step = random.randint(300, 600)
            current_pos += scroll_step
            await page.mouse.wheel(0, scroll_step)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            # Her birkaç adımda bir durup bekle (okuma simülasyonu)
            if random.random() < 0.2:
                await asyncio.sleep(random.uniform(1.0, 2.0))
            # Dinamik olarak değişen yüksekliği tekrar kontrol et
            total_height = await page.evaluate("document.body.scrollHeight")

    async def scrape_the_school(self, url, school_name="Bilinmeyen Okul"):
        result = {
            "school_name": school_name,
            "world_rank": None,
            "subjects": [],
            "status": "partial"
        }
        
        async with async_playwright() as p:
            # Tarayıcıyı başlat
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )
            
            page = await context.new_page()
            # Stealth script
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            try:
                print(f"[{self.agent_name}] Sayfa yükleniyor: {url}")
                await page.goto(url, wait_until="load", timeout=60000)
                await asyncio.sleep(5) # JS render bekleyişi
                
                # Cookie Kabul (Opsiyonel)
                try:
                    cookie_btn = page.locator('button:has-text("Accept"), button:has-text("Kabul")').first
                    if await cookie_btn.is_visible():
                        await cookie_btn.click()
                except: pass

                # Slider öğelerini bekle
                try:
                    await page.wait_for_selector('.react-horizontal-scrolling-menu--item', timeout=10000)
                except:
                    pass
                
                slider_items = page.locator('.react-horizontal-scrolling-menu--item')
                count = await slider_items.count()
                print(f"[{self.agent_name}] Bulunan slider öğesi sayısı: {count}")
                
                for i in range(count):
                    item = slider_items.nth(i)
                    try:
                        name_locator = item.locator('span.css-1lk1zhk, h4 span').first
                        val_locator = item.locator('span.css-13clqac, h4 span').last
                        
                        if await name_locator.is_visible() and await val_locator.is_visible():
                            name_text = await name_locator.inner_text()
                            val_text = await val_locator.inner_text()
                            normalized_val = self.normalize_rank(val_text)
                            
                            if "World University Rankings" in name_text or "Dünya Üniversite Sıralamaları" in name_text:
                                result["world_rank"] = normalized_val
                            else:
                                clean_name = re.sub(r'\s+202\d', '', name_text).strip()
                                result["subjects"].append({"name": clean_name, "rank": normalized_val})
                    except: continue
                
                if result["world_rank"] or result["subjects"]:
                    result["status"] = "success"
                else:
                    result["status"] = "no_data_found"
                    
            except Exception as e:
                print(f"[{self.agent_name}] HATA: {e}")
                result["status"] = "error"
                result["message"] = str(e)
            finally:
                await browser.close()
                
        return result

    async def run(self, input_data):
        """
        Main entry point for Scraping Agent.
        input_data: {"school_name": "...", "the_url": "..."}
        """
        url = input_data.get("the_url")
        school = input_data.get("school_name", "Bilinmeyen Okul")
        
        if not url:
            return {"status": "error", "message": "URL sağlanmadı."}
            
        print(f"\n--- Scraping Başlatıldı: {school} ---")
        return await self.scrape_the_school(url, school)
