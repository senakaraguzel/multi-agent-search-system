# 📦 Pipelines – Multi-Agent Web Araştırma ve Scrape Sistemi

Bu klasör, sistemin farklı **arama pipeline’larını** içerir. Her pipeline, kullanıcıdan aldığı doğal dil sorgusunu analiz eder, ilgili web kaynaklarını keşfeder, veri toplar, filtreler ve yapılandırılmış bir sonuç sunar. Pipeline’lar, ortak **agentlar** üzerinden çalışır; *_core.py dosyaları agentlar tarafından çağrılır.

---

## 🔹 Mevcut Pipeline’lar

| Pipeline | Amaç | Örnek Query |
|----------|------|-------------|
| **spesifik_pipeline** | Daraltılmış, spesifik bilgi arama | "Galatasaray'ın 2025 yılında attığı gollerin detayları" |
| **kategorik_pipeline** | Belirli bir kategori veya sektörde geniş bilgi toplama | "Beyaz eşya sektöründeki teknolojik gelişmeler" |
| **lokalfirma_pipeline** | Belirli lokasyondaki firmaları ve mekanları bulma | "Şişli'deki dişçiler" |
| **jenerik_pipeline** | Çeşitli kaynaklardan sistematik veri toplama | "İstanbul'daki fullstack developerlar" |

---

## 🔹 Pipeline Akışı (Ortak)

Tüm pipeline’lar aynı **7 ajanlı multi-agent mimari**yi kullanır:

1. **Source Planner Agent:** Sorguyu analiz eder ve genişletilmiş arama query listesi oluşturur.
2. **Source Discovery Agent:** Her query için ana URL’leri bulur.
3. **Browsing Agent:** Hedef web sitelerinde gezerek, filtreleyerek alt URL’leri toplar.
4. **Scraping Agent:** Alt URL’lerin içeriklerini çekip `scrape.json` dosyasına kaydeder.
5. **Filtering Agent:** Scrape edilmiş verileri işleyip `result.json` dosyasını oluşturur.
6. **Presentation Agent:** UI ve başlıkları `result.json` içeriğine göre günceller.
7. **Opsiyonel - Google Comment Agent:** Lokal firma aramalarında yorum verilerini toplar.

> 🔹 Pipeline’lar **sadece ana akışı yönetir**, tüm agentlar `agents/` klasöründen çağrılır. Bu sayede kod tekrarından kaçınılır.

---

## 🔹 JSON Dosyaları

- `search.json` → Plan ve hedef URL bilgileri  
- `scrape.json` → Ham veri (kazıyıcılar tarafından toplanır)  
- `result.json` → Filtrelenmiş ve yapılandırılmış nihai sonuç  

---

## 🔹 Örnek Kullanım

```python
# Örnek: Spesifik Bilgi Arama Pipeline
from pipelines.spesifik_pipeline.main import run_pipeline

query = "Galatasaray'ın 2025 yılında attığı gollerin detayları"
results = run_pipeline(query)
print(results)
