"""
Scraping Agent - LinkedIn Şirket Sayfası Detaylı Veri Çekici
=============================================================
Kendisine iletilen LinkedIn şirket URL'sinden kapsamlı şirket bilgilerini scrape eder.
Oturum açma işlemi linkedin_cookies.json üzerinden gerçekleştirilir.
"""

import asyncio
import json
import os
import re
import datetime
import random
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()


class ScrapingAgent:
    def __init__(self, cookies_path="linkedin_cookies.json", headless=True):
        self.cookies_path = cookies_path
        self.headless = headless
        self.results_path = "scraping_results.json"

    async def _get_browser_context(self, playwright):
        """Oturum açık tarayıcı bağlamı oluşturur."""
        browser = await playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100,
            channel="chrome",  # Güvenlik duvarına takılmamak için standart Chrome kullanımı
            args=["--disable-blink-features=AutomationControlled"]
        )

        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 768},
            "locale": "en-US",
            "timezone_id": "Europe/Istanbul",
            "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"}
        }

        state_path = "linkedin_state.json"
        use_old_cookies = False

        if os.path.exists(state_path):
            context_args["storage_state"] = state_path
        else:
            use_old_cookies = True

        context = await browser.new_context(**context_args)

        if not use_old_cookies:
            print("✓ Oturum 'linkedin_state.json' üzerinden (Tam Storage State) yüklendi.")
        else:
            # Önce LinkedIn ana sayfasına git (cookie domain'ini doğru tanımak için zorunlu)
            page = await context.new_page()
            await page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1)
            await page.close()
            
            # Cookie'leri yükle - domain .linkedin.com olarak normalize et
            if os.path.exists(self.cookies_path):
                try:
                    with open(self.cookies_path, "r", encoding="utf-8") as f:
                        cookies_data = json.load(f)
                        if isinstance(cookies_data, list):
                            normalized = []
                            for c in cookies_data:
                                nc = dict(c)
                                nc["domain"] = ".linkedin.com"
                                # sameSite değerini Playwright'a uygun forma çevir
                                if nc.get("sameSite") == "None":
                                    nc["sameSite"] = "None"
                                normalized.append(nc)
                            await context.add_cookies(normalized)
                            print(f"✓ {len(normalized)} çerez yüklendi (Eski Yöntem).")
                except Exception as e:
                    print(f"⚠ Çerez yükleme hatası: {e}")

        return browser, context

    async def _check_and_recover_login(self, page):
        """
        Sayfanın login/authwall sayfasına düşüp düşmediğini kontrol eder.
        Düşmüşse JS ile cookie enjekte ederek kurtarmayı dener.
        Başarılıysa True, hala login ekranındaysa False döner.
        """
        current_url = page.url
        if "login" in current_url or "authwall" in current_url or "signup" in current_url:
            print(f"⚠ Login sayfasına düşüldü, JS injection ile oturum kurtarılmaya çalışılıyor...")
            try:
                # 1. li_at cookie'sini oku
                li_at_val = None
                with open(self.cookies_path, "r", encoding="utf-8") as f:
                    cookies_data = json.load(f)
                    for c in cookies_data:
                        if c.get("name") == "li_at":
                            li_at_val = c.get("value")
                            break
                
                # 2. Varsa JS ile enjekte et ve reload at
                if li_at_val:
                    await page.evaluate(f'document.cookie = "li_at={li_at_val}; domain=.linkedin.com; path=/";')
                    await asyncio.sleep(1)
                    print("  ✓ Cookie JS ile enjekte edildi, sayfa yenileniyor...")
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(random.uniform(4, 6))
                
                # 3. Tekrar kontrol et
                if "login" in page.url or "authwall" in page.url or "signup" in page.url:
                    return False, f"LinkedIn oturum açma sayfasına yönlendirildi: {page.url}"
                else:
                    print("  ✓ Oturum kurtarma BAŞARILI!")
                    return True, None
            except Exception as e:
                return False, f"Oturum kurtarma hatası: {e}"
        return True, None

    async def _safe_text(self, page, selectors, default=""):
        """Birden fazla selektör deneyerek metin çeker."""
        if isinstance(selectors, str):
            selectors = [selectors]
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if await loc.count() > 0:
                    text = await loc.inner_text(timeout=5000)
                    text = text.strip()
                    if text:
                        return text
            except Exception:
                continue
        return default

    async def _safe_attr(self, page, selector, attr, default=""):
        """Bir selektörden belirli bir özellik değeri çeker."""
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0:
                val = await loc.get_attribute(attr, timeout=5000)
                return val.strip() if val else default
        except Exception:
            pass
        return default

    async def _human_scroll(self, page):
        """İnsan benzeri yavaş ve rastgele scroll hareketi yapar."""
        for _ in range(3):
            scroll_amount = random.randint(300, 700)
            await page.mouse.wheel(0, scroll_amount)
            await asyncio.sleep(random.uniform(0.5, 1.5))

    async def scrape_company(self, url):
        """
        LinkedIn şirket URL'inden kapsamlı veri çeker.
        Akış: Ana sayfa (Top Card: Tagline, Followers) -> About sayfası (Detaylar)
        """
        base_company_url = url.rstrip("/")
        if "/about" in base_company_url:
            base_company_url = base_company_url.replace("/about", "")
        
        main_url = f"{base_company_url}?locale=en_US"
        about_url = f"{base_company_url}/about/?locale=en_US"
        
        print(f"\n{'='*60}")
        print(f"Scraping Başlatıldı: {base_company_url}")
        print(f"{'='*60}")

        result = {
            "url": url,
            "scraped_at": datetime.datetime.now().isoformat(),
            "name": "",
            "tagline": "",
            "about": "",
            "website": "",
            "industry": "",
            "company_size": "",
            "headquarters": "",
            "type": "",
            "founded": "",
            "specialties": [],
            "followers": "",
            "employees_on_linkedin": "",
            "locations": [],
            "error": None
        }

        # Etiket Haritası (Genişletilmiş ve Dil Destekli)
        LABEL_MAP = {
            "website": ["Website", "Web sitesi", "Web Sitesi", "Site"],
            "industry": ["Industry", "Sektör", "Endüstri"],
            "company_size": ["Company size", "Şirket büyüklüğü", "Şirket Boyutu"],
            "headquarters": ["Headquarters", "Genel Merkez", "Genel merkez", "Merkez"],
            "type": ["Type", "Tür", "Şirket türü", "Tip"],
            "founded": ["Founded", "Kuruluş", "Kuruluş yılı", "Kurulma"],
            "specialties": ["Specialties", "Uzmanlık Alanları", "Uzmanlık alanları", "Uzmanlıklar"]
        }

        async with async_playwright() as p:
            browser, context = await self._get_browser_context(p)
            page = await context.new_page()

            try:
                # 1. ADIM: Ana Sayfa (Top Card verileri için)
                print(f"1. Adım: Ana sayfa yükleniyor (Top Card)...")
                await page.goto(main_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(3, 5))
                
                # Login kontrolü
                success, error_msg = await self._check_and_recover_login(page)
                if not success:
                    print(f"✗ Login hatası: {error_msg}")
                    result["error"] = error_msg
                    return result

                await self._human_scroll(page)
                
                # Şirket Adı
                result["name"] = await self._safe_text(page, ["h1.org-top-card-summary__title", "h1.t-24", "h1"])
                
                # Tagline (Özel locator)
                result["tagline"] = await self._safe_text(page, [".org-top-card-summary__tagline", "p.t-16.t-black.t-normal.break-words"])

                # Top Card Summary List
                summary_items = await page.locator(".org-top-card-summary-info-list__info-item").all()
                summary_texts = []
                for item in summary_items:
                    txt = (await item.inner_text()).strip()
                    if txt: summary_texts.append(txt)
                
                if summary_texts:
                    # Eğer tagline hala boşsa ilk öğeyi al
                    if not result["tagline"]:
                        result["tagline"] = summary_texts[0]
                    
                    for txt in summary_texts:
                        # Industry tespiti (Rakam içermez, takipçi ya da lokasyon değilse)
                        if not any(x in txt.lower() for x in ["followers", "takipçi", "çalışan", "member", "üye"]):
                            if not any(c.isdigit() for c in txt):
                                if not result["industry"]: result["industry"] = txt
                        
                        # Followers tespiti (Milyon/Bin desteğiyle)
                        f_match = re.search(r'([\d\.,\s]+(?:milyon|million|bin|thousand|K|M)?)\s*(?:followers|takipçi)', txt, re.I)
                        if f_match:
                            result["followers"] = f_match.group(1).strip()
                        
                        # Lokasyon/HQ tespiti
                        if txt != result["tagline"] and txt != result["industry"]:
                            if not any(x in txt.lower() for x in ["followers", "takipçi", "çalışan", "member", "üye"]):
                                if not any(c.isdigit() for c in txt):
                                    if not result["headquarters"]: result["headquarters"] = txt

                print(f"  ✓ Name: {result['name']}")
                print(f"  ✓ Tagline: {result['tagline']}")
                print(f"  ✓ Followers: {result['followers']}")

                # 2. ADIM: About Sayfası (Detaylar için)
                print(f"\n2. Adım: About sayfası yükleniyor...")
                # Bazı durumlarda LinkedIn /about/ linkini reddedebilir, o yüzden URL'yi temiz kontrol et
                await page.goto(about_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(5, 8))
                
                # About sayfasında tekrar login kontrolü
                success, error_msg = await self._check_and_recover_login(page)
                if not success:
                    print(f"  ⚠ About sayfasında login duvarına çarpıldı, kurtarılamadı.")
                
                # 'See more' butonunu daha agresif ara
                try:
                    btn = page.locator("button:has-text('see more'), button:has-text('Devamını gör'), button.lt-line-clamp__more").first
                    if await btn.count() > 0:
                        await btn.scroll_into_view_if_needed()
                        await btn.click()
                        await asyncio.sleep(1)
                except: pass

                # About Metni
                result["about"] = await self._safe_text(page, [
                    ".org-page-details-module__card-spacing p",
                    "p.break-words",
                    "section.artdeco-card p",
                    ".t-14.t-black--light.t-normal"
                ])

                # Detaylar (Daha robust etiket tarama)
                try:
                    all_dts = await page.locator("dt").all()
                    for dt in all_dts:
                        dt_text = (await dt.inner_text()).strip()
                        for key, labels in LABEL_MAP.items():
                            if any(label.lower() in dt_text.lower() for label in labels):
                                # İlgili dt'den sonra gelen dd'yi bul
                                dd = page.locator(f"dt:has-text('{dt_text}') + dd").first
                                if await dd.count() > 0:
                                    val = (await dd.inner_text()).strip()
                                    if val and not result[key]:
                                        if key == "specialties":
                                            result[key] = [s.strip() for s in val.split(',') if s.strip()]
                                        elif key == "company_size":
                                            result[key] = val.split('\n')[0].strip()
                                        else:
                                            result[key] = val
                except Exception as e:
                    print(f"  ⚠ Detay tarama hatası: {e}")

                # Çalışan sayısı linki
                try:
                    emp_text = await self._safe_text(page, "a:has-text('employees on LinkedIn'), a:has-text('çalışan')")
                    if emp_text: result["employees_on_linkedin"] = emp_text
                except: pass

                # Lokasyonlar (Daha kapsamlı tarama)
                try:
                    await page.mouse.wheel(0, 1000) # Biraz daha scroll
                    await asyncio.sleep(1)
                    loc_selectors = [
                        ".org-about-us-location__address",
                        ".org-location-card",
                        "p.t-14.t-black--light.t-normal" # Bazen düz p içinde olur
                    ]
                    all_locations = []
                    for sel in loc_selectors:
                        loc_locs = await page.locator(sel).all()
                        for l in loc_locs:
                            t = (await l.inner_text()).strip()
                            if t and t not in all_locations:
                                all_locations.append(t)
                    
                    result["locations"] = all_locations
                    
                    # Eğer headquarters hala boşsa ilk lokasyonu merkez sayabiliriz (fallback)
                    if not result["headquarters"] and all_locations:
                        result["headquarters"] = all_locations[0]
                except: pass

                # SON ADIM: Veri İyileştirme (Heuristic & Cross-fill)
                
                # 1. Industry Fallback (Tagline'dan çek)
                if not result["industry"] and result["tagline"]:
                    # Tagline genellikle sektörü içerir (Örn: "BT Sistemi Özel Yazılım Geliştirme")
                    # Eğer tagline rakam içermiyorsa ve çok uzun değilse sektördür
                    if len(result["tagline"]) < 100 and not any(c.isdigit() for c in result["tagline"]):
                        result["industry"] = result["tagline"]
                        print(f"  ✓ Industry tagline'dan kopyalandı.")

                # 2. Headquarters ve Locations arası çapraz doldurma
                if result["headquarters"] and not result["locations"]:
                    result["locations"] = [result["headquarters"]]
                elif not result["headquarters"] and result["locations"]:
                    result["headquarters"] = result["locations"][0]

                # 3. Hala boşsa 'about' metninden lokasyon çıkarma denemesi (Gelişmiş)
                if not result["headquarters"] and result["about"]:
                    print("  [*] Lokasyon boş, 'about' metni analiz ediliyor...")
                    text_to_search = result["about"].replace("İ", "i").replace("I", "ı").lower()
                    cities_map = {
                        "istanbul": "İstanbul", "ankara": "Ankara", "izmir": "İzmir", 
                        "bursa": "Bursa", "antalya": "Antalya", "konya": "Konya", 
                        "adana": "Adana", "gaziantep": "Gaziantep", "kocaeli": "Kocaeli", 
                        "mersin": "Mersin", "balıkesir": "Balıkesir", "duzce": "Düzce", "düzce": "Düzce"
                    }
                    for city_key, city_name in cities_map.items():
                        if city_key in text_to_search:
                            result["headquarters"] = city_name
                            if city_name not in result["locations"]:
                                result["locations"].append(city_name)
                            print(f"  ✓ 'about' içinden lokasyon yakalandı: {city_name}")
                            break
                
                # 4. Final Cross-fill (Eğer heuristic bir şey bulduysa tekrar yansıt)
                if result["headquarters"] and not result["locations"]:
                    result["locations"] = [result["headquarters"]]

                print(f"  ✓ Industry: {result['industry']}")
                print(f"  ✓ HQ: {result['headquarters']}")
                print(f"  ✓ Founded: {result['founded']}")
                print(f"\n✓ Scraping TAMAMLANDI: {result['name']}")

            except Exception as e:
                print(f"✗ Scraping hatası: {e}")
                result["error"] = str(e)
            finally:
                await browser.close()

        return result


    def save_result(self, result):
        """Sonucu scraping_results.json dosyasına ekler (Append)."""
        data = []
        if os.path.exists(self.results_path):
            try:
                with open(self.results_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            except Exception:
                data = []
        
        data.append(result)

        with open(self.results_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✓ Sonuç {self.results_path} dosyasına eklendi (Append).")
        return result

    async def run(self, url):
        """Ana akış: scrape et ve kaydet."""
        result = await self.scrape_company(url)
        return self.save_result(result)


if __name__ == "__main__":
    async def main():
        agent = ScrapingAgent(headless=False)
        # Örnek test
        await agent.run("https://www.linkedin.com/company/deloitte")

    asyncio.run(main())
