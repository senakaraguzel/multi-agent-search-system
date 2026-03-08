import json
from llm.groq_client import GroqClient

SYSTEM_PROMPT = """
You are a strict JSON generator.

You MUST return ONLY valid JSON.
Do NOT write explanations.
Do NOT write text before or after JSON.
Return ONLY JSON.

If information is missing, use null.
"""

class QueryParser:

    def __init__(self):
        self.llm = GroqClient()

    def parse(self, query: str, domain: str = "emlak"):

        if domain in ["araba", "vasita"]:
            user_prompt = f"""
Parse the following vehicle (araba/vasıta) query into structured JSON.

Query: "{query}"

Expected format:
{{
    "marka": string or null,
    "seri": string or null,
    "model": string or null,
    "yil_min": number or null,
    "yil_max": number or null,
    "price_min": number or null,
    "price_max": number or null
}}

Return ONLY JSON.
"""
        else:
            user_prompt = f"""
Parse the following real estate (emlak) query into structured JSON.

Query: "{query}"

Expected format:
{{
    "city": string or null,
    "district": string or null,
    "price_min": number or null,
    "price_max": number or null,
    "rooms": string or null,
    "listing_type": string or null
}}

Return ONLY JSON.
"""

        response = self.llm.generate(SYSTEM_PROMPT, user_prompt)

        try:
            return json.loads(response)
        except:
            print("JSON parse edilemedi")
            print("LLM response:", response)
            return {}
