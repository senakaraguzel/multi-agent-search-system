"""
FilterRouter — scrape.json pipeline türüne ve domain'e göre
doğru FilterHandler sınıfını seçer.

Öncelik sırası:
1. Pipeline türüne göre (Spesifik → SpecificFilterHandler, vb.)
2. Domain oylamasına göre (sahibinden, linkedin, google maps)
3. Fallback: GenericFilterHandler
"""

from agents.filter_handlers.sahibinden_filter_handler import SahibindenFilterHandler
from agents.filter_handlers.linkedin_filter_handler   import LinkedInFilterHandler
from agents.filter_handlers.generic_filter_handler    import GenericFilterHandler
from agents.filter_handlers.local_filter_handler      import LocalFilterHandler
from agents.filter_handlers.categoric_filter_handler  import CategoricFilterHandler
from agents.filter_handlers.specific_filter_handler   import SpecificFilterHandler


class FilterRouter:
    """
    LLM'den gelen analiz sonucuna (intent_data) ve
    kazınan verinin kaynağına göre (domain oylaması) doğru
    FilterHandler sınıfını seçen yönlendirici.
    """

    # Pipeline anahtar kelime eşlemeleri (lowercase)
    _PIPELINE_MAP = {
        "spesifik": SpecificFilterHandler,
        "specific":  SpecificFilterHandler,
        "kategorik": CategoricFilterHandler,
        "categoric": CategoricFilterHandler,
        "kategoric": CategoricFilterHandler,
        "lokal":     LocalFilterHandler,
        "local":     LocalFilterHandler,
    }

    def route(self, intent_data: dict, raw_items: list):
        """
        intent_data["pipeline"] veya domain oylamasına göre handler döner.

        Args:
            intent_data: LLM'in ürettiği intent analizi (pipeline, requested_fields vb.)
            raw_items:   scrape.json → scraped_pages listesi

        Returns:
            BaseFilterHandler alt sınıfının instance'ı
        """
        # ── 1. Pipeline türüne göre yönlendirme (öncelikli) ───────────────────
        pipeline = intent_data.get("pipeline", "")
        pipeline_lower = pipeline.lower()

        for keyword, handler_cls in self._PIPELINE_MAP.items():
            if keyword in pipeline_lower:
                print(f"[FilterRouter] Pipeline '{pipeline}' → {handler_cls.__name__}")
                return handler_cls(intent_data, raw_items)

        # ── 2. Domain oylamasına göre yönlendirme (fallback) ──────────────────
        domain_votes = {
            "sahibinden.com":   0,
            "linkedin.com":     0,
            "google.com/maps":  0,
        }

        for item in raw_items:
            url = str(item.get("url") or item.get("profile_url") or "")
            for d in domain_votes:
                if d in url:
                    domain_votes[d] += 1

        voted = max(domain_votes, key=domain_votes.get)
        if domain_votes[voted] > 0:
            if voted == "sahibinden.com":
                print(f"[FilterRouter] Domain oylaması → SahibindenFilterHandler")
                return SahibindenFilterHandler(intent_data, raw_items)
            elif voted == "linkedin.com":
                print(f"[FilterRouter] Domain oylaması → LinkedInFilterHandler")
                return LinkedInFilterHandler(intent_data, raw_items)
            elif voted == "google.com/maps":
                print(f"[FilterRouter] Domain oylaması → LocalFilterHandler (Google Maps)")
                intent_data["requested_fields"] = []  # Tüm alanları döndür
                return LocalFilterHandler(intent_data, raw_items)

        # ── 3. Tam fallback ────────────────────────────────────────────────────
        print(f"[FilterRouter] Fallback → GenericFilterHandler")
        return GenericFilterHandler(intent_data, raw_items)
