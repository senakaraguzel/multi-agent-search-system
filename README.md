# Şirket Puanlama Takımı (Company Scoring Team)

Bu proje, adayların geçmiş iş deneyimlerini ve çalıştıkları şirketleri, hedef bir iş ilanındaki kriterlere göre analiz eden, LinkedIn üzerinden veri toplayan ve yapay zeka destekli anlamsal (Semantic) bir puanlama sunan çoklu ajanlı (Multi-Agent) bir pipeline sistemidir.

---

## 🚀 Temel Özellikler

- **Çoklu Ajan Mimarisi**: Her biri spesifik bir görevden sorumlu 5 farklı uzman ajan.
- **Yapay Zeka Destekli Doğrulama**: LinkedIn sayfalarının doğruluğunu teyit eden o4-mini tabanlı kontrol mekanizması.
- **Dinamik Veri Çekme**: Playwright kullanarak LinkedIn'den şirket büyüklüğü, takipçi sayısı, sektör ve lokasyon bilgilerini otomatik toplama.
- **Gelişmiş Puanlama Algoritması**: Metin yerleştirme (Embedding) ve kural tabanlı mantığı hibritleyerek 20 puan üzerinden hassas değerlendirme.
- **Esnek Eşleştirme**: Yazım farklılıklarını ve şirket varyasyonlarını (Örn: Sampa Otomotiv vs Sampa Global) akıllıca yöneten bulanık eşleştirme (Fuzzy Matching).

---

## 🛠 Sistem Mimarisi ve Ajanlar

Sistem, `agents/` dizini altında toplanan ve birbirini takip eden 5 ana katmandan oluşur:

1.  **URLAgent**: Verilen şirket ismi ve şehir bilgisiyle Google üzerinden ilgili LinkedIn şirket sayfasını (Company Page) bulur.
2.  **ValidationAgent**: Bulunan URL'lerin gerçekten hedef şirkete ait olup olmadığını Azure OpenAI (o4-mini) kullanarak doğrular. "Branch" sayfalarını veya yanlış eşleşmeleri eler.
3.  **ScrapingAgent**: Doğrulanmış LinkedIn sayfalarına giderek; sektör, çalışan sayısı, takipçi sayısı, kuruluş yılı, uzmanlık alanları ve lokasyon bilgilerini çeker.
4.  **DataAgent**: Ham scraping verilerini temizler, sayısal değerleri normalize eder (Örn: "10,001+ employees" -> 10001) ve puanlama motoruna hazır hale getirir.
5.  **ScoringAgent**: Nihai zeka katmanıdır. Adayın pozisyonunu ve şirketin profilini ilan kriterleriyle kıyaslayarak puan üretir.

---

## 📊 Puanlama Mantığı (Scoring Logic)

Puanlama, her bir iş deneyimi için **20 puan** üzerinden hesaplanır. Altı ana kriterin ağırlıklı ortalaması alınır:

| Kriter | Ağırlık | Açıklama |
| :--- | :---: | :--- |
| **Position Relevancy** | %42 | Rollerin anlamsal benzerliği (Embedding tabanlı). |
| **Industry Relevancy** | %16 | Adayın çalıştığı sektörün ilan sektörüyle uyumu. |
| **Working Time** | %16 | Deneyim süresinin hedeflenen tecrübe yılına oranı. |
| **Chronology** | %10 | Son iş deneyimlerine verilen öncelik (Güncel iş daha değerlidir). |
| **Reputation** | %9 | Şirketin LinkedIn takipçi sayısı üzerinden repütasyonu. |
| **Company Size** | %7 | Şirket büyüklüğünün ilan sahibiyle kıyaslanması. |

**Final Skor**: Değerlendirilen son 3 şirketin puanlarının ortalamasıdır.

---

## 📂 Dosya Yapısı

```text
sirket_puanlama_takimi/
├── agents/                 # Ajan modülleri (URL, Validation, Scraping, Data, Scoring)
├── .env                    # API Anahtarları ve Model yapılandırmaları
├── linkedin_cookies.json   # LinkedIn oturum çerezleri
├── test_full_pipeline.py  # Tüm sistemi uçtan uca çalıştıran test scripti
├── scoring_results.json    # Nihai analiz ve puan raporu
└── scraped_companies.json # LinkedIn'den çekilen ham veriler
```

---

## ⚙️ Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.10+
- Azure OpenAI API Erişimi
- Playwright (Browser Automation)

### Adımlar
1. Bağımlılıkları yükleyin: `pip install -r requirements.txt`
2. Tarayıcıları kurun: `playwright install chromium`
3. `.env` dosyasını oluşturun ve `AZURE_OPENAI_KEY`, `ENDPOINT` bilgilerini girin.
4. LinkedIn oturumu için `login_linkedin.py` dosyasını bir kez çalıştırarak giriş yapın.
5. Testi başlatın: `python test_full_pipeline.py`

---

## 📈 Çıktılar

Sistem çalışmasını tamamladığında `scoring_results.json` dosyasında her aday için şu detayları sunar:
- Şirket bazlı detaylı skor dökümleri.
- Pozisyon ve sektör benzerlik oranları.
- Şirket repütasyon ve büyüklük analizleri.
- **Toplam Puan (Max 20)**.

