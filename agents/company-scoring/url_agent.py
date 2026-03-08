import os
import asyncio
import re
import urllib.parse
import random
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from openai import AzureOpenAI
from fuzzywuzzy import fuzz

# .env dosyasını yükle
load_dotenv()

class URLAgent:
    def __init__(self, headless=True):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.model = os.getenv("AZURE_OPENAI_MODEL", "o4-mini")
        self.headless = headless

    async def search_google(self, company_name, city_name=None):
        """
        Google üzerinde şirket aratılarak LinkedIn URL'si bulunur.
        `city_name` varsa sorguya dahil edilir: "linkedin [company] / [city] company page"
        """
        if city_name:
            query = f'linkedin {company_name} {city_name} company page'
        else:
            query = f'linkedin {company_name} company page'
        
        async with async_playwright() as p:
            # slow_mo: Her işlemi yavaşlatarak insan hızına yaklaştırır
            browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=random.randint(50, 100),
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1366, 'height': 768},
                locale="tr-TR",
                timezone_id="Europe/Istanbul"
            )
            
            page = await context.new_page()
            
            # Kapsamlı Manuel Stealth Scriptleri
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['tr-TR', 'tr', 'en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)
            
            try:
                # 1. Google'a git
                await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(1, 2))
                
                # Rastgele mouse hareketleri
                for _ in range(2):
                    await page.mouse.move(random.randint(0, 800), random.randint(0, 600))
                    await asyncio.sleep(random.uniform(0.1, 0.2))
                
                # Çerez uyarısını kapat (Eğer varsa)
                try:
                    accept_button = page.locator('button:has-text("Kabul et"), button:has-text("Accept all"), button:has-text("Tümünü kabul et"), button:has-text("I agree")')
                    if await accept_button.is_visible(timeout=3000):
                        await asyncio.sleep(random.uniform(0.5, 1))
                        await accept_button.click()
                        await asyncio.sleep(random.uniform(0.5, 1))
                except:
                    pass

                # 2. Arama kutusunu bul ve odaklan
                search_box = page.locator('textarea[name="q"], input[name="q"]')
                await search_box.click()
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # 3. İnsan gibi yavaş yavaş yaz
                for char in query:
                    await page.keyboard.type(char, delay=random.randint(50, 150))
                    if random.random() < 0.05: # Arada ekstra kısa duraksama
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        
                await asyncio.sleep(random.uniform(0.8, 1.5))
                await page.keyboard.press("Enter")
                
                # 4. Sonuçların yüklenmesini bekle
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except:
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                
                await asyncio.sleep(random.uniform(2, 4))
                
                # 5. İnsan gibi sayfada gezin (scroll)
                for _ in range(random.randint(2, 4)):
                    await page.mouse.wheel(0, random.randint(300, 600))
                    await asyncio.sleep(random.uniform(1, 3))
                
                # 6. Linkleri topla
                links = []
                # Google sonuçlarındaki tüm muhtemel link alanları
                search_results = page.locator('a')
                count = await search_results.count()
                
                for i in range(count):
                    try:
                        href = await search_results.nth(i).get_attribute("href")
                        if href and "linkedin.com/company/" in href:
                            clean_url = self.clean_url(href)
                            if clean_url and self.is_valid_company_url(clean_url):
                                links.append(clean_url)
                    except:
                        continue
                
                return list(dict.fromkeys(links))
            except Exception as e:
                print(f"Arama sırasında hata: {e}")
                return []
            finally:
                await browser.close()

    def clean_url(self, url):
        """
        Google yönlendirmelerini temizler.
        """
        if "/url?q=" in url:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            if "q" in query:
                url = query["q"][0]
        
        # Subdomain bağımsız eşleşme (www, tr, vb. desteklerle)
        match = re.search(r'(https://[a-z]+\.linkedin\.com/company/[^/?#]+)', url)
        if match:
            return match.group(1)
        return None

    def is_valid_company_url(self, url):
        """
        /in/, /school/, /jobs/ gibi istenmeyen kısımları eler.
        """
        forbidden = ["/in/", "/school/", "/jobs/", "/posts/", "/life/"]
        return not any(f in url for f in forbidden)

    def calculate_similarity(self, company_name, url):
        """
        Şirket adı ile URL slug'ı arasındaki benzerliği hesaplar.
        """
        slug = url.split("/")[-1].replace("-", " ").lower()
        name_norm = company_name.lower()
        return fuzz.token_sort_ratio(name_norm, slug)

    async def select_with_llm(self, company_name, candidate_urls):
        """
        OpenAI kullanarak en doğru resmi hesabı seçer.
        """
        if not candidate_urls:
            return None
        
        if len(candidate_urls) == 1:
            return candidate_urls[0]

        prompt = f"""You are selecting the official LinkedIn company page.

Company Name:
{company_name}

Candidate URLs:
{candidate_urls}

Rules:
- Select ONLY one URL from the provided list.
- Do NOT invent, modify, or create a new URL.
- Choose the main official company page.
- Do NOT select subsidiaries, regional branches, or sub-brands unless the company name explicitly refers to them.
- Prefer the global or primary company page.
- If none of the URLs clearly match the company, return "NONE".

Output format:
Return only the selected URL.
If no correct match exists, return exactly: NONE"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1 # o4-mini/o1 fixed at 1
            )
            result = response.choices[0].message.content.strip()
            return result if result != "NONE" else None
        except Exception as e:
            print(f"LLM Error: {e}")
            return candidate_urls[0] # Hata durumunda ilkini döndür (veya None)

    async def run(self, company_name, city_name=None):
        """
        Ana işlem akışı: Sadece Google'dan adayları toplar.
        """
        print(f"Google üzerinden adaylar toplanıyor: {company_name}{f' ({city_name})' if city_name else ''}...")
        
        # Sadece Google Adayları
        all_candidates = await self.search_google(company_name, city_name)
        
        if not all_candidates:
            print("Google'da hiçbir aday bulunamadı.")
            return {"company_name": company_name, "candidates": [], "status": "not_found"}

        return {
            "company_name": company_name,
            "candidates": all_candidates,
            "status": "success"
        }

if __name__ == "__main__":
    async def main():
        agent = URLAgent(headless=False)
        test_company = "OpenAI"
        result = await agent.run(test_company)
        print(result)

    asyncio.run(main())
