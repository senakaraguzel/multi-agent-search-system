import asyncio
import json
import os
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from agents.utils.scraping_utils import generate_html_hash, remove_boilerplate, parse_tables

class BaseScraper:
    """Temel Scraper sinifi. Diger butun Scraper'lar bundan turer."""
    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        raise NotImplementedError("Bu metot alt siniflarda ezilmeli (override)")

class SpecificScraper(BaseScraper):
    """Nokta atisi veri ceken (RegEx, Table, JS-rendered) sinif."""
    def __init__(self):
        super().__init__("SpecificScraper")
        
    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] Spesifik (Tablo/Skor) kazimasi yapiliyor: {target_url}")
        
        # Önce networkidle ile dene (JS render için), başarısız olursa domcontentloaded
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=20000)
        except Exception:
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                # JS render için ekstra bekleme
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"[{self.agent_name}] Navigasyon hatasi (devam ediliyor): {e}")
        
        html_content = await page.content()
        html_hash = generate_html_hash(html_content)
        
        # HTML tablolarını çıkar
        tables = parse_tables(html_content)
        
        # JS render edilmiş görünür metni de çıkar (goal.com, mackolik gibi SPA siteler için)
        visible_text = ""
        try:
            visible_text = await page.evaluate("document.body.innerText")
        except Exception:
            pass
        
        # Her iki kaynaktan da metin al, uzun olanı tercih et
        boilerplate_text = remove_boilerplate(html_content)
        combined_text = visible_text if len(visible_text) > len(boilerplate_text) else boilerplate_text
        
        return {
             "url": target_url,
             "metadata": metadata,
             "html_snapshot_hash": html_hash,
             "scrape_confidence": 0.85 if tables else (0.6 if len(combined_text) > 500 else 0.3),
             "structured_blocks": tables,
             "extracted_text": combined_text[:5000]  # Filtreleme ajanı için tam metin
        }


class CategoricScraper(BaseScraper):
    """Haber/Blog gibi uzun yazi (Boilerplate removal) ceken sinif."""
    def __init__(self):
        super().__init__("CategoricScraper")
        
    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] Kategorik (Makale/Haber) kazimasi yapiliyor: {target_url}")
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"[{self.agent_name}] Navigasyon hatasi (devam ediliyor): {e}")
        html_content = await page.content()
        html_hash = generate_html_hash(html_content)
        
        clean_text = remove_boilerplate(html_content)
        
        return {
             "url": target_url,
             "metadata": metadata,
             "html_snapshot_hash": html_hash,
             "scrape_confidence": 0.9 if len(clean_text) > 300 else 0.3,
             "extracted_text": clean_text
        }

class LocalScraper(BaseScraper):
    """Firma, Harita ve Puanlama verilerini ceken (Google Maps DOM) sinif."""
    def __init__(self):
        super().__init__("LocalScraper")
        
    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] Lokal (Firma/Harita) kazimasi yapiliyor: {target_url}")
        
        # Google Maps JavaScript render gerektirir — networkidle + ekstra bekleme
        try:
            await page.goto(target_url, wait_until="networkidle", timeout=25000)
        except Exception:
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(4000)  # Maps JS render için ekstra bekleme
            except Exception as e:
                print(f"[{self.agent_name}] Navigasyon hatasi: {e}")
        
        # Sayfanın tamamen render olması için bekle
        try:
            await page.wait_for_selector("h1, div.fontHeadlineLarge", timeout=8000)
        except Exception:
            pass  # Yüklenemediyse devam et
        
        html_content = await page.content()
        html_hash = generate_html_hash(html_content)
        
        # JSON-LD structured data
        json_ld_blocks = []
        js_locs = await page.locator("script[type='application/ld+json']").all()
        for loc in js_locs:
             try:
                 txt = await loc.inner_text()
                 json_ld_blocks.append(json.loads(txt))
             except:
                 pass
                 
        # Ekrandaki görünür metin
        visible_text = ""
        try:
             visible_text = await page.evaluate("document.body.innerText")
        except Exception as e:
             print(f"[{self.agent_name}] Visible text alinirken hata: {e}")
             
        # Özel Google Maps Metadata Çıkarımı
        extracted_data = {
            "company_name": metadata.get("name", ""),
            "address": "",
            "phone": "",
            "rating": metadata.get("rating"),
            "reviews_count": metadata.get("reviews_count"),
            "category": ""
        }
        
        try:
            # 1. Firma Adı — Google Maps h1 veya div.fontHeadlineLarge
            for selector in ["h1", "div.fontHeadlineLarge"]:
                name_el = await page.query_selector(selector)
                if name_el:
                    text = (await name_el.inner_text()).strip()
                    if text:
                        extracted_data["company_name"] = text
                        break
                
            # 2. Adres
            for selector in ['button[data-item-id="address"]', 'div[data-item-id="address"]']:
                address_el = await page.query_selector(selector)
                if address_el:
                    extracted_data["address"] = (await address_el.inner_text()).strip()
                    break
                
            # 3. Telefon
            for selector in ['button[data-item-id^="phone:"]', 'button[data-item-id^="oloc!"]', 'a[href^="tel:"]']:
                phone_el = await page.query_selector(selector)
                if phone_el:
                    text = await phone_el.inner_text()
                    if not text:
                        text = await phone_el.get_attribute("href") or ""
                        text = text.replace("tel:", "")
                    extracted_data["phone"] = text.strip()
                    break
                
            # 4. Rating (birden fazla selector dene)
            for selector in ['div.F7nice > span[aria-hidden="true"]', 'div.fontBodyMedium span[aria-hidden="true"]', 'span.MW4etd']:
                rating_el = await page.query_selector(selector)
                if rating_el:
                    text = (await rating_el.inner_text()).strip()
                    if text and any(c.isdigit() for c in text):
                        extracted_data["rating"] = text
                        break
            
            # 5. Kategori
            category_el = await page.query_selector("button.DkEaL")
            if category_el:
                extracted_data["category"] = (await category_el.inner_text()).strip()
                
        except Exception as e:
            print(f"[{self.agent_name}] DOM cikarimi sirasinda hata: {e}")
            
        # Metadata önceliği — sayfadan alınamadıysa metadata kullan
        if metadata.get("rating") and not extracted_data["rating"]:
            extracted_data["rating"] = metadata.get("rating")
        if metadata.get("name") and not extracted_data["company_name"]:
            extracted_data["company_name"] = metadata.get("name")
                  
        return {
             "url": target_url,
             "metadata": metadata,
             "extracted_entity": extracted_data,
             "html_snapshot_hash": html_hash,
             "scrape_confidence": 0.95 if extracted_data["company_name"] else 0.4,
             "extracted_json_ld": json_ld_blocks,
             "extracted_text": visible_text[:5000]
        }

class GenericScraper(BaseScraper):
    """Bilet, E-ticaret listelemeleri icin calisan genel kaziyici sinif."""
    def __init__(self):
        super().__init__("GenericScraper")
        
    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] Jenerik (Liste/Kart) kazimasi yapiliyor: {target_url}")
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print(f"[{self.agent_name}] Navigasyon hatasi (devam ediliyor): {e}")
        html_content = await page.content()
        html_hash = generate_html_hash(html_content)
        
        return {
             "url": target_url,
             "metadata": metadata,
             "html_snapshot_hash": html_hash,
             "scrape_confidence": 0.7,
             "extracted_text": remove_boilerplate(html_content)[:5000]
        }



class LinkedInScraper(BaseScraper):
    """LinkedIn profil sayfalarini AuthManager ve session cookie'leri ile kaziyan ozel sinif."""
    def __init__(self):
        super().__init__("LinkedInScraper")
        from utils.auth_manager import AuthManager
        self.auth_manager = AuthManager()

    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] LinkedIn Profili kaziniyor: {target_url}")
        
        # Cookie'leri scraper sayfasina da bas
        context = page.context
        await context.add_cookies(self.auth_manager.get_cookies())
        
        # Stealth evasion is already applied globally by ScraperAgent during page initialization.
        
        # Validasyon ve Strict LinkedIn rate limiting (5-8 profiles / min)
        await self.auth_manager.throttle_linkedin()
        
        # Stealth navigasyon
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await self.auth_manager.simulate_human_reading(page)
        await self.auth_manager.simulate_human_scroll(page, scrolls=2)
        
        is_valid = await self.auth_manager.check_session_validity(page)
        if not is_valid:
             print(f"[{self.agent_name}] UYARI: Oturum dusmus olabilir. Veriler eksik gelebilir.")
             
        html_content = await page.content()
        html_hash = generate_html_hash(html_content)
        
        extracted_data = {
            "name": None,
            "title": None,
            "company": None,
            "location": None,
            "profile_url": target_url
        }
        
        try:
            # Profil DOM'un inmesini bekle
            try:
                await page.wait_for_selector('h1, section[componentkey*="Topcard"], div[data-view-name*="profile-top-card"]', timeout=20000)
            except:
                pass
                
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            
            # --- SDUI Parsing Strategy (Firefox/Mobile View) ---
            # 1. NAME & TOP CARD
            top_card_section = soup.select_one("section[componentkey*='Topcard']")
            if not top_card_section:
                top_card_section = soup.select_one("div[data-view-name*='profile-top-card']")
            
            if top_card_section:
                # Name
                name_elem = top_card_section.select_one("h1, h2")
                if name_elem:
                    extracted_data["name"] = name_elem.get_text(strip=True)
                
                # Title & Location (P tags)
                ps = top_card_section.select("p")
                texts = [p.get_text(strip=True) for p in ps if p.get_text(strip=True)]
                
                if len(texts) >= 1:
                    extracted_data["title"] = texts[0]
                
                if len(texts) >= 2:
                    # Location Heuristic
                    for t in texts[1:]:
                        if any(x in t for x in [",", "Türkiye", "Turkey", "Istanbul", "Ankara", "Izmir"]):
                            extracted_data["location"] = t
                            break
                    if not extracted_data["location"]:
                        extracted_data["location"] = texts[-1] if len(texts) > 2 else texts[1]

            # 2. COMPANY (From Experience Section)
            exp_section = soup.select_one("section[componentkey*='ExperienceTopLevelSection']")
            if exp_section and not extracted_data["company"]:
                first_logo = exp_section.select_one("figure")
                if first_logo and first_logo.get("aria-label"):
                     label = first_logo.get("aria-label")
                     extracted_data["company"] = label.replace(" logosu", "").replace(" logo", "").strip()
            
            # --- Fallback: Standard Async Selectors (Desktop/Old View) ---
            if not extracted_data["name"]:
                name_el = await page.query_selector("h1.text-heading-xlarge, h1.text-heading-large")
                if name_el:
                    extracted_data["name"] = (await name_el.inner_text()).strip()
                else:
                    title = await page.title()
                    if title:
                        parts = title.split(" | ")
                        if len(parts) > 0:
                            extracted_data["name"] = parts[0].split(" - ")[0]

            if not extracted_data["title"]:
                title_el = await page.query_selector("div.text-body-medium.break-words")
                if title_el:
                    extracted_data["title"] = (await title_el.inner_text()).strip()

            if not extracted_data["company"]:
                company_el = (await page.query_selector("button[aria-label*='Şu anki çalıştığı şirket']")) or \
                             (await page.query_selector("div[aria-label*='Şu anki çalıştığı şirket']")) or \
                             (await page.query_selector("button[aria-label*='Current company']")) or \
                             (await page.query_selector(".pv-text-details__right-panel li:first-child"))
                if company_el:
                    text = (await company_el.inner_text()).strip()
                    text = text.replace("Şu anki çalıştığı şirket:", "").replace("Current company:", "").strip()
                    extracted_data["company"] = text

            if not extracted_data["location"]:
                location_el = await page.query_selector("span.text-body-small.inline.t-black--light.break-words")
                if location_el:
                    extracted_data["location"] = (await location_el.inner_text()).strip()

            # --- FALLBACK: Title Parsing ---
            if not extracted_data.get("company") and extracted_data.get("title"):
                title_lower = extracted_data["title"].lower()
                separator = None
                if " at " in title_lower:
                    separator = " at "
                elif " @ " in title_lower:
                    separator = " @ "
                
                if separator:
                    parts = re.split(f"{separator}", extracted_data["title"], flags=re.IGNORECASE)
                    if len(parts) > 1:
                        company_from_title = parts[-1].strip()
                        company_from_title = company_from_title.split("|")[0].strip()
                        extracted_data["company"] = company_from_title

        except Exception as e:
            print(f"[{self.agent_name}] Eleman cikarimi sirasinda hata: {e}")
            
        confidence = 0.95 if extracted_data["name"] else 0.4
            
        return {
             "url": target_url,
             "metadata": metadata,
             "extracted_entity": extracted_data,
             "html_snapshot_hash": html_hash,
             "scrape_confidence": confidence,
             "extracted_text": "" # DOM mapping yeterli, kaba metne gerek yok
        }

class ScraperRouter:
    """search.json'dan gelen pipeline bilgisine gore URL'yi dogru kaziyiciya paslar."""
    def __init__(self):
        self.specific = SpecificScraper()
        self.categoric = CategoricScraper()
        self.local = LocalScraper()
        self.generic = GenericScraper()
        self.linkedin = LinkedInScraper()
        self.sahibinden = SahibindenScraper()
        self.biletix = BiletixScraper()
        
    def route(self, pipeline: str, url: str = "") -> BaseScraper:
        url_lower = url.lower()
        pipeline_lower = pipeline.lower()
        
        # 1. Oncelik: Temel Arama Pipeline'i (Eger spesifik veya kategorik vs. ise mini-agenta bolme)
        if "spe" in pipeline_lower:
             return self.specific
        elif "kat" in pipeline_lower or "cat" in pipeline_lower:
             return self.categoric
        elif "lokal" in pipeline_lower or "local" in pipeline_lower:
             return self.local
             
        # 2. Oncelik: Eger pipeline 'Generic' ise, platform tabanli yonlendirme
        if "linkedin.com/in/" in url_lower or "linkedin.com/pub/" in url_lower:
             return self.linkedin
        elif "sahibinden.com" in url_lower:
             return self.sahibinden
        elif "biletix.com" in url_lower:
             return self.biletix
             
        # Hicbiri degilse standart Jenerik Liste Kaziyici
        return self.generic

class SahibindenScraper(BaseScraper):
    """
    Sahibinden ilan (araba, emlak, vb) verilerini kazan Ozel Scraper.
    Aşırı hızlı çalışması için route.abort() ile gereksiz dosyaları (resim, css) durdurur.
    Exponential backoff ve CAPTCHA Bypass (AuthManager) içerir.
    """
    def __init__(self):
        super().__init__("SahibindenScraper")
        from utils.auth_manager import AuthManager
        self.auth_manager = AuthManager()

    async def _abort_unnecessary_resources(self, route):
        """Hız ve Stealth için resim/css yüklemesini kestiğimiz kanca."""
        try:
            if route.request.resource_type in ["image", "media", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()
        except:
             pass

    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] Sahibinden İlan Verisi Çekiliyor: {target_url}")
        
        # Gereksiz kaynakları engelle
        try: await page.route("**/*", self._abort_unnecessary_resources)
        except: pass
        
        from utils.network_retry import with_retry
        
        @with_retry(max_retries=3, base_backoff=5)
        async def fetch_and_extract():
            # WebDriver Override
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Dinamik Referer
            referers = ["https://www.sahibinden.com/arama", "https://www.sahibinden.com/", "https://www.google.com/"]
            chosen_referer = __import__('random').choice(referers)
            
            await page.goto(target_url, referer=chosen_referer, wait_until="domcontentloaded", timeout=60000)
            
            # Anti-Bot (Checkbox veya Hold Captcha asimi)
            await self.auth_manager.solve_captcha(page)
            await self.auth_manager.simulate_human_reading(page)
            
            # Yavas kaydir ki ilan acilsin
            await self.auth_manager.simulate_human_scroll(page, scrolls=2)
            
            html_content = await page.content()
            html_hash = generate_html_hash(html_content)
            
            extracted_data = {}
            
            # 1. Başlık
            title_el = await page.query_selector("div.classifiedDetailTitle h1")
            extracted_data["title"] = (await title_el.inner_text()).strip() if title_el else None
            
            # 2. Fiyat
            price_el = await page.query_selector(".classifiedInfo h3")
            extracted_data["price"] = (await price_el.inner_text()).strip() if price_el else None
            
            # 3. Lokasyon (Breadcrumb misali)
            locs = await page.evaluate('''() => {
                const elems = document.querySelectorAll('div.classifiedInfo > h2 > a');
                return Array.from(elems).map(el => el.innerText.trim());
            }''')
            extracted_data["location"] = " / ".join(locs) if locs else None
            
            # 4. Dinamik Info Listesi (Yıl, Kilometre, Oda Sayısı, Emlak Tipi vs)
            info_list = await page.locator("ul.classifiedInfoList li").all()
            for li in info_list:
                try:
                    label = (await li.locator("strong").inner_text()).strip()
                    value = (await li.locator("span").inner_text()).strip()
                    
                    # Anahtari normalize et (örn: 'Motor Hacmi' -> 'motor_hacmi')
                    key = label.lower().replace("ç","c").replace("ğ","g").replace("ı","i").replace("ö","o").replace("ş","s").replace("ü","u")
                    key = key.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "").replace("/", "_")
                    extracted_data[key] = value
                except:
                    pass
                    
            # 5. İlan Açıklaması (Sadece birazını al)
            desc_el = await page.query_selector("#classifiedDescription")
            extracted_data["description"] = (await desc_el.inner_text()).strip()[:400] if desc_el else None

            confidence = 0.95 if extracted_data.get("title") else 0.4
            
            return {
                 "url": target_url,
                 "metadata": metadata,
                 "extracted_entity": extracted_data,
                 "html_snapshot_hash": html_hash,
                 "scrape_confidence": confidence,
                 "extracted_text": ""
            }
            
        try:
             result = await fetch_and_extract()
             return result
        except Exception as e:
             print(f"[{self.agent_name}] Fetch & Extract tum retries sonrasi HATA: {e}")
             return {
                 "url": target_url,
                 "metadata": metadata,
                 "extracted_entity": {"error": str(e)},
                 "html_snapshot_hash": "",
                 "scrape_confidence": 0.0,
                 "extracted_text": ""
             }

class BiletixScraper(BaseScraper):
    """Biletix ozel etkinlik sayfalarini scroll ederek gecmis/gelecek programlari toplar."""
    def __init__(self):
        super().__init__("BiletixScraper")

    async def scrape(self, page, target_url: str, metadata: dict) -> dict:
        print(f"[{self.agent_name}] Biletix Etkinlik Sayfasi Kaziniyor: {target_url}")
        
        try:
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            
            # Popup kapatimlari
            try:
                alert_btn = page.locator("button.onetrust-close-btn-handler")
                if await alert_btn.is_visible(timeout=3000):
                    await alert_btn.click()
            except:
                pass
                
            # Scroll to load everything
            print(f"[{self.agent_name}] Lazy load (resimler/etkinlikler) icin asagi iniliyor...")
            for i in range(5):
                await page.evaluate("window.scrollBy(0, document.body.scrollHeight / 5)")
                await asyncio.sleep(1.0)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2.0)
            
            # Etkinlikleri Heuristic Olarak DOM'dan Bul ve Cikar
            print(f"[{self.agent_name}] DOM analizi ile etkinlik kartlari cikariliyor...")
            extracted_events_raw = await page.evaluate('''() => {
                let items = [];
                // 1. Taktik: 'Satışta' veya 'Tükendi' ibaresi olan etiketlerin ebeveynlerini bul (Kartlar)
                const badges = Array.from(document.querySelectorAll('span, div, a')).filter(el => {
                    const txt = el.innerText ? el.innerText.trim().toLowerCase() : "";
                    return (txt === 'satışta' || txt === 'tükendi') && el.children.length === 0;
                });
                
                if (badges.length > 0) {
                    badges.forEach(b => {
                        let card = b.closest('div.card') || b.closest('li') || b.closest('.event-list-item') || b.parentElement.parentElement;
                        if (card && !items.includes(card)) items.push(card);
                    });
                }
                
                // 2. Taktik (Fallback): Standart class isimleri
                if (items.length === 0) {
                    items = Array.from(document.querySelectorAll('.event-list-item, div.card, li.searchResultListing, div[class*="event-item"]'));
                }
                
                return items.map(el => {
                    let url = null;
                    const linkEl = el.querySelector('a');
                    if (linkEl) url = linkEl.getAttribute('href');
                    if (url && !url.startsWith('http')) url = 'https://www.biletix.com' + url;
                    
                    return {
                        text: el.innerText.trim(),
                        url: url
                    };
                }).filter(o => o.text.length > 5);
            }''')
            
            events = []
            for item in extracted_events_raw:
                lines = [line.strip() for line in item["text"].splitlines() if line.strip()]
                events.append({
                    "raw_title_or_date": lines[0] if lines else "Unknown",
                    "full_item_text": "\\n".join(lines),
                    "event_url": item["url"]
                })
                
            print(f"[{self.agent_name}] Toplam {len(events)} etkinlik ayiklandi.")
                    
            html_content = await page.content()
            html_hash = generate_html_hash(html_content)
            
            # Sayfa ozel baslik (fallback)
            page_title = await page.title()
            
            return {
                 "url": target_url,
                 "metadata": metadata,
                 "extracted_entity": {
                     "page_title": page_title,
                     "event_count": len(events),
                     "events_list": events
                 },
                 "html_snapshot_hash": html_hash,
                 "scrape_confidence": 0.9 if events else 0.4,
                 "extracted_text": ""
            }
            
        except Exception as e:
             print(f"[{self.agent_name}] HATA: {e}")
             return {
                 "url": target_url,
                 "metadata": metadata,
                 "extracted_entity": {"error": str(e)},
                 "html_snapshot_hash": "",
                 "scrape_confidence": 0.0,
                 "extracted_text": ""
             }
