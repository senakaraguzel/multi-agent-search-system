from agents.filter_handlers.base_filter_handler import BaseFilterHandler

class SahibindenFilterHandler(BaseFilterHandler):
    """
    Sahibinden ilanlarini kaziyan Agent'tan gelen verileri
    isleyip, kullanicinin query intentine (fiyat karsilastir, toplam ev sayisi) gore
    deterministik bir sonuc uretir.
    """
    
    def filter_relevant_data(self) -> list:
        filtered = []
        # Orijinal niyet emlak fiyatlarini listelemek/toplamak olabilir.
        requested = self.intent_data.get("requested_fields", [])
        
        for item in self.raw_items:
            if not isinstance(item, dict): continue
            
            ext = item.get("extracted_entity", {})
            if not ext: continue
            
            # Record source
            url = item.get("profile_url") or item.get("url")
            if url and url not in self.sources_used:
                self.sources_used.append(url)
                
            entry = {}
            if "title" in requested or not requested:
                entry["title"] = ext.get("title", "Bilinmeyen İlan")
            if "price" in requested or not requested:
                price_str = ext.get("price", "")
                # Temizle ve sayiya donustur
                try:
                    p = price_str.split("TL")[0].replace(".", "").strip()
                    entry["price_numeric"] = int(p)
                except:
                    entry["price_numeric"] = None
                    
            if "location" in requested or not requested:
                entry["location"] = ext.get("location", "")
                
            # Gayrimenkul spesifik
            if "m2" in str(requested).lower():
                entry["m2"] = ext.get("m²_net", ext.get("m²_brut", ""))
                
            filtered.append(entry)
            
        return filtered
        
    def aggregate_data(self, filtered_items: list) -> dict:
        total_price = 0
        valid_price_count = 0
        
        for item in filtered_items:
            if item.get("price_numeric") is not None:
                total_price += item["price_numeric"]
                valid_price_count += 1
                
        avg_price = total_price / valid_price_count if valid_price_count > 0 else 0
        
        return {
            "total_items_processed": len(filtered_items),
            "items_with_valid_price": valid_price_count,
            "average_price": round(avg_price, 2),
            "total_price_sum": total_price,
            "listings": filtered_items
        }

    def compute_confidence_score(self, aggregated: dict) -> float:
        # Base class skoru al
        base_score = super().compute_confidence_score(aggregated)
        
        # Ekstra: Fiyatlar duzgun parse edilmisse Completeness skoruna yuklen
        if aggregated.get("items_with_valid_price", 0) == aggregated.get("total_items_processed", -1) and aggregated.get("total_items_processed") > 0:
            base_score += 0.2
            
        # Ekstra: Eger 0 kayit geldiyse skor dusuk olmali
        if aggregated.get("total_items_processed", 0) == 0:
            return 0.1
            
        return min(max(round(base_score, 2), 0.0), 1.0)
