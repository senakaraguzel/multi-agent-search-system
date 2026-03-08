import json
import os
import asyncio

from agents.utils.execution_tracer import tracer

_AGENT_KEY = "agent_3_browsing"

# Çekirdek anti-bot kütüphanesi ve alt ajanlar
from agents.browsing_agent_core import (
    LocalBusinessBrowsingAgent,
    SpecificBrowsingAgent,
    CategoricBrowsingAgent,
    GenericBrowsingAgent
)

class BrowsingAgentRouter:
    """
    Agent 3 — Browsing Agent Router
    
    Responsibilities:
    - `search.json` dosyasını okuyup arama tipine (pipeline) bakar.
    - Doğru dikey Browsing Ajanı'nı seçer.
    - Alt ajanın döndürdüğü 'hedef URL'leri' toplayıp JSON'a target_pages olarak işler.
    """

    def __init__(self):
        self.search_file = "data/search.json"
        self.agent_name = "browsing-router-v1"

    async def execute(self):
        print(f"\n[{self.agent_name}] Browsing Agent Router Started")
        tracer.log(_AGENT_KEY, "Browsing Router başladı")
        
        if not os.path.exists(self.search_file):
            print(f"[{self.agent_name}] search.json not found!")
            return

        with open(self.search_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        pipeline = data.get("pipeline", "Generic")
        original_query = data.get("original_query", "")
        root_sources = data.get("root_sources", [])
        
        if not root_sources and pipeline != "Lokal Firma Arama":
            tracer.log(_AGENT_KEY, "root_sources boş, browsing atlanıyor", "warning")
            print(f"[{self.agent_name}] No root sources found. Skipping browsing.")
            return

        if not root_sources and pipeline == "Lokal Firma Arama":
            print(f"[{self.agent_name}] Lokal Firma Arama bypass identified. Proceeding without root_sources.")

        print(f"[{self.agent_name}] Detected Pipeline: '{pipeline}'. Routing to expert browser...")

        # Spesifik ve Kategorik aramalarda kaynakları filtrele
        if pipeline in ["Spesifik Bilgi Arama", "Kategorik Bilgi Arama"]:
            original_len = len(root_sources)
            hints = data.get("planning", {}).get("pipeline_hints", {})
            preferred_domains = [d.lower() for d in hints.get("preferred_sources", [])]
            avoid_domains = [d.lower() for d in hints.get("avoid_sources", [])]
            
            filtered_sources = []
            for s in root_sources:
                # q1 her zaman korunur
                if s.get("query_id") == "q1":
                    filtered_sources.append(s)
                    continue
                    
                # Avoid listesindeki domainleri atla
                is_avoided = any(
                    any(av in dom_data.get("domain", "").lower() for av in avoid_domains)
                    for dom_data in s.get("domains", [])
                )
                if is_avoided:
                    continue
                
                # Preferred varsa sadece o domainleri al; preferred boşsa hepsini kabul et
                if preferred_domains:
                    is_preferred = any(
                        any(pref in dom_data.get("domain", "").lower() for pref in preferred_domains)
                        or "biletix.com" in dom_data.get("domain", "").lower()
                        for dom_data in s.get("domains", [])
                    )
                    if is_preferred:
                        filtered_sources.append(s)
                else:
                    # Preferred tanımlanmamışsa tüm avoid-dışı kaynakları kabul et
                    filtered_sources.append(s)
                        
            root_sources = filtered_sources
            print(f"[{self.agent_name}] Optimizasyon: Alakasiz/engellenen q2..qN siteleri elendi. URL kaynagi {original_len}'den {len(root_sources)}'a dusuruldu.")



        # Sifreleme: Biletix, Sahibinden gibi listeleme siteleri her zaman Jenerik Arama kalibina (Platform Arama) sokulmalidir.
        for s in root_sources:
            for dom_data in s.get("domains", []):
                d = dom_data.get("domain", "").lower()
                if "biletix.com" in d or "sahibinden.com" in d or "linkedin.com" in d:
                    print(f"[{self.agent_name}] Platform tespiti yapildi ('{d}'). Pipeline 'Jenerik Arama' olarak eziliyor.")
                    pipeline = "Jenerik Arama"
                    break
        
        # Yönlendirme Mantığı
        if pipeline == "Lokal Firma Arama":
            expert_browser = LocalBusinessBrowsingAgent()
        elif pipeline == "Spesifik Bilgi Arama":
            expert_browser = SpecificBrowsingAgent()
        elif pipeline == "Kategorik Bilgi Arama":
            expert_browser = CategoricBrowsingAgent()
        elif pipeline == "Jenerik Arama":
            expert_browser = GenericBrowsingAgent()
        else:
            print(f"[{self.agent_name}] Unknown pipeline '{pipeline}', falling back to GenericBrowser.")
            expert_browser = GenericBrowsingAgent()

        # Uzman ajanı çalıştır
        print(f"[{self.agent_name}] Bounding off to -> {expert_browser.agent_name}")
        tracer.log(_AGENT_KEY, f"Pipeline: '{pipeline}' → {expert_browser.agent_name} seçildi")
        
        try:
            target_pages = await expert_browser.run_browsing(root_sources, data)
        except Exception as e:
            tracer.log(_AGENT_KEY, f"Hata: {expert_browser.agent_name}: {e}", "error")
            print(f"[{self.agent_name}] Fatal Error in {expert_browser.agent_name}: {e}")
            target_pages = []

        # Target Pages listesini JSON'a kaydet (Mevcut olanı da koruyabiliriz veya üstüne yazabiliriz)
        # Önceki kayıtların yanına ekle (extends)
        existing_targets = data.get("target_pages", [])
        existing_targets.extend(target_pages)
        
        # Deduplicate
        unique_targets = { t["url"]: t for t in existing_targets }.values()
        data["target_pages"] = list(unique_targets)

        with open(self.search_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n[{self.agent_name}] Browsing Router Completed. {len(target_pages)} new URLs added.")
        print(f"[{self.agent_name}] Resulting array 'target_pages' has {len(data['target_pages'])} urls now.")
        tracer.set_results(
            _AGENT_KEY,
            list(data["target_pages"]),
            extra_meta={"new_urls_found": len(target_pages)},
        )
        tracer.log(_AGENT_KEY, f"{len(target_pages)} yeni URL eklendi, toplam: {len(data['target_pages'])}", "success")

    def run(self):
        """Synchronous start"""
        asyncio.run(self.execute())


if __name__ == "__main__":
    router = BrowsingAgentRouter()
    router.run()
