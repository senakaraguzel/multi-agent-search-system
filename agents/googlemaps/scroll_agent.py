import time
import random
from typing import List
from playwright.sync_api import Page


def scroll_agent(page: Page, max_scrolls: int = 50) -> List[str]:
    """
    Google Maps arama sonuç sayfasında scroll yaparak tüm işletme URL'lerini toplar.

    Args:
        page (Page): Playwright page objesi (search yapılmış olmalı).
        max_scrolls (int): Maksimum scroll deneme sayısı (infinite loop koruması).

    Returns:
        List[str]: Benzersiz işletme URL listesi.

    Raises:
        Exception: Eğer scroll container bulunamazsa.
    """

    print("🚀 Scroll Agent başlatıldı...")

    feed_selector = '[role="feed"]'

    # 1️⃣ Feed container kontrolü
    try:
        page.wait_for_selector(feed_selector, state="visible", timeout=15000)
    except:
        raise Exception(
            "❌ Scroll container bulunamadı. Arama sonuçları yüklenmemiş olabilir."
        )

    feed = page.locator(feed_selector)

    if feed.count() == 0:
        raise Exception("❌ Scroll container DOM'da yok.")

    collected_urls = set()
    last_count = 0
    stagnation_counter = 0
    MAX_STAGNATION = 4  # Link artmazsa kaç tur sonra duracak

    for step in range(max_scrolls):

        # 2️⃣ Mevcut linkleri topla (performanslı yöntem)
        links = page.locator("a.hfpxzc")
        link_count = links.count()

        for i in range(link_count):
            url = links.nth(i).get_attribute("href")
            if url and "/maps/place/" in url:
                collected_urls.add(url)

        current_count = len(collected_urls)

        print(
            f"📜 Scroll {step+1}/{max_scrolls} | DOM link: {link_count} | Unique: {current_count}"
        )

        # 3️⃣ Sonlandırma kontrolü (stagnation logic)
        if current_count == last_count:
            stagnation_counter += 1
            if stagnation_counter >= MAX_STAGNATION:
                print("🛑 Yeni veri gelmiyor. Scroll durduruldu.")
                break
        else:
            stagnation_counter = 0

        last_count = current_count

        # 4️⃣ Incremental scroll (insan davranışı simülasyonu)
        try:
            feed.evaluate(
                "element => element.scrollBy(0, Math.floor(element.scrollHeight * 0.8))"
            )
        except Exception as e:
            print(f"⚠️ Scroll hatası: {e}")
            break

        # 5️⃣ Lazy load için akıllı bekleme
        sleep_time = random.uniform(2.0, 3.5)
        time.sleep(sleep_time)

    print(f"✅ Scroll tamamlandı. Toplam benzersiz URL: {len(collected_urls)}")

    return list(collected_urls)
