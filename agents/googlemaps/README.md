# 🤖 Google Maps Scraper Agents

Bu dizin, Google Haritalar üzerindeki verileri asenkron ve otonom bir şekilde işleyen, **Playwright** tabanlı tarayıcı ajanlarını içerir. Her ajan, veri kazıma (scraping) sürecinin belirli bir aşamasından sorumludur.



---

## 🧭 Ajan Hiyerarşisi ve Görev Dağılımı

### 1. Koordinatör Ajan (`browsing_agent.py`)
Tüm süreci yöneten ana beyindir. Diğer ajanları (Search, Scroll, Scraper) doğru sıra ile çağırır ve aralarındaki veri akışını koordine eder.
* **Sorumluluk:** Tarayıcı oturumunu başlatmak ve fazlar (`PHASE:searching`, `PHASE:extracting` vb.) arası geçişi yönetmek.

### 2. Arama Ajanı (`search_agent.py`)
Kullanıcının doğal dildeki sorgusunu Google Haritalar'ın anlayacağı bir navigasyon işlemine dönüştürür.
* **Sorumluluk:** Arama çubuğunu bulma, sorguyu yazma ve sonuçlar sayfasının yüklendiğini doğrulama.
* **Teknik:** Sayfa elementlerinin yüklenmesini bekleyen `wait_for_selector` mekanizmasını kullanır.

### 3. Kaydırma Ajanı (`scroll_agent.py`)
Google Maps'in dinamik yükleme (infinite scroll) yapısını yöneterek mümkün olan en fazla işletme linkine ulaşmayı sağlar.
* **Sorumluluk:** Sol paneli algılama ve yeni sonuçlar yüklenmeyene kadar aşağı kaydırma yaparak URL bağlantılarını toplama.
* **Çıktı:** `data/listing_urls.json` dosyasını oluşturur.

### 4. Veri Ayıklama Ajanı (`scraper_agent.py`)
Toplanan URL'leri tek tek ziyaret ederek işletme detaylarını yapılandırılmış veriye dönüştüren son aşama ajanıdır.
* **Sorumluluk:** İşletme adı, puanı, yorum sayısı, adres ve telefon gibi meta verileri HTML içerisinden ayıklamak.
* **Bot Koruması:** `playwright-stealth` kullanımı ve insan benzeri bekleme süreleri ile Google'ın bot tespit mekanizmalarını aşar.
* **Çıktı:** `data/listing_details.json` dosyasını nihai sonuçlarla doldurur.

---

## 🛠️ Teknik Detaylar ve Güvenlik

* **Playwright Stealth:** Google'ın "headless" tarayıcıları tespit etmesini engellemek için tüm ajanlar gizlilik modunda çalışır.
* **Asenkron Yapı:** Python `asyncio` kütüphanesi sayesinde tarayıcı işlemleri bloklanmadan yürütülür.
* **Hata Yönetimi:** Bir işletme sayfasında eksik veri olduğunda sistem çökmez, o alanı işaretleyerek devam eder.

---

## 📂 Dosya Erişimi
Bu ajanlar tarafından üretilen tüm veriler bir üst dizindeki `data/` klasöründe saklanır. API sunucusu (`api/server.py`), bu klasördeki değişimleri izleyerek Frontend'e anlık bilgi aktarır.
