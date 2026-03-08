import json
import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from agents.utils.execution_tracer import tracer

_AGENT_KEY = "agent_5_5_google_comments"

BASE_DIR = Path(__file__).parent.parent
SCRAPE_JSON = BASE_DIR / "data" / "scrape.json"
SEARCH_JSON = BASE_DIR / "data" / "search.json"

class GoogleCommentAgent:
    def __init__(self):
        self.agent_name = "Agent 5.5 - Google Comment Scraper"

    def _is_local_business_search(self) -> bool:
        """Check if the search pipeline is for local businesses."""
        try:
            with open(SEARCH_JSON, "r", encoding="utf-8") as f:
                search_data = json.load(f)
            return search_data.get("search_intent") == "Local Business Search" or "Lokal" in search_data.get("pipeline", "")
        except Exception:
            return False

    async def _scrape_reviews_for_url(self, page, url: str) -> list:
        try:
            print(f"[{self.agent_name}] Yükleniyor: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # "Tüm yorumlar" sekmesine tıkla veya "Yorumlar" butonunu bul
            # Google Maps genelde "Yorumlar" tab'ına veya button[aria-label*="Yorumlar"]'a sahiptir.
            # Eger tab yoksa, scroll etmesi gerekebilir. Biz dogrudan tab'lara bakalim.
            review_tab_selector = "button[aria-label*='Yorumlar'], button[aria-label*='Reviews'], button[role='tab']:has-text('Yorumlar')"
            try:
                await page.wait_for_selector(review_tab_selector, timeout=5000)
                await page.click(review_tab_selector)
                await page.wait_for_timeout(2000)
            except Exception:
                print(f"[{self.agent_name}] Yorum sekmesi bulunamadı, normal devam ediliyor.")

            # Scroll işlemi için yorum container'ını bul
            # Google Maps'te yorum listesi genelde class="m6QErb DxyBCb kA9KIf dS8AEf"
            # Veya yorumları içeren herhangi bir div scroll edilebilir.
            review_elements_selector = ".jftiEf" # Google Maps review element class
            
            # Yorum sayısı 10'a ulaşana kadar aşağı kaydır
            reviews = []
            for _ in range(5):
                current_count = await page.locator(review_elements_selector).count()
                if current_count >= 10:
                    break
                # Scroll the container
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1000)

            # Yorumları çek
            elements = await page.locator(review_elements_selector).all()
            for el in elements[:10]: # Max 10 reviews
                try:
                    # Daha fazla göster butonu varsa bas
                    more_btn = el.locator("button:has-text('Daha fazla')")
                    if await more_btn.count() > 0:
                        await more_btn.first.click()
                        await page.wait_for_timeout(300)

                    author = await el.locator(".d4r55").inner_text() if await el.locator(".d4r55").count() > 0 else None
                    
                    rating_el = el.locator(".kvMYJc")
                    rating = await rating_el.get_attribute("aria-label") if await rating_el.count() > 0 else None
                    if rating:
                        rating = rating.split(' ')[0] # "5 yıldız" -> "5"

                    date = await el.locator(".rsqaWe").inner_text() if await el.locator(".rsqaWe").count() > 0 else None
                    text_el = el.locator(".wiI7pd")
                    text = await text_el.inner_text() if await text_el.count() > 0 else None

                    if text and len(text.strip()) >= 10:
                        reviews.append({
                            "author": author.strip() if author else None,
                            "rating": rating,
                            "date": date.strip() if date else None,
                            "text": text.strip()
                        })
                except Exception as e:
                    print(f"[{self.agent_name}] Yorum satırı parse edilirken hata: {e}")
                    continue

            print(f"[{self.agent_name}] {len(reviews)} adet yorum başarıyla çekildi.")
            return reviews

        except Exception as e:
            print(f"[{self.agent_name}] Yorumları çekerken hata: {e}")
            return []

    async def _execute(self):
        if not SCRAPE_JSON.exists():
            print(f"[{self.agent_name}] scrape.json bulunamadı. Çıkılıyor.")
            return

        with open(SCRAPE_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not self._is_local_business_search():
            tracer.log(_AGENT_KEY, "Lokal business değil, yorum kazma atlandı", "warning")
            print(f"[{self.agent_name}] Local business araması değil, çıkış yapılıyor.")
            return

        pages = data.get("scraped_pages", [])
        if not pages:
            return

        tracer.log(_AGENT_KEY, f"{len(pages)} kazınan sayfa için yorum taranacak")

        print(f"[{self.agent_name}] Playwright (headless) başlatılıyor...")
        async with async_playwright() as p:
            # Arka planda (headless) çalışması için True yapıldı
            browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="tr-TR"
            )
            page = await context.new_page()

            processed_count = 0
            for i, page_obj in enumerate(pages):
                url = page_obj.get("profile_url") or page_obj.get("url")
                
                # Sadece google maps adreslerine yorum kontrolü
                if not url or "google.com/maps" not in url:
                    continue

                if processed_count >= 6:
                    print(f"[{self.agent_name}] Max 6 yer sınırına ulaşıldı.")
                    break

                reviews = await self._scrape_reviews_for_url(page, url)
                
                if reviews:
                    page_obj["reviews"] = reviews
                    page_obj["reviews_scraped_at"] = datetime.now(timezone.utc).isoformat()
                    page_obj["reviews_source"] = "Google Maps"
                
                processed_count += 1
                
                if processed_count < 6 and i < len(pages) - 1:
                    print(f"[{self.agent_name}] 2 saniye bekleniyor...")
                    await page.wait_for_timeout(2000)

            await browser.close()

        # Güncel scrape.json dosyasını kaydet
        with open(SCRAPE_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[{self.agent_name}] scrape.json güncellendi.")

        all_reviews = [
            r
            for p in data.get("scraped_pages", [])
            for r in (p.get("reviews") or [])
        ]
        tracer.set_results(_AGENT_KEY, all_reviews)
        tracer.log(_AGENT_KEY, f"{len(all_reviews)} toplam yorum kaydedildi → scrape.json güncellendi", "success")

    def run(self):
        asyncio.run(self._execute())
