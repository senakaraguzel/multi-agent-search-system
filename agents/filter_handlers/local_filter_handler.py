"""
LocalFilterHandler — Agent 6 için Lokal Firma Arama Pipeline Handler'ı.
Google Maps, Yelp gibi kaynaklardan gelen LocalScraper + GoogleCommentAgent
verilerini işler; firma adı, adres, telefon, puan, yorum sayısı, kategori ve
yorumları yapılandırılmış bir listeye dönüştürür.
"""

from agents.filter_handlers.base_filter_handler import BaseFilterHandler


def _safe_float(value) -> float | None:
    """String veya float olan rating değerini güvenli şekilde float'a çevirir."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


class LocalFilterHandler(BaseFilterHandler):
    """
    Lokal firma verilerini işleyen ve nitel/nicel özet üreten handler.

    Desteklenen alanlar (extracted_entity içinden):
        - company_name, address, phone, rating, reviews_count, category
    Google Comment Agent'ın ürettiği ek veriler:
        - google_reviews (liste) — her biri {author, rating, text, date}
    """

    def filter_relevant_data(self) -> list:
        filtered = []
        requested = self.intent_data.get("requested_fields", [])
        date_context = self.intent_data.get("date_context")

        for item in self.raw_items:
            if not isinstance(item, dict):
                continue

            url = item.get("url") or item.get("profile_url", "")
            if url and url not in self.sources_used:
                self.sources_used.append(url)

            # LocalScraper'ın doldurduğu extracted_entity
            ext = item.get("extracted_entity", {})
            if not ext:
                continue

            entry = {
                "company_name": ext.get("company_name") or ext.get("name"),
                "address":      _clean_str(ext.get("address")),
                "phone":        _clean_str(ext.get("phone")),
                "rating":       _safe_float(ext.get("rating")),
                "reviews_count": _safe_int(ext.get("reviews_count")),
                "category":     _clean_str(ext.get("category")),
                "website":      _clean_str(ext.get("website")),
                "source_url":   url,
            }

            # Google Comment Agent'tan gelen yorumlar (opsiyonel)
            reviews = item.get("google_reviews") or ext.get("reviews", [])
            if reviews and isinstance(reviews, list):
                entry["reviews"] = reviews[:10]  # En fazla 10 yorum sakla
            else:
                entry["reviews"] = []

            # Filtre: kullanıcı belirli bir alan istediyse diğerlerini atla.
            # Ancak niyet "Listings" ise veya requested_fields boşsa tüm verileri koru.
            intent_str = str(self.intent_data.get("intent", "")).lower()
            is_listing = "listing" in intent_str
            
            if requested and not is_listing:
                entry = {k: v for k, v in entry.items()
                         if k in requested or k in ("company_name", "source_url")}

            # Boş company_name'leri çıkar (anlamsız kayıt)
            if not entry.get("company_name"):
                continue

            filtered.append(entry)

        return filtered

    def aggregate_data(self, filtered_items: list) -> dict:
        total = len(filtered_items)

        # Rating istatistikleri
        rated = [item for item in filtered_items
                 if item.get("rating") is not None]
        avg_rating = None
        min_rating = None
        max_rating = None
        if rated:
            ratings = [item["rating"] for item in rated]
            avg_rating = round(sum(ratings) / len(ratings), 2)
            min_rating = min(ratings)
            max_rating = max(ratings)

        # Kategori dağılımı
        category_distribution: dict[str, int] = {}
        for item in filtered_items:
            cat = item.get("category") or "Bilinmiyor"
            category_distribution[cat] = category_distribution.get(cat, 0) + 1

        # Telefon bilgisi olanlar
        with_phone = sum(1 for item in filtered_items if item.get("phone"))

        return {
            "total_items_processed":  total,
            "items_with_rating":      len(rated),
            "average_rating":         avg_rating,
            "min_rating":             min_rating,
            "max_rating":             max_rating,
            "items_with_phone":       with_phone,
            "category_distribution":  category_distribution,
            "businesses":             filtered_items,
        }

    def compute_confidence_score(self, aggregated: dict) -> float:
        base_score = super().compute_confidence_score(aggregated)

        total = aggregated.get("total_items_processed", 0)
        if total == 0:
            return 0.1

        # Puan bilgisi olan firma oranı yüksekse ekstra güven
        rated_ratio = aggregated.get("items_with_rating", 0) / total
        if rated_ratio >= 0.7:
            base_score += 0.15

        # Telefon bilgisi varsa ekstra güven
        phone_ratio = aggregated.get("items_with_phone", 0) / total
        if phone_ratio >= 0.5:
            base_score += 0.05

        return min(max(round(base_score, 2), 0.0), 1.0)


# ─── Yardımcı Fonksiyonlar ───────────────────────────────────────────────────
def _clean_str(value) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).replace(",", "").replace(".", "").strip())
    except (ValueError, TypeError):
        return None
