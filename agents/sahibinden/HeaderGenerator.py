from utils.domain_classifier import DomainClassifier

class HeaderGenerator:
    """
    Module 3 in the Architecture: Generates dynamic headers based on search query category.
    """
    def __init__(self):
        self.domain_classifier = DomainClassifier()

    def generate_headers(self, search_query: str):
        """
        Detects the category from the query and returns a list of dictionary headers.
        Each dictionary contains "key" (for JSON mapping) and "label" (for UI display).
        """
        domain = self.domain_classifier.classify(search_query)

        if domain == "emlak":
            headers = [
                {"key": "location",       "label": "İl / İlçe"},
                {"key": "oda_sayisi",     "label": "Oda Sayısı"},
                {"key": "price",          "label": "Fiyat / Kira"},
                {"key": "bina_yasi",      "label": "Bina Yaşı"},
                {"key": "bulundugu_kat",  "label": "Bulunduğu Kat"},
                {"key": "m2_net",         "label": "m² (Net)"},
                {"key": "title",          "label": "Başlık"},
                {"key": "url",            "label": "URL"},
            ]
        elif domain in ("araba", "vasita"):
            headers = [
                {"key": "marka",       "label": "Marka"},
                {"key": "model",       "label": "Model"},
                {"key": "yil",         "label": "Yıl"},
                {"key": "km",          "label": "KM"},
                {"key": "yakit_tipi",  "label": "Yakıt Tipi"},
                {"key": "vites",       "label": "Vites"},
                {"key": "price",       "label": "Fiyat"},
                {"key": "url",         "label": "URL"},
            ]
        else:
            headers = [
                {"key": "title",    "label": "Başlık"},
                {"key": "price",    "label": "Fiyat"},
                {"key": "location", "label": "Konum"},
                {"key": "emlak_tipi","label": "Kategori"},
                {"key": "i̇lan_tarihi","label": "Tarih"},
                {"key": "kimden",   "label": "Kimden"},
                {"key": "url",      "label": "URL"},
            ]

        return {
            "domain": domain,
            "headers": headers
        }
