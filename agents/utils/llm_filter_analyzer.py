import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_azure_client():
    key = os.environ.get("OPENAI_API_KEY")
    azure_endpoint = "https://genarion-deep-search-source-1.openai.azure.com/"
    api_version = "2024-12-01-preview"
    
    if not key:
        print("[Warning] OPENAI_API_KEY environment variable is missing!")
        return None
        
    return AzureOpenAI(
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        api_key=key
    )

def analyze_query_for_filtering(original_query: str) -> dict:
    """
    Kullanicinin orijinal sorgusunu LLM ile analiz edip, niyetini (intent) ve
    aradiginiz semayi (entity, season, fields vs) cikarir.
    """
    client = get_azure_client()
    if not client:
        return {}
        
    prompt = f"""
    You are a Filtering Agent in a multi-agent web scraping system.
    The user's original search query is: '{original_query}'
    TODAY'S DATE: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}
    
    Your task is to extract the skeleton of this query in the following JSON format:
    1. Parse the user's original query and determine the intent, main entity, season/date, and requested fields.
    2. IMPORTANT: If the query mentions a specific year (e.g., "2025", "2024-25 season"), extract it exactly as-is.
       Do NOT substitute the user's year with today's date or current year.
    
    OUTPUT FORMAT (return ONLY valid JSON):
    {{
      "intent": "Listings/Prices/Stats/Personnel",
      "main_entity": "What/who is being searched (e.g., 2+1 apartment in Ankara)",
      "date_context": "Exact year or season from the user query if present (e.g., '2025'), otherwise null",
      "target_year": 2025,  // Integer year extracted from the query, or null if no year is mentioned
      "is_time_sensitive": true,  // true if the query has a year/season constraint
      "requested_fields": ["price", "location", "title"]  // target fields inferred from the original query
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="o4-mini", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        
        result_content = response.choices[0].message.content
        if not result_content:
            print("[llm_filter_analyzer] Warning: LLM returned empty string.")
            return {}
            
        reply = result_content.strip()
        
        # Olası Markdown hatalarını temizle
        if reply.startswith("```json"): reply = reply[7:]
        if reply.startswith("```"): reply = reply[3:]
        if reply.endswith("```"): reply = reply[:-3]
            
        parsed = json.loads(reply.strip())
        return parsed
    except Exception as e:
        print(f"[llm_filter_analyzer] Error parsing intent: {e}")
        return {}
