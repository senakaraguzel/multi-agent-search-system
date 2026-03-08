"""
CategoricFilterHandler — Agent 6 için Kategorik Bilgi Arama Pipeline Handler'ı.
Haber, blog, makale ve akademik içeriklerden gelen CategoricScraper verilerini işler.
Her makalenin başlık, tarih, kaynak ve özet metnini yapılandırılmış forma çevirir.
LLM kullanarak birden fazla makaledeki ortak temayı ve anahtar bulguları özetler.
"""

import os
import json
import re
from dotenv import load_dotenv
from openai import AzureOpenAI
from agents.filter_handlers.base_filter_handler import BaseFilterHandler

load_dotenv()


def _get_azure_client():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    return AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint="https://genarion-deep-search-source-1.openai.azure.com/",
        api_key=key,
    )


def _llm_summarize_articles(original_query: str, articles: list) -> dict:
    """
    Birden fazla haber/makale metnini LLM ile sentezler.
    Her makalenin birkaç cümlelik özetini çıkarır ve genel bir tematik özet üretir.
    """
    client = _get_azure_client()
    if not client or not articles:
        return {}

    # LLM'e gönderilecek makale metinlerini hazırla (max 7000 karakter)
    article_snippets = []
    char_budget = 7000
    for i, art in enumerate(articles):
        snippet = f"[Makale {i+1}] Kaynak: {art.get('source_url','?')}\n{art.get('text','')[:1200]}"
        if len("\n\n".join(article_snippets)) + len(snippet) > char_budget:
            break
        article_snippets.append(snippet)

    combined = "\n\n".join(article_snippets)

    prompt = f"""You are a research synthesis assistant. The user searched for: "{original_query}"

Below are raw article excerpts collected from the web:

{combined}

Your task:
1. For each article, write a 1-2 sentence factual summary (key finding, date if mentioned, statistic if any).
2. Write an overall thematic synthesis (3-4 sentences) combining all articles.
3. Extract key entities (people, orgs, dates, numbers) mentioned across articles.

Return ONLY valid JSON (no markdown):
{{
  "article_summaries": [
    {{"article_index": 1, "source_url": "...", "summary": "...", "key_date": null}},
    ...
  ],
  "overall_synthesis": "...",
  "key_entities": ["entity1", "entity2", ...]
}}"""

    try:
        response = client.chat.completions.create(
            model="o4-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            return {}
        return json.loads(content)
    except Exception as e:
        print(f"[CategoricFilterHandler] LLM sentez hatası: {e}")
        return {}


def _extract_date(text: str) -> str | None:
    """Metin içinden basit tarih pattern'ı bulmaya çalışır."""
    if not text:
        return None
    # 2024, 2025, Ocak 2025, 12 Mart 2025 vb.
    match = re.search(
        r"\b((?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
        r"\s+\d{4}|\d{1,2}\s+\w+\s+\d{4}|\d{4})\b",
        text,
    )
    return match.group(0) if match else None


class CategoricFilterHandler(BaseFilterHandler):
    """
    Haber / Blog / Araştırma makalelerini işleyen handler.

    İşlem akışı:
    1. Her kalem için başlık, tarih, metin çıkar.
    2. LLM ile makale başına özet + genel sentez üret.
    3. İstatistiksel özet (makale sayısı, ortalama uzunluk, kaynak listesi) ekle.
    """

    def filter_relevant_data(self) -> list:
        filtered = []
        date_ctx = self.intent_data.get("date_context")

        for item in self.raw_items:
            if not isinstance(item, dict):
                continue

            url = item.get("url") or item.get("profile_url", "")
            if url and url not in self.sources_used:
                self.sources_used.append(url)

            raw_text = item.get("extracted_text", "").strip()
            if not raw_text or len(raw_text) < 100:
                continue  # Anlamlı içerik yok, atla

            # Tarih filtresi: eğer kullanıcı yıl belirttiyse sadece o yılı içeren makaleleri al
            if date_ctx and str(date_ctx) not in raw_text:
                pass  # Yumuşak filtre — kaldırma, sadece işaretle

            # Metadata'dan başlık çek (browsing agent bazen title koyar)
            meta = item.get("metadata", {})
            title = (
                meta.get("title")
                or item.get("title")
                or _first_line(raw_text)
            )

            detected_date = _extract_date(raw_text)

            filtered.append({
                "title":      title,
                "source_url": url,
                "date":       detected_date,
                "text":       raw_text[:3000],  # Sentez için yeterli
                "word_count": len(raw_text.split()),
            })

        return filtered

    def aggregate_data(self, filtered_items: list) -> dict:
        total = len(filtered_items)
        avg_words = (
            int(sum(a["word_count"] for a in filtered_items) / total)
            if total > 0 else 0
        )

        # LLM sentezi
        synthesis_result = {}
        original_query = self.intent_data.get("original_query") or self.intent_data.get("main_entity", "")
        if filtered_items:
            print(f"[CategoricFilterHandler] {total} makale LLM ile sentezleniyor...")
            synthesis_result = _llm_summarize_articles(original_query, filtered_items)

        # Makale listesi — LLM özetlerini mevcut ham veriye entegre et
        articles_out = filtered_items.copy()
        llm_summaries = {
            s["article_index"] - 1: s
            for s in synthesis_result.get("article_summaries", [])
        }
        for i, art in enumerate(articles_out):
            if i in llm_summaries:
                art["llm_summary"] = llm_summaries[i].get("summary")
                art["key_date"]    = llm_summaries[i].get("key_date") or art.get("date")
            # Ham metni sonuçtan kaldır (çok uzun, synthesis yeterli)
            art.pop("text", None)

        return {
            "total_items_processed":  total,
            "average_word_count":     avg_words,
            "overall_synthesis":      synthesis_result.get("overall_synthesis", ""),
            "key_entities":           synthesis_result.get("key_entities", []),
            "articles":               articles_out,
            "sources":                self.sources_used,
        }

    def compute_confidence_score(self, aggregated: dict) -> float:
        base_score = super().compute_confidence_score(aggregated)

        total = aggregated.get("total_items_processed", 0)
        if total == 0:
            return 0.1

        # Sentez üretilmişse yüksek güven
        if aggregated.get("overall_synthesis"):
            base_score += 0.2

        # Birden fazla kaynaktan veri geliyorsa
        if len(self.sources_used) >= 3:
            base_score += 0.1

        return min(max(round(base_score, 2), 0.0), 1.0)


# ─── Yardımcı ──────────────────────────────────────────────────────────────
def _first_line(text: str) -> str:
    """Metin içindeki ilk anlamlı satırı başlık olarak döner."""
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 15:
            return line[:120]
    return text[:80]
