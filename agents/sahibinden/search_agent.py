from utils.domain_classifier import DomainClassifier
from utils.query_parser import QueryParser


class SearchAgent:

    def __init__(self):
        self.domain_classifier = DomainClassifier()
        self.query_parser = QueryParser()

    def generate_metadata(self, domain, parsed_data):
        """
        Domain'e göre en az 7 metadata header üretir.
        key: JSON'daki gerçek alan adı
        label: Tabloda gösterilecek başlık
        """

        if domain == "emlak":

            metadata = [
                {"key": "title",          "label": "Başlık"},
                {"key": "price",          "label": "Fiyat / Kira"},
                {"key": "location",       "label": "İl / İlçe"},
                {"key": "oda_sayisi",     "label": "Oda Sayısı"},
                {"key": "m2_net",         "label": "m² (Net)"},
                {"key": "bina_yasi",      "label": "Bina Yaşı"},
                {"key": "bulundugu_kat",  "label": "Bulunduğu Kat"},
                {"key": "url",            "label": "URL"},
            ]

        elif domain in ("araba", "vasita"):

            metadata = [
                {"key": "title",       "label": "Başlık"},
                {"key": "price",       "label": "Fiyat"},
                {"key": "marka",       "label": "Marka"},
                {"key": "seri",        "label": "Seri"},
                {"key": "model",       "label": "Model"},
                {"key": "yil",         "label": "Yıl"},
                {"key": "yakit_tipi",  "label": "Yakıt Tipi"},
                {"key": "vites",       "label": "Vites"},
                {"key": "arac_durumu", "label": "Araç Durumu"},
                {"key": "km",          "label": "KM"},
                {"key": "url",         "label": "URL"},
            ]

        else:

            metadata = [
                {"key": "title",    "label": "Başlık"},
                {"key": "price",    "label": "Fiyat"},
                {"key": "location", "label": "Konum"},
                {"key": "emlak_tipi","label": "Kategori"},
                {"key": "i̇lan_tarihi","label": "Tarih"},
                {"key": "kimden",   "label": "Kimden"},
                {"key": "url",      "label": "URL"},
            ]

        return metadata


    def run(self, user_query: str):

        print("\n===== SEARCH AGENT =====")

        # 1️⃣ Domain Belirleme

        print("Domain belirleniyor...")
        domain = self.domain_classifier.classify(user_query)

        print("Domain:", domain)


        # 2️⃣ Query Parsing

        print("Query parse ediliyor...")
        parsed_data = self.query_parser.parse(user_query, domain=domain)

        print("Parsed Data:", parsed_data)


        # 3️⃣ Metadata Üretme

        print("Metadata oluşturuluyor...")

        metadata = self.generate_metadata(domain, parsed_data)

        print("Metadata:", metadata)


        # 4️⃣ Sonuç Döndürme

        return {

            "domain": domain,

            "parsed_data": parsed_data,

            "metadata": metadata

        }