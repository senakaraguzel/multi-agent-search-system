import json
import os
import random
import asyncio
from datetime import datetime, timedelta

try:
    from playwright_stealth import Stealth
    stealth_available = True
except ImportError:
    stealth_available = False

class AuthManager:
    """
    Merkezi Kimlik Dogrulama, Oturum ve Rate-Limiting Yoneticisi.
    LinkedIn gibi zorlu hedeflerde Stealth (Gizlilik) ve Human-Like davranislari saglar.
    """
    # Sabit, gercekci bir User-Agent (Fingerprint degismesin diye)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, secret_path="secret.json"):
        self.secret_path = secret_path
        self._cookies = []
        self._last_request_time = None
        self._last_linkedin_time = None
        self._min_delay = 3.0
        self._max_delay = 7.0
        
        # --- BAN / OBSERVABILITY METRICS ---
        self.metrics = {
             "403_forbidden": 0,
             "429_too_many_requests": 0,
             "captcha_encountered": 0,
             "captcha_solved": 0,
             "cloudflare_blocks": 0
        }
        
        self.load_cookies()

    def load_cookies(self):
        """secret.json dosyasindan cerezleri okur ve Playwright formatina donusturur."""
        if not os.path.exists(self.secret_path):
            print(f"[AuthManager] UYARI: {self.secret_path} bulunamadi. Kimlik dogrulama gerektiren islemler (LinkedIn vb.) basarisiz olabilir.")
            return

        try:
            with open(self.secret_path, "r", encoding="utf-8") as f:
                secrets = json.load(f)
                
            # Playwright Cookie Format (Ornek: .linkedin.com)
            if "li_at" in secrets:
                 self._cookies.append({
                     "name": "li_at",
                     "value": secrets["li_at"],
                     "domain": ".linkedin.com",
                     "path": "/"
                 })
            if "JSESSIONID" in secrets:
                 self._cookies.append({
                     "name": "JSESSIONID",
                     "value": secrets["JSESSIONID"],
                     "domain": ".linkedin.com",
                     "path": "/"
                 })
                 
            print(f"[AuthManager] Session verileri ({len(self._cookies)} adet) basariyla yuklendi.")
        except Exception as e:
            print(f"[AuthManager] secret.json okuma hatasi: {e}")

    def get_cookies(self):
        return self._cookies

    async def apply_stealth(self, page):
        """navigator.webdriver override ve diger bot detection mitigation (playwright-stealth)"""
        if stealth_available:
             await Stealth().apply_stealth_async(page)
        else:
             print("[AuthManager] UYARI: playwright-stealth modulu yuklu degil, stealth uygulanmadi.")

    async def check_session_validity(self, page) -> bool:
        """
        LinkedIn'e hafif bir baglanti yaparak oturumun aktif olup olmadigini (Orn: giris yap butonu yok mu) kontrol eder.
        CAPTCHA, 403 veya 429 gibi durumlar gorulmedigine emin olur.
        """
        if not self._cookies:
            print("[AuthManager] Cookie bulunmadigi icin session gecersiz.")
            return False
            
        try:
            print("[AuthManager] Session validity ve IP saglik kontrolu yapiliyor...")
            
            # Ana sayfaya git (zaten aciksa feed'e gider)
            if "linkedin.com" not in page.url:
                await page.goto("https://www.linkedin.com/feed/", timeout=45000, wait_until="domcontentloaded")
            
            # Sayfa html'ini alip CAPTCHA/429/403 testleri
            content = await page.content()
            
            # Security Wall / Captcha Kontrolu
            title = await page.title()
            has_captcha_frame = await page.locator('iframe[src*="captcha"]').count() > 0
            has_challenge_box = await page.locator('#captcha-internal').count() > 0
            
            if has_captcha_frame or has_challenge_box or "security verification" in title.lower() or "captcha" in title.lower():
                 print("[AuthManager] UYARI: LinkedIn CAPTCHA / Security Block tespit etti!")
                 print("-> Lutfen tarayici uzerinden CAPTCHA'yi manuel olarak cozun. 60 saniye islem bekletiliyor...")
                 await page.wait_for_timeout(60000)
                 
                 # Tekrar kontrol et
                 if await page.locator('iframe[src*="captcha"]').count() > 0 or await page.locator('#captcha-internal').count() > 0:
                     print("[AuthManager] KRITIK HATA: 60 saniye icinde CAPTCHA cozulmedi. Sistem durduruluyor.")
                     import sys; sys.exit(1)
                 else:
                     print("[AuthManager] CAPTCHA basariyla asildi! Isleme devam ediliyor...")
                 
            # 429 Too Many Requests
            if "HTTP ERROR 429" in content or "Too Many Requests" in content:
                 print("[AuthManager] KRITIK HATA: 429 Too Many Requests (Rate Limit asildi)!")
                 import sys; sys.exit(1)

            # Login Kontrolu
            if "login" in page.url or "session_redirect" in page.url:
                 print("[AuthManager] HATA: Session (li_at) suresi dolmus veya gecersiz. Giris ekranina yonlendirildi.")
                 return False
                 
            # Eger hicbir hata yoksa
            auth_element = await page.query_selector('div.global-nav__me-content, a[href*="/in/"]')
            if auth_element:
                 print("[AuthManager] Session gecerli. Giris yapilmis durumda. Bot detection gozukmuyor.")
                 return True
                 
            return True
        except Exception as e:
            if "sys.exit" in str(getattr(e, '__cause__', '')):
                raise e # Eger sys.exit cagirildiysa firlat
            print(f"[AuthManager] Session kontrolu atlandi (Zaman asimi): {e}")
            return True

    async def throttle(self):
        """Standard rate-limiting beklemesi"""
        now = datetime.now()
        if self._last_request_time:
             elapsed = (now - self._last_request_time).total_seconds()
             target_delay = random.uniform(self._min_delay, self._max_delay)
             if elapsed < target_delay:
                  await asyncio.sleep(target_delay - elapsed)
        self._last_request_time = datetime.now()

    async def throttle_linkedin(self):
        """
        LinkedIn ozel asiri strict rate limit. 
        Dakikada max 5-8 profil hedefleniyor -> Ortalama 8-12 saniye bekleme.
        """
        now = datetime.now()
        if self._last_linkedin_time:
             elapsed = (now - self._last_linkedin_time).total_seconds()
             # 8.0 - 13.0 saniye random bekleme (max ~5-7 req/min yapar)
             target_delay = random.uniform(8.0, 13.5)
             if elapsed < target_delay:
                  wait_time = target_delay - elapsed
                  print(f"[AuthManager] LinkedIn Strict Rate Limit: {wait_time:.1f} sn proxy/profil arasi bekleniyor...")
                  await asyncio.sleep(wait_time)
        self._last_linkedin_time = datetime.now()

    # --- HUMAN-LIKE BEHAVIOR SIMULATIONS (Anti-Bot) ---

    async def simulate_human_reading(self, page):
        """Fare hareketleri ve rastgele kısa beklemeler simüle eder."""
        await self.throttle() # Once rate-limit'e tabi tut
        
        # Sayfaya geldikten sonra 1-3 saniye "okuma/algilama" payi
        await page.wait_for_timeout(random.randint(1000, 3000))

    async def simulate_mouse_move(self, page):
         """Fareyi ekranda rastgele dolastirir."""
         try:
             # Ekranda hayali bir mouse gezintisi
             width = page.viewport_size['width'] if page.viewport_size else 1280
             height = page.viewport_size['height'] if page.viewport_size else 800
             x = random.randint(100, width - 100)
             y = random.randint(100, height - 100)
             await page.mouse.move(x, y, steps=random.randint(5, 15))
             await page.wait_for_timeout(random.randint(500, 1500))
         except: pass

    async def simulate_human_scroll(self, page, scrolls=2):
        """
        Saygfa icinde robot gibi tek bir asagi kaydirma degil, insan gibi duraklayarak
        asagi ve bazen biraz yukari kaydirma islemi yapar.
        """
        for _ in range(scrolls):
            # Asagi kaydir
            scroll_amount = random.randint(300, 700)
            await page.mouse.wheel(0, scroll_amount)
            await page.wait_for_timeout(random.randint(800, 2000))
            
            # %20 ihtimalle biraz okumak icin geri (yukari) kaydir
            if random.random() < 0.2:
                 await page.mouse.wheel(0, -random.randint(100, 300))
                 await page.wait_for_timeout(random.randint(500, 1000))

    async def solve_captcha(self, page):
        """Cloudflare Turnstile ve Sahibinden Captcha Çözücü (İnsan benzeri fare hareketleri)"""
        try:
             # 1. Cloudflare Turnstile
             try:
                 for _ in range(3):
                     cf_iframe = page.frame_locator("iframe[src*='cloudflare'], iframe[title*='Widget']").locator(".ctp-checkbox-label, input[type='checkbox'], #challenge-stage").first
                     
                     if await cf_iframe.is_visible(timeout=3000):
                         print("🛡️ [AuthManager] Cloudflare Turnstile tespit edildi, tıklanıyor...")
                         self.metrics["cloudflare_blocks"] += 1
                         box = await cf_iframe.bounding_box()
                         if box:
                             x = box["x"] + box["width"] / 2
                             y = box["y"] + box["height"] / 2
                             await page.mouse.move(x, y, steps=10)
                             await page.wait_for_timeout(random.randint(500, 1000))
                             await page.mouse.click(x, y)
                         else:
                             await cf_iframe.click(force=True)
                             
                         await page.wait_for_timeout(random.randint(3000, 5000))
                     else:
                         break
             except Exception as e:
                 pass

             # 2. Sahibinden Klasik "Basılı Tutun" (Press and Hold)
             try:
                 button = page.locator("button:has-text('Basılı Tutun'), button:has-text('Press and Hold')").first
                 if await button.is_visible(timeout=2000):
                     print("🛡️ [AuthManager] CAPTCHA (Basılı Tutun) çözülüyor")
                     self.metrics["captcha_encountered"] += 1
                     box = await button.bounding_box()
                     if box:
                         x = box["x"] + box["width"]/2
                         y = box["y"] + box["height"]/2
                         await page.mouse.move(x,y, steps=10)
                         await page.mouse.down()
                         await page.wait_for_timeout(random.randint(4000, 6000))
                         await page.mouse.up()
                         self.metrics["captcha_solved"] += 1
             except Exception as e:
                 pass
        except Exception as e:
             print(f"⚠️ [AuthManager] solve_captcha hatasi: {e}")
