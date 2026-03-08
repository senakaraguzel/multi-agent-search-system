# Sahibinden.com Akıllı Arama ve Veri Kazıma Asistanı

Bu proje, Sahibinden.com üzerinde doğal dil ile arama yapmanızı sağlayan yapay zeka destekli tam yığıt (full-stack) bir web uygulaması ve otomasyon aracıdır. Kullanıcıların "Kadıköy'de 3+1 kiralık deniz manzaralı daire" gibi doğal dildeki karmaşık ifadelerini anlar, bot korumalarını aşarak Sahibinden.com üzerinde gezinti yapar ve sonuçları kullanıcı dostu modern bir arayüzde (React) sergiler.

## 🚀 Öne Çıkan Özellikler

*   **Doğal Dil İşleme (Groq LLM):** Llama-3 modeli sayesinde arama niyetini anlar, karmaşık istekleri ("25.000 TL altı, sıfır bina") yapılandırılmış doğru filtrelere dönüştürür.
*   **Gelişmiş Tarayıcı Otomasyonu:** Playwright Stealth modu kullanılarak anti-bot sistemleri aşılır. İnsan benzeri klavye tuşlamaları, fare hareketleri ve bekleme süreleri simüle edilir.
*   **Dinamik Kategori Tespiti:** Aranan kelimenin `emlak` veya `araba/vasıta` gibi kategorilere ait olduğunu otomatik saptayarak uygun URL parametrelerini ve arayüz sütunlarını belirler.
*   **Çift Katmanlı Kazıma Sistemi:**
    *   **Browsing Agent:** Arama yapar, filtreleri uygular, çoklu sayfaları gezer ve ilan URL'lerini toplar.
    *   **Scraper Agent:** İlan detay sayfalarına tek tek girerek başlık, konum, fiyat, nitelikler ve açıklamaları toplar.
*   **Modern Web Arayüzü:** React.js ile geliştirilmiş frontend sayesinde, komut satırı ile uğraşmadan bir web sitesinden kolayca işlem yapılmasını sağlar.
*   **API Altyapısı (FastAPI):** Vue/React gibi uygulamaların, Python çekirdeği ile haberleşmesini sağlayan RESTful API.

## 📂 Mimari ve Proje Yapısı

```
sahibinden_task/
├── sahibinden-ui/          # React tabanlı modern Web Arayüzü
├── agents/                 # Otonom Ajanlar
│   ├── browsing_agent.py   # Tarayıcı navigasyon ve URL toplama
│   ├── scraper_agent.py    # İlan detaylarını veri olarak kazıma
│   └── HeaderGenerator.py  # Dinamik tablo başlığı oluşturucu
├── llm/                    # Dil Modeli Entegrasyonu
│   └── groq_client.py      # Groq Llama-3 API Bağlantısı
├── utils/                  # Yardımcı Araçlar
│   ├── filter_manager.py   # URL ve Sahibinden Filter-ID format çeviricileri
│   ├── query_parser.py     # LLM yanıtını işleme
│   └── domain_classifier.py# Kategori (emlak/vasıta) tahmini
├── main.py                 # Çekirdek iş akışı ve terminal tabanlı kullanım
├── api_server.py           # Frontend için FastAPI sunucusu
├── .env                    # API anahtarları deposu (GROQ_API_KEY)
└── README.md               # Proje Dokümantasyonu
```

## 🛠️ Kurulum Adımları

**1. Çekirdek Python Bağımlılıkları:**
Python 3.8+ ortamında aşağıdaki modülleri yükleyin:
```bash
pip install playwright groq python-dotenv playwright-stealth fastapi uvicorn
playwright install
```

**2. React UI Kurulumu:**
Frontend dizinine giderek Node.js paketlerini yükleyin:
```bash
cd sahibinden-ui
npm install
cd ..
```

**3. Çevre Değişkenleri (.env) Yapılandırması:**
Kök klasörde `.env` isimli yeni bir dosya oluşturup Groq API anahtarınızı girin:
```env
GROQ_API_KEY=gsk_sizin_api_anahtariniz_gelmeli
```

## ▶️ Nasıl Çalıştırılır?

Projeyi iki farklı şekilde (Terminal arayüzü veya Web arayüzü) kullanabilirsiniz.

### Seçenek 1: Web Arayüzü ile (Tavsiye Edilen)
Kullanıcı dostu arayüzü başlatmak için hem API sunucusunu hem de React uygulamasını çalıştırmanız gerekir.

**Terminal 1 (Backend API):**
```bash
uvicorn api_server:app --reload --port 8000
```
**Terminal 2 (Frontend React):**
```bash
cd sahibinden-ui
npm start
```
*Tarayıcınız otomatik olarak `http://localhost:3000` adresinde uygulamayı açacaktır.*

### Seçenek 2: Komut Satırı ile (CLI)
Hızlı denemeler ve komut satırı tutkunları için:
```bash
python main.py "İstanbul Kadıköy 2+1 deniz manzaralı kiralık daire 40000 TL"
```
* İşlem bittiğinde sonuçlar kök dizindeki `listing_details.json` (Ayrıntılı İlan Verisi) ve `listing_urls.json` dosyalarına kaydedilir.

