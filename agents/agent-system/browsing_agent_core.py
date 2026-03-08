import asyncio
from playwright.async_api import async_playwright

from agents.utils.anti_bot_bypass import solve_captcha
from agents.handlers.platform_handlers import route_platform
from agents.utils.llm_browser_control import get_azure_client
import random
import json
from urllib.parse import urlparse
import urllib.parse
from playwright_stealth import Stealth
import re
from datetime import datetime
import dateutil.parser as dparser
import urllib.robotparser
import xml.etree.ElementTree as ET
import httpx

class BaseBrowserAgent:
    """
    Tüm dikey (Specific, Categoric, vs) Browsing Ajanları için temel sınıf.
    Anti-bot korumasını, proxy (gerekirse), stealth modunu ve performansı (kaynak engelleme) yönetir.
    """
    
    def __init__(self, agent_name="base-browser-v1"):
        self.agent_name = agent_name
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        from utils.auth_manager import AuthManager
        self.auth_manager = AuthManager()
        
    async def configure_context(self, browser):
        context = await browser.new_context(
            user_agent=self.auth_manager.USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
            locale="tr-TR",
            timezone_id="Europe/Istanbul"
        )
        return context

    async def create_stealth_page(self, context):
        page = await context.new_page()
        await self.auth_manager.apply_stealth(page)
        return page

    async def safe_goto(self, page, url, timeout=120000):
        try:
            # Önce robots.txt izni kontrol ediliyor:
            if not await self._check_robots_txt(url):
                print(f"[{self.agent_name}] Robots.txt engeli: {url}")
                return False
                
            print(f"[{self.agent_name}] Navigating to (Deep Search): {url}")
            
            # JS Rendered Page Fallback: load yerine önce domcontentloaded, ardından networkidle beklemesi
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            try:
                # React, Vue gibi SPA'ların HTTP call'larını bitirmesi için ekstra bekleme
                await page.wait_for_load_state("networkidle", timeout=15000)
            except:
                print(f"[{self.agent_name}] Networkidle timeout, DOM yuklenmisse kabul edilecek.")
                
            # İnsan simülasyonu süresi
            await page.wait_for_timeout(random.randint(4000, 7500))
            return True
        except Exception as e:
            if "Timeout" in str(e):
                print(f"[{self.agent_name}] Ag yavasligindan timeout alindi ama DOM yuklenmis olabilir, isleme devam ediliyor...")
                return True
            print(f"[{self.agent_name}] Error navigating to {url}: {e}")
            return False

    async def _check_robots_txt(self, url):
        """Deep Search: Robots.txt dosyasını analiz edip hedefe girilip girilemeyeceğini söyler."""
        try:
            parsed_url = urlparse(url)
            
            # Whitelist/Bypass: Google Maps, Sahibinden gibi API veya agresif hedeflerde robots yok say!
            if "google.com" in parsed_url.netloc or "sahibinden" in parsed_url.netloc:
                return True
                
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    rp = urllib.robotparser.RobotFileParser()
                    rp.parse(response.text.splitlines())
                    return rp.can_fetch(random.choice(self.user_agents), url)
            return True # Yoksa veya ulaşılamazsa default izinli varsay
        except:
            return True

    async def _fetch_sitemap_urls(self, base_url):
        """Deep Search: Kök domain'in sitemap.xml dosyasından sayfaları çıkarır."""
        try:
            sitemap_url = urllib.parse.urljoin(base_url, "/sitemap.xml")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(sitemap_url)
                if response.status_code == 200:
                    urls = []
                    root = ET.fromstring(response.content)
                    for child in root:
                        for sub_child in child:
                            if 'loc' in sub_child.tag:
                                urls.append(sub_child.text)
                    print(f"[{self.agent_name}] Sitemap'ten {len(urls)} URL basariyla okundu.")
                    return urls
            return []
        except Exception as e:
             # Site haritası xml değil index olabilir vb. Hatayı yoksay.
             return []

    async def _detect_and_click_pagination(self, page, target_url):
        """
        Deep Search: Sayfalama (Pagination, Next Page) düğmesini tespit eder ve yeni URL döner veya tıklar.
        Şu an sadece 'href' tabanlı next butonlarını tespit ederek o linkleri extraction havuzuna atar.
        """
        try:
            pagination_links = await page.evaluate('''() => {
                let nextLinks = [];
                // Sık kullanılan pagination (ileri/sonraki/next) class veya aria etiketleri
                let selectors = ['a.next', 'a[rel="next"]', 'link[rel="next"]', 'a.page-next', 'li.next a', 'a[aria-label*="Next"]', 'a[aria-label*="İleri"]'];
                
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        if (el.href) nextLinks.push(el.href);
                    });
                });
                return nextLinks;
            }''')
            
            unique_links = list(set(pagination_links))
            if unique_links:
                print(f"[{self.agent_name}] Pagination bulundu: {len(unique_links)} sonraki sayfa linki ayristirildi.")
            return unique_links
        except:
            return []
        """Soyut metod. Alt ajanlar (Specific, vb.) bu metodu ezip kendi mantığını yazacak."""
        raise NotImplementedError("Subclasses must implement run_browsing()")

    async def extract_links(self, page, base_url):
        """Sayfadaki tüm internal (iç) linkleri toplar."""
        extracted = []
        try:
            links = await page.evaluate(
                "Array.from(document.querySelectorAll('a')).map(a => a.href)"
            )
            for href in links:
                if not href:
                    continue
                # Sadece mutlak url'ye çevirip ekle
                absolute_url = urllib.parse.urljoin(base_url, href)
                extracted.append(absolute_url)
        except Exception as e:
            print(f"[{self.agent_name}] Link çıkarma hatası: {e}")
            
        return list(set(extracted))

    async def handle_consent(self, page):
        """Genel çerez onayı / consent popuplarını atlatma metodu."""
        try:
            print(f"[{self.agent_name}] Consent kontrolü yapılıyor...")
            if "consent.google.com" in page.url:
                try:
                    await page.locator("form").locator("button").last.click()
                    return
                except: pass
            
            try:
                dialog = page.locator("div[role='dialog'], div[class*='consent']").first
                if await dialog.is_visible(timeout=3000):
                    accept_btn = dialog.locator("button").filter(has_text="Tümünü kabul et").first
                    if not await accept_btn.is_visible():
                        accept_btn = dialog.locator("button").filter(has_text="Accept all").first
                    if await accept_btn.is_visible():
                        await accept_btn.click()
                        await page.wait_for_timeout(1000)
                        return
                    else:
                        btns = await dialog.locator("button").all()
                        if btns:
                            await btns[-1].click()
                            await page.wait_for_timeout(1000)
                            return
                        span_btn = dialog.locator("span").filter(has_text="Kabul et").first
                        if await span_btn.is_visible():
                            await span_btn.click()
                            return
            except: pass
            
            try:
                consent_btn = await page.wait_for_selector(
                    'button[aria-label="Tümünü kabul et"], button[aria-label="Accept all"]',
                    timeout=2000, state="visible"
                )
                if consent_btn:
                    await consent_btn.click()
                    return
            except: pass
        except Exception as e:
            print(f"[{self.agent_name}] Consent hatası (Önemli Değil): {e}")

    async def _extract_publish_date(self, page):
        """HTML içerisinden meta tagler veya time etiketleri ile yayın tarihini bulur."""
        try:
            date_str = await page.evaluate('''() => {
                let d = document.querySelector('meta[property="article:published_time"]');
                if (d && d.content) return d.content;
                d = document.querySelector('meta[name="pubdate"]');
                if (d && d.content) return d.content;
                d = document.querySelector('time[datetime]');
                if (d && d.getAttribute('datetime')) return d.getAttribute('datetime');
                return null;
            }''')
            return date_str
        except:
            return None

    async def _check_rss_feed(self, page):
        """Sayfada RSS/Atom feed olup olmadığını (meta taglerle dahil) kontrol eder."""
        try:
            has_rss = await page.evaluate('''() => {
                let links = document.querySelectorAll('link[type="application/rss+xml"], link[type="application/atom+xml"]');
                if (links.length > 0) return true;
                let a_tags = document.querySelectorAll('a[href$=".rss"], a[href$=".xml"], a[href*="/feed"]');
                return a_tags.length > 0;
            }''')
            return has_rss
        except:
            return False

class LocalBusinessBrowsingAgent(BaseBrowserAgent):
    def __init__(self):
        super().__init__(agent_name="local-business-browser-v1")

    async def _extract_google_maps_metadata(self, page, card_element):
        """
        Deep Search: Haritalarda listelenen dükkanın yapısal verilerini DOM stringinden (innerText) Regex ile çıkarır.
        """
        try:
            # İsmi genellikle linkin aria-label'ından alırız
            title = await card_element.get_attribute("aria-label") or "Bilinmeyen Işletme"
            
            # Kartın tamamının metin içeriğini JS ile alalım
            try:
                card_text = await card_element.evaluate("el => el.parentElement ? el.parentElement.innerText : el.innerText")
            except:
                card_text = ""

            rating = 0.0
            reviewsCount = 0

            # Türkçe/İngilizce Google Maps formatı genelde: "4,6 (1.100)" veya "4.6(50)" şeklindedir
            # Text içerisinde bu regex'i arıyoruz:  (\d[.,]\d)\s*\(([\d.,]+)\)
            match = re.search(r'([\d.,]+)\s*\(([\d.,]+)\)', card_text)
            if match:
                # 4,6 veya 4.6
                r_str = match.group(1).replace(',', '.')
                # (1.100) -> 1100
                v_str = match.group(2).replace('.', '').replace(',', '')
                try:
                    rating = float(r_str)
                    reviewsCount = int(v_str)
                except:
                    pass

            href = await card_element.get_attribute("href")
            
            # Konsolda çökmemek için tüm metinlerdeki garip karakterleri atalım
            safe_title = title.encode('ascii', 'ignore').decode('ascii')
            
            return {
                "title": safe_title,
                "rating": rating,
                "reviews": reviewsCount,
                "url": href
            }
        except Exception as e:
             return None

    async def scroll_and_collect_metadata(self, page, max_scrolls=10):
        """Google maps sidebar'ı scroll ederek asenkron DOM içerisinden Structured JSON (Rating, Link) okuma."""
        feed_selector = '[role="feed"]'
        try:
            await page.wait_for_selector(feed_selector, state="visible", timeout=60000)
        except:
            print(f"[{self.agent_name}] ❌ Scroll container bulunamadı veya sonuç yok.")
            return []

        feed = page.locator(feed_selector)
        if await feed.count() == 0:
            return []

        collected_businesses = []
        seen_urls = set()
        last_count = 0
        stagnation_counter = 0

        for step in range(max_scrolls):
            # Google maps'te her liste elementi 'a.hfpxzc' etiketi taşıyor
            links = page.locator("a.hfpxzc")
            link_count = await links.count()

            for i in range(link_count):
                el = links.nth(i)
                data = await self._extract_google_maps_metadata(page, el)
                
                if data and data['url'] and data['url'] not in seen_urls:
                    # RATING FİLTRESİ
                    if data['rating'] >= 4.0:
                         collected_businesses.append(data)
                         seen_urls.add(data['url'])
                    else:
                         print(f"[{self.agent_name}] Düşük Puan Elendi ({data['rating']}): {data['title']}")

            current_count = len(collected_businesses)
            print(f"[{self.agent_name}] Scroll {step+1}/{max_scrolls} | Taranan: {link_count} | Filtreden Gecen: {current_count}")

            if current_count >= 6:
                print(f"[{self.agent_name}] Hedeflenen 6 sonuca ulaşıldı.")
                break

            if current_count == last_count:
                stagnation_counter += 1
                if stagnation_counter >= 2:
                    break
            else:
                stagnation_counter = 0

            last_count = current_count

            try:
                # scrollBy px artırıldı, JS hatasına karşı exception eklendi
                await feed.evaluate("element => element.scrollBy(0, Math.floor(element.scrollHeight * 0.9))")
            except:
                break

            await page.wait_for_timeout(random.randint(2000, 3500))

        return collected_businesses

    async def run_browsing(self, root_sources, data):
        target_pages = []
        print(f"[{self.agent_name}] Özel Lokal Firma (Structured Metadata & API) Arama senaryosu başlatıldı.")
        
        # Öncelikli olarak orijinal sorguyu, yoksa expanded_queries listesini kullan
        original_query = data.get("original_query", "")
        expanded_queries = data.get("planning", {}).get("expanded_queries", [])
        
        queries_to_search = []
        if original_query:
            queries_to_search.append({"query_id": "q_local_1", "text": original_query})
        else:
            queries_to_search = expanded_queries
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await self.configure_context(browser)
            
            for query in queries_to_search:
                query_id = query.get("query_id", "q_1")
                query_text = query.get("text")
                
                if not query_text:
                    continue
                    
                print(f"\n[{self.agent_name}] Google Maps aranıyor: '{query_text}'")
                page = await self.create_stealth_page(context)
                
                # Jenerik Safe Goto (JS Render beklemesi eklenmiş haliye)
                success = await self.safe_goto(page, f"https://www.google.com/maps/search/{urllib.parse.quote(query_text)}?hl=tr")
                
                if success:
                    await self.handle_consent(page)
                    try:
                        # Artık direkt URL'den arattığımız için form doldurmayı beklemeye gerek kalmayabilir, 
                        # yine de feed'in yüklenmesini bekleyelim
                        print(f"[{self.agent_name}] Harita sayfasının yüklenmesi bekleniyor...")
                        try:
                             # Eğer form varsa enterlamak da zararsızdır ama gerekli değil:
                             input_selector = 'input[name="q"], #searchboxinput, #searchbox'
                             search_input = await page.wait_for_selector(input_selector, state="visible", timeout=10000)
                             if search_input:
                                 await search_input.press("Enter")
                        except:
                             pass
                            
                        # API Yanıtları ve Feed kutusunun dolmasını tam bekleyelim
                        print(f"[{self.agent_name}] JS Form sonuçlarının yüklenmesi bekleniyor...")
                        await page.wait_for_timeout(4000) 
                        
                        # Review Scraping ve Rating Filtresi uygulayan Extraction Fonksiyonu
                        businesses = await self.scroll_and_collect_metadata(page)
                        
                        # JSON Objesi (Structured Entity) olarak target_pages'a kaydedelim
                        for biz in businesses:
                            target_pages.append({
                                "query_id": query_id,
                                "business_name": biz.get("title"),
                                "metadata": {
                                     "rating": biz.get("rating"),
                                     "reviews_count": biz.get("reviews")
                                },
                                "url": biz.get("url"),
                                "domain": "google.com/maps",
                                "status": "ready_for_scrape",
                                "source_type": "structured_business"
                            })
                    except Exception as e:
                        print(f"[{self.agent_name}] Kayıt metadata toplama hatası: {e}")
                
                await page.close()
            await browser.close()
            
        return target_pages


class SpecificBrowsingAgent(BaseBrowserAgent):
    def __init__(self):
        super().__init__(agent_name="specific-browser-v1")
        self.irrelevant_keywords = [
            "login", "signin", "register", "signup", "auth",
            "about", "hakkimizda", "contact", "iletisim", 
            "terms", "privacy", "gizlilik", "faq", "sss",
            "cart", "checkout", "sepet", "password", "social",
            "facebook", "twitter", "instagram", "linkedin",
            "share", "footer", "cookie", "tag", "etiket", "kategori",
            "basketbol", "voleybol", "tenis", "motorsporlari", "atletizm", "gundem", "canli-yayin"
        ]
        
        self.priority_keywords = [
            "spielbericht", "match", "mac-ozeti", "goller", "fikstur", 
            "istatistik", "stats", "oyuncu", "player", "squad", "kadro", "sezon", "season"
        ]

    def _is_time_relevant(self, query_text, publish_date_str):
        """
        Sorgudaki yılı tespit edip içeriğin tarihiyle kıyaslar.
        Tolerans: hedef yıl - 1 kabul edilir (sezon öncesi haberler için).
        Hedef yıldan sonraki yıllar reddedilir.
        Tarih bulunamazsa (fallback): True döner.
        """
        if not publish_date_str:
            return True  # Fallback: Tarih yoksa kabul et

        match = re.search(r'\b(20\d{2})\b', query_text)
        if not match:
            return True  # Sorguda yıl geçmiyorsa zamandan bağımsız

        target_year = int(match.group(1))

        try:
            parsed_date = dparser.parse(publish_date_str, fuzzy=True)
            publish_year = parsed_date.year

            # Alt tolerans: hedef_yıl-1 (sezon öncesi içerikler için)
            # Üst tolerans: hedef_yıl + 1 (geçen yıla ait toplu istatistik sayfaları genellikle yeni yılın başında güncellenir)
            # Örn: 2025 sorgusu → 2024, 2025 ve 2026 sayfaları kabul edilir ✔ | 2027+ ✖
            if target_year - 1 <= publish_year <= target_year + 1:
                return True
            else:
                print(f"[{self.agent_name}] ⏳ Zaman Dışı: hedef={target_year}, içerik={publish_year} → reddedildi.")
                return False
        except:
            return True

    def _score_link(self, base_domain, link, query_text):
        try:
            parsed = urlparse(link)
            link_domain = parsed.netloc.lower()
            
            # Subdomain kontrolü
            if base_domain.replace("www.", "") not in link_domain:
                return -1
                
            path_lower = parsed.path.lower()
            
            if path_lower == "" or path_lower == "/":
                return -1
                
            if path_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.css', '.js')):
                return -1
                
            for bad_word in self.irrelevant_keywords:
                if bad_word in path_lower:
                    return -1
                    
            # Sadece kulüp startseite engelle (Eğer çok kısa bir path ise)
            if len(path_lower.split('/')) < 3 and ("startseite" in path_lower or "verein" in path_lower or "takim" in path_lower):
                 return -1

            score = 0
            
            # --- OFFICIAL SOURCE (RESMİ KAYNAK) KONTROLÜ ---
            official_domains = [
                "tff.org", "fenerbahce.org", "galatasaray.org", "bjk.com.tr", 
                "kap.org.tr", "uefa.com", "fifa.com"
            ]
            
            is_official = any(o_dom in link_domain for o_dom in official_domains) or link_domain.endswith(('.edu', '.gov', '.org'))
            
            if is_official:
                score += 15 # Kesin öncelik
            
            # Transfermarkt, Mackolik, Soccerway gibi yarı-resmi/güvenilir istatistik siteleri
            elif any(semi_official in link_domain for semi_official in ["transfermarkt", "mackolik", "soccerway", "fbref"]):
                score += 8
                
            # 1. Öncelikli Anahtar Kelimeler (Maç Raporu, İstatistik, Goller vb.)
            for p_word in self.priority_keywords:
                if p_word in path_lower:
                    score += 3
            
            # 2. Sorgu (Query) İçindeki Kelimelerin Linkte Geçmesi
            query_words = [w.lower() for w in query_text.split() if len(w) > 3]
            
            # Ana entiteyi (ilk veya en uzun kelimeyi) tespit et. Genelde Kulüp vb. olur
            main_entities = sorted(query_words, key=len, reverse=True)
            if main_entities:
                primary_entity = main_entities[0].replace("ç","c").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ı","i")
                # Eğer linkte ana entite GEÇMİYORSA puanı radikal biçimde düşür (Alakasız takımları -angers-sco, west-ham- filtrelemek için)
                if primary_entity not in path_lower and "fenerbahce" not in path_lower: # Hardcode fallback (sadece garanti olması için)
                     score -= 5
                     
            for qw in query_words:
                # Türkçe karakterleri kabaca eşleştirme
                qw_clean = qw.replace("ç","c").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ı","i")
                
                # Sadece takım isimleri değil, genel query eşleşmesi (+ Puan)
                if qw_clean in path_lower:
                    score += 5
                    
            # 3. Yıl geçiyorsa (+ puan)
            match = re.search(r'\b(20\d{2})\b', query_text)
            if match and match.group(1) in path_lower:
                score += 4
                
            return score
        except:
            return -1

    async def run_browsing(self, root_sources, data):
        target_pages = []
        print(f"[{self.agent_name}] Spesifik Bilgi arama senaryosu çalıştırılıyor...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await self.configure_context(browser)
            
            # URL listesini hazırla
            all_targets = []
            for source_group in root_sources:
                query_id = source_group.get("query_id")
                query_text = ""
                for q in data.get("planning", {}).get("expanded_queries", []):
                    if q.get("query_id") == query_id:
                        query_text = q.get("text", "")
                        break
                if not query_text:
                    query_text = data.get("original_query", "")
                
                for domain_entry in source_group.get("domains", [])[:3]:
                    exact_urls = domain_entry.get("exact_urls", []) or [domain_entry.get("base_url")]
                    for target_url in exact_urls[:2]:
                        if target_url:
                            all_targets.append((query_id, query_text, target_url, domain_entry.get("domain", "")))

            semaphore = asyncio.Semaphore(3) # Spesifik aramada aynı anda 3 sekme yeterli

            async def _process_specific(q_id, q_text, t_url, base_dom):
                async with semaphore:
                    page = await self.create_stealth_page(context)
                    try:
                        print(f"\n[{self.agent_name}] Spesifik URL inceleniyor: {t_url}")
                        success = await self.safe_goto(page, t_url)
                        if success:
                            await self.handle_consent(page)
                            pub_date = await self._extract_publish_date(page)
                            has_rss = await self._check_rss_feed(page)
                            
                            strategy_year = data.get("target_time_frame")
                            if strategy_year:
                                try:
                                    strategy_year_int = int(strategy_year)
                                    if pub_date:
                                        parsed_date = dparser.parse(pub_date, fuzzy=True)
                                        # Alt: hedef_yıl-1, Üst: tam hedef yıl
                                        # 2025 sorgusu → 2024, 2025 kabul | 2026+ red
                                        if not (strategy_year_int - 1 <= parsed_date.year <= strategy_year_int):
                                            print(f"[{self.agent_name}] ❌ ZAMAN UYUMSUZ (target={strategy_year}): {t_url}")
                                            return
                                except:
                                    pass
                            elif not self._is_time_relevant(q_text, pub_date):
                                return

                            official_source_req = data.get("official_source_required", False)
                            source_label = "official_record" if (official_source_req or "transfermarkt" in t_url or "tff.org" in t_url) else "exact_target"
                            
                            target_pages.append({
                                "query_id": q_id, "url": t_url, "domain": base_dom,
                                "status": "ready_for_scrape", "source_type": source_label,
                                "has_rss": has_rss, "publish_date": pub_date
                            })
                            
                            # Kısa scroll & Link extraction
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
                            all_links = await self.extract_links(page, t_url)
                            scored_links = sorted([(lnk, self._score_link(base_dom, lnk, q_text)) for lnk in all_links if self._score_link(base_dom, lnk, q_text) >= 0], key=lambda x: x[1], reverse=True)
                            
                            for internal_url in [x[0] for x in scored_links[:2]]: # Max 2 internal link
                                target_pages.append({
                                    "query_id": q_id, "url": internal_url, "domain": base_dom,
                                    "status": "ready_for_scrape", "source_type": "deep_discovery"
                                })
                    except Exception as e:
                        print(f"[{self.agent_name}] İşleme hatası ({t_url}): {e}")
                    finally:
                        await page.close()

            tasks = [_process_specific(*t) for t in all_targets]
            await asyncio.gather(*tasks)

            await browser.close()
        return target_pages



class CategoricBrowsingAgent(BaseBrowserAgent):
    def __init__(self):
        super().__init__(agent_name="categoric-browser-v1")
        # Geniş araştırma için filtre kelimelerimiz
        self.irrelevant_keywords = [
            "login", "signin", "register", "signup", "auth",
            "about", "hakkimizda", "contact", "iletisim", 
            "terms", "privacy", "gizlilik", "faq", "sss",
            "cart", "checkout", "sepet", "password", "social",
            "facebook", "twitter", "instagram", "linkedin",
            "share", "footer", "cookie"
        ]

    def _score_categoric_link(self, base_domain, link, query_text, publish_date_str=None):
        """
        Kategorik arama (Geniş araştırma) için Recursive Spam önleyici link skorlama aracı.
        Authority Score, Recency Score, Relevance Score faktörlerini birleştirir.
        """
        try:
            parsed = urlparse(link)
            link_domain = parsed.netloc.lower()
            path_lower = parsed.path.lower()
            
            # --- 1. GÜRÜLTÜ AYIKLAMA (Noise Filtering) ---
            if path_lower == "" or path_lower == "/":
                return -1 # Çok genel kök sayfalar bilgi füzyonu için gereksiz
                
            if path_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.css', '.js')):
                return -1
                
            for bad_word in self.irrelevant_keywords:
                if bad_word in path_lower:
                    return -1

            score = 0
            
            # --- 2. AUTHORITY SCORE (Otorite Puanı) ---
            # İstatistik/spor siteleri: Kesin tablo verisi için en yüksek otorite
            stats_authority_domains = [
                "mackolik.com", "transfermarkt.com.tr", "transfermarkt.com",
                "sofascore.com", "tff.org",
                "livescore.com", "goal.com", "fotmob.com",
                "tuik.gov.tr", "tcmb.gov.tr", "investing.com", "tradingeconomics.com"
            ]
            
            high_authority_domains = [
                "forbes", "bloomberg", "reuters", "mckinsey", "gartner", "techcrunch", "wired", "wsj"
            ]
            
            medium_authority_domains = [
                "medium.com", "ycombinator.com", "reddit.com", "quora.com", "stackoverflow.com"
            ]
            
            # Wikipedia için: istatistik sorularında düşük otorite, genel sorgularda orta
            is_stats_query = any(kw in query_text.lower() for kw in ["gol", "maç", "skor", "puan", "istatistik", "oran", "enflasyon", "gdp", "büyüme", "goals", "stats", "score", "standings"])
            
            if any(sd in link_domain for sd in stats_authority_domains):
                score += 25  # En yüksek öncelik: gerçek veri kaynağı
            elif "wikipedia" in link_domain:
                score += (3 if is_stats_query else 12)  # İstatistik sorgularında düşür
            elif any(ha in link_domain for ha in high_authority_domains) or link_domain.endswith(('.edu', '.gov', '.org')):
                score += 15
            elif any(ma in link_domain for ma in medium_authority_domains):
                score += 8

                
            # Eğer dışarıya link veriyorsa (Kapsam Genişletme) ve otoriterse bonus ver. 
            if base_domain.replace("www.", "") not in link_domain:
                 if score > 0: # Otorite veya medium ise dış linke yüksek bonus
                     score += 10
                 else:
                     score += 2 # Sıradan dış link

            # --- 3. RELEVANCE SCORE (Alaka Puanı) ---
            query_words = [w.lower() for w in query_text.split() if len(w) > 3]
            for qw in query_words:
                 qw_clean = qw.replace("ç","c").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ı","i")
                 if qw_clean in path_lower or qw in path_lower:
                     score += 5
            
            # Uzun path / Makale tarzı başlıklar daha değerlidir 
            path_segments = [s for s in path_lower.split('/') if s]
            if len(path_segments) >= 2:
                 score += 3
            if len(path_lower) > 30: # Slug muhtemelen uzun ve açıklayıcıdır
                 score += 2
                 
            # --- 4. RECENCY SCORE (Güncellik Puanı) Yıl Analizi ---
            # Path içerisindeki yılı (Örn: /2024/05/20/haber) analiz et
            current_year = datetime.now().year
            path_year_match = re.search(r'/((?:19|20)\d{2})/', path_lower)
            
            found_year = None
            if path_year_match:
                 found_year = int(path_year_match.group(1))
            elif publish_date_str:
                 try:
                     parsed_date = dparser.parse(publish_date_str, fuzzy=True)
                     found_year = parsed_date.year
                 except: pass

            if found_year:
                age_in_years = current_year - found_year
                if age_in_years == 0:
                     score += 10 # Bu sene
                elif age_in_years == 1:
                     score += 6  # Geçen sene
                elif age_in_years <= 3:
                     score += 2  # Son 3 yıl
                elif age_in_years > 5:
                     score -= 5  # Çok eski (Penalty)
                     
            return score
        except:
            return -1

    async def run_browsing(self, root_sources, data):
        target_pages = []
        print(f"[{self.agent_name}] Kategorik Bilgi arama senaryosu (Kapsamlı İçerik Taraması) çalıştırılıyor...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await self.configure_context(browser)
            
            # URL listesini hazırla
            all_targets = []
            for source_group in root_sources:
                query_id = source_group.get("query_id")
                query_text = ""
                for q in data.get("planning", {}).get("expanded_queries", []):
                    if q.get("query_id") == query_id:
                        query_text = q.get("text", "")
                        break
                if not query_text:
                    query_text = data.get("original_query", "")
                
                for domain_entry in source_group.get("domains", [])[:5]:
                    exact_urls = domain_entry.get("exact_urls", []) or [domain_entry.get("base_url")]
                    for target_url in exact_urls[:2]:
                        if target_url:
                            all_targets.append((query_id, query_text, target_url, domain_entry.get("domain", "")))

            semaphore = asyncio.Semaphore(3)
            domain_count_tracker = {}
            MAX_LINKS_PER_DOMAIN = 3

            async def _process_categoric(q_id, q_text, t_url, base_dom):
                async with semaphore:
                    page = await self.create_stealth_page(context)
                    try:
                        print(f"[{self.agent_name}] Kategorik Kaynak İnceleniyor: {t_url}")
                        success = await self.safe_goto(page, t_url)
                        if success:
                            await self.handle_consent(page)
                            pub_date = await self._extract_publish_date(page)
                            
                            target_pages.append({
                                "query_id": q_id, "url": t_url, "domain": base_dom,
                                "status": "ready_for_scrape", "source_type": "category_root", "publish_date": pub_date
                            })
                            
                            # Derinlemesine scroll & Link extraction
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                            all_links = await self.extract_links(page, t_url)
                            scored_links = sorted([(lnk, self._score_categoric_link(base_dom, lnk, q_text, pub_date)) for lnk in all_links if self._score_categoric_link(base_dom, lnk, q_text, pub_date) >= 0], key=lambda x: x[1], reverse=True)
                            
                            added = 0
                            for i_url, sc in scored_links:
                                if added >= 4: break
                                lnk_dom = urlparse(i_url).netloc.lower().replace("www.", "")
                                if domain_count_tracker.get(lnk_dom, 0) >= MAX_LINKS_PER_DOMAIN: continue
                                
                                domain_count_tracker[lnk_dom] = domain_count_tracker.get(lnk_dom, 0) + 1
                                target_pages.append({
                                    "query_id": q_id, "url": i_url, "domain": lnk_dom,
                                    "status": "ready_for_scrape", "source_type": "category_context"
                                })
                                added += 1
                    except Exception as e:
                        print(f"[{self.agent_name}] Hata ({t_url}): {e}")
                    finally:
                        await page.close()

            tasks = [_process_categoric(*t) for t in all_targets]
            await asyncio.gather(*tasks)
            await browser.close()
        return target_pages
        return target_pages


class GenericBrowsingAgent(BaseBrowserAgent):
    def __init__(self):
        super().__init__(agent_name="generic-browser-v1")
        # Rule-Based Routing Keyword Groups
        self.REAL_ESTATE_KEYWORDS = ["emlak", "kiralık", "kiralik", "satılık daire", "arsa", "ev", "yazlık"]
        self.CAR_KEYWORDS = ["araba", "otomobil", "satılık araç", "satilik arac", "tesla", "vasıta", "ikinci el binek"]
        self.JOB_KEYWORDS = ["frontend developer", "backend developer", "iş ilanı", "is ilani", "yazılım uzmanı", "developer"]
        self.HOTEL_KEYWORDS = ["otel", "hotel", "pansiyon", "bungalov", "tatil"]
        self.EVENT_KEYWORDS = ["bilet", "konser", "etkinlik", "festival"]

    async def _sahibinden_search_and_collect(self, page, original_query: str, query_id: str) -> list:
        """
        CDP ile bağlı sahibinden.com sayfasında orijinal sorguyu arama kutusuna yazar,
        Ara butonuna basar ve çıkan 5 ilan URL'sini toplar.
        """
        target_pages = []
        try:
            # Eğer sahibinden.com'da değilse ana sayfaya git
            current_url = page.url
            if "sahibinden.com" not in current_url:
                print(f"[{self.agent_name}] Sahibinden.com'a yönlendiriliyor... (mevcut: {current_url})")
                await page.goto("https://www.sahibinden.com", wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2)
            else:
                print(f"[{self.agent_name}] Sahibinden.com zaten açık: {current_url}")
                await asyncio.sleep(1)

            # --- Arama Kutusunu Bul ve Orijinal Sorguyu Yaz ---
            # Sahibinden.com'un gerçek arama kutusu selector'ları (öncelik sırasıyla)
            search_input_selectors = [
                "#searchText",                    # Sahibinden'in asıl ID'si
                "input[name='query']",
                "input[id*='search']",
                "input[placeholder*='Ara']",
                "input[placeholder*='arama']",
                "input.search-form-input",
                "input[type='search']",
                "input[type='text']"
            ]
            input_found = False
            used_selector = None
            for sel in search_input_selectors:
                try:
                    await page.wait_for_selector(sel, state="visible", timeout=5000)
                    # Önce temizle
                    await page.click(sel)
                    await page.keyboard.press("Control+a")
                    await page.keyboard.press("Delete")
                    await asyncio.sleep(0.3)
                    # Sonra yaz
                    await page.type(sel, original_query, delay=80)
                    print(f"[{self.agent_name}] ✓ Sorgu yazıldı: '{original_query}' → selector: {sel}")
                    input_found = True
                    used_selector = sel
                    break
                except:
                    continue

            if not input_found:
                # Fallback: URL ile doğrudan arama sayfasına git
                print(f"[{self.agent_name}] Arama kutusu bulunamadı! URL fallback devreye giriyor...")
                from urllib.parse import quote
                search_url = f"https://www.sahibinden.com/arama?query={quote(original_query)}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(0.5)
                # --- Ara Butonuna Bas ---
                # Kullanıcının belirttiği: <button type="submit" value="Ara"></button>
                submit_selectors = [
                    "button[type='submit'][value='Ara']",
                    "button[type='submit']",
                    "input[type='submit'][value='Ara']",
                    "input[type='submit']",
                ]
                btn_clicked = False
                for btn_sel in submit_selectors:
                    try:
                        btn = page.locator(btn_sel).first
                        if await btn.count() > 0:
                            await btn.click()
                            print(f"[{self.agent_name}] ✓ 'Ara' butonu tıklandı → selector: {btn_sel}")
                            btn_clicked = True
                            break
                    except:
                        continue

                if not btn_clicked:
                    await page.keyboard.press("Enter")
                    print(f"[{self.agent_name}] Buton bulunamadı, Enter ile arama yapıldı.")

            # --- Sonuç Sayfasının Yüklenmesini Bekle ---
            print(f"[{self.agent_name}] Arama sonuçları yükleniyor...")
            await asyncio.sleep(4)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                pass

            # --- İlan URL'lerini Topla (max 5) ---
            # Sahibinden sonuç listesi selectors (öncelik sırasıyla)
            listing_selectors = [
                "a.classifiedTitle",
                "td.searchResultsTitle a",
                "tr.searchResultsItem a.classifiedTitle",
                "table.searchResultsTable a[href*='/ilan/']",
                "a[href*='/ilan/']"
            ]
            collected = []
            for ls in listing_selectors:
                try:
                    links = page.locator(ls)
                    count = await links.count()
                    if count > 0:
                        print(f"[{self.agent_name}] {count} ilan bulundu (selector: {ls})")
                        for i in range(count):
                            if len(collected) >= 5:
                                break
                            href = await links.nth(i).get_attribute("href")
                            try:
                                title_text = await links.nth(i).inner_text()
                            except:
                                title_text = "Sahibinden İlan"
                            if href and href not in ["", "#", "javascript:void(0)"]:
                                full_url = href if href.startswith("http") else "https://www.sahibinden.com" + href
                                if full_url not in [x["url"] for x in collected]:
                                    collected.append({
                                        "url": full_url,
                                        "title": title_text.strip()[:150] if title_text else "İlan"
                                    })
                        if collected:
                            break  # İlk çalışan selector yeterli
                except:
                    continue

            print(f"[{self.agent_name}] Sahibinden: {len(collected)} ilan URL'si toplandı.")
            for item in collected:
                target_pages.append({
                    "query_id": query_id,
                    "url": item["url"],
                    "domain": "sahibinden.com",
                    "status": "ready_for_scrape",
                    "source_type": "platform_listing",
                    "metadata": {"title": item["title"], "source": "sahibinden"},
                    "business_name": item["title"]
                })

        except Exception as e:
            print(f"[{self.agent_name}] Sahibinden arama hatası: {e}")
            import traceback
            traceback.print_exc()

        return target_pages


    async def _decide_platform(self, query_text):
        """
        Kullanıcı sorgusuna göre (önce Rule-Based Cache, sonra LLM kullanarak) hedef platformu seçitirir.
        Return: (domain_str, is_high_confidence, metadata_dict)
        """
        # 1. Rule-Based Keyword Kontrolü
        query_lower = query_text.lower()
        
        import re
        def has_match(keywords, text):
            for kw in keywords:
                # Kisa kelimelerde (orn: 'ev') kelime sinirlari muhim, D*ev*eloper ile karismasin
                if len(kw) <= 3:
                     pattern = rf"\b{kw}\b"
                     if re.search(pattern, text, re.IGNORECASE):
                          return True
                else:
                     # Uzun kelimelerde (orn: 'developer') suffixleri (lar, ler) desteklemek icin duz substring
                     if kw in text:
                          return True
            return False
            
        if has_match(self.REAL_ESTATE_KEYWORDS, query_lower):
            print(f"[{self.agent_name}] [Rule Match]: Emlak/Gayrimenkul -> sahibinden.com")
            return "sahibinden.com", True, {"source": "rule_based", "category": "real_estate", "confidence": 1.0}
            
        if has_match(self.CAR_KEYWORDS, query_lower):
            print(f"[{self.agent_name}] [Rule Match]: Araba/Vasita -> sahibinden.com")
            return "sahibinden.com", True, {"source": "rule_based", "category": "cars", "confidence": 1.0}
            
        if has_match(self.JOB_KEYWORDS, query_lower):
            print(f"[{self.agent_name}] [Rule Match]: Is Ilani -> linkedin.com")
            return "linkedin.com", True, {"source": "rule_based", "category": "jobs", "confidence": 1.0}
            
        if has_match(self.HOTEL_KEYWORDS, query_lower):
            print(f"[{self.agent_name}] [Rule Match]: Otel/Konaklama -> booking.com")
            return "booking.com", True, {"source": "rule_based", "category": "hotels", "confidence": 1.0}

        if has_match(self.EVENT_KEYWORDS, query_lower):
            print(f"[{self.agent_name}] [Rule Match]: Etkinlik/Bilet -> biletix.com")
            return "biletix.com", True, {"source": "rule_based", "category": "events", "confidence": 1.0}

        # 2. LLM Fallback
        client = get_azure_client()
        if not client:
            return None, False, {"error": "No LLM Client", "confidence": 0}

        print(f"[{self.agent_name}] LLM 'Platform Jump' logic is being executed...")
        prompt = f"""
        User Search Query (Generic Listing or Classified Search):  '{query_text}'
        
        Question: What is the most suitable main domain address for listing (classifieds, hotel, ticket, 2nd hand, event, etc.) in the Turkish (or global) market for this specific search? 

        Rules:
        1. Return ONLY the Domain (root URL), such as "sahibinden.com", "arabam.com", "hepsiemlak.com", "airbnb.com", "booking.com", "biletix.com", "reddit.com". Do NOT include https:// or www. at the beginning.
        2. 'confidence': A decimal number between 0.0 and 1.0. If it is a well-known platform, return above 0.90; if unsure, return 0.50.
        3. If the query is too general and a single website does not make sense (e.g., "AI news"), return an empty string "" for the domain.
        
        Return ONLY a JSON object in the format below (do not add any other text):
        {{
            "domain": "sahibinden.com",
            "confidence": 0.95,
            "reason": "It is the largest source for car and real estate listings in Turkey"
        }}
        """

        try:
            response = client.chat.completions.create(
                model="o4-mini", 
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            llm_reply = response.choices[0].message.content.strip()
            
            # Markdown temizligi
            if llm_reply.startswith("```json"): llm_reply = llm_reply[7:]
            if llm_reply.startswith("```"): llm_reply = llm_reply[3:]
            if llm_reply.endswith("```"): llm_reply = llm_reply[:-3]
            
            data = json.loads(llm_reply.strip())
            domain = data.get("domain", "")
            confidence = float(data.get("confidence", 0.0))
            
            # Domain Normalization (www. vb atma)
            domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip()
            # Bitiş slash atmaları
            if domain.endswith("/"): domain = domain[:-1]

            # 3. Confidence Threshold
            if not domain:
                 return None, False, {"source": "llm", "confidence": confidence, "reason": "Empty domain"}
                 
            if confidence >= 0.70:
                print(f"[{self.agent_name}] [LLM Karari]: {domain} (Güven: {confidence}) -> {data.get('reason','')}")
                return domain, True, {"source": "llm", "confidence": confidence, "reason": data.get("reason", "")}
            else:
                print(f"[{self.agent_name}] [LOW CONFIDENCE] LLM Güveni çok düşük ({confidence}). Jenerik root_sources kullanılacak. Domain: {domain}")
                return None, False, {"source": "llm", "confidence": confidence, "reason": "Confidence threshold sub-optimal"}
                
        except Exception as e:
             print(f"[{self.agent_name}] LLM Platform Karar Hatasi: {e}")
             return None, False, {"error": str(e), "confidence": 0}

    async def run_browsing(self, root_sources, search_data):
        """
        Agent 4 (Jenerik Arama): Sahibinden vb. zorlu siteler icin tasarlandi.
        Login zorunlulugu olan veya aktif Anti-Bot'lara (CF) karsi kullanicinin mevcut
        Chrome profiline CDP (Port 9222) uzerinden baglanmayi dener.
        """
        query_text = search_data.get("original_query", "")
        print(f"[{self.agent_name}] Jenerik Arama (Generic Listing) senaryosu baslatildi. Sorgu: '{query_text}'")
        
        target_pages = []
        
        # --- Dinamik LLM / Cache Routing Deneyimi ---
        best_domain, is_confident, router_meta = await self._decide_platform(query_text)
        
        # Debug Json'a eklensin diye search_data'ya yazdiriyoruz
        search_data["routing_debug"] = {
             "selected_domain": best_domain if is_confident else "fallback_roots",
             "is_confident": is_confident,
             "metadata": router_meta
        }
        
        # LinkedIn Ozel Senaryosu: Eger domain linkedin ise dogrudan ozel agenta devret
        if is_confident and best_domain == "linkedin.com":
             print(f"[{self.agent_name}] Sorgu is ilanina / profile isaret ediyor. LinkedInBrowsingAgent baslatiliyor...")
             from agents.browsing_agent_core import LinkedInBrowsingAgent # self icinde cagir, evet ayni dosya ama explicit
             li_agent = LinkedInBrowsingAgent()
             return await li_agent.run_browsing(root_sources, search_data)
        
        # ─── Sahibinden Özel Senaryosu: CDP ile orijinal sorgu araması ────────────
        if is_confident and best_domain == "sahibinden.com":
            print(f"[{self.agent_name}] Sahibinden senaryosu tespit edildi. CDP ile orijinal sorgu araması yapılacak.")
            original_query = search_data.get("original_query", "")
            query_id = search_data.get("planning", {}).get("expanded_queries", [{}])[0].get("query_id", "q_gen_1")

            async with async_playwright() as p:
                browser = None
                page = None
                using_cdp = False

                try:
                    print(f"[{self.agent_name}] CDP (localhost:9222) bağlantısı deneniyor...")
                    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                    contexts = browser.contexts
                    context = contexts[0] if contexts else await browser.new_context(viewport={"width": 1366, "height": 768})
                    pages = context.pages
                    page = pages[0] if pages else await context.new_page()
                    using_cdp = True
                    print(f"[{self.agent_name}] CDP Bağlantısı Başarılı! Mevcut sayfa: {page.url}")
                except Exception as e:
                    print(f"[{self.agent_name}] CDP başarısız ({e}). Headless ile devam ediliyor...")
                    browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
                    context = await browser.new_context(user_agent=random.choice(self.user_agents), viewport={"width": 1366, "height": 768})
                    page = await context.new_page()
                
                target_pages = await self._sahibinden_search_and_collect(page, original_query, query_id)
                
                if not using_cdp:
                    await browser.close()
            
            return target_pages

        # Eğer LLM veya Cache başarılı bir domain seçmişse (Sahibinden DIŞI), arama motorundan (Agent 2) gelen listeyi 
        # ezip SADECE hedeflenen domain'e gidelim.
        if is_confident and best_domain:
             print(f"[{self.agent_name}] Dinamik Yonlendirme Aktif. Sadece hedeflenen domaine {best_domain} gidilecek.")
             
             # Mevcut root_sources icinde bu domaine ait derin link tespiti (Google'dan gelen vb)
             existing_deep_links = []
             for src in root_sources:
                 for dom_data in src.get("domains", []):
                     existing_deep_links.extend([u for u in dom_data.get("exact_urls", []) if best_domain in u])
             
             if not existing_deep_links:
                  existing_deep_links = [f"https://www.{best_domain}"]
                  
             # User Request Override: Harbiye konserleri icin etkinlik-grup URL'sine zorla
             if best_domain == "biletix.com" and "harbiye" in search_data.get("original_query", "").lower():
                  print(f"[{self.agent_name}] Biletix Harbiye URL Override uygulaniyor...")
                  existing_deep_links = ["https://www.biletix.com/etkinlik-grup/493997366/ISTANBUL/tr/harbiye-cemil-topuzlu-acikhava-2025-etkinlikleri"]
                  
             root_sources = [
                 {
                     "domains": [
                         {
                             "domain": best_domain, 
                             "exact_urls": existing_deep_links 
                         }
                     ]
                 }
             ]
        
        
        # URL listesini hazırla ve Sahibinden tespiti yap
        all_urls_to_visit = []
        has_sahibinden = False
        
        for source in root_sources:
            for domain_data in source.get("domains", []):
                d_name = domain_data.get("domain", "").lower()
                urls = domain_data.get("exact_urls", []) or [f"https://{d_name}"]
                if "sahibinden.com" in d_name:
                    has_sahibinden = True
                    # Sahibinden için sadece ana sayfayı ekle — arama sayfasına gidecek
                    if "sahibinden.com" not in [x[1] for x in all_urls_to_visit]:
                        all_urls_to_visit.insert(0, ("https://www.sahibinden.com", d_name))
                else:
                    for u in urls:
                        all_urls_to_visit.append((u, d_name))

        original_query = search_data.get("original_query", "")
        query_id = search_data.get("planning", {}).get("expanded_queries", [{}])[0].get("query_id", "q_gen_1")

        async with async_playwright() as p:
            browser = None
            context = None
            page = None
            using_cdp = False

            if has_sahibinden:
                try:
                    print(f"[{self.agent_name}] Sahibinden tespit edildi. CDP (localhost:9222) bağlantısı deneniyor...")
                    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                    contexts = browser.contexts
                    if contexts:
                        context = contexts[0]
                    else:
                        context = await browser.new_context(viewport={"width": 1366, "height": 768})
                    pages = context.pages
                    page = pages[0] if pages else await context.new_page()
                    using_cdp = True
                    print(f"[{self.agent_name}] CDP Bağlantısı Başarılı! Sayfa: {page.url}")
                except Exception as e:
                    print(f"[{self.agent_name}] CDP başarısız ({e}). Headless devam ediliyor...")

            if not using_cdp:
                print(f"[{self.agent_name}] Headless tarayıcı başlatılıyor...")
                browser_args = ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"]
                browser = await p.chromium.launch(headless=True, args=browser_args)
                context = await browser.new_context(
                    user_agent=random.choice(self.user_agents),
                    viewport={"width": 1366, "height": 768},
                )
                page = await context.new_page()
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # ─── Sahibinden: Özel Arama Akışı ──────────────────────────────────────
            if has_sahibinden and using_cdp:
                try:
                    print(f"[{self.agent_name}] Sahibinden.com'a gidiliyor...")
                    await page.goto("https://www.sahibinden.com", wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(2)

                    # Arama kutusunu bul ve orijinal sorguyu yaz
                    search_input_selectors = [
                        "input[name='query']",
                        "input[placeholder*='Ara']",
                        "input[placeholder*='arama']",
                        "input.search-input",
                        "#search-query",
                        "input[type='text']"
                    ]
                    input_found = False
                    for sel in search_input_selectors:
                        try:
                            await page.wait_for_selector(sel, state="visible", timeout=5000)
                            await page.fill(sel, "")
                            await page.type(sel, original_query, delay=80)
                            print(f"[{self.agent_name}] Sorgu yazıldı: '{original_query}' (selector: {sel})")
                            input_found = True
                            break
                        except:
                            continue

                    if not input_found:
                        print(f"[{self.agent_name}] UYARI: Arama kutusu bulunamadı! URL ile devam ediliyor...")
                        from urllib.parse import quote
                        search_url = f"https://www.sahibinden.com/arama?query={quote(original_query)}"
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                    else:
                        # Ara butonuna bas (kullanıcı tarafından belirtilen buton)
                        submit_selectors = [
                            "button[type='submit'][value='Ara']",
                            "button[type='submit']",
                            "input[type='submit']",
                            ".search-button",
                            "button.btn-search"
                        ]
                        btn_clicked = False
                        for btn_sel in submit_selectors:
                            try:
                                await page.wait_for_selector(btn_sel, state="visible", timeout=4000)
                                await page.click(btn_sel)
                                print(f"[{self.agent_name}] 'Ara' butonu tıklandı (selector: {btn_sel})")
                                btn_clicked = True
                                break
                            except:
                                continue

                        if not btn_clicked:
                            # Fallback: Enter tuşu
                            await page.keyboard.press("Enter")
                            print(f"[{self.agent_name}] Buton bulunamadı, Enter ile arama yapıldı.")

                    # Sonuç sayfasının yüklenmesini bekle
                    print(f"[{self.agent_name}] Arama sonuçları bekleniyor...")
                    await asyncio.sleep(3)
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    except:
                        pass

                    # İlan URL'lerini topla (max 5)
                    print(f"[{self.agent_name}] İlan URL'leri toplanıyor (maks 5)...")
                    listing_selectors = [
                        "a.classifiedTitle",
                        "td.searchResultsTitle a",
                        ".classified-list a.title",
                        "tr.searchResultsItem a.classifiedTitle",
                        "a[href*='/ilan/']"
                    ]
                    
                    collected_urls = []
                    for ls in listing_selectors:
                        try:
                            links = page.locator(ls)
                            count = await links.count()
                            if count > 0:
                                print(f"[{self.agent_name}] {count} ilan bulundu (selector: {ls})")
                                for i in range(min(count, 5)):
                                    href = await links.nth(i).get_attribute("href")
                                    title_text = await links.nth(i).inner_text()
                                    if href:
                                        full_url = href if href.startswith("http") else "https://www.sahibinden.com" + href
                                        if full_url not in [x["url"] for x in collected_urls]:
                                            collected_urls.append({
                                                "url": full_url,
                                                "metadata": {"title": title_text.strip()[:150], "source": "sahibinden"}
                                            })
                                    if len(collected_urls) >= 5:
                                        break
                                break
                        except:
                            continue

                    print(f"[{self.agent_name}] Sahibinden: {len(collected_urls)} ilan URL'si toplandı.")
                    for item in collected_urls:
                        target_pages.append({
                            "query_id": query_id,
                            "url": item["url"],
                            "domain": "sahibinden.com",
                            "status": "ready_for_scrape",
                            "source_type": "platform_listing",
                            "metadata": item["metadata"],
                            "business_name": item["metadata"].get("title", "")
                        })

                except Exception as e:
                    print(f"[{self.agent_name}] Sahibinden arama akışı hatası: {e}")

            # ─── Diğer Platformlar: Standart Akış ─────────────────────────────────
            other_urls = [(u, d) for u, d in all_urls_to_visit if "sahibinden.com" not in d]
            
            if other_urls:
                semaphore = asyncio.Semaphore(3)
                query_text = original_query

                async def _process_generic(u, d_name):
                    async with semaphore:
                        p_page = await self.create_stealth_page(context)
                        try:
                            print(f"[{self.agent_name}] Hedef ziyaret ediliyor: {u}")
                            await p_page.goto(u, wait_until="domcontentloaded", timeout=45000)
                            await solve_captcha(p_page, agent_name=self.agent_name)
                            await asyncio.sleep(2)

                            is_deep = len(str(u).split("/")) > 4 and "biletix" in u
                            if is_deep:
                                target_pages.append({
                                    "query_id": query_id, "business_name": "Deep Link", "url": u,
                                    "domain": d_name, "status": "ready_for_scrape", "source_type": "platform_listing",
                                    "metadata": {"title": "Direct Listing"}
                                })
                            else:
                                items = await route_platform(p_page, u, query=query_text, agent_name=self.agent_name, limit=10)
                                for item in items:
                                    target_pages.append({
                                        "query_id": query_id, "url": item["url"], "domain": d_name,
                                        "status": "ready_for_scrape", "source_type": "platform_listing",
                                        "metadata": item["metadata"], "business_name": item["metadata"].get("title", "")
                                    })
                        except Exception as e:
                            print(f"[{self.agent_name}] Hata ({u}): {e}")
                        finally:
                            await p_page.close()

                tasks = [_process_generic(url, dom) for url, dom in other_urls]
                await asyncio.gather(*tasks)

            if not using_cdp:
                await browser.close()
            # CDP modunda tarayıcıyı kapatmıyoruz (kullanıcının session'ı bozulmasın)
            
        return target_pages



class LinkedInBrowsingAgent(BaseBrowserAgent):
    """
    Kullanicinin gizli (secret.json) auth cookie'sini kullanarak LinkedIn 'People' ve 'Location' filtreleriyle 
    arama yapip sonuclari ceken spesifik Browsing Ajani.
    """
    def __init__(self):
         super().__init__(agent_name="linkedin-browser-v1")
         from utils.auth_manager import AuthManager
         self.auth_manager = AuthManager()

    async def run_browsing(self, root_sources, search_data):
         # LinkedIn raw Turkce cumlelerde (orn: "Ankaradaki frontend developerlar") takilir.
         # Bu yuzden Planner (Agent 1) tarafindan cikarilan 'normalized_entities'i kullaniyoruz.
         planning_data = search_data.get("planning", {})
         query_analysis = planning_data.get("query_analysis", {})
         normalized_entities = query_analysis.get("normalized_entities", [])
         
         location_name = query_analysis.get("location_name", None)
         
         if normalized_entities:
             if location_name:
                 keywords = [e for e in normalized_entities if location_name.lower() not in e.lower() and e.lower() not in location_name.lower()]
                 query_text = " ".join(keywords) if keywords else " ".join(normalized_entities)
             else:
                 query_text = " ".join(normalized_entities)
             print(f"[{self.agent_name}] Optimizasyon: Role='{query_text}', Lokasyon='{location_name}'")
         else:
             query_text = search_data.get("original_query", "")
             
         import re
         if not location_name and query_text:
             match = re.search(r'(?i)^(istanbul|ankara|izmir|bursa|antalya)(?:daki|deki|\'daki|\'deki|lı|li|lu|lü)?\s+(.*)', query_text)
             if match:
                 location_name = match.group(1).capitalize()
                 query_text = match.group(2).strip()
                 print(f"[{self.agent_name}] Regex ile lokasyon tespit edildi. Role='{query_text}', Lokasyon='{location_name}'")
         
         if not query_text:
             query_text = search_data.get("original_query", "")
             print(f"[{self.agent_name}] Anahtar kelime bulunamadi, ham sorgu kullaniliyor: '{query_text}'")
             
         query_id = search_data.get("planning", {}).get("expanded_queries", [{}])[0].get("query_id", "q_linkedin_1")
         print(f"[{self.agent_name}] LinkedIn'de derinlemesine kisi/pozisyon aramasi baslatildi: '{query_text}'")
         
         target_pages = []
         async with async_playwright() as p:
             browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
             ]
             browser = await p.chromium.launch(headless=True, args=browser_args)
             # Context'e sir'lari / cookie'leri gom
             context = await browser.new_context(
                 user_agent=self.auth_manager.USER_AGENT,
                 viewport={"width": 1366, "height": 768},
             )
             
             await context.add_cookies(self.auth_manager.get_cookies())
             page = await context.new_page()
             
             # Stealth Patch uygula
             await self.auth_manager.apply_stealth(page)
             
             # LinkedIn Login Check
             is_valid = await self.auth_manager.check_session_validity(page)
             if not is_valid:
                 print(f"[{self.agent_name}] Oturum gecersiz. Arama yapilamiyor.")
                 await browser.close()
                 return target_pages
                 
             # Human sim
             await self.auth_manager.simulate_mouse_move(page)
             
             # Simulating Human Search via UI (Slow Typing)
             print(f"[{self.agent_name}] Navigating to LinkedIn Feed to type the search query...")
             try:
                 if "feed" not in page.url:
                     await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
                     await self.auth_manager.simulate_human_reading(page)

                 search_selectors = [
                      'input.search-global-typeahead__input',
                      'input.search-global-typeahead-focused',
                      'input[placeholder*="Search"]',
                      'input[placeholder*="Arama"]'
                 ]
                 
                 found_input = False
                 for sel in search_selectors:
                      try:
                           await page.wait_for_selector(sel, state="visible", timeout=15000)
                           await page.click(sel)
                           found_input = True
                           break
                      except:
                           continue
                           
                 if not found_input:
                      print(f"[{self.agent_name}] Uyari: Arama kutusu bulunamadi! URL manipülasyonuna geciliyor...")
                      from urllib.parse import quote
                      encoded_q = quote(query_text)
                      search_url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_q}"
                      await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                 else:
                     # Type SLOWLY as a human would
                     print(f"[{self.agent_name}] Typing query slowly: {query_text}")
                     for char in query_text:
                         await page.keyboard.insert_text(char)
                         await asyncio.sleep(random.uniform(0.1, 0.4)) # VERY slow random typing delay
                     
                     await self.auth_manager.simulate_mouse_move(page)
                     await page.keyboard.press('Enter')
                     
                     # Wait for initial global search results to partially load
                     await page.wait_for_timeout(3000)
                     
                     # 1. "Kişiler" (People) Filtresi (URL manipülasyonu ile kesin geçiş)
                     print(f"[{self.agent_name}] Hedef URL ile 'People' (Kişiler) filtre sayfasina geciliyor...")
                     from urllib.parse import quote
                     safe_keywords = quote(query_text)
                     await page.goto(f"https://www.linkedin.com/search/results/people/?keywords={safe_keywords}", wait_until="domcontentloaded", timeout=60000)
                     await self.auth_manager.simulate_human_reading(page)
                     # 2. "Konumlar" (Locations) Filtresi
                     if location_name:
                         print(f"[{self.agent_name}] Applying 'Locations' filter for: {location_name}...")
                         location_selectors = [
                             "label:has-text('Konumlar')",
                             "label:has-text('Locations')",
                             "button[aria-label*='Konum']", 
                             "button[aria-label*='Location']"
                         ]
                         
                         for selector in location_selectors:
                             try:
                                 btn = page.locator(f"{selector} >> visible=true").first
                                 await btn.click(timeout=3000)
                                 print(f"[{self.agent_name}] Clicking 'Locations' filter using selector: {selector}")
                                 await asyncio.sleep(1.0)
                                 break
                             except:
                                 continue

                         # Input bul ve yaz
                         try:
                             loc_input = page.locator(
                                 "input[placeholder*='Konum'], input[placeholder*='location'], input[aria-label*='Konum']"
                             ).first
                             
                             await loc_input.wait_for(state="visible", timeout=5000)
                             await loc_input.fill("")
                             
                             # human_type delay
                             for char in location_name:
                                 await page.keyboard.insert_text(char)
                                 await asyncio.sleep(random.uniform(0.1, 0.3))

                             await page.wait_for_selector("div[role='option']", timeout=5000)
                             suggestions = page.locator("div[role='option']")
                             if await suggestions.count() > 0:
                                 await suggestions.first.click()

                             # Sonuçları Göster
                             try:
                                 show_btn = page.locator(
                                     "button:has-text('Sonuçları göster'), button:has-text('Show results')"
                                 ).locator("visible=true").first
                                 await show_btn.click(timeout=5000)
                                 await asyncio.sleep(1.0)
                             except:
                                 await page.keyboard.press("Enter")
                                 await asyncio.sleep(1.0)
                         except Exception as e:
                             print(f"[{self.agent_name}] Konum filtresi eklenirken hata: {e}")
                             await page.keyboard.press("Enter")
                 
                 await self.auth_manager.simulate_human_reading(page)
                 await self.auth_manager.simulate_human_scroll(page, scrolls=3)
                 
                 profile_links = set()
                 max_pages = 2
                 current_page = 1
                 
                 while current_page <= max_pages:
                     print(f"[{self.agent_name}] Sayfa {current_page} sonuclari isleniyor...")
                     
                     try:
                         # Yeni icerigin guncellenmesini bekle
                         await page.wait_for_selector('.entity-result__item, .reusable-search__result-container, div.search-results-container__no-results', state="attached", timeout=15000)
                     except:
                         pass

                     # Linkleri topla - Genis Kapsamli Selectorler
                     possible_link_selectors = [
                         "div[data-view-name='people-search-result'] > a",
                         "span.entity-result__title-text a.app-aware-link",
                         "span.entity-result__title-text a",
                         ".reusable-search__result-container a.app-aware-link",
                         "li.reusable-search__result-container h3 a"
                     ]
                     
                     found_links_count = 0
                     
                     for selector in possible_link_selectors:
                         links = page.locator(selector)
                         count = await links.count()
                         
                         if count > 0:
                             print(f"[{self.agent_name}] Selector '{selector}' ile {count} profil linki bulundu.")
                             
                             for i in range(count):
                                 try:
                                     href = await links.nth(i).get_attribute("href")
                                     if href and "/in/" in href:   # Sadece profil linkleri
                                         clean_url = href.split("?")[0]
                                         if clean_url not in profile_links:
                                             profile_links.add(clean_url)
                                             target_pages.append({
                                                 "query_id": query_id,
                                                 "url": clean_url,
                                                 "domain": "linkedin.com",
                                                 "status": "ready_for_scrape",
                                                 "source_type": "linkedin_person"
                                             })
                                             found_links_count += 1
                                 except:
                                     continue
                             
                             if found_links_count > 0:
                                 break
                     
                     if current_page >= max_pages:
                         break
                         
                     print(f"[{self.agent_name}] Sonraki sayfaya geciliyor...")
                     
                     # Sayfanin en altina parca parca in ki lazy load tetiklensin
                     await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                     await asyncio.sleep(1.0)
                     await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                     await asyncio.sleep(random.uniform(2.0, 3.0))
                     
                     pagination_selectors = [
                         "button.artdeco-pagination__button--next",
                         "button[aria-label='İleri']",
                         "button[aria-label='Next']",
                         ".artdeco-pagination__button.artdeco-pagination__button--next",
                         "button:has-text('İleri')",
                         "button:has-text('Next')",
                         "svg[data-test-icon='chevron-right-small']",
                         "span:has-text('Sonraki')",
                         "span:has-text('Next')",
                         "span:has(svg#chevron-right-small)"
                     ]
                     
                     next_btn = None
                     for sel in pagination_selectors:
                         try:
                             btn = page.locator(sel).first
                             if await btn.is_visible():
                                 next_btn = btn
                                 print(f"[{self.agent_name}] Pagination butonu bulundu: {sel}")
                                 break
                         except:
                             continue
                             
                     if next_btn and await next_btn.is_enabled():
                         await next_btn.scroll_into_view_if_needed()
                         await asyncio.sleep(random.uniform(1.0, 2.0))
                         
                         try:
                             async with page.expect_request_finished(timeout=10000):
                                 await next_btn.click(force=True)
                         except:
                             await next_btn.click(force=True)
                             
                         await asyncio.sleep(random.uniform(5.0, 7.0))
                         
                         if current_page % 2 == 0:
                             await asyncio.sleep(random.uniform(2.0, 4.0)) # extra break
                             
                     else:
                         print(f"[{self.agent_name}] Uyari: Sonraki butonu bulunamadi. URL manipülasyonu ile zorlaniyor...")
                         current_url = page.url
                         # URL'de zaten &page=2 gibi parametreler varsa temizleyip yenisini ekle
                         base_url = current_url.split("&page=")[0] if "&page=" in current_url else current_url
                         next_page_url = f"{base_url}&page={current_page + 1}"
                         print(f"[{self.agent_name}] Gidiliyor: {next_page_url}")
                         await page.goto(next_page_url, wait_until="domcontentloaded", timeout=60000)
                         await asyncio.sleep(random.uniform(4.0, 7.0))
                         
                     current_page += 1
                         
                 print(f"[{self.agent_name}] Success: Bulunan ve isaretlenen toplam kisi sayisi: {len(target_pages)}")
                 
             except Exception as e:
                 print(f"[{self.agent_name}] LinkedIn Arama surecinde hata: {e}")
                 
             await browser.close()
             
         return target_pages

class SahibindenBrowsingAgent(BaseBrowserAgent):
    """
    Sahibinden.com'a ozel arama ajani. Emlak ve Vasıta ilanlarini listeler,
    resilience (Exponential Backoff), bot engelleme (Cloudflare/Captcha asma) saglar
    ve bulunan ilan URL'lerini target_pages icerisine toplar.
    """
    def __init__(self):
        super().__init__("sahibinden-browser-v1")
        from utils.domain_handlers.sahibinden_handler import SahibindenHandler
        self.handler = SahibindenHandler()

    async def run_browsing(self, root_sources, data):
        target_pages = []
        parsed = data.get("parsed_data", {})
        query_id = data.get("query_id", "q_sahibinden")
        
        # 1. SahibindenHandler ile URL Olustur
        search_url = self.handler.build_search_url(data)
        print(f"[{self.agent_name}] Sahibinden Hedef URL Olusturuldu: {search_url}")
        
        from utils.network_retry import with_retry
        
        @with_retry(max_retries=3, base_backoff=5)
        async def fetch_pages():
            pages_found = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
                context = await self.configure_context(browser)
                page = await self.create_stealth_page(context)
                
                try:
                    # Stealth Init - WebDriver Bypass
                    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    # Ana arama sayfasina git
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Cloudflare / Basili Tut Captcha Cozucu (AuthManager üzerinden)
                    await self.auth_manager.solve_captcha(page)
                    await self.auth_manager.simulate_human_reading(page)
                    
                    # Lazy-load ve sayfada geziniyor imaji vermek icin scroll
                    await self.auth_manager.simulate_human_scroll(page, scrolls=2)
                    
                    # Sahibinden'de sonuclar listelenene kadar bekle
                    try:
                        await page.wait_for_selector(".searchResultsItem, tr.searchResultsItem, table.searchResultsTable tr", timeout=20000)
                    except:
                        pass # Belki sonuc yoktur veya tablo degismistir, yine de devam et.
                        
                    # Linkleri Topla (İlan Başlıkları)
                    links = page.locator("a.classifiedTitle")
                    count = await links.count()
                    
                    if count > 0:
                        print(f"[{self.agent_name}] Sayfada {count} ilan bulundu. URL'ler cikariliyor...")
                        for i in range(count):
                            href = await links.nth(i).get_attribute("href")
                            if href:
                                if href.startswith("http"):
                                    full_url = href
                                else:
                                    full_url = f"https://www.sahibinden.com{href}"
                                
                                pages_found.append({
                                    "query_id": query_id,
                                    "url": full_url,
                                    "domain": "sahibinden.com",
                                    "status": "ready_for_scrape",
                                    "source_type": "sahibinden_listing"
                                })
                    else:
                        print(f"[{self.agent_name}] UYARI: Ilan listesi alinmadi. Captcha'da kalinmis veya ilan yok olabilir.")
                    
                finally:
                    await browser.close()
            return pages_found

        try:
             target_pages = await fetch_pages()
        except Exception as e:
             print(f"[{self.agent_name}] Fetch Pages Network Retry blogu tamamen coktu: {e}")
             
        return target_pages
