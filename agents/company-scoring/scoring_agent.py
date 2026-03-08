"""
Scoring Agent (Embedding Tabanlı) - İş Deneyimi Puanlama Motoru
================================================================
CV'deki şirket deneyimlerini ve iş ilanındaki pozisyonu karşılaştırarak
adayı 20 üzerinden puanlar.

Teknik Yaklaşım:
    - Position ve Industry uyumu: text-embedding-3-large + cosine similarity
    - Working Time: Formül tabanlı (ay cinsinden süre)
    - Working Chronology: Formül tabanlı (sıra/rank)

Ağırlıklar:
    position    → 0.50 (en yüksek)
    working_time→ 0.25
    chronology  → 0.15
    industry    → 0.10 (en düşük)

Final Puan = Ortalama(Son 3 şirket puanı) × 20
"""

import os
import json
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

MAX_SCORE = 20

# ANA SKOR AĞIRLIKLARI (Yeni Görselden)
WEIGHTS_BASE = {
    "position": 0.42,
    "industry": 0.16,
    "working_time": 0.16,
    "chronology": 0.10,
    "reputation": 0.09,
    "size": 0.07,
}

# RELEVANCE GATE AĞIRLIKLARI
WEIGHTS_GATE = {
    "base": 0.50,
    "position": 0.35,
    "industry": 0.15,
}

class ScoringAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
        self.chat_model = os.getenv("AZURE_OPENAI_MODEL", "o4-mini")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self._cache = {}   # Embedding ön belleği
        self._llm_cache = {}  # LLM skoru ön belleği
        self._use_embedding = True 

    # ------------------------------------------------------------------
    # Semantic Similarity via LLM (o4-mini)
    # ------------------------------------------------------------------
    def get_semantic_similarity(self, text_a: str, text_b: str) -> float:
        """
        o4-mini modelini kullanarak iki metin arasındaki anlamsal benzerliği hesaplar.
        Embedding modeli bulunmadığı durumlar için en sağlıklı yöntemdir.
        """
        cache_key = f"sim||{text_a}||{text_b}"
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        prompt = f"""
        Aşağıdaki iki metin arasındaki anlamsal benzerliği 0.0 ile 1.0 arasında bir puan olarak döndür.
        1.0: Tamamen aynı veya eş anlamlı.
        0.0: Tamamen alakasız.
        
        Metin 1: {text_a}
        Metin 2: {text_b}
        
        Sadece sayısal puanı döndür (örneğin: 0.85). Başka hiçbir metin ekleme.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1
            )
            score_str = response.choices[0].message.content.strip()
            # Sayısal olmayan karakterleri temizle
            score_str = "".join(c for c in score_str if c.isdigit() or c == '.')
            score = float(score_str)
            score = max(0.0, min(1.0, score))
            self._llm_cache[cache_key] = score
            return score
        except Exception as e:
            print(f"  ⚠ LLM Similarity hatası: {e}. Fallback Jaccard kullanılıyor.")
            return self._jaccard_similarity(text_a, text_b)

    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Fallback kural tabanlı benzerlik."""
        sim = 0.7 * self._domain_similarity(text_a, text_b) + 0.3 * self._token_overlap(text_a, text_b)
        return round(max(0.0, min(1.0, sim)), 4)

    # ------------------------------------------------------------------
    # Alan (domain) eşleştirme (LLM Fallback için)
    # ------------------------------------------------------------------
    _DOMAIN_GROUPS = [
        {"siber güvenlik", "cyber", "security", "soc", "pentest", "güvenlik", "network"},
        {"yazılım", "software", "developer", "geliştirme", "python", "java", "backend", "frontend"},
        {"elektronik", "elektrik", "electronic", "electrical", "pcb", "hardware"},
        {"makine", "mekanik", "mechanical", "imalat", "üretim", "tasarım"},
        {"üretim planlama", "production", "planlama", "erp", "lojistik"},
        {"satış", "sales", "pazarlama", "marketing", "müşteri", "crm"},
        {"finans", "muhasebe", "finance", "accounting", "bütçe"},
        {"insan kaynakları", "hr", "işe alım", "recruitment"},
        {"veri", "data", "analitik", "analytics", "sql", "bi"},
        {"otomotiv", "automotive", "araç", "motor"},
        {"gıda", "food", "restoran", "yiyecek"},
        {"perakende", "retail", "mağaza", "satış"},
    ]

    @classmethod
    def _domain_similarity(cls, text_a: str, text_b: str) -> float:
        ta, tb = text_a.lower(), text_b.lower()
        ga, gb = None, None
        for i, group in enumerate(cls._DOMAIN_GROUPS):
            if any(kw in ta for kw in group): ga = i
            if any(kw in tb for kw in group): gb = i
            if ga is not None and gb is not None: break
        
        if ga is None and gb is None: return 0.4
        return 0.85 if ga == gb else 0.15

    @staticmethod
    def _token_overlap(text_a: str, text_b: str) -> float:
        stop = {"ve", "ile", "bir", "bu", "için", "de", "da", "the", "and"}
        tokens_a = {t for t in text_a.lower().split() if len(t) > 2 and t not in stop}
        tokens_b = {t for t in text_b.lower().split() if len(t) > 2 and t not in stop}
        if not tokens_a or not tokens_b: return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

    def _llm_similarity(self, text_a: str, text_b: str) -> float:
        cache_key = f"{text_a}||{text_b}"
        if cache_key in self._llm_cache: return self._llm_cache[cache_key]
        sim = 0.7 * self._domain_similarity(text_a, text_b) + 0.3 * self._token_overlap(text_a, text_b)
        val = round(max(0.0, min(1.0, sim)), 4)
        self._llm_cache[cache_key] = val
        return val

    # ------------------------------------------------------------------
    # Kriterler
    # ------------------------------------------------------------------
    def score_position(self, cand_role: str, job_role: str) -> float:
        return self.get_semantic_similarity(cand_role, job_role)

    def score_industry(self, cand_ind: str, job_ind: str) -> float:
        if not cand_ind or cand_ind == "Unknown": return 0.3
        return self.get_semantic_similarity(cand_ind, job_ind)

    @staticmethod
    def score_working_time(months: int, req_months: int = 24) -> float:
        """İstenen tecrübeye oranla çalışma süresi."""
        if req_months <= 0: req_months = 12
        ratio = months / req_months
        return min(1.0, ratio)

    @staticmethod
    def score_chronology(rank: int, total: int) -> float:
        if total <= 1: return 1.0
        return round(1.0 - ((rank - 1) * (0.7 / (total - 1))), 3)

    @staticmethod
    def score_company_size(cand_size: int, job_size: int) -> float:
        """Adayın şirketinin ilan sahibine göre büyüklük oranı."""
        if job_size <= 0: return 0.5
        ratio = cand_size / job_size
        # Eğer aday daha büyük bir şirketten geliyorsa bonus, çok küçükse ceza
        if ratio >= 1.0: return 1.0
        if ratio >= 0.5: return 0.8
        if ratio >= 0.1: return 0.5
        return 0.3

    @staticmethod
    def score_company_reputation(cand_foll: int, job_foll: int) -> float:
        """Takipçi sayısı üzerinden repütasyon kıyaslaması."""
        if job_foll <= 0: return 0.5
        ratio = cand_foll / job_foll
        if ratio >= 1.0: return 1.0
        if ratio >= 0.5: return 0.8
        return 0.4

    # ------------------------------------------------------------------
    # Tek Şirket İçin Final Puan (Base * Gate)
    # ------------------------------------------------------------------
    def score_company(
        self,
        company: dict,      # Adayın çalıştığı şirket verisi
        exp: dict,          # Deneyim bilgisi
        job_info: dict,     # İlan ve ilan sahibi şirket bilgisi
        rank: int,
        total: int,
    ) -> dict:
        job_pos = job_info.get("position", "")
        job_ind = job_info.get("industry", "Unknown")
        job_size = job_info.get("company_size_numeric", 0)
        job_foll = job_info.get("followers", 0)
        req_months = job_info.get("required_experience_months", 24)

        # Temel Skorlar (0-1)
        pr = self.score_position(exp.get("role", ""), job_pos)
        ir = self.score_industry(company.get("industry", "Unknown"), job_ind)
        wt = self.score_working_time(exp.get("months", 12), req_months)
        ch = self.score_chronology(rank, total)
        cs = self.score_company_size(company.get("company_size_numeric", 0), job_size)
        cr = self.score_company_reputation(company.get("followers", 0), job_foll)

        # 1) Base Score
        base_score = (
            pr * WEIGHTS_BASE["position"] +
            ir * WEIGHTS_BASE["industry"] +
            wt * WEIGHTS_BASE["working_time"] +
            ch * WEIGHTS_BASE["chronology"] +
            cr * WEIGHTS_BASE["reputation"] +
            cs * WEIGHTS_BASE["size"]
        )

        # 2) Relevance Gate
        gate = (
            WEIGHTS_GATE["base"] +
            pr * WEIGHTS_GATE["position"] +
            ir * WEIGHTS_GATE["industry"]
        )

        # 3) Final Score (Scaled to 20)
        score_20 = round(base_score * gate * 20, 2)

        return {
            "rank": rank,
            "company_name": company.get("name") or exp.get("company"),
            "candidate_role": exp.get("role", ""),
            "months_worked": exp.get("months", 0),
            "candidate_industry": company.get("industry", "Unknown"),
            "scores": {
                "PR_Position_Relevancy": round(pr, 3),
                "IR_Industry_Relevancy": round(ir, 3),
                "WT_Working_Time": round(wt, 3),
                "CH_Chronology": round(ch, 3),
                "CR_Company_Reputation": round(cr, 3),
                "CS_Company_Size": round(cs, 3)
            },
            "base_score": round(base_score, 4),
            "gate": round(gate, 4),
            "company_score_20": score_20
        }

    # ------------------------------------------------------------------
    # Ana Akış
    # ------------------------------------------------------------------
    def run(
        self,
        job_info: dict,
        experiences: list,
        company_data: list = None,
        top_n: int = 3,
    ) -> dict:
        """
        job_info: {
            "position": str,
            "industry": str,
            "company_size_numeric": int,
            "followers": int,
            "required_experience_months": int
        }
        """
        if not experiences: return {"error": "Deneyim yok.", "final_score": 0}

        sorted_exp = sorted(experiences, key=lambda x: x.get("order", 99))
        selected = sorted_exp[:top_n]
        total = len(selected)

        # Şirket verisini indeksle
        company_index = { (c.get("name") or "").lower(): c for c in (company_data or []) }

        print(f"\n=== YENİ PUANLAMA MOTORU AKTİF ===")
        print(f"İş: {job_info.get('position')} | Şirket: {job_info.get('name', 'İlan Sahibi')}")

        company_scores = []
        for rank, exp in enumerate(selected, start=1):
            cname = (exp.get("company") or "").lower()
            cinfo = next((v for k, v in company_index.items() if cname in k or k in cname), {})
            
            res = self.score_company(cinfo, exp, job_info, rank, total)
            company_scores.append(res)
            print(f"  [{rank}/{total}] {res['company_name']} -> {res['company_score_20']}/20")

        final_score = round(sum(s["company_score_20"] for s in company_scores) / len(company_scores), 2)
        print(f"🏆 Final Skor: {final_score}/20")

        return {
            "job_position": job_info.get("position"),
            "company_scores": company_scores,
            "final_score": final_score
        }
        if not experiences:
            return {"error": "Deneyim listesi boş.", "final_score": 0}

        # En son çalışılan şirketten geriye doğru sırala, sadece son N'i al
        sorted_exp = sorted(experiences, key=lambda x: x.get("order", 99))
        selected   = sorted_exp[:top_n]
        total      = len(selected)

        # Şirket verisini isimle indeksle (küçük harf, esnek eşleştirme)
        company_index = {}
        if company_data:
            for c in company_data:
                name_key = (c.get("name") or "").lower()
                company_index[name_key] = c

        print(f"\n=== SKORLAMA BAŞLATILDI ===")
        print(f"Pozisyon: {job_position}  |  Değerlendirilen şirket: {total}")

        # Job position embedding'ini önden al (cache'e kaydeder)
        print("[*] Job position embedding üretiliyor...")
        self.get_embedding(job_position)

        company_scores = []
        for rank, exp in enumerate(selected, start=1):
            company_name = (exp.get("company") or "").lower()

            # Esnek şirket adı eşleştirme
            company_info = {}
            for key, val in company_index.items():
                if company_name in key or key in company_name:
                    company_info = val
                    break

            print(f"  [{rank}/{total}] {exp.get('company')} - {exp.get('role')} ({exp.get('months')} ay)")
            score_detail = self.score_company(
                company=company_info,
                exp=exp,
                job_position=job_position,
                rank=rank,
                total=total,
            )
            company_scores.append(score_detail)

        # Final puan: ortalama
        final_score = round(
            sum(s["company_score_20"] for s in company_scores) / len(company_scores), 2
        )

        result = {
            "job_position": job_position,
            "total_companies_scored": total,
            "weights_used": WEIGHTS,
            "company_scores": company_scores,
            "final_score": final_score,
        }

        print(f"\n✓ Puanlama tamamlandı. Final Skor: {final_score} / {MAX_SCORE}")

        return result


# ------------------------------------------------------------------
# Hızlı Test
# ------------------------------------------------------------------
if __name__ == "__main__":
    agent = ScoringAgent()

    job_position = "Elektronik Mühendisi"

    # CV deneyimleri (order=1 → en son çalışılan)
    experiences = [
        {"company": "AssemCorp Elektronik", "role": "Elektronik Mühendisi",      "months": 24, "order": 1},
        {"company": "Defne Mühendislik",    "role": "Mekanik Tasarım Mühendisi", "months": 18, "order": 2},
        {"company": "Fropie",               "role": "Üretim Planlama",           "months": 12, "order": 3},
    ]

    # Scrape verisi
    company_data = []
    scoring_path = "linkedin_scoring.json"
    if os.path.exists(scoring_path):
        with open(scoring_path, "r", encoding="utf-8") as f:
            company_data = json.load(f)
    else:
        print(f"⚠ {scoring_path} bulunamadı, şirket verisi olmadan devam ediliyor.")

    result = agent.run(
        job_position=job_position,
        experiences=experiences,
        company_data=company_data,
        top_n=3,
    )

    print("\n=== DETAYLI PUANLAMA SONUÇLARI ===")
    for s in result["company_scores"]:
        print(f"\n#{s['rank']} {s['company_name']} | Rol: {s['candidate_role']} | {s['months_worked']} ay")
        sc = s["scores"]
        print(f"   Pozisyon Uyumu  : {sc['position_similarity']:.3f}  × 0.50")
        print(f"   Sektör Uyumu    : {sc['industry_similarity']:.3f}  × 0.10")
        print(f"   Çalışma Süresi  : {sc['working_time']:.3f}  × 0.25")
        print(f"   Kronoloji       : {sc['chronology']:.3f}  × 0.15")
        print(f"   → Şirket Puanı  : {s['company_score_20']} / 20")

    print(f"\n🏆  FINAL PUAN: {result['final_score']} / 20")
