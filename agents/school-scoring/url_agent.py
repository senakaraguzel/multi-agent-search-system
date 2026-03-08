import asyncio
import json
import random
import re
import urllib.parse
from playwright.async_api import async_playwright
from utils.text_utils import validate_school_name, slugify

class URLAgent:
    def __init__(self, headless=False):
        self.agent_name = "url_agent"
        self.headless = headless
        self.base_url = "https://www.google.com"

    async def search_google(self, school_name):
        """
        Google üzerinde arama yapar ve ham linkleri toplar.
        Stealth özellikleri eklenmiş versiyon.
        """
        query = f"timeshighereducation {school_name} ranking"
        
        async with async_playwright() as p:
            # Gerçekçi bir tarayıcı başlatma
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"] # Otomasyon bayrağını gizle
            )
            
            # Daha detaylı bağlam (context) ayarları
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale="tr-TR",
                timezone_id="Europe/Istanbul"
            )
            
            page = await context.new_page()
            
            # JavaScript degiskenlerini manipule ederek bot oldugumuzu gizleyelim
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            try:
                # Rastgele bir başlangıç gecikmesi
                await asyncio.sleep(random.uniform(1, 3))
                
                await page.goto(self.base_url, wait_until="networkidle")
                
                # Cookie popup kontrolü
                accept_button = page.locator('button:has-text("Kabul et"), button:has-text("Accept all"), button:has-text("Tümünü kabul et"), button:has-text("I agree")')
                if await accept_button.is_visible(timeout=5000):
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    await accept_button.click()
                
                # Arama kutusuna odaklan ve gerçekçi bir şekilde yaz
                search_input = page.locator('textarea[name="q"], input[name="q"]')
                await search_input.click()
                
                # Kelimeleri tek tek yazarak (insan gibi) simüle et
                for char in query:
                    await page.keyboard.type(char, delay=random.randint(50, 150))
                
                await asyncio.sleep(random.uniform(0.5, 1.0))
                await page.keyboard.press("Enter")
                
                # Sonuçların yüklenmesini bekle
                await page.wait_for_load_state("networkidle")
                
                # Sayfayı biraz aşağı kaydır (insan davranışı simülasyonu)
                await page.mouse.wheel(0, random.randint(300, 700))
                await asyncio.sleep(random.uniform(2, 4))
                
                # Linkleri topla
                links = []
                search_results = page.locator('div#search a')
                count = await search_results.count()
                
                for i in range(min(count, 30)): # Daha fazla linke bakalım
                    href = await search_results.nth(i).get_attribute("href")
                    if href and (href.startswith("http") or href.startswith("/url")):
                        links.append(href)
                
                return list(set(links))
                
            except Exception as e:
                print(f"Hata oluştu: {str(e)}")
                return []
            finally:
                await browser.close()

    def clean_google_link(self, url):
        """
        Google redirect linklerini temizler (/url?q=...).
        """
        if "/url?q=" in url:
            # q= parametresini al
            parsed_url = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'q' in query_params:
                clean_url = query_params['q'][0]
                # & karakterinden sonrasını (varsa) temizle (zaten parse_qs ile hallolur ama garanti olsun)
                return clean_url
        return url

    def filter_the_links(self, links):
        """
        Times Higher Education linklerini filtreler ve istenmeyenleri eler.
        """
        the_links = []
        forbidden_keywords = ['/news/', '/student/', '/about/', '/events/', '/rankings/impact/']
        
        for link in links:
            clean_link = self.clean_google_link(link)
            
            # THE domaini içermeli ve translate linki olmamalı
            if "timeshighereducation.com" in clean_link and "translate.google" not in clean_link:
                # Yasaklı kelimeleri içermemeli
                if not any(kw in clean_link for kw in forbidden_keywords):
                    the_links.append(clean_link)
        
        return list(set(the_links))

    def find_best_match(self, school_name, links):
        """
        Girdi okul adı ile bulunan linkler arasındaki en iyi eşleşmeyi bulur.
        Kelime bazlı ağırlıklı bir skorlama kullanır.
        """
        if not links:
            return None
            
        school_slug = slugify(school_name)
        school_words = set(school_slug.split('-'))
        
        best_link = None
        max_score = -1
        
        for link in links:
            # Link içindeki son kısmı al
            link_parts = link.strip('/').split('/')
            last_part = link_parts[-1]
            link_words = set(last_part.split('-'))
            
            # 1. Kelime kesişimi (Jaccard-like score)
            intersection = school_words.intersection(link_words)
            
            # Önemli: Eğer okul adındaki kritik kelimeler linkte yoksa skoru düşür
            # Örn: "technical" girilmişse ama linkte yoksa bu büyük bir dezavantajdır
            score = len(intersection) * 2
            
            # Tam kelime eşleşmesi bonusu
            if intersection == school_words:
                score += 5
                
            # Uzunluk farkı cezası (Geri kalan kelimeler için)
            diff = abs(len(school_words) - len(link_words))
            score -= diff * 0.5
            
            # Öncelik: /world-university-rankings/ içerenler
            if "/world-university-rankings/" in link:
                score += 3
            
            # Rankings listesi veya directory sayfalarını eliyoruz (genelde okul adı slug'da yalnız olur)
            if "rankings" in last_part and len(link_words) < 3:
                score -= 10
                
            if score > max_score:
                max_score = score
                best_link = link
                
        # Eğer skor çok düşükse eşleşme sayma
        if max_score < 0:
            return None
            
        return best_link

    async def run(self, school_name):
        """
        Main entry point for URL Agent.
        """
        # 1. Validation
        cleaned_name, is_valid = validate_school_name(school_name)
        if not is_valid:
            return {
                "agent": self.agent_name,
                "status": "invalid_input",
                "school_name": school_name
            }
            
        # 2. Google Search
        raw_links = await self.search_google(cleaned_name)
        
        # 3. Filter and Clean
        the_links = self.filter_the_links(raw_links)
        
        # 4. Find Best Match
        best_url = self.find_best_match(cleaned_name, the_links)
        
        if best_url:
            return {
                "agent": self.agent_name,
                "status": "success",
                "school_name": cleaned_name,
                "url": best_url,
                "method": "google_search"
            }
        else:
            return {
                "agent": self.agent_name,
                "status": "not_found",
                "school_name": cleaned_name
            }

if __name__ == "__main__":
    # Test
    agent = URLAgent(headless=False)
    result = asyncio.run(agent.run("Boğaziçi Üniversitesi"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
