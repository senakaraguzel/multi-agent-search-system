# 🤖 Agents

Bu klasör, sistemin çekirdeğini oluşturan **AI Agent bileşenlerini** içerir.  
Her agent belirli bir göreve odaklanır ve diğer agentlarla birlikte çalışarak kullanıcının sorgusunu araştırır, veri toplar ve sonuç üretir.

Sistem **çok ajanlı (multi-agent)** bir mimari kullanır. Her ajan belirli bir uzmanlık alanına sahiptir ve iş akışı boyunca sırayla çalışarak araştırma pipeline'ını oluşturur.

---

# 🔄 Agent Workflow

Ajanlar aşağıdaki sırayla çalışarak araştırma sürecini tamamlar:

1. **Planner Agent**
2. **Source Discovery Agent**
3. **Source Planning Agent**
4. **Browsing Agent**
5. **Scraper Agent**
6. **Filtering Agent**
7. **Presentation Agent**

Bu akış, kullanıcının doğal dilde verdiği bir sorguyu alıp anlamlı bir sonuç listesine dönüştürür.

---

# 🔍 Search Pipelines

Sistem farklı sorgu türlerine göre farklı **arama pipeline stratejileri** kullanır.  
Planner Agent, kullanıcının sorgusunu analiz ederek uygun pipeline türünü belirler.

## 1️⃣ Spesifik Pipeline

Belirli bir şirket, kurum veya hedef hakkında bilgi toplamak için kullanılır.

**Örnek sorgular**

- "OpenAI hakkında bilgi topla"
- "Tesla şirketi hakkında detaylı bilgi"

**Amaç**

Belirli bir hedef hakkında güvenilir kaynaklardan detaylı bilgi toplamak.

---

## 2️⃣ Kategorik Pipeline

Belirli bir sektör veya kategori içindeki şirketleri bulmak için kullanılır.

**Örnek sorgular**

- "Türkiye'deki yapay zeka şirketleri"
- "Fintech startup şirketleri"

**Amaç**

Belirli bir sektördeki şirketleri keşfetmek ve listelemek.

---

## 3️⃣ Lokal Firma Pipeline

Belirli bir şehir veya lokasyondaki işletmeleri bulmak için kullanılır.

**Örnek sorgular**

- "Ankara'daki yazılım şirketleri"
- "İstanbul'daki dijital pazarlama ajansları"

**Amaç**

Konum tabanlı firma araştırması yapmak.

---

## 4️⃣ Jenerik Pipeline

Daha genel araştırma sorguları için kullanılır.

**Örnek sorgular**

- "Yapay zeka alanında çalışan şirketler"
- "En iyi SaaS şirketleri"

**Amaç**

Genel bilgi toplama ve geniş kapsamlı araştırma yapmak.

---

# 🧠 Agent Bileşenleri

## Planner Agent

Kullanıcı sorgusunu analiz eder ve hangi pipeline stratejisinin kullanılacağını belirler.

Görevleri:

- Sorgu analiz etmek
- Arama stratejisi belirlemek
- Pipeline seçmek

---

## Source Discovery Agent

Web üzerinde potansiyel veri kaynaklarını keşfeder.

Görevleri:

- Arama motorlarını kullanmak
- Potansiyel URL'leri bulmak
- Veri kaynaklarını listelemek

---

## Source Planning Agent

Bulunan kaynakları analiz ederek tarama planı oluşturur.

Görevleri:

- Kaynakları değerlendirmek
- Tarama önceliği belirlemek
- Araştırma planı hazırlamak

---

## Browsing Agent

Web sayfalarını ziyaret eder ve içerikleri yükler.

Görevleri:

- Playwright ile sayfa açmak
- Dinamik siteleri yüklemek
- Anti-bot sistemlerini aşmak

---

## Scraper Agent

Web sayfalarından veri çıkarır.

Görevleri:

- HTML içeriği analiz etmek
- Yapılandırılmış veri çıkarmak
- Ham veriyi kaydetmek

---

## Filtering Agent

Toplanan ham veriyi temizler ve anlamlı hale getirir.

Görevleri:

- Gürültülü veriyi temizlemek
- Alakasız sonuçları elemek
- Veriyi normalize etmek

---

## Presentation Agent

Sonuçları kullanıcıya sunar.

Görevleri:

- Verileri analiz etmek
- Nihai sonucu oluşturmak
- UI veya API üzerinden sunmak

---

# 📂 Veri Akışı

Sistem üç temel veri katmanı üzerinden çalışır:

### `search.json`
Ajanların oluşturduğu arama planını içerir.

### `scrape.json`
Kazıyıcılardan gelen ham verileri içerir.

### `result.json`
LLM tarafından analiz edilerek oluşturulan nihai sonuçtur.

---

# ⚙️ Teknolojiler

Agent sistemi aşağıdaki teknolojiler ile çalışır:

- **OpenAI o4-mini (Azure OpenAI)**
- **Playwright (Browser Automation)**
- **Python**
- **JSON veri katmanı**

---

# 🎯 Amaç

Bu mimarinin amacı:

- Web üzerinde **otonom araştırma yapmak**
- **LLM destekli veri filtreleme**
- **çok ajanlı modüler bir araştırma sistemi oluşturmak**
