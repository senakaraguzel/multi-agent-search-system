import json
import re
import time
import random
from typing import List, Dict, Optional
from playwright.sync_api import Page


class ScraperAgent:
    """
    listing_urls.json'dan URL'leri okuyarak her işletmeyi scrape eden ajan.

    Çekilen alanlar:
        name, rating, reviews, address, phone, website, category, source_url
    """

    def __init__(self, page: Page, urls_file: str):
        """
        Args:
            page      (Page): Playwright page objesi.
            urls_file (str) : listing_urls.json dosyasının yolu.
        """
        self.page      = page
        self.urls_file = urls_file

    # ─────────────────────────────────────────────────────────────────
    # Public
    # ─────────────────────────────────────────────────────────────────

    def scrape_listings(self) -> List[Dict]:
        """
        listing_urls.json'dan URL listesini okur ve her birini scrape eder.

        Returns:
            List[Dict]: Çekilen işletme verilerinin listesi.
        """
        with open(self.urls_file, "r", encoding="utf-8") as f:
            urls: List[str] = json.load(f)

        total   = len(urls)
        results = []
        success = 0
        failed  = 0

        print(f"[ScraperAgent] {total} işletme scrape edilecek.")

        for i, url in enumerate(urls):
            print(f"[ScraperAgent] [{i+1}/{total}] Ziyaret ediliyor...")

            # Rate limiting — bot tespitini engeller
            time.sleep(random.uniform(2.0, 4.0))

            detail = self._extract_detail(url)
            if detail:
                print(f"  ✓ {detail.get('name', 'Bilinmeyen')}")
                results.append(detail)
                success += 1
            else:
                print(f"  ✗ Başarısız: {url}")
                failed += 1

        print(f"[ScraperAgent] Tamamlandı — Başarılı: {success} | Hatalı: {failed}")
        return results

    # ─────────────────────────────────────────────────────────────────
    # Private — Extraction
    # ─────────────────────────────────────────────────────────────────

    def _extract_detail(self, url: str) -> Optional[Dict]:
        """Tek bir işletme sayfasını ziyaret ederek veri çeker."""
        try:
            self.page.goto(url, timeout=60000)

            # h1 yüklenene kadar bekle
            try:
                self.page.wait_for_selector("h1", state="visible", timeout=10000)
            except Exception:
                pass

            # Dinamik içeriğin render olması için kısa bekleme
            time.sleep(2)

            name     = self._safe_text("h1")
            address  = self._clean(
                self._safe_attr('[data-item-id="address"]', "aria-label"),
                ["Adres: ", "Address: "]
            )
            phone    = self._clean(
                self._safe_attr('[data-item-id^="phone"]', "aria-label"),
                ["Telefon: ", "Phone: "]
            )
            website  = self._safe_attr('[data-item-id="authority"]', "href")
            category = self._safe_text(".DkEaL")
            rating   = self._extract_rating()
            reviews  = self._extract_reviews()

            return {
                "name"      : name,
                "rating"    : rating,
                "reviews"   : reviews,
                "address"   : address,
                "phone"     : phone,
                "website"   : website,
                "category"  : category,
                "source_url": url,
            }

        except Exception as e:
            print(f"  [ScraperAgent] Hata: {e}")
            return None

    def _extract_rating(self) -> Optional[str]:
        """Google Maps yıldız puanını çeker."""
        try:
            elem = self.page.locator(".F7nice").first
            if elem.is_visible():
                text = elem.locator("span").first.get_attribute("aria-hidden")
                if not text:
                    text = elem.inner_text().split("\n")[0]
                return text.replace(",", ".").strip() if text else None

            # Fallback: aria-label üzerinden
            elem = self.page.locator(
                '[role="img"][aria-label*="yıldız"], [role="img"][aria-label*="star"]'
            ).first
            if elem.is_visible():
                label = elem.get_attribute("aria-label")
                if label:
                    return label.split(" ")[0].replace(",", ".")
        except Exception:
            pass
        return None

    def _extract_reviews(self) -> Optional[str]:
        """Değerlendirme (review) sayısını çeker."""
        try:
            # Yöntem 1: aria-label içinde "değerlendirme" / "review"
            elem = self.page.locator(
                '[aria-label*="değerlendirme"], [aria-label*="review"]'
            ).first
            if elem.is_visible():
                label = elem.get_attribute("aria-label") or ""
                nums  = re.findall(r"[\d.,]+", label)
                if nums:
                    return nums[0]

            # Yöntem 2: .F7nice içindeki ikinci satır (puan + yorum sayısı)
            elem = self.page.locator(".F7nice").first
            if elem.is_visible():
                text  = elem.inner_text()
                parts = text.split("\n")
                if len(parts) > 1:
                    nums = re.findall(r"[\d.,]+", parts[1])
                    if nums:
                        return nums[0]
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────────────
    # Private — Helpers
    # ─────────────────────────────────────────────────────────────────

    def _safe_text(self, selector: str) -> Optional[str]:
        try:
            loc = self.page.locator(selector).first
            if loc.is_visible():
                return loc.inner_text().strip()
        except Exception:
            pass
        return None

    def _safe_attr(self, selector: str, attribute: str) -> Optional[str]:
        try:
            loc = self.page.locator(selector).first
            if loc.is_visible():
                return loc.get_attribute(attribute)
        except Exception:
            pass
        return None

    def _clean(self, value: Optional[str], prefixes: List[str]) -> Optional[str]:
        if not value:
            return None
        for p in prefixes:
            value = value.replace(p, "")
        return value.strip()
