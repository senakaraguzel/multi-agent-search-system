from agents.filter_handlers.base_filter_handler import BaseFilterHandler

class LinkedInFilterHandler(BaseFilterHandler):
    """
    LinkedIn Profillerinden ('Name', 'Title', 'Company') gelen raw dictionary'leri isler.
    Kullanicinin query'sine (orn: izmir frontend) gore uyanlari gruplar.
    """
    def filter_relevant_data(self) -> list:
        filtered = []
        for item in self.raw_items:
             if not isinstance(item, dict): continue
             ext = item.get("extracted_entity", {})
             if not ext: continue
             
             url = item.get("profile_url") or item.get("url")
             if url and url not in self.sources_used:
                  self.sources_used.append(url)
                  
             entry = {
                 "name": ext.get("name") or item.get("name", "Unknown"),
                 "title": ext.get("title") or item.get("title", ""),
                 "company": ext.get("company") or item.get("company", ""),
                 "location": ext.get("location") or item.get("location", "")
             }
             filtered.append(entry)
             
        return filtered

    def aggregate_data(self, filtered_items: list) -> dict:
        total_profiles = len(filtered_items)
        
        # Basit gruplama (Title tabanli)
        title_breakdown = {}
        for item in filtered_items:
            t = item.get("title", "Unknown Role")
            title_breakdown[t] = title_breakdown.get(t, 0) + 1
            
        return {
            "total_profiles_processed": total_profiles,
            "title_breakdown": title_breakdown,
            "profiles": filtered_items
        }
        
    def compute_confidence_score(self, aggregated: dict) -> float:
        base_score = super().compute_confidence_score(aggregated)
        if aggregated.get("total_profiles_processed", 0) > 0:
            base_score += 0.2
        return min(max(round(base_score, 2), 0.0), 1.0)
