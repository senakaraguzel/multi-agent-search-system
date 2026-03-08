import json

class BaseFilterHandler:
    """
    Tüm filtreleme isleyicilerinin turetilmesi gereken taban sinif.
    """
    def __init__(self, intent_data: dict, raw_items: list):
        self.intent_data = intent_data
        self.raw_items = raw_items
        self.sources_used = []
        
    def filter_relevant_data(self) -> list:
        raise NotImplementedError
        
    def aggregate_data(self, filtered_items: list) -> dict:
        raise NotImplementedError
        
    def compute_confidence_score(self, aggregated: dict) -> float:
        """
        Kullanici kuralli skorlama: 
        0.4 -> 2+ bagimsiz kaynak (benzersiz domain veya ayri ilan URL'si)
        0.2 -> resmi / guvenilir kaynak (sahibinden, linkedin vb bilindikse)
        0.2 -> numeric consistency (sayisal veriler hesaplandi mi, hata var mi)
        0.2 -> missing fields (veriler tam mi)
        """
        score = 0.0
        
        # 1. 2+ sources
        unique_urls = set(item.get("url", item.get("profile_url", "")) for item in self.raw_items if type(item) is dict)
        if len(unique_urls) >= 2:
            score += 0.4
            
        # 2. Resmi yetkili kaynak (Sahibinden / LinkedIn vs)
        official_domains = ["sahibinden.com", "linkedin.com", "airbnb.com", "biletix.com", "transfermarkt.com"]
        domain_found = False
        for url in unique_urls:
            for official in official_domains:
                if official in url:
                    domain_found = True
                    break
        if domain_found:
            score += 0.2
            
        # 3. Numeric & 4. Completeness depend on aggregated data
        # These should be overridden or supplemented by child classes if needed.
        # As a base metric, if we aggregated at least 1 item and no explicit errors occurred:
        if aggregated.get("total_items_processed", 0) > 0:
             score += 0.2 # assume partial completeness
             score += 0.2 # assume partial consistency
             
        # Cap to 1.0
        return min(max(round(score, 2), 0.0), 1.0)
        
    def process(self):
        filtered = self.filter_relevant_data()
        agg = self.aggregate_data(filtered)
        score = self.compute_confidence_score(agg)
        
        return {
            "final_structured_result": agg,
            "sources_used": self.sources_used,
            "confidence_score": score
        }
