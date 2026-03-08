import os
import time
import random
import json
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
except ImportError:
    from playwright_stealth import Stealth
    def stealth_sync(page):
        Stealth().apply_stealth_sync(page)


class BrowsingAgent:

    def __init__(self):

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.base_url = "https://www.sahibinden.com"

        self.urls_file = "listing_urls.json"


    # ======================
    # HUMAN SIMULATION
    # ======================

    def _random_pause(self,min_ms=1000,max_ms=3000):

        time.sleep(random.uniform(min_ms,max_ms)/1000)


    def _human_type(self,selector,text):

        element = self.page.locator(selector).first

        element.wait_for(state="visible",timeout=8000)

        element.click()

        self.page.keyboard.press("Control+A")

        self.page.keyboard.press("Backspace")

        for c in text:

            self.page.keyboard.type(c,delay=random.randint(50,120))



    # ======================
    # CAPTCHA
    # ======================

    def solve_captcha(self):

        try:

            # 1. Cloudflare Turnstile Checkbox
            try:
                # Cloudflare'ın checkbox'u bazen gizlidir veya shadow DOM içindedir.
                for _ in range(3):
                    cf_iframe = self.page.frame_locator("iframe[src*='cloudflare'], iframe[title*='Widget']").locator(".ctp-checkbox-label, input[type='checkbox'], #challenge-stage").first
                    
                    if cf_iframe.is_visible(timeout=3000):
                        print("🛡️ Cloudflare Turnstile tespit edildi, tıklanıyor...")
                        box = cf_iframe.bounding_box()
                        if box:
                            # Tıklamayı direkt koordinata yap ki bot algılanmasın
                            x = box["x"] + box["width"] / 2
                            y = box["y"] + box["height"] / 2
                            self.page.mouse.move(x, y, steps=10)
                            time.sleep(random.uniform(0.5, 1.0))
                            self.page.mouse.click(x, y)
                        else:
                            cf_iframe.click(force=True)
                            
                        time.sleep(random.uniform(3, 5))
                    else:
                        break # Eğer görünmüyorsa zaten geçilmiştir
            except:
                pass

            # 2. Sahibinden Klasik "Basılı Tutun"
            button = self.page.locator(
            "button:has-text('Basılı Tutun'), button:has-text('Press and Hold')"
            ).first


            if button.is_visible(timeout=2000):

                print("🛡️ CAPTCHA çözülüyor")

                box = button.bounding_box()
                if box:
                    x = box["x"] + box["width"]/2
                    y = box["y"] + box["height"]/2

                    self.page.mouse.move(x,y)

                    self.page.mouse.down()

                    time.sleep(random.uniform(4,6))

                    self.page.mouse.up()

                    print("✅ CAPTCHA geçildi")

        except:

            pass



    # ======================
    # OPEN SITE
    # ======================

    def open_site(self):

        print("\n===== Browsing Agent =====")

        self.playwright = sync_playwright().start()

        try:
            print("🔗 Chrome'a CDP (localhost:9222) üzerinden bağlanılıyor...")
            self.browser = self.playwright.chromium.connect_over_cdp("http://localhost:9222")
            self.context = self.browser.contexts[0]
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = self.context.new_page()
                
        except Exception as e:
            print("\n❌ Chrome CDP bağlantı hatası!")
            print("Lütfen Chrome'u debug modunda başlattığınızdan emin olun:")
            print("Yol: chrome.exe --remote-debugging-port=9222")
            print(f"Hata detayı: {e}\n")
            raise e
        
        # Kesin çözüm: Navigator webdriver override (Turnstile için çok önemli)
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Stealth ÖNCE uygulanmalı (goto'dan önce)
        try:
            stealth_sync(self.page)
        except Exception as e:
            print(f"⚠️ Stealth uygulama hatası: {e}")

        # Gerçek tarayıcı header'ları
        self.page.set_extra_http_headers({
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "DNT": "1",
        })

        try:
            self.page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"⚠️ Ana sayfa yüklenemedi: {e}")

        time.sleep(random.uniform(2, 4))

        self.solve_captcha()

        print("✅ Sahibinden açıldı")



    # ======================
    # SEARCH
    # ======================

    def search(self, query):
        """Arama kutusuna yazarak arama yapar (iç kullanım)."""
        print("🔎 Arama:", query)

        try:
            self.page.wait_for_selector("#searchText", timeout=10000)
            self._human_type("#searchText", query)
            self.page.keyboard.press("Enter")
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            except:
                pass
            time.sleep(3)
            self.solve_captcha()
        except Exception as e:
            print(f"⚠️ Search kutusu bulunamadı, URL ile devam: {e}")
            self.search_with_query(query)


    def search_with_query(self, query):
        """URL tabanlı arama — daha kararlı yöntem."""
        from urllib.parse import quote_plus

        print("🔎 URL ile arama:", query)

        search_url = f"{self.base_url}/arama?query_text={quote_plus(query)}"

        try:
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"⚠️ goto timeout: {e}")

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
        except:
            pass

        time.sleep(3)
        self.solve_captcha()
        print("✅ Arama tamamlandı, URL:", self.page.url[:80])


    # ======================
    # FILTER
    # ======================

    def apply_filters(self,filters):

        if not filters:

            print("Filtre yok")

            return


        print("⚙️ Filtre uygulanıyor")

        from utils.filter_manager import FilterProcessor,UrlBuilder


        current_url = self.page.url


        params = FilterProcessor.process(filters)


        builder = UrlBuilder(current_url)

        new_url = builder.add_params(current_url,params)


        self.page.goto(new_url)

        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except:
            pass
        time.sleep(3)

        print("✅ Filtre uygulandı")



    # ======================
    # URL COLLECTION
    # ======================

    def collect_urls(self,max_pages=5):

        print("\nURL toplanıyor...")

        urls=set()

        for page_no in range(1,max_pages+1):

            print("Sayfa:",page_no)

            # Sahibinden.com'da ilan satırları tr.searchResultsItem veya benzer selector'da
            # Birden fazla alternatif dene
            found = False
            for selector in [
                "tr.searchResultsItem",
                ".searchResultsItem",
                "table.searchResultsTable tr",
                ".classified-list li",
            ]:
                try:
                    self.page.wait_for_selector(selector, timeout=20000)
                    found = True
                    break
                except:
                    continue

            if not found:
                print(f"⚠️ Sayfa {page_no}: ilan listesi bulunamadı, atlanıyor")
                # Yine de link toplamayı dene
                pass

            links=self.page.locator("a.classifiedTitle").all()

            for l in links:

                href=l.get_attribute("href")

                if href:

                    if href.startswith("http"):
                        urls.add(href)
                    else:
                        urls.add(self.base_url+href)

            print("Toplanan:",len(urls))

            if not urls and page_no == 1:
                print("❌ Hiç URL toplanamadı, durduruluyor")
                break

            next_btn=self.page.locator(
                "a.prevNextBut[title='Sonraki']"
            ).first

            if next_btn.is_visible():

                next_btn.click()

                # Sahibinden'in bot tespitini atlatmak için sayfa geçişleri arası insan beklemesi
                time.sleep(random.uniform(10, 18))

            else:

                break



        urls=list(urls)


        with open(self.urls_file,"w",encoding="utf-8") as f:

            json.dump(urls,f,indent=2,ensure_ascii=False)


        print("\nToplam URL:",len(urls))


        return urls


    def collect_urls_from_pages(self, max_pages=5):
        """main.py API uyumu için — collect_urls() metodunu çağırır."""
        return self.collect_urls(max_pages=max_pages)


    # ======================
    # MAIN ENTRY
    # ======================

    def run(self,search_data):

        """
        SearchAgent output alır
        """

        parsed = search_data["parsed_data"]

        query = parsed.get("query","")

        filters = parsed.get("filters",{})


        self.open_site()


        self.search(query)


        self.apply_filters(filters)


        urls=self.collect_urls()


        return urls



    # ======================
    # CLOSE
    # ======================

    def close(self):
        
        try:
            if self.browser:
                self.browser.disconnect()
            
            if self.playwright:
                self.playwright.stop()
        except:
            pass
