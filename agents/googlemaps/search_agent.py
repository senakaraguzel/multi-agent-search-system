import time
import random
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

def handle_consent(page: Page):
    """
    Google konsent popup'ını (varsa) kapatır.
    """
    try:
        print("Consent kontrolü yapılıyor...")
        
        # 1. URL kontrolü
        if "consent.google.com" in page.url:
            print("Consent sayfasına yönlenildi.")
            try:
                # Genellikle form içindeki butonlar
                page.locator("form").locator("button").last.click()
                print("Consent form butonuna tıklandı.")
                return
            except:
                pass

        # 2. Overlay / Dialog kontrolü
        # Google Maps dialogları genellikle role="dialog" veya "modal" class'ları içerir.
        try:
            # Genel bir dialog içinde buton arayalım
            dialog = page.locator("div[role='dialog'], div[class*='consent']").first
            if dialog.is_visible(timeout=3000):
                print("Dialog tespit edildi.")
                # Genellikle "Kabul et" butonu
                accept_btn = dialog.locator("button").filter(has_text="Tümünü kabul et").first
                if not accept_btn.is_visible():
                    accept_btn = dialog.locator("button").filter(has_text="Accept all").first
                
                if accept_btn.is_visible():
                    accept_btn.click()
                    print("Dialog consent kabul edildi.")
                    time.sleep(1)
                    return
                else:
                    # Fallback: Dialog içindeki son buton (Genellikle kabul et)
                    btns = dialog.locator("button").all()
                    if btns:
                        btns[-1].click()
                        print("Dialog içindeki son butona tıklandı.")
                        time.sleep(1)
                        return
                    # Fallback 2: 'span:has-text("Kabul et")'
                    span_btn = dialog.locator("span").filter(has_text="Kabul et").first
                    if span_btn.is_visible():
                        span_btn.click()
                        return

        except:
            pass
            
        # Standart buton kontrolü (eski yöntem)
        try:
            consent_btn = page.wait_for_selector(
                'button[aria-label="Tümünü kabul et"], button[aria-label="Accept all"]',
                timeout=2000, state="visible"
            )
            if consent_btn:
                consent_btn.click()
                print("Standart consent butonu tıklandı.")
                return
        except:
            pass

    except Exception as e:
        print(f"Consent yönetimi hatası: {e}")

def search_agent(page: Page, query: str) -> bool:
    search_url = "https://www.google.com/maps"
    timeout_ms = 60000 
    
    try:
        print(f"Gidiliyor: {search_url}")
        page.goto(search_url, timeout=timeout_ms)
        time.sleep(3) # Yükleme için bekle
        
        handle_consent(page)
        
        print("Arama kutusu aranıyor...")
        input_selector = 'input[name="q"], input[role="combobox"], input#searchboxinput, input[aria-label="Google Haritalar\'da arayın"], input[aria-label="Search Google Maps"]'
        
        search_input = page.wait_for_selector(input_selector, state="visible", timeout=timeout_ms)
        
        if not search_input:
            print("Hata: Arama kutusu bulunamadı.")
            return False
        
        print(f"Yazılıyor: {query}")
        search_input.fill(query)
        
        sleep_time = random.uniform(2, 3)
        print(f"Bekleniyor: {sleep_time:.2f} saniye...")
        time.sleep(sleep_time)
        
        print("Enter tuşuna basılıyor...")
        search_input.press("Enter")
        
        print("Sonuçlar bekleniyor ([role='feed'])...")
        page.wait_for_selector('[role="feed"]', state="visible", timeout=timeout_ms)
        
        print("Liste öğeleri bekleniyor (a.hfpxzc)...")
        page.wait_for_selector('a.hfpxzc', state="attached", timeout=timeout_ms)
        
        print("Başarılı: Sonuçlar ve liste öğeleri yüklendi.")
        return True

    except PlaywrightTimeoutError:
        print("Hata: Zaman aşımı.")
        try:
            page.screenshot(path="error_screenshot.png")
            print("Ekran görüntüsü: error_screenshot.png")
        except:
            pass
    except Exception as e:
        print(f"Beklenmeyen Hata: {e}")
        
    return False
