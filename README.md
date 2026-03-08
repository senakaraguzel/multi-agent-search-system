# Okul Puanlama Takımı (School Scoring Team)

Bu proje, bir adayın eğitim aldığı üniversiteyi, başvurduğu pozisyon ve şirketin global ölçeğine göre dinamik olarak puanlayan çok ajanlı (multi-agent) bir otomasyon sistemidir. Sistem, Times Higher Education (THE) verilerini kullanarak bilimsel temelli bir değerlendirme yapar.

## 🚀 Temel Özellikler

- **Çok Ajanlı Mimari:** Farklı görevler için özelleşmiş 4 ayrı ajan (LLM, URL, Scraping, Scoring) koordineli çalışır.
- **Dinamik Veri Çekme:** Playwright kullanarak Google aramaları ve THE web sitesi üzerinden güncel dünya sıralamalarını anlık olarak çeker.
- **Akıllı Analiz:** Azure OpenAI (GPT-4o/mini) desteği ile şirketlerin pazar gücünü ve lokasyon uyumunu analiz eder.
- **Ağırlıklı Puanlama:** Sadece okulun genel sıralamasını değil, bölüme özel başarıları ve iş-eğitim uyumunu da hesaba katan gelişmiş bir algoritma kullanır.

## 🛠️ Kurulum

### Gereksinimler
- Python 3.8+
- Node.js (Playwright için)
- Azure OpenAI API Erişimi

### Adımlar
1. Depoyu klonlayın:
   ```bash
   git clone <repo-url>
   cd okul_puanlama_takimi
   ```
2. Sanal ortam oluşturun ve bağımlılıkları yükleyin:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Playwright tarayıcılarını yükleyin:
   ```bash
   playwright install chromium
   ```
4. `.env` dosyasını oluşturun ve API bilgilerinizi ekleyin:
   ```env
   AZURE_OPENAI_KEY=your_key
   AZURE_OPENAI_ENDPOINT=your_endpoint
   AZURE_OPENAI_MODEL=gpt-4o-mini
   ```

## 📖 Kullanım

Ana uygulamayı çalıştırın:
```bash
python main.py
```
Program sizden şu bilgileri isteyecektir:
- Okul Adı (örn: İTÜ)
- Başvurulacak Pozisyon (örn: AI Engineer)
- Şirket Adı (örn: Google)

İşlem tamamlandığında sonuçlar hem terminale yazdırılır hem de `university_data.json` dosyasına kaydedilir.

## 📁 Proje Yapısı

- `main.py`: Sistemin orkestra şefi; ajanları sırayla çalıştırır.
- `agents/`: Özelleşmiş ajanların bulunduğu klasör.
- `utils/`: Metin işleme ve yardımcı fonksiyonlar.
- `university_data.json`: Analiz edilen tüm verilerin saklandığı veritabanı.

---
*Bu proje Genarion kapsamında geliştirilmiştir.*
