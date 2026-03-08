import json
import time
import random


class ScraperAgent:

    def __init__(self, page, headers=None):

        self.page = page

        self.headers = headers or []
        self.expected_keys = [h["key"] for h in self.headers]

        self.input_file = "listing_urls.json"

        self.output_file = "listing_details.json"

        self.scraped_data = []

        self.dynamic_headers = set()

    def abort_routes(self, route):
        """Hız ve gizlilik için resim, css, font gibi kaynakları engelle."""
        try:
            if route.request.resource_type in ["image", "media", "stylesheet", "font"]:
                route.abort()
            else:
                route.continue_()
        except:
            pass

    def scrape_listings(self):

        print("🕵️ ScraperAgent başlatıldı (Optimized Playwright Modu)...")
        
        # Resim vb engelleme aktif ediliyor
        try:
            self.page.route("**/*", self.abort_routes)
        except:
            pass


        try:

            with open(self.input_file,"r",encoding="utf-8") as f:

                urls = json.load(f)

        except:

            print("❌ listing_urls.json bulunamadı")

            return []


        print(f"Toplam {len(urls)} ilan işlenecek")

        # Güvenlik molası için hedef eşik belirleyelim
        self.next_pause_threshold = random.randint(5, 7)
        self.processed_count_since_pause = 0

        # Başarılı referer listesi
        referer_list = [
            "https://www.sahibinden.com/",
            "https://www.sahibinden.com/arama",
            "https://www.sahibinden.com/kategori/emlak",
            "https://www.google.com/",
            None 
        ]

        for i,url in enumerate(urls):

            print(f"[{i+1}/{len(urls)}] İşleniyor: {url[:60]}...")


            try:
                # Evasion: WebDriver bayrağını sil (her navigasyon öncesi garanti olması için)
                self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                # Evasion: Rastgele Referer seçimi
                chosen_referer = random.choice(referer_list)
                
                # Bazen query string ile sahte bir arama geçmişi yarat
                if chosen_referer == "https://www.sahibinden.com/arama" and random.random() > 0.5:
                    chosen_referer += "?query_text=" + random.choice(["kiralik", "satilik", "istanbul", "ankara"])

                if chosen_referer:
                    self.page.goto(url,
                               referer=chosen_referer,
                               wait_until="domcontentloaded",
                               timeout=60000)
                else:
                    self.page.goto(url,
                               wait_until="domcontentloaded",
                               timeout=60000)

                # Evasion: Cloudflare Turnstile veya Klasik Captcha kontrolü
                self.solve_captcha()

                # Sayfa yüklendiğinde insan gibi rastgele fare hareketleri ve ufak tıklamalar yap
                self._random_mouse_move_and_click()

                self._human_scroll()

                # Bot tespitini zorlaştırmak için ilanlar arası rastgele bekleme süresini artırdık
                time.sleep(random.uniform(10, 20))


                data = self.extract_details()

                data["url"]=url


                self.scraped_data.append(data)


                # HEADER GENERATION
                self.dynamic_headers.update(data.keys())


                self.processed_count_since_pause += 1
                
                # Güvenlik Molası - Uzun Bekleme (İnsan hareketi simülasyonu)
                if self.processed_count_since_pause >= self.next_pause_threshold:
                    pause_time = random.uniform(20, 35)
                    print(f"🛡️ Güvenlik Molası: {pause_time:.1f} saniye dinleniliyor (Bot algılamasını önlemek için)...")
                    self.save_data()
                    time.sleep(pause_time)
                    
                    # Sonraki mola için yeni eşik belirle
                    self.processed_count_since_pause = 0
                    self.next_pause_threshold = random.randint(6, 8)
                elif (i+1)%5 == 0:
                    self.save_data()



            except Exception as e:

                print("Hata:",e)



        self.save_data()

        print("✅ Scraper tamamlandı")

        print("Header sayısı:",len(self.dynamic_headers))

        return self.scraped_data

    def _human_scroll(self):
        """İnsan benzeri okuma ve kaydırma simülasyonu"""
        try:
            # 1. İlk yükleme anındaki hafif yukarı/aşağı bekleme
            time.sleep(random.uniform(1.5, 3.5))
            
            # 2. Aşağı doğru yavaşça kaydır
            scroll_steps = random.randint(3, 6)
            for _ in range(scroll_steps):
                # Evasion: Mouse tekerini çevirirken x ekseninde de ufak kaymalar olabilir
                self.page.mouse.wheel(random.randint(-10, 10), random.randint(200, 600))
                time.sleep(random.uniform(0.8, 2.0))
            
            # 3. İlanı okuyormuş gibi bekleme
            time.sleep(random.uniform(3.0, 5.0))
            
            # 4. Bazen biraz yukarı geri kaydır (İnsanlarda sık görülür)
            if random.random() > 0.3:
                self.page.mouse.wheel(random.randint(-5, 5), -random.randint(150, 400))
                time.sleep(random.uniform(1.0, 2.0))
                
        except Exception as e:
            print(f"Scroll hatası (önemsiz): {e}")

    def solve_captcha(self):
        """Cloudflare Turnstile ve Sahibinden Captcha Çözücü"""
        try:
            # 1. Cloudflare Turnstile
            try:
                for _ in range(3):
                    cf_iframe = self.page.frame_locator("iframe[src*='cloudflare'], iframe[title*='Widget']").locator(".ctp-checkbox-label, input[type='checkbox'], #challenge-stage").first
                    
                    if cf_iframe.is_visible(timeout=3000):
                        print("🛡️ Scraper: Cloudflare Turnstile tespit edildi, tıklanıyor...")
                        box = cf_iframe.bounding_box()
                        if box:
                            x = box["x"] + box["width"] / 2
                            y = box["y"] + box["height"] / 2
                            self.page.mouse.move(x, y, steps=10)
                            time.sleep(random.uniform(0.5, 1.0))
                            self.page.mouse.click(x, y)
                        else:
                            cf_iframe.click(force=True)
                            
                        time.sleep(random.uniform(3, 5))
                    else:
                        break
            except:
                pass

            # 2. Sahibinden Klasik "Basılı Tutun"
            try:
                button = self.page.locator("button:has-text('Basılı Tutun'), button:has-text('Press and Hold')").first
                if button.is_visible(timeout=2000):
                    print("🛡️ Scraper: CAPTCHA (Basılı Tutun) çözülüyor")
                    box = button.bounding_box()
                    if box:
                        x = box["x"] + box["width"]/2
                        y = box["y"] + box["height"]/2
                        self.page.mouse.move(x,y)
                        self.page.mouse.down()
                        time.sleep(random.uniform(4,6))
                        self.page.mouse.up()
            except:
                pass
        except Exception as e:
            pass

    def _random_mouse_move_and_click(self):
        """Sayfa içinde rastgele fare hareketleri ve boş alanlara tıklama simülasyonu"""
        try:
            viewport = self.page.viewport_size
            if not viewport:
                return

            width = viewport.get("width", 1280)
            height = viewport.get("height", 720)

            # Rastgele 2-4 fare hareketi
            movements = random.randint(2, 4)
            for _ in range(movements):
                x = random.randint(10, width - 10)
                y = random.randint(10, height - 10)
                # Fareyi belirtilen koordinata hareket ettir
                self.page.mouse.move(x, y, steps=random.randint(5, 15))
                time.sleep(random.uniform(0.2, 0.8))

            # %40 ihtimalle zararsız bir boşluğa tıkla (sayfa odağını almak için)
            if random.random() > 0.6:
                # Header veya footer altındaki nispeten boş olabilecek sol kısımlar
                safe_x = random.randint(10, width // 4)
                safe_y = random.randint(height // 2, height - 20)
                self.page.mouse.click(safe_x, safe_y)
                time.sleep(random.uniform(0.5, 1.2))
                
        except Exception as e:
            pass



    def extract_details(self):

        data={}


        # TITLE

        try:

            data["title"]=self.page.locator(
                "div.classifiedDetailTitle h1"
            ).inner_text().strip()

        except:

            data["title"]=None



        # PRICE

        try:

            data["price"]=self.page.locator(
                ".classifiedInfo h3"
            ).first.inner_text().strip()

        except:

            data["price"]=None



        # LOCATION

        try:

            locs=self.page.locator(
                "div.classifiedInfo > h2 > a"
            ).all_inner_texts()

            data["location"]=" / ".join(locs)

        except:

            data["location"]=None



        # INFO TABLE (Dynamic Metadata)

        try:

            rows=self.page.locator(
                "ul.classifiedInfoList li"
            )

            count=rows.count()


            for i in range(count):

                item=rows.nth(i)

                label=item.locator("strong").inner_text()

                value=item.locator("span").inner_text()

                key=self.normalize_key(label)

                data[key]=value


        except:

            pass



        # DESCRIPTION

        try:

            desc=self.page.locator(
                "#classifiedDescription"
            ).inner_text()

            data["description"]=desc[:300]

        except:

            data["description"]=None


        # ONLY RETURN EXPECTED KEYS
        if self.expected_keys:
            filtered_data = {}
            for k in self.expected_keys:
                filtered_data[k] = data.get(k, None)
            return filtered_data

        return data



    def normalize_key(self,text):

        repl={

        "ç":"c",
        "ğ":"g",
        "ı":"i",
        "ö":"o",
        "ş":"s",
        "ü":"u",

        " ":"_",
        "(":"",
        ")":"",
        ".":"",
        "/":"_"
        }


        text=text.lower().strip()

        for k,v in repl.items():

            text=text.replace(k,v)


        return text



    def save_data(self):

        try:

            with open(self.output_file,
                      "w",
                      encoding="utf-8") as f:

                json.dump(
                    self.scraped_data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            print("💾 listing_details.json güncellendi")

        except Exception as e:

            print("Kayıt hatası:",e)