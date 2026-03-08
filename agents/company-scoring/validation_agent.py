import random
import asyncio
import json
import os
import re
import datetime
from playwright.async_api import async_playwright
from rapidfuzz import fuzz
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

class ValidationAgent:
    def __init__(self, state_path="linkedin_state.json", headless=True):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.model = os.getenv("AZURE_OPENAI_MODEL", "o4-mini")
        self.state_path = state_path
        self.headless = headless
        self.results_path = "validation_results.json"
        
        # Her yeni oturum başatılırken sonuç dosyasını temizle
        with open(self.results_path, "w", encoding="utf-8") as f:
            json.dump([], f)

    def normalize_text(self, text):
        """
        Metni normalize eder: lower, özel karakter temizleme, türkçe karakter dönüşümü.
        """
        if not text:
            return ""
        text = text.lower()
        # Türkçe karakter dönüşümü
        char_map = str.maketrans("çğışüö", "cgisuo")
        text = text.translate(char_map)
        # Özel karakterleri temizle
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Fazla boşlukları temizle
        text = " ".join(text.split())
        return text

    def get_initials(self, text):
        """
        Metindeki kelimelerin baş harflerini döndürür. (Örn: International Business Machines -> IBM)
        """
        words = text.split()
        if len(words) > 1:
            return "".join([word[0] for word in words if word]).lower()
        return ""

    async def light_scrape(self, url):
        """
        LinkedIn sayfasından minimum veriyi (H1, Title, Slug, About) çeker.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            
            # Storage state varsa onu kullan, yoksa boş context aç
            if os.path.exists(self.state_path):
                context = await browser.new_context(
                    storage_state=self.state_path,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={'width': 1366, 'height': 768},
                    locale="en-US",
                    timezone_id="UTC"
                )
                print(f"DEBUG: Storage state yüklendi: {self.state_path}")
            else:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={'width': 1366, 'height': 768},
                    locale="en-US",
                    timezone_id="UTC"
                )
                print("DEBUG: Storage state bulunamadı, girişsiz devam ediliyor.")
            page = await context.new_page()
            
            try:
                print(f"DEBUG: Sayfaya gidiliyor: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(random.uniform(2, 4))
                
                # Eğer hala giriş sayfasına yönlendiriliyorsa
                if "login" in page.url:
                    print(f"UYARI: LinkedIn Giriş sayfasına yönlendirildi! ({page.url})")
                    return None
                
                # Başlık kontrolü (Login duvarına takılıp takılmadığımızı anlamak için)
                page_title = await page.title()
                print(f"DEBUG: Sayfa Başlığı: {page_title}")
                
                if "LinkedIn: Log In or Sign Up" in page_title or "LinkedIn’e Giriş Yap" in page_title:
                    print("ERROR: LinkedIn login duvarına takıldı! Çerezler geçersiz olabilir.")
                
                h1_name = ""
                # Öncelikli kurumsal başlık selektörleri
                h1_locators = [
                    "h1.org-top-card-summary__title", 
                    "h1", 
                    ".org-top-card-summary__title span",
                    "span[itemprop='name']"
                ]
                for selector in h1_locators:
                    try:
                        loc = page.locator(selector).first
                        if await loc.count() > 0:
                            h1_name = await loc.inner_text()
                            if h1_name.strip():
                                break
                    except:
                        continue
                
                print(f"DEBUG: Scraped Name: {h1_name.strip()}")
                
                # Slug ayıkla
                slug = url.split("/company/")[-1].strip("/")
                
                # About section
                about_text = ""
                about_locators = [
                    "section.org-about-company-module__about-us-alignment p",
                    ".org-about-us-organization-description__text",
                    ".org-grid__content-main--with-columns p",
                    "p.break-words",
                    "section.about-us p"
                ]
                for selector in about_locators:
                    try:
                        loc = page.locator(selector).first
                        if await loc.count() > 0:
                            about_text = await loc.inner_text()
                            if about_text.strip():
                                break
                    except:
                        continue
                
                # Lokasyon bilgisi
                location_text = ""
                location_locators = [
                    "div.org-top-card-summary-info-list__info-item",
                    ".org-top-card-summary__info-list-item",
                    "span.org-top-card-summary__location"
                ]
                for selector in location_locators:
                    try:
                        loc = page.locator(selector).first
                        if await loc.count() > 0:
                            location_text = await loc.inner_text()
                            if location_text.strip():
                                break
                    except:
                        continue

                return {
                    "scraped_name": h1_name.strip(),
                    "page_title": page_title.strip(),
                    "slug": slug,
                    "about_text": about_text.strip()[:500], # İlk 500 karakter yeterli
                    "location": location_text.strip()
                }
            except Exception as e:
                print(f"Scraping hatası ({url}): {e}")
                return None
            finally:
                await browser.close()

    def calculate_confidence(self, result_type, similarity=0):
        """
        Blueprint'e göre güven skoru hesaplar.
        """
        if result_type == "deterministic_strong":
            return round(0.85 + (similarity / 100) * 0.1, 2)
        elif result_type == "deterministic_weak":
            return round(similarity / 200, 2)
        elif result_type == "llm_true":
            return 0.75
        elif result_type == "llm_false":
            return 0.35
        return 0.0

    async def validate_with_llm_comparative(self, company_name, candidates_data, city_name=None, role_name=None):
        """
        Birden fazla aday arasından hedef şirkete en uygun olanı seçer.
        Zenginleştirilmiş aday özet formatı ve güncel prompt kullanır.
        """
        candidates_summary = ""
        for i, data in enumerate(candidates_data):
            candidates_summary += f"{i+1}. Name: {data.get('scraped_name', 'N/A')}\n"
            candidates_summary += f"   Location: {data.get('location', 'N/A')}\n"
            candidates_summary += f"   Industry: {data.get('industry', 'N/A')}\n"
            candidates_summary += f"   Description: {data.get('about_text', 'N/A')[:200]}...\n\n"

        prompt = f"""
You are a professional LinkedIn validation agent. Your job is to choose the BEST LinkedIn company page from the given candidates that represents the SAME real-world company.

TARGET COMPANY:
Name: {company_name}
City: {city_name if city_name else "Unknown"}
Role: {role_name if role_name else "Unknown"}

CANDIDATES:
{candidates_summary}

STRICT DECISION RULES (follow these exactly):

1. NAME MATCH (HIGH PRIORITY)
- Candidate name must contain the core words of the target company.
- Ignore small suffixes like Ltd, A.Ş., Inc, Group, Teknoloji, Yazılım.
- Accept common abbreviations (e.g., LCW for LC Waikiki, IBM for International Business Machines).
- If core name is completely different and no known alias exists → reject.

2. INDUSTRY MATCH (RECOMMENDED)
- Candidate should operate in the same industry or business type.
- However, do NOT reject solely based on industry if the name match is very strong.
- Many large companies (Getir, Amazon, etc.) operate in multiple industries (Tech, Delivery, Retail).

3. LOCATION MATCH (PRIORITY)
- Exact city match -> highest priority.
- Different city within Turkey but same company -> acceptable.
- Unknown location but name and industry strongly match -> acceptable.

4. NO GUESSING / ANTI-HALLUCINATION
- If multiple candidates share the name but have VERY different industries (e.g., "Eskidji" auction vs "Eskidji" real estate) and the target is clear, pick the right one.
- If none match, set is_valid = false.

5. CONFIDENCE SCORE
- Assign 0.0–1.0 based on evidence.

OUTPUT FORMAT (JSON ONLY):
{{
  "best_candidate_index": number,
  "is_valid": true/false,
  "reasoning": "Açıklama",
  "confidence_score": 0.0 to 1.0
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1
            )
            raw_content = response.choices[0].message.content
            # Markdown ve gereksiz boşluk temizleme
            clean_content = re.sub(r'```json\s*|\s*```', '', raw_content).strip()
            # JSON içindeki yorum satırlarını temizle (// ...)
            clean_content = re.sub(r'//.*', '', clean_content)
            
            result = json.loads(clean_content)
            return result
        except Exception as e:
            print(f"LLM Karşılaştırma Hatası: {e}\nHamah İçerik: {raw_content if 'raw_content' in locals() else 'N/A'}")
            return {"best_candidate_index": 0, "is_valid": False, "reasoning": str(e)}

    async def validate_with_llm(self, company_name, scraped_data, city_name=None):
        """
        Şüpheli durumlarda LLM ile semantik doğrulama yapar ve gerekçe sunar.
        """
        prompt = f"""You are a professional business analyst validating a LinkedIn company page.
        
TARGET:
Company Name: {company_name}
Target City: {city_name if city_name else 'N/A'}

SCRAPED DATA FROM LINKEDIN:
Scraped Name: {scraped_data.get('scraped_name', 'N/A')}
Page Title: {scraped_data.get('page_title', 'N/A')}
Location: {scraped_data.get('location', 'N/A')}
About Section: {scraped_data.get('about_text', 'N/A')}

VERIFICATION RULES:
1. **SAME ENTITY**: Does this page represent the same company? (Consider initials, subsidiaries, and common naming variations).
2. **LOCATION MATCH**: 
   - If a city is provided, a global/main headquarters page is VALID (e.g., Target "Ford / Ankara" -> "Ford Otosan HQ" is VALID).
   - If the page is a direct branch in a DIFFERENT city than the target and NOT the HQ, be extremely cautious (Halicination Risk).
3. **INDUSTRY CONSISTENCY**: Does the 'About' section describe the same industry?
4. **AMBIGUITY**: If the name is very common (e.g., "Yılmaz Elektrik"), ensure the location or context makes it plausible.

OUTPUT FORMAT (JSON ONLY):
{{
  "is_valid": true/false,
  "reasoning": "Explain why in 1-2 sentences in Turkish",
  "confidence_score": 0.0 to 1.0
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1
            )
            raw_content = response.choices[0].message.content
            print(f"DEBUG: LLM Raw Output:\n{raw_content}\n---")
            
            clean_content = re.sub(r'```json\s*|\s*```', '', raw_content).strip()
            clean_content = re.sub(r'//.*', '', clean_content)
            
            result = json.loads(clean_content)
            return result
        except Exception as e:
            print(f"LLM doğrulama hatası (JSON Parsing): {e}")
            if 'raw_content' in locals():
                print(f"Hatalı İçerik: {raw_content}")
            return {"is_valid": False, "reasoning": f"Tahmini hata: {str(e)}", "confidence_score": 0.0}

    async def run(self, company_name, candidates_urls, city_name=None, role_name=None):
        """
        Birden fazla aday arasından en doğru olanı bulur ve doğrular.
        """
        if not candidates_urls:
            return {"is_valid": False, "reason": "Aday URL bulunamadı."}

        print(f"\n--- {len(candidates_urls)} Aday Değerlendiriliyor: {company_name} ---")
        
        candidates_data = []
        for url in candidates_urls[:10]: # En fazla 10 adayı derinlemesine incele
            data = await self.light_scrape(url)
            if data:
                data['url'] = url
                candidates_data.append(data)
            await asyncio.sleep(1)

        if not candidates_data:
            return {"is_valid": False, "reason": "Aday verileri çekilemedi."}

        # LLM Karşılaştırmalı Seçim
        print("Adaylar kıyaslanıyor...")
        decision = await self.validate_with_llm_comparative(company_name, candidates_data, city_name, role_name)
        
        best_idx = decision.get("best_candidate_index", 0) - 1
        
        if best_idx >= 0 and best_idx < len(candidates_data) and decision.get("is_valid"):
            best_candidate = candidates_data[best_idx]
            result = {
                "company_name": company_name,
                "linkedin_url": best_candidate['url'],
                "is_valid": True,
                "confidence": decision.get("confidence_score", 0.0),
                "reason": decision.get("reasoning"),
                "scraped_data": best_candidate,
                "timestamp": datetime.datetime.now().isoformat()
            }
        else:
            result = {
                "company_name": company_name,
                "is_valid": False,
                "reason": decision.get("reasoning", "Hiçbir aday uygun bulunmadı."),
                "timestamp": datetime.datetime.now().isoformat()
            }

        return self.save_result(result)

    def save_result(self, result):
        """
        Sonucu JSON dosyasına ekler.
        """
        data = []
        if os.path.exists(self.results_path):
            with open(self.results_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        
        data.append(result)
        with open(self.results_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return result

if __name__ == "__main__":
    # Örnek test
    async def main():
        agent = ValidationAgent()
        # IBM Testi (LLM Semantic Check tetiklemesi muhtemel)
        test1 = await agent.run("International Business Machines", "https://www.linkedin.com/company/ibm")
        print(f"Test 1 Sonucu: {test1}")
        
        # Yanlış sayfa testi (Regional)
        test2 = await agent.run("OpenAI", "https://www.linkedin.com/company/openai-france")
        print(f"Test 2 Sonucu: {test2}")

    asyncio.run(main())
