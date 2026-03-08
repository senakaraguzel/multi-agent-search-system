# 🤖 Company Scoring Agents

Bu klasör, **Şirket Puanlama Takımı** tarafından kullanılan çoklu ajan mimarisini içerir.  
Her ajan, pipeline içerisinde belirli bir görevi yerine getirir ve bir sonraki ajan için veri hazırlar.

Pipeline'ın amacı, adayın geçmiş iş deneyimlerini analiz ederek çalıştığı şirketleri **hedef iş pozisyonuna göre 20 üzerinden puanlamaktır.**

---

# 🧠 Agent Pipeline

Ajanlar aşağıdaki sırayla çalışır:

```
Company Name + City
        │
        ▼
URLAgent
        │
        ▼
ValidationAgent
        │
        ▼
ScrapingAgent
        │
        ▼
DataAgent
        │
        ▼
ScoringAgent
        │
        ▼
Final Score (0-20)
```

Her ajan çıktısını bir sonraki ajan için hazırlar.

---

# 🧩 Agent Detayları

## 1️⃣ URLAgent

**Görevi:**  
Verilen şirket ismi ve şehir bilgisiyle **LinkedIn şirket sayfasını bulmak**.

### Çalışma Mantığı

Agent aşağıdaki formatta bir arama query oluşturur:

```
site:linkedin.com/company "Company Name" City
```

Ardından Google sonuçlarını analiz ederek doğru LinkedIn şirket sayfasını bulur.

### Output

```
{
  "company_name": "Sampa Global",
  "linkedin_url": "https://www.linkedin.com/company/sampa-global/"
}
```

---

## 2️⃣ ValidationAgent

**Görevi:**  
Bulunan LinkedIn sayfasının gerçekten hedef şirkete ait olup olmadığını doğrulamak.

### Kullanılan Teknoloji

- Azure OpenAI
- o4-mini modeli

### Kontrol Kriterleri

Agent aşağıdaki durumları kontrol eder:

- Şirket adı eşleşmesi
- Şehir veya lokasyon uyumu
- Yanlış "branch" sayfalarının filtrelenmesi
- Yanlış şirket eşleşmelerinin elenmesi

### Output

```
{
  "company_name": "Sampa Global",
  "validated": true,
  "linkedin_url": "https://www.linkedin.com/company/sampa-global/"
}
```

---

## 3️⃣ ScrapingAgent

**Görevi:**  
Doğrulanmış LinkedIn şirket sayfasından şirket bilgilerini kazımak.

### Kullanılan Teknoloji

- Playwright
- Browser Automation

### Çekilen Veriler

- Şirket sektörü
- Çalışan sayısı
- LinkedIn takipçi sayısı
- Kuruluş yılı
- Uzmanlık alanları
- Lokasyon bilgisi

### Output

```
{
  "company_name": "Sampa Global",
  "industry": "Automotive",
  "employees": "10,001+",
  "followers": "250,000",
  "founded": 1994,
  "location": "Istanbul"
}
```

---

## 4️⃣ DataAgent

**Görevi:**  
Scraping verisini temizlemek ve puanlama için hazır hale getirmek.

### Yapılan İşlemler

- Metin temizleme
- Sayısal veri normalizasyonu

Örnek:

```
"10,001+ employees" → 10001
```

### Output

```
{
  "company_name": "Sampa Global",
  "industry": "Automotive",
  "employees": 10001,
  "followers": 250000,
  "founded": 1994,
  "location": "Istanbul"
}
```

---

## 5️⃣ ScoringAgent

**Görevi:**  
Şirket profilini iş ilanı kriterleri ile karşılaştırarak puan üretmek.

### Değerlendirme Kriterleri

| Kriter | Açıklama |
|------|------|
| Position Relevancy | Rol benzerliği (Embedding tabanlı) |
| Industry Relevancy | Sektör uyumu |
| Working Time | Deneyim süresi |
| Chronology | Güncel deneyim ağırlığı |
| Reputation | LinkedIn takipçi sayısı |
| Company Size | Şirket büyüklüğü |

### Output

```
{
  "company_name": "Sampa Global",
  "position": "Backend Engineer",
  "score": 17.8
}
```

---

# 🔄 Veri Akışı

Pipeline boyunca veri aşağıdaki JSON dosyalarında tutulur:

| Dosya | Açıklama |
|------|------|
| `scraped_companies.json` | LinkedIn'den çekilen ham veriler |
| `scoring_results.json` | Nihai analiz ve puan sonuçları |

---

# 🎯 Amaç

Bu agent mimarisi sayesinde sistem:

- aday şirket deneyimlerini analiz eder
- LinkedIn verilerini otomatik toplar
- iş ilanı kriterleriyle karşılaştırır
- **20 üzerinden objektif bir şirket skoru üretir**

Bu yapı özellikle **AI destekli işe alım sistemleri** ve **otomatik CV değerlendirme pipeline'ları** için tasarlanmıştır.
