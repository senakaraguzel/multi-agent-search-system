import os
import json
import uuid
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from agents.utils.execution_tracer import tracer

_AGENT_KEY = "agent_1_planner"

from openai import AzureOpenAI

class SourcePlannerAgent:

    def __init__(self):
        self.output_dir = "data"
        self.output_path = os.path.join(self.output_dir, "search.json")
        key = os.environ.get("OPENAI_API_KEY") # Kullanıcının .env dosyasına göre kontrol edecek
        azure_endpoint = "https://genarion-deep-search-source-1.openai.azure.com/"
        api_version = "2024-12-01-preview"
        
        if not key:
            print("[Warning] OPENAI_API_KEY environment variable is missing!")
            self.client = None
        else:
            self.client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                api_key=key
            )

    def plan(self, user_query: str) -> dict:
        """
        Uses an LLM to generate the search plan.
        """
        tracer.log(_AGENT_KEY, f"Planlama başladı: '{user_query}'")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:6]
        session_id = f"session_{timestamp}_{short_uuid}"

        if not self.client:
            tracer.log(_AGENT_KEY, "API anahtarı eksik, LLM kullanılamıyor", "error")
            return {}
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt = f"""
        You are the 'Search Strategist' agent (Agent 1), the brain of the system.
        Current system time and date: {current_time}
        Task: Analyze the user's search query using deep cognitive skills, not just as random google searches.
        
        Cognitive Steps to apply:
        1. Temporal Reasoning: Convert relative time expressions like "this year", "last summer", "next winter" into absolute years based on the current system time ({current_time}) (e.g., 2025). If a specific time is targeted, return this as 'target_time_frame'.
        2. Entity Normalization: Normalize abbreviations or slang (e.g., "FB" -> "Fenerbahçe", "GS" -> "Galatasaray").
        3. Search Intent Classification: Classify the user's core intent (statistical, news, historical, listing, etc.).
        4. Platform Selection: Strategically select the target platforms based on the accuracy of the goal.
        
        User Query: '{user_query}'

        SUPPORTED SEARCH TYPES AND RULES (PIPELINE):
        1. "Spesifik Bilgi Arama" (Specific Information Search - Used for finding EXACT SINGLE ANSWERS, statistical or factual data, OR SPECIFIC EVENT LISTINGS that meet set criteria. E.g., "Galatasaray's 2025 goals", "Turkey's 2024 inflation rate", "2026 AI events in Istanbul", "Harbiye Concerts". Use this for exact lists of events/concerts/conferences where data points are clear).
        2. "Kategorik Bilgi Arama" (Categoric Information Search - Used when general "News, Trends, or Articles" about a topic need to be read. Requires synthesis. E.g., "Technological developments in the white goods sector", "2026 Hamburg event trends". WARNING: DO NOT use for specific event listings, concert schedules, or strictly defined search result lists!).
        3. "Lokal Firma Arama" (Local Business Search - These are detailed physical place/shop searches on Google Maps (e.g., "Kadıköy plumbers", "Beşiktaş restaurants"). WARNING: DO NOT use this for software developers, freelancers, or job searches even if they contain a city name. E.g., "Ankara frontend developerlar" is NOT a local business search!).
        4. "Jenerik Arama" (Generic Search - This is a STRICT schema-based listing search to extract standardized lists of people, ads, or products on SITES like LinkedIn, Sahibinden, Airbnb. WARNING: Job searches, freelancer searches, car or real estate searches MUST be Generic Search, regardless of location).
        
        STATISTICAL AND SPORTS QUERY MANDATORY RULES (for all queries related to sports stats, goals, matches, standings, economic indicators):
        - ALWAYS prefer these platforms as preferred_sources: "statmuse.com", "mackolik.com", "transfermarkt.com.tr", "sofascore.com", "tff.org", "goal.com/tr", "livescore.com", "fbref.com"
        - For NBA-specific queries (Alperen Şengün, LeBron James, etc.): ALWAYS include "statmuse.com" and "nba.com" in preferred_sources.
        - Wikipedia RULE: Put "wikipedia.org" in avoid_sources for GENERIC statistical queries (e.g. economy, general knowledge). 
          EXCEPTION: For football SEASON-SPECIFIC queries (goals scored, match results, season data), Turkish Wikipedia's season page IS a primary source.
          In that case DO NOT put wikipedia.org in avoid_sources.
        - For football/soccer goals/stats queries for a specific CALENDAR YEAR (e.g., 2025):
          * q2: site:mackolik.com [team] [year-1]-[year] istatistik
          * q3: site:mackolik.com [team] [year]-[year+1] istatistik
          * q4: site:transfermarkt.com.tr [team] goller [year]
          * q5: site:tr.wikipedia.org [team_normalized] [year-1]-[year] sezonu
          * q6: site:tr.wikipedia.org [team_normalized] [year]-[year+1] sezonu
          These MUST use the "site:" operator so DuckDuckGo returns DIRECT stat pages, not the homepage.
        - For economic/financial data: prefer tuik.gov.tr, tcmb.gov.tr, investing.com
        - For NBA stats (assists, points, rebounds) for a specific CALENDAR YEAR (e.g., 2025):
          * MANDATORY q2: site:statmuse.com [player_name] [stat_type] [year-1]-[year]
          * MANDATORY q3: site:statmuse.com [player_name] [stat_type] [year]-[year+1]
          * q4: site:statmuse.com [player_name] [stat_type] this year (if [year] is current year)
          * q5: site:statmuse.com [player_name] stats this season
          * q6: site:statmuse.com [player_name] {user_query} [year]
          These MUST use the "site:statmuse.com" operator. You MUST generate both [year-1]-[year] and [year]-[year+1] queries to cover the full calendar year.
        - NEVER use news articles or blogs as the primary source for numeric statistics
        
        TEMPORAL DISAMBIGUATION RULE (CRITICAL):
        - If the user query contains an explicit year (e.g., "2025"), that year MUST be used in ALL expanded queries and as target_time_frame.
        - Do NOT replace the user's year with the current year. Current time is {current_time} but if the user says "2025", target_time_frame MUST be "2025".
        - Example: "Galatasaray'ın 2025'te attığı goller" → target_time_frame: "2025", all queries must include "2025", NOT "2026".
        
        When generating search terms (expanded_queries):
        - q1 MUST ALWAYS be the original query entered by the user (`{user_query}`) and its priority must be 1.0.
        - Create 5 alternative queries from q2 to q6 that fit your strategic thinking (e.g., like a direct mackolik / transfermarkt query).
        
        PROVIDE THE OUTPUT ONLY AS A VALID JSON IN THE FOLLOWING FORMAT:
        ```json
        {{
            "normalized_query": "Lowercase, simplified query",
            "search_intent": "Statistical Verification (etc.)", 
            "pipeline": "Spesifik Bilgi Arama (or your chosen one)",
            "pipeline_reason": "Your Selection and Strategy Explanation (Thinking)",
            "official_source_required": true,
            "target_time_frame": "2025",
            "forced_domain": "If the user EXPLICITLY targets a single site, write that domain (e.g., youtube.com). Data will be extracted only from that domain. Leave null or empty if it's a general search.",
            "planning": {{
                "search_depth": "deep or shallow",
                "pipeline_hints": {{
                    "preferred_sources": ["tff.org", "fenerbahce.org", "transfermarkt.com.tr"],
                    "avoid_sources": ["wikipedia.org"]
                }},
                "query_analysis": {{
                    "normalized_entities": ["Fenerbahçe", "2025"],
                    "location_detected": false,
                    "location_name": "If location_detected is true, extract the normalized city/country here, else null",
                    "time_detected": true,
                    "platform_hints": ["official site", "statistics portal"],
                    "expected_source_types": ["official record", "sports statistics site"]
                }},
                "expanded_queries": [
                    {{
                        "query_id": "q1",
                        "text": "{user_query}",
                        "priority": 1.0,
                        "status": "planned"
                    }},
                    {{
                        "query_id": "q2",
                        "text": "1st strategic sub-query",
                        "priority": 0.9,
                        "status": "planned"
                    }},
                    {{
                        "query_id": "q3",
                        "text": "2nd strategic sub-query",
                        "priority": 0.8,
                        "status": "planned"
                    }},
                    {{
                        "query_id": "q4",
                        "text": "3rd strategic sub-query",
                        "priority": 0.8,
                        "status": "planned"
                    }},
                    {{
                        "query_id": "q5",
                        "text": "4th strategic sub-query",
                        "priority": 0.7,
                        "status": "planned"
                    }},
                    {{
                        "query_id": "q6",
                        "text": "5th strategic sub-query",
                        "priority": 0.7,
                        "status": "planned"
                    }}
                ]
            }}
        }}
        ```
        """

        try:
            tracer.log(_AGENT_KEY, "LLM'e sorgu gönderiliyor (o4-mini)")
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="o4-mini",
                response_format={ "type": "json_object" },
                # O modelleri (o1-mini, o4 vs.) kullanırken temperature desteklenmeyebiliyor veya 1.0 zorunlu tutuluyor.
            )
            text = chat_completion.choices[0].message.content
            
            # Extract JSON from markdown
            match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_str = text

            llm_result = json.loads(json_str)
            tracer.log(_AGENT_KEY, f"LLM yanıtı alındı. Pipeline: {llm_result.get('pipeline','?')}", "success")

        except Exception as e:
            tracer.log(_AGENT_KEY, f"LLM parsing hatası: {e}", "error")
            print(f"[Agent1] LLM Parsing Error: {e}")
            print("Response was:", text if 'text' in locals() else "None")
            print("[Agent1] Falling back to generic plan due to API error.")
            llm_result = {
                "normalized_query": user_query.lower(),
                "pipeline": "4. Jenerik Arama (Fallback)",
                "pipeline_reason": "LLM API hatası nedeniyle jenerik arama planı oluşturuldu. Limit aşıldı veya sunucu yanıt vermedi.",
                "planning": {
                    "search_depth": "shallow",
                    "pipeline_hints": {"preferred_sources": [], "avoid_sources": []},
                    "query_analysis": {},
                    "expanded_queries": [
                        {
                            "query_id": "q1",
                            "text": user_query,
                            "priority": 1.0,
                            "status": "planned"
                        }
                    ]
                }
            }

        # Construct final JSON combining system vars with LLM plan
        # Combine system vars with LLM plan
        planning_data = llm_result.get("planning", {})
        expanded_queries = planning_data.get("expanded_queries", [])
        
        json_output = {
            "search_session_id": session_id,
            "original_query": user_query,
            "normalized_query": llm_result.get("normalized_query", user_query.lower()),
            "search_intent": llm_result.get("search_intent", "Unknown"),
            "pipeline": llm_result.get("pipeline", "generic"),
            "pipeline_reason": llm_result.get("pipeline_reason", ""),
            "official_source_required": llm_result.get("official_source_required", False),
            "target_time_frame": llm_result.get("target_time_frame", None),
            "forced_domain": llm_result.get("forced_domain", None),
            "queries": expanded_queries,
            "planning": {
                "planner_agent": "source-planner-llm-v2",
                "search_depth": planning_data.get("search_depth", "deep"),
                "pipeline_hints": planning_data.get("pipeline_hints", {}),
                "query_analysis": planning_data.get("query_analysis", {}),
                "expanded_queries": expanded_queries
            },
            "root_sources": [],
            "target_pages": []
        }
        
        self._generate_search_json(json_output)
        queries = json_output.get("queries", [])
        tracer.set_results(
            _AGENT_KEY,
            queries,
            extra_meta={
                "pipeline":     json_output.get("pipeline"),
                "search_intent":json_output.get("search_intent"),
                "session_id":   json_output.get("search_session_id"),
            },
        )
        tracer.log(_AGENT_KEY, f"{len(queries)} genişletilmiş sorgu üretildi → search.json kaydedildi", "success")
        return json_output

    def _generate_search_json(self, data: dict) -> None:
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
        # Emoji veya surrogate unicode hatalarina karsi guvenli kayit (Windows destegi)
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        safe_str = json_str.encode("utf-8", "replace").decode("utf-8")
        
        with open(self.output_path, "w", encoding="utf-8") as file:
            file.write(safe_str)

