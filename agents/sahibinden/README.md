# 🤖 Agents Directory

Bu dizin, sistemin otonom karar verme ve veri toplama süreçlerini yürüten tüm ajanları (agents) içerir.

## 🏠 Sahibinden Agents

Sahibinden.com üzerindeki akıştan sorumlu olan ana ajanlar şunlardır:

### 1. Browsing Agent (`browsing_agent.py`)
- **Görevi:** Kullanıcı sorgusuna göre tarayıcıyı başlatır, filtreleri uygular ve arama sonuçlarındaki ilan URL'lerini toplar.
- **Teknoloji:** Playwright Stealth & Human-like behavior simülasyonu.

### 2. Scraper Agent (`scraper_agent.py`)
- **Görevi:** Toplanan ilan URL'lerine tek tek girerek detaylı özellikleri (fiyat, konum, oda sayısı vb.) yapılandırılmış veri olarak çeker.
- **Teknoloji:** BeautifulSoup4 & Playwright.

### 3. Header Generator (`HeaderGenerator.py`)
- **Görevi:** Bot korumasına yakalanmamak için her istekte dinamik ve gerçekçi tarayıcı başlıkları (User-Agent) üretir.

## 🛠️ Ortak Araçlar
Ajanlar, `utils/` klasöründeki `query_parser.py` ve `filter_manager.py` araçlarını kullanarak dil modelinden (LLM) gelen emirleri işleme yeteneğine sahiptir.
