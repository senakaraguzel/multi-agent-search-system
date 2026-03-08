# Google Maps Multi-Agent Scraper

Bu proje, kullanıcının girdiği doğal dildeki aramalara göre Google Haritalar (Google Maps) üzerinden otomatik olarak işletme verilerini toplayan, sunan ve dışa aktarılmasını sağlayan çok ajanlı (multi-agent) bir **FastAPI + Playwright + React** uygulamasıdır. 

Sistem, işletmelerin adı, puanı, değerlendirme sayısı, adresi, telefonu, web sitesi ve harita linki gibi değerli meta verilerini asenkron bir şekilde tarar.

---

## 🏗️ Mimari ve Çalışma Mantığı

Proje mimarisi **3 Katmanlı (3-Tier)** bir yapıdan oluşur:
1. **Frontend (React - Vite)**: Kullanıcı arayüzü ve verilerin tablolaştırılması.
2. **Backend (FastAPI)**: İstemciden gelen istekleri yöneten, arka plan görevlerini (background tasks) çalıştıran ve durum yönetimini (status pooling) sağlayan API katmanı.
3. **Scraper Agents (Playwright - Python)**: Browser otomasyonunu sağlayan 3 alt ajandan oluşur.

### Ajanlar (Agents) Sistemi
Arama işlemi başlatıldığında alt süreç (subprocess) olarak çalışan yapay zeka/otomasyon ajanları şunlardır:

1. **`SearchAgent`**: Tarayıcıyı açarak Google Haritalar'a gider ve kullanıcının girdiği (Örn: "Kadıköy kahveci") sorgusunu aratır.
2. **`ScrollAgent`**: Sol taraftaki arama sonuçları listesinde aşağı doğru otomatik kaydırma (scroll) yapar. Yüklenen tüm işletmelerin profillerine ait benzersiz URL bağlantılarını (href) toplayıp geçici olarak kaydeder (`listing_urls.json`).
3. **`ScraperAgent`**: Toplanan bu işletme URL'lerini tek tek sırayla (bot korumasına yakalanmamak için rate limiting/sleep uygulayarak) ziyaret eder. Sayfanın yüklenmesini formüle edip işletmeye ait tüm detayları (Rating, Address, Phone vb.) ayıklar ve `listing_details.json` dosyasına kaydeder.

---

## 🚀 İsteklerin İşlenme Akışı (Data Flow)

1. Kullanıcı, React arayüzünde arama çubuğuna sorgusunu yazar (Örn: İzmir Diş Kliniği) ve "Ara" butonuna tıklar.
2. Frontend, `/api/search` (POST) uç noktasına bu sorguyu gönderir.
3. FastAPI, arka planda (Background Task) `main.py` dosyasını bir alt süreç (subprocess) olarak başlatır.
4. `main.py`, Playwright kütüphanesini kullanarak işlemleri ajanlara devreder. Terminale anlık ilerleme durumu loglanır (`PHASE:searching`, `PHASE:extracting` vb.)
5. Frontend, belirli aralıklarla `/api/status` (GET) uç noktasına istek atarak arka planda çalışan bu scraper'ın anlık durumunu öğrenir. Bu durum "Taranıyor", "Veriler ayıklanıyor", "Tamamlandı" gibi UI durumlarına (Status Bar) dönüşür.
6. İşlem bittiğinde (phase: 'done' olduğunda), frontend `/api/results` (GET) endpointine istek atarak çekilen tüm verileri alır ve tablo şeklinde ekrana basar.

---

## 📂 Proje Dizin Yapısı

```
googlemaps/
│
├── agents/                     # Scraper ajanlarını içeren klasör
│   ├── browsing_agent.py       # Ana koordinatör ajan
│   ├── search_agent.py         # Arama yapma yeteneği (Maps search)
│   ├── scroll_agent.py         # URL toplama / Scroll kaydırma yeteneği
│   └── scraper_agent.py        # Sayfa içeriğini ayıklama (Data extraction)
│
├── api/                        # FastAPI Sunucusu
│   └── server.py               # REST uç noktaları ve durum yönetimi
│
├── data/                       # Çalışma zamanı veri dosyaları
│   ├── listing_urls.json       # Toplanan URL'ler 
│   └── listing_details.json    # Ayıklanıp JSON'a dönüştürülmüş veriler
│
├── frontend/                   # UI Katmanı (React + Vite)
│   ├── src/components/         # Arama çubuğu, Tablo, Kart, Log vb. bileşenler
│   ├── src/App.jsx             # Ana arayüz dosyası
│   └── src/App.css             # UI Tasarım stilleri (Dark Mode)
│
├── main.py                     # İşlemi başlatan Runner script
├── requirements.txt            # Python bağımlılıkları listesi
└── README.md                   # Bu döküman
```

---

## 🛠️ Kurulum ve Çalıştırma

Sistemin tam olarak çalışması için iki farklı sunucuyu ayağa kaldırmanız gerekmektedir (Biri Python arka ucu, diğeri React ön ucu için):

### 1. Backend (FastAPI) Başlatılması
Projenin ana dizininden (terminalde) `googlemaps/` klasörü içinde:

```powershell
# Eğer sanal ortam kullanıyorsanız aktif edin:
# .venv\Scripts\activate
python -m uvicorn api.server:app --reload --port 8000
```
*(Bu terminal penceresini açık bırakın)*

### 2. Frontend (React) Başlatılması
Yeni bir terminal penceresinde `googlemaps/frontend/` klasörüne geçerek:

```powershell
cd frontend
npm install   # İlk kurulum için sadece
npm run dev
```

Sunucular aktif edildiğinde tarayıcınızdan **[http://localhost:5173/](http://localhost:5173/)** adresine giderek uygulamayı kullanmaya başlayabilirsiniz.
