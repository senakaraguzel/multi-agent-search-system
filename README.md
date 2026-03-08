# 🚀 Multi-Agent Web Araştırma ve Scrape Sistemi

Bu proje, kullanıcının girdiği doğal dil sorgularını analiz eden, otonom olarak web üzerinde araştırma yapan, verileri kazıyan ve anlamlı bir sonuç raporu sunan çok katmanlı bir **AI Agent** sistemidir.

Sistem, OpenAI **o4-mini** modelini (Azure üzerinden) kullanarak akıllı planlama ve veri filtreleme yapar. Playwright tabanlı kazıma motoru sayesinde modern web sitelerinden (React, Vue vb.) veri çekebilir ve anti-bot (Cloudflare, CAPTCHA) engellerini insan benzeri davranışlarla aşabilir.

---

## ✨ Öne Çıkan Özellikler

- **Otonom Planlama:** Sorguyu analiz edip "Spesifik", "Lokal", "Jenerik" veya "Kategorik" rotalardan birini seçer.
- **Multi-Agent Mimarisi:** 7 farklı uzman ajanın işbirliğiyle (Planner, Discovery, Browsing, Scraper, Filtering, Presentation) çalışır.
- **Anti-Bot & Stealth:** Playwright stealth modu ve akıllı parmak izi yönetimi ile engellenmeden tarama yapar.
- **Platform Destekleri:** LinkedIn, Sahibinden, Google Maps, gibi zorlu platformlar için özel işleyiciler içerir.
- **Modern UI:** React tabanlı arayüz ile arama sürecini canlı izleme ve sonuçları görselleştirme imkanı sunar.

---

## 🏗️ Sistem Mimarisi

Sistem 3 ana veri katmanı üzerinden çalışır:
1.  **`search.json` (Plan):** Ajanların rotasını ve hedef URL'leri tutar.
2.  **`scrape.json` (Ham Veri):** Kazıyıcılardan gelen yapılandırılmamış verileri toplar.
3.  **`result.json` (Sentez):** LLM tarafından filtrelenmiş ve son kullanıcıya hazır hale getirilmiş veridir.

---

## 🚀 Kurulum ve Çalıştırma

### 1. Gereksinimler
- Python 3.10+
- Node.js & npm (UI için)
- Playwright tarayıcıları

### 2. Backend Kurulumu
```bash
# Sanal ortam oluşturun
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Playwright tarayıcılarını kurun
playwright install chromium
```

### 3. Ortam Değişkenleri
Bir `.env` dosyası oluşturun ve Azure OpenAI bilgilerinizi girin:
```env
OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
```

### 4. Kullanım

#### CLI Modu (Tüm Pipeline)
```bash
python main.py
```
*Sorgunuzu girin ve ajanların çalışmasını terminalden izleyin.*

#### UI Modu (Web Arayüzü)
1. **Backend API'yi Başlatın:**
   ```bash
   python -m agents.presentation_agent
   ```
2. **Frontend'i Başlatın:**
   ```bash
   cd ui
   npm install
   npm run dev
   ```
*Arayüze `http://localhost:5173` adresinden ulaşabilirsiniz.*

---

## 📂 Proje Yapısı

- `agents/`: Otonom ajanların mantık ve çekirdek kodları.
- `ui/`: React + Vite tabanlı kullanıcı arayüzü.
- `data/`: JSON tabanlı veri depolama katmanı.
- `utils/`: Kimlik doğrulama, stealth ve yardımcı araçlar.

---

## 🛠️ Kullanılan Teknolojiler
- **LLM:** OpenAI o4-mini
- **Browser Automation:** Playwright (Python)
- **Backend:** FastAPI, Uvicorn
- **Frontend:** React, Vite
- **Data:** JSON

