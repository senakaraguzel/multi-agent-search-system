import json
import os
from urllib.parse import urlparse
from ddgs import DDGS
from agents.utils.execution_tracer import tracer

_AGENT_KEY = "agent_2_discovery"

class SourceDiscoveryAgent:
    """
    Agent 2 — Source Discovery Agent

    Responsibilities:
    - Reads expanded queries from search.json
    - Searches DuckDuckGo
    - Extracts domains (root sources)
    - Removes duplicates
    - Assigns trust scores
    - Updates search.json

    Output:
    search.json → root_sources filled
    """

    def __init__(self):
        self.search_file = "data/search.json"
        self.agent_name = "source-discovery-agent-v1"

        # Trusted domains
        self.high_trust_domains = [
            "google.com",
            "sahibinden.com",
            "arabam.com",
            "hepsiemlak.com",
            "linkedin.com",
            "kariyer.net",
            "indeed.com",
            "wikipedia.org",
            "tr.wikipedia.org"
        ]

    # ==============================
    # MAIN RUN
    # ==============================
    def run(self):
        print("\n[Agent2] Source Discovery Started")
        tracer.log(_AGENT_KEY, "Source Discovery başladı")

        data = self._load_search_json()
        pipeline = data.get("planning", {}).get("pipeline", "")
        expanded_queries = data.get("planning", {}).get("expanded_queries", [])
        preferred_sources = data.get("planning", {}).get("pipeline_hints", {}).get("preferred_sources", [])
        forced_domain = data.get("forced_domain", None) # Zorunlu tekil domain okumasi

        root_sources = []

        if pipeline == "Lokal Firma Arama":
            tracer.log(_AGENT_KEY, "Lokal pipeline: web araması atlandı", "warning")
            print(f"[Agent2] Bypassed: Pipeline '{pipeline}' dogrudan haritalar uzerinden calisacagindan web aramasi atlandi.")
            # root_sources listesi bos kalmali ki Agent 3 kendi isini haritalarda yapsin
        else:
            for query in expanded_queries:
                query_text = query["text"]
                query_id = query["query_id"]
            
                # Eger Forced Domain varsa arama metnine "site:..." ozel operatorunu (Google Hack) ekleyelim.
                search_term = f"site:{forced_domain} {query_text}" if forced_domain else query_text

                print(f"[Agent2] Searching -> {search_term}")
                tracer.log(_AGENT_KEY, f"Arama: {search_term}")

                domains = self._discover_domains(search_term, forced_domain)
                
                # Agent 1 (Planner) tarafından önerilen hedefleri (preferred_sources) zorunlu ekle
                existing_domains = [d["domain"] for d in domains]
                for pref_source in preferred_sources:
                    pref_source_clean = pref_source.replace("www.", "").lower()
                    if pref_source_clean not in existing_domains:
                        domains.append({
                            "domain": pref_source_clean,
                            "base_url": f"https://{pref_source_clean}",
                            "trust_score": 0.95,  # Planner önerdiği için yüksek güven puanı
                            "status": "queued_for_browsing",
                            "exact_urls": [f"https://{pref_source_clean}"]
                        })
                        existing_domains.append(pref_source_clean)

                # Optimizasyon: Domainleri güven puanına göre sıralayıp EN FAZLA 8 tanesini al
                domains = sorted(domains, key=lambda x: x.get("trust_score", 0), reverse=True)[:8]

                root_sources.append({
                    "query_id": query_id,
                    "discovered_by": self.agent_name,
                    "domains": domains
                })
                tracer.log(_AGENT_KEY, f"{query_id}: {len(domains)} domain bulundu", "success")
        data["root_sources"] = root_sources
        self._save_search_json(data)

        # Bulunan tüm domain'leri results olarak kaydet
        all_domains = [d for qs in root_sources for d in qs.get("domains", [])]
        tracer.set_results(
            _AGENT_KEY,
            all_domains,
            extra_meta={"total_queries_searched": len(expanded_queries)},
        )
        tracer.log(_AGENT_KEY, f"{len(root_sources)} sorgu için {len(all_domains)} benzersiz domain kaydedildi", "success")

        if pipeline == "Lokal Firma Arama":
            print(f"[Agent2] Source Discovery Bypassed for Local Tasks.")
        else:
            print(f"[Agent2] Source Discovery Completed. Found urls for {len(root_sources)} queries.")

    # ==============================
    # DOMAIN DISCOVERY
    # ==============================
    def _discover_domains(self, query, forced_domain=None):
        urls = self._search_ddgs(query)

        unique_domains = {}
        for url in urls:
            domain = self._extract_domain(url)
            if domain is None:
                continue
                
            # Eger kullanici aramasinda tekil bir alan adi (youtube) dayatilmissa diger domainleri filtrele (Örn: alakasiz haber siteleri)
            if forced_domain and forced_domain not in domain:
                continue

            if domain not in unique_domains:
                unique_domains[domain] = {
                    "domain": domain,
                    "base_url": f"https://{domain}",
                    "trust_score": self._calculate_trust_score(domain),
                    "status": "queued_for_browsing",
                    "exact_urls": [url]
                }
            else:
                if url not in unique_domains[domain].get("exact_urls", []):
                    unique_domains[domain].setdefault("exact_urls", []).append(url)

        return list(unique_domains.values())

    # ==============================
    # DDGS SEARCH
    # ==============================
    def _search_ddgs(self, query):
        urls = []
        try:
            results = DDGS().text(query, region="tr-tr", safesearch="off", max_results=15)
            for r in results:
                urls.append(r.get("href", ""))
                
            # Fallback if no results with region filter
            if not urls:
                print(f"[Agent2] No results in TR for '{query}', trying generic search...")
                results = DDGS().text(query, max_results=10)
                for r in results:
                    urls.append(r.get("href", ""))
            
            print(f"[Agent2] -> Found {len(urls)} URLs for '{query}'")
                    
        except Exception as e:
            print("[Agent2] Search Error:", e)
        return urls

    # ==============================
    # DOMAIN EXTRACTION
    # ==============================
    def _extract_domain(self, url):
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            domain = domain.replace("www.", "")
            return domain if domain != "" else None
        except:
            return None

    # ==============================
    # TRUST SCORE
    # ==============================
    def _calculate_trust_score(self, domain):
        if domain in self.high_trust_domains:
            return 0.95
        elif ".gov" in domain or ".edu" in domain:
            return 0.9
        else:
            return 0.6

    # ==============================
    # JSON LOAD
    # ==============================
    def _load_search_json(self):
        if not os.path.exists(self.search_file):
            raise Exception("search.json not found")
        with open(self.search_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # ==============================
    # JSON SAVE
    # ==============================
    def _save_search_json(self, data):
        with open(self.search_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ==============================
# TEST
# ==============================
if __name__ == "__main__":
    agent = SourceDiscoveryAgent()
    agent.run()