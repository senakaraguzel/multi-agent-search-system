# Google Maps Multi-Agent Scraper

Bu proje, kullanıcının girdiği doğal dildeki aramalara göre Google Haritalar (Google Maps) üzerinden otomatik olarak işletme verilerini toplayan, sunan ve dışa aktarılmasını sağlayan çok ajanlı (multi-agent) bir **FastAPI + Playwright + React** uygulamasıdır. Sistem, işletmelerin adı, puanı, değerlendirme sayısı, adresi, telefonu, web sitesi ve harita linki gibi değerli meta verilerini asenkron bir şekilde tarar.

---

## 🏗️ Mimari ve Çalışma Mantığı

Proje mimarisi **3 Katmanlı (3-Tier)** bir yapıdan oluşur:

1. **Frontend (React - Vite)**: Kullanıcı arayüzü ve verilerin tablolaştırılması.  
2. **Backend (FastAPI)**: İstemciden gelen istekleri yöneten, arka plan görevlerini (background tasks) çalıştıran ve durum yönetimini (status pooling) sağlayan API katmanı.  
3. **Scraper Agents (Playwright - Python)**: Browser otomasyonunu sağlayan 3 alt ajandan oluşur.

### Ajanlar (Agents) Sistemi

Arama işlemi başlatıldığında alt süreç (subprocess) olarak çalışan yapay zeka/otomasyon ajanları şunlardır:

- **`SearchAgent`**: Tarayıcıyı açarak Google Haritalar'a gider ve kullanıcının girdiği (örn: "Kadıköy kahveci") sorgusunu aratır.  
- **`ScrollAgent`**: Sol taraftaki arama sonuçları listesinde aşağı doğru otomatik kaydırma (scroll) yapar. Yüklenen tüm işletmelerin profillerine ait benzersiz URL bağlantılarını (`listing_urls.json`) toplar.  
- **`ScraperAgent`**: Toplanan işletme URL'lerini tek tek sırayla ziyaret eder, sayfa yüklenmesini bekler ve işletmeye ait tüm detayları (`Rating`, `Address`, `Phone` vb.) ayıklayarak `listing_details.json` dosyasına kaydeder.

---

## 🚀 İsteklerin İşlenme Akışı (Data Flow)

1. Kullanıcı, React arayüzünde arama çubuğuna sorgusunu yazar (örn: "İzmir Diş Kliniği") ve "Ara" butonuna tıklar.  
2. Frontend, `/api/search` (POST) uç noktasına sorguyu gönderir.  
3. FastAPI, arka planda (Background Task) `main.py` dosyasını bir alt süreç olarak başlatır.  
4. `main.py`, Playwright kütüphanesini kullanarak işlemleri ajanlara devreder. Terminale anlık ilerleme durumu loglanır (`PHASE:searching`, `PHASE:extracting` vb.)  
5. Frontend, belirli aralıklarla `/api/status` (GET) uç noktasına istek atarak scraper'ın anlık durumunu öğrenir. Durum "Taranıyor", "Veriler ayıklanıyor", "Tamamlandı" gibi UI durumlarına yansır.  
6. İşlem bittiğinde, frontend `/api/results` (GET) endpointine istek atarak çekilen verileri tablo şeklinde ekrana basar.

---

## 📂 Proje Dizin Yapısı

```
googlemaps/
├── agents/
│   ├── browsing_agent.py
│   ├── search_agent.py
│   ├── scroll_agent.py
│   └── scraper_agent.py
├── api/
│   └── server.py
├── data/
│   ├── listing_urls.json
│   └── listing_details.json
├── frontend/
│   ├── src/components/
│   ├── src/App.jsx
│   └── src/App.css
├── pipelines/
│   └── googlemaps_pipeline/
│       ├── __init__.py
│       ├── main.py
│       ├── utils.py
│       ├── config.py
│       └── README.md
├── main.py
├── requirements.txt
└── README.md
```

---

## 🛠️ Kurulum ve Çalıştırma

Sistemin çalışması için **Backend (FastAPI)** ve **Frontend (React)** sunucularını çalıştırmanız gerekir.

### 1. Backend (FastAPI) Başlatılması

Proje ana dizininden terminalde `googlemaps/` klasörüne geçin:

```bash
# Sanal ortam varsa aktif edin
python -m uvicorn api.server:app --reload --port 8000
```

---

### 2. Frontend (React) Başlatılması

Yeni bir terminal penceresinde `googlemaps/frontend/` klasörüne geçin ve aşağıdaki komutları çalıştırın:

```bash
cd frontend
npm install   # İlk kurulum için
npm run dev
```

Tarayıcınızdan **[http://localhost:5173/](http://localhost:5173/)** adresine giderek uygulamayı kullanabilirsiniz.
