# 🚀 Multi-Agent Web Research & Scoring System

Bu proje, kullanıcı tarafından verilen doğal dil sorgularını analiz eden, internet üzerinde otonom araştırma yapan, veri kazıyan ve elde edilen bilgileri analiz ederek anlamlı sonuçlar üreten **çok ajanlı (Multi-Agent) bir yapay zeka sistemidir.**

Sistem; web araştırması, veri kazıma (scraping), bilgi filtreleme ve puanlama işlemlerini farklı uzman **AI Agent'lar** üzerinden yürütür.

Proje özellikle şu kullanım senaryoları için tasarlanmıştır:

- AI destekli **araştırma otomasyonu**
- **CV / aday değerlendirme sistemleri**
- **şirket ve okul puanlama sistemleri**
- **web veri toplama ve analiz pipeline'ları**

---

# 🧠 Sistem Özeti

Sistem, kullanıcının sorgusunu analiz ederek uygun araştırma pipeline'ını seçer ve aşağıdaki çok katmanlı veri akışını çalıştırır.

```
User Query
     │
     ▼
Source Planning Agent
     │
     ▼
Source Discovery Agent
     │
     ▼
Browsing Agent
     │
     ▼
Scraping Agent
     │
     ▼
Filtering Agent
     │
     ▼
Result Generation
     │
     ▼
Presentation Agent
```

Sistem tüm verileri üç ana veri katmanı üzerinden yönetir.

| Dosya | Açıklama |
|------|------|
| `search.json` | Arama planı ve hedef kaynaklar |
| `scrape.json` | Web sitelerinden çekilen ham veriler |
| `result.json` | Filtrelenmiş ve son kullanıcıya hazır sonuçlar |

---

# ⚙️ Kullanılan Teknolojiler

| Teknoloji | Amaç |
|------|------|
| **OpenAI o4-mini (Azure)** | Planlama, doğrulama ve semantic analiz |
| **Playwright** | Browser otomasyonu ve scraping |
| **FastAPI** | Backend servisleri |
| **React + Vite** | Kullanıcı arayüzü |
| **Python** | Agent pipeline sistemi |
| **JSON** | Veri depolama ve pipeline state yönetimi |

---

# 🧩 Multi-Agent Mimarisi

Sistem farklı görevleri yerine getiren bağımsız agent'lardan oluşur.

### 1️⃣ Source Planning Agent
Kullanıcının sorgusunu analiz eder ve genişletilmiş arama query'leri oluşturur.

Örnek:

```
Input Query:
Galatasaray'ın 2025 yılında attığı goller
```

Planner şu queryleri oluşturabilir:

```
Galatasaray 2024/25 season goals
Galatasaray 2025/26 season statistics
Galatasaray match results 2025
```

---

### 2️⃣ Source Discovery Agent

Oluşturulan arama query'leri için güvenilir kaynakları bulur.

Örnek:

```
mackolik.com
beinsports.com
uefa.com
```

---

### 3️⃣ Browsing Agent

Bulunan kaynak sitelerde gezinerek hedef veri sayfalarını keşfeder.

---

### 4️⃣ Scraping Agent

Hedef sayfalardan verileri kazır ve `scrape.json` dosyasına kaydeder.

---

### 5️⃣ Filtering Agent

Scrape edilen ham veriyi analiz eder ve sorgu ile ilişkili olan bilgileri filtreler.

---

### 6️⃣ Presentation Agent

Sonuçları kullanıcı arayüzüne uygun formatta hazırlar.

---

# 🔎 Desteklenen Arama Pipeline'ları

Sistem farklı araştırma türleri için ayrı pipeline'lar içerir.

## 1️⃣ Spesifik Bilgi Arama

Daraltılmış bilgi aramaları için kullanılır.

Örnek:

```
Galatasaray'ın 2025 sezonu golleri
```

Pipeline:

```
spesifik_pipeline/
```

---

## 2️⃣ Kategorik Bilgi Arama

Belirli bir konu hakkında geniş kapsamlı bilgi toplar.

Örnek:

```
Beyaz eşya sektöründeki teknolojik gelişmeler
```

Pipeline:

```
kategorik_pipeline/
```

---

## 3️⃣ Lokal Firma Arama

Google Maps veya yerel kaynaklardan firma verisi toplar.

Örnek:

```
Şişli'deki dişçiler
```

Pipeline:

```
lokalfirma_pipeline/
```

---

## 4️⃣ Jenerik Platform Arama

LinkedIn, Sahibinden, Reddit gibi platformlardan veri toplar.

Örnek:

```
İstanbul'daki fullstack developerlar
```

Pipeline:

```
jenerik_pipeline/
```

---

# 🧪 Scoring Sistemleri

Proje ayrıca aday değerlendirme sistemleri için özel scoring pipeline'ları içerir.

---

## 🎓 School Scoring Team

Adayın mezun olduğu üniversiteyi **Times Higher Education ranking** verilerine göre analiz eder ve **20 üzerinden puan verir.**

Pipeline:

```
URL Agent
↓
Browsing + Scraping Agent
↓
School Scoring Agent
```

---

## 🏢 Company Scoring Team

Adayın çalıştığı şirketleri LinkedIn üzerinden analiz eder ve iş ilanı kriterlerine göre puanlar.

Pipeline:

```
URL Agent
↓
Validation Agent
↓
Scraping Agent
↓
Data Processing Agent
↓
Scoring Agent
```

Değerlendirme kriterleri:

- Position relevancy
- Industry relevancy
- Experience duration
- Company reputation
- Company size

Final skor:

```
Max Score = 20
```

---

# 📂 Proje Yapısı

```
project-root
│
├── agents/                 # AI agent modülleri
│
├── pipelines/              # Araştırma pipeline'ları
│   ├── spesifik_pipeline/
│   ├── kategorik_pipeline/
│   ├── lokalfirma_pipeline/
│   └── jenerik_pipeline/
│  
│
├── ui/                     # React arayüzü
│
├── utils/                  # yardımcı araçlar
│
└── README.md
```

---

# ⚙️ Kurulum

### 1️⃣ Gereksinimler

- Python 3.10+
- Node.js
- Playwright
- Azure OpenAI erişimi

---

### 2️⃣ Backend Kurulumu

```bash
pip install -r requirements.txt
playwright install chromium
```

---

### 3️⃣ Ortam Değişkenleri

`.env` dosyası oluşturun.

```
OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
```

---

### 4️⃣ Frontend

```
cd ui
npm install
npm run dev
```

---

# 🚀 Kullanım

CLI üzerinden pipeline çalıştırmak:

```
python main.py
```

Arayüz üzerinden kullanmak:

```
http://localhost:5173
```

---

# 🎯 Projenin Amacı

Bu sistemin amacı:

- web araştırmasını otomatikleştirmek
- veri toplama ve analiz pipeline'larını AI ile yönetmek
- aday değerlendirme sistemlerini otomatik hale getirmek
- multi-agent mimarisini gerçek dünyada kullanmaktır.

---

# 👨‍💻 Geliştirme

Bu proje **modüler multi-agent mimarisi** kullanır.

Yeni bir agent eklemek için:

```
agents/
```

Yeni bir pipeline eklemek için:

```
pipelines/
```

klasörleri genişletilebilir.

---
