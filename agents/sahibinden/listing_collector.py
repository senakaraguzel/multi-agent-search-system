import json
import time
import os

class ListingCollectorAgent:
    def __init__(self, page):
        self.page = page
        self.output_file = "listing_urls.json"
        self.collected_urls = []

    def collect_urls(self):
        """
        Mevcut arama sonuçları sayfasından başlayarak tüm sayfaları gezer ve ilan linklerini toplar.
        """
        print("🔍 ListingCollectorAgent başlatıldı...")
        page_num = 1
        
        try:
            while True:
                print(f"📄 Sayfa {page_num} işleniyor...")
                
                # İlanları bul
                listings = self.page.locator("a.classifiedTitle")
                count = listings.count()
                
                if count == 0:
                    print("⚠️ Bu sayfada ilan bulunamadı.")
                    break
                    
                print(f"  -> {count} ilan bulundu.")
                
                for i in range(count):
                    url = listings.nth(i).get_attribute("href")
                    if url:
                        full_url = f"https://www.sahibinden.com{url}"
                        if full_url not in self.collected_urls:
                            self.collected_urls.append(full_url)
                
                # Her sayfa sonunda kaydet
                self.save_urls()
                
                # Sonraki sayfa kontrolü
                next_btn = self.page.locator("a.prevNextBut[title='Sonraki'], a.prevNextBut:has-text('Sonraki')").first
                
                # Eğer buton yoksa veya 'inactive' sınıfına sahipse bitir
                if not next_btn.is_visible() or "inactive" in (next_btn.get_attribute("class") or ""):
                    print("✅ Başka sayfa yok. Toplama işlemi tamamlandı.")
                    break
                
                # Sayfalama
                print("➡️ Sonraki sayfaya geçiliyor...")
                
                # Overlay (Yükleniyor ekranı) varsa bekle
                try:
                    self.page.wait_for_selector(".opening", state="hidden", timeout=5000)
                except:
                    pass

                try:
                    # Normal click
                    next_btn.click(timeout=5000)
                except Exception as e:
                    print(f"Normal tıklama başarısız ({e}), JS click deneniyor...")
                    # Eğer overlay (opening) yüzünden tıklanamıyorsa JS ile tıkla
                    self.page.evaluate("arguments[0].click();", next_btn.element_handle())
                
                try:
                    self.page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass
                time.sleep(2) # Nezaket beklemesi
                page_num += 1
                
        except Exception as e:
            print(f"❌ Toplama işlemi sırasında hata: {e}")
        finally:
            self.save_urls()
            
        return self.collected_urls

    def save_urls(self):
        """Toplanan URL'leri dosyaya kaydeder."""
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(self.collected_urls, f, indent=4, ensure_ascii=False)
            print(f"💾 {len(self.collected_urls)} ilan linki '{self.output_file}' dosyasına kaydedildi.")
        except Exception as e:
            print(f"❌ Kayıt hatası: {e}")
