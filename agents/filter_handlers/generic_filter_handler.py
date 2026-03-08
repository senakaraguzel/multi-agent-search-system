import os
import json
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
        api_key=key
    )

def _llm_extract_structured(original_query: str, intent_data: dict, raw_texts: list, sources: list) -> dict:
    """
    LLM'e ham metinleri ve kullanıcı niyetini vererek istenen alanları
    yapılandırılmış JSON olarak çıkarmasını söyler.
    """
    client = _get_azure_client()
    if not client or not raw_texts:
        return {}

    # Ham içerikleri birleştir (max 8000 karakter)
    combined_text = "\n\n---\n\n".join(raw_texts)[:8000]
    sources_str = "\n".join(sources[:5])

    prompt = f"""You are a data extraction expert. Your task: convert the given raw web content into structured JSON containing only numeric and factual data.

USER QUESTION: "{original_query}"
SOURCES: {sources_str}

RAW CONTENT:
{combined_text}

MANDATORY EXTRACTION RULES:
1. Extract ONLY numbers, dates, and names that actually exist in the text. Never fabricate data.
2. If the content has table rows, each row should be a separate item.
3. Write numeric values (goals, prices, percentages, etc.) as INTEGER or FLOAT.
4. If a value cannot be found, write null inside "details"; do NOT remove the item.
5. Return as many records as possible — fewer records is worse.
6. summary_stats: write total_count and a statistical summary extractable from the text.
7. Return ONLY valid JSON. Do not write any other text.

FORMAT:
{{
  "items": [
    {{
      "title": "Short title (e.g., player name, event name)",
      "date": "Date if available",
      "details": {{
        "field1": value,
        "field2": value
      }},
      "source_note": "Brief note about which source this data came from"
    }}
  ],
  "summary_stats": {{
    "total_count": 0,
    "aggregated_values": {{}},
    "note": "Summary information extracted from the text"
  }}
}}
"""

    try:
        response = client.chat.completions.create(
            model="o4-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if not content:
            return {}
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"[GenericFilterHandler] LLM çıkarma hatası: {e}")
        return {}


class GenericFilterHandler(BaseFilterHandler):
    """
    Belirli bir şablonu (Sahibinden, LinkedIn) olmayan,
    tüm diğer sayfalardan gelen scraping verileri için fallback
    filtreleyici.
    
    İki mod:
    1. Yapılandırılmış mod: `extracted_entity` dict'i varsa deterministik key eşleştirme.
    2. LLM modu: `extracted_text` veya `structured_blocks` varsa LLM ile ayrıştırma.
    """

    def filter_relevant_data(self) -> list:
        filtered = []
        requested = self.intent_data.get("requested_fields", [])

        # Önce yapılandırılmış `extracted_entity` dict'lerini dene
        structured_items = []
        unstructured_texts = []

        for item in self.raw_items:
            if not isinstance(item, dict):
                continue

            url = item.get("url") or item.get("profile_url", "")
            if url and url not in self.sources_used:
                self.sources_used.append(url)

            ext = item.get("extracted_entity")

            # Yapılandırılmış entity varsa TÜM alanları aktar (company_name, address, phone, rating, vb.)
            if ext and isinstance(ext, dict) and len(ext) > 1 and ext.get("company_name"):
                entry = dict(ext)  # requested_fields kısıtlaması olmadan tümünü al
                entry["source_url"] = url
                # Temizlik: boş string değerleri None yap
                entry = {k: (v if v != "" else None) for k, v in entry.items()}
                # Telefon/adres başındaki \n temizle
                for field in ("phone", "address"):
                    if entry.get(field) and isinstance(entry[field], str):
                        entry[field] = entry[field].strip()
                structured_items.append(entry)

            # Yapılandırılmamış metin varsa LLM için topla
            else:
                text_parts = []
                raw_text = item.get("extracted_text", "")
                if raw_text and raw_text not in ("", "..."):
                    text_parts.append(raw_text)

                blocks = item.get("structured_blocks", [])
                for block in blocks:
                    if isinstance(block, dict):
                        text_parts.append(json.dumps(block, ensure_ascii=False))
                    elif isinstance(block, str):
                        text_parts.append(block)

                if text_parts:
                    unstructured_texts.append("\n".join(text_parts))

        filtered.extend(structured_items)

        # LLM ile yapılandırılmamış metinleri işle
        if unstructured_texts:
            original_query = self.intent_data.get("main_entity", "") or ""
            llm_result = _llm_extract_structured(
                original_query=original_query,
                intent_data=self.intent_data,
                raw_texts=unstructured_texts,
                sources=self.sources_used
            )
            llm_items = llm_result.get("items", [])
            if llm_items:
                print(f"[GenericFilterHandler] LLM {len(llm_items)} kayıt çıkardı.")
                filtered.extend(llm_items)
                # Summary istatistiklerini de sakla
                self._llm_summary = llm_result.get("summary_stats", {})
            else:
                self._llm_summary = {}
        else:
            self._llm_summary = {}

        return filtered

    def aggregate_data(self, filtered_items: list) -> dict:
        result = {
            "total_extracted_items": len(filtered_items),
            "data": filtered_items
        }
        if hasattr(self, "_llm_summary") and self._llm_summary:
            result["summary_stats"] = self._llm_summary
        return result
