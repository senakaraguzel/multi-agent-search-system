# 🎓 School Ranking Agents

Bu klasör, **Okul Puanlama Sistemi** için kullanılan agentları içerir. Sistem, bir adayın mezun olduğu okulun akademik kalitesini analiz ederek belirli bir pozisyon için **20 üzerinden bir puan üretir**.

Sistem özellikle **Times Higher Education (THE)** verilerini kullanarak okul hakkında güvenilir bilgiler toplar ve bu bilgileri pozisyon gereksinimleriyle karşılaştırır.

---

# ⚙️ Agent Mimarisi

Bu task üç temel agent tarafından gerçekleştirilir:

1️⃣ **URL Agent**

Görevi, verilen okul adı için doğru **Times Higher Education** sayfasını bulmaktır.

### Çalışma Adımları
1. Okul adını input olarak alır.
2. Aşağıdaki formatta bir arama query oluşturur:

```
timeshighereducation <okul adı> ranking
```

3. Arama sonuçlarını analiz eder.
4. `timeshighereducation.com` domainine ait doğru üniversite sayfasını bulur.
5. Bulduğu URL’i bir sonraki agente iletir.

### Output

```
{
  "school_name": "University of Oxford",
  "ranking_url": "https://www.timeshighereducation.com/world-university-rankings/university-of-oxford"
}
```

---

2️⃣ **Browsing & Scraping Agent**

Bu agent, URL Agent tarafından bulunan sayfayı ziyaret eder ve okul hakkında gerekli bilgileri kazır.

### Scrape Edilen Bilgiler

Agent aşağıdaki akademik metrikleri toplamaya çalışır:

- Dünya sıralaması
- Araştırma skoru
- Öğretim skoru
- Uluslararası görünüm
- Endüstri geliri
- Genel üniversite skoru
- Üniversite açıklaması

### Output

```
{
  "school_name": "University of Oxford",
  "world_ranking": 1,
  "research_score": 99.7,
  "teaching_score": 99.5,
  "international_outlook": 98.4,
  "industry_income": 96.2
}
```

---

3️⃣ **Scoring Agent**

Bu agent, okuldan scrape edilen akademik verileri **pozisyon gereksinimleriyle karşılaştırarak** bir puan üretir.

### Input

- Pozisyon bilgisi
- Okulun akademik verileri

### Değerlendirme Kriterleri

Scoring Agent aşağıdaki faktörleri dikkate alır:

- Üniversitenin dünya sıralaması
- Araştırma gücü
- Uluslararası akademik itibarı
- Endüstri ile ilişkisi
- Pozisyonun akademik gereksinimleri

### Puanlama

Agent okula **0 – 20 arası** bir skor verir.

### Output

```
{
  "school_name": "University of Oxford",
  "position": "AI Research Engineer",
  "school_score": 19,
  "reasoning": "Oxford is a top ranked university with strong research performance and international reputation which matches the requirements of an AI research role."
}
```

---

# 🔄 Agent Pipeline

Sistem aşağıdaki sırayla çalışır:

```
School Name
     │
     ▼
URL Agent
     │
     ▼
Browsing & Scraping Agent
     │
     ▼
Scoring Agent
     │
     ▼
Final Score (0-20)
```

---

# 📊 Kullanım Senaryosu

Örnek input:

```
Pozisyon: AI Research Engineer
Okul: University of Oxford
```

Pipeline sonucu:

```
Oxford ranking sayfası bulunur
↓
Üniversite akademik verileri scrape edilir
↓
Pozisyon ile karşılaştırılır
↓
20 üzerinden bir okul skoru üretilir
```

---

# 🧩 Kullanım Alanı

Bu sistem özellikle aşağıdaki senaryolar için tasarlanmıştır:

- AI destekli **aday değerlendirme sistemleri**
- **HR otomasyonu**
- Akademik kalite bazlı **CV filtreleme**
- Üniversite prestij analizleri
