import json
import os
from agents.utils.llm_filter_analyzer import analyze_query_for_filtering
from agents.filtering_agent_core import FilterRouter
from agents.utils.execution_tracer import tracer

_AGENT_KEY = "agent_6_filtering"

class FilteringAgent:
    """
    Sistemin Agent 6 asamasidir.
    Kullanicinin orijinal sorgusunu LLM ile analiz edip istenen kolonlari ceker.
    scrape.json icindeki ham formattaki datalari domain_specific kodlayicilara yoneltir.
    Sonuclari matematiksel & kurala dayali birlestirip `result.json`a yazar.
    """
    
    def __init__(self):
        self.agent_name = "filtering-agent-v1"
        self.input_file = os.path.join("data", "scrape.json")
        self.output_file = os.path.join("data", "result.json")
        self.router = FilterRouter()
        
    def _load_data(self) -> dict:
        if not os.path.exists(self.input_file):
            return {}
        try:
             with open(self.input_file, 'r', encoding='utf-8') as f:
                 return json.load(f)
        except Exception as e:
             print(f"[{self.agent_name}] scrape.json okuma hatasi: {e}")
             return {}
             
    def _save_data(self, data: dict):
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
             json.dump(data, f, ensure_ascii=False, indent=2)

    def execute(self):
        print(f"\n[{self.agent_name}] Filtreleme, Dogrulama ve Birlestirme Basladi...")
        tracer.log(_AGENT_KEY, "Filtreleme başladı")
        
        # 1. Ham veriyi oku
        scrape_data = self._load_data()
        
        original_query = scrape_data.get("original_query", "")
        session_id = scrape_data.get("search_session_id", "session_unassigned")
        raw_scraped_items = scrape_data.get("scraped_pages", [])
        
        # Pipeline türünü scrape.json'dan oku (ScraperAgent session_id ile birlikte yazar)
        # Yoksa search.json'dan fallback olarak oku
        pipeline = scrape_data.get("pipeline", "")
        if not pipeline:
            search_path = os.path.join("data", "search.json")
            if os.path.exists(search_path):
                try:
                    with open(search_path, "r", encoding="utf-8") as f:
                        search_data = json.load(f)
                    pipeline = search_data.get("pipeline", "")
                except Exception:
                    pass
        
        if not original_query or not raw_scraped_items:
             tracer.log(_AGENT_KEY, "scrape.json boş veya original_query eksik", "error")
             print(f"[{self.agent_name}] Islenecek scrape kaydi bulunamadi.")
             return
             
        # 2. Origin Query'i Parse Et (LLM)
        print(f"[{self.agent_name}] LLM Intent Analysis calisiyor: '{original_query}'")
        intent_analysis = analyze_query_for_filtering(original_query)
        print(f"[{self.agent_name}] Analiz Edilen Schema: {json.dumps(intent_analysis, ensure_ascii=False)}")
        tracer.log(_AGENT_KEY, f"Intent analizi tamamlandı: {intent_analysis.get('intent','?')}")
        
        # 3. Domain Specifik Islemler (Python Aggregation)
        # Orijinal sorgu, pipeline ve main_entity'yi enjekte et
        intent_analysis["original_query"] = original_query
        intent_analysis["main_entity"] = intent_analysis.get("main_entity") or original_query
        
        # Ek bağlamı (yıl, pipeline) search.json'dan enjekte et
        search_path = os.path.join("data", "search.json")
        if os.path.exists(search_path):
            try:
                with open(search_path, "r", encoding="utf-8") as f:
                    search_data = json.load(f)
                if not intent_analysis.get("target_year") and search_data.get("target_time_frame"):
                    try:
                        intent_analysis["target_year"] = int(search_data.get("target_time_frame"))
                        intent_analysis["is_time_sensitive"] = True
                    except: pass
                if not intent_analysis.get("pipeline"):
                    intent_analysis["pipeline"] = search_data.get("pipeline", "")
            except: pass

        handler = self.router.route(intent_data=intent_analysis, raw_items=raw_scraped_items)
        handler_name = handler.__class__.__name__
        tracer.log(_AGENT_KEY, f"Handler seçildi: {handler_name}")
        print(f"[{self.agent_name}] Uygun Handler Secildi: {handler_name}")
        
        # 4. Result uretimi (Deterministic)
        filtered_result = handler.process()
        
        # 5. Opsiyonel Validation Note
        # Basit Pythonik validation yapiyoruz LLM'i daha fazla ugrastirmadan
        total = filtered_result.get("final_structured_result", {}).get("total_items_processed", 
                filtered_result.get("final_structured_result", {}).get("total_profiles_processed", 0))
        note = f"Deterministically parsed {total} active records using {handler_name}. Fields extracted matching intent: {intent_analysis.get('intent', 'Mixed Data')}."
        
        # 6. JSON Structuring
        final_output = {
            "search_session_id": session_id,
            "original_query": original_query,
            "final_structured_result": filtered_result.get("final_structured_result", {}),
            "sources_used": filtered_result.get("sources_used", []),
            "confidence_score": filtered_result.get("confidence_score", 0.0),
            "validation_notes": note
        }
        
        self._save_data(final_output)
        print(f"[{self.agent_name}] Ozet Data basariyla result.json'a kaydedildi. Confidence Score: {final_output['confidence_score']}\n")

        # Nihai sonucu tracer'a kaydet
        result_items = (
            final_output.get("final_structured_result", {}).get("results")
            or final_output.get("final_structured_result", {}).get("businesses")
            or final_output.get("final_structured_result", {}).get("articles")
            or final_output.get("final_structured_result", {}).get("listings")
            or final_output.get("final_structured_result", {}).get("profiles")
            or [final_output.get("final_structured_result", {})]
        )
        tracer.set_results(
            _AGENT_KEY,
            result_items,
            extra_meta={
                "confidence_score": final_output["confidence_score"],
                "handler": handler_name,
                "validation_notes": final_output["validation_notes"],
            },
        )
        tracer.log(_AGENT_KEY, f"{len(result_items)} kayıt filtrelendi → result.json kaydedildi (skor: {final_output['confidence_score']})", "success")

if __name__ == "__main__":
    FilteringAgent().execute()
