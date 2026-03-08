import os
import json
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

class LLMAgent:
    def __init__(self):
        self.agent_name = "llm_agent"
        # Load environment variables (e.g., AZURE_OPENAI_KEY)
        load_dotenv()
        
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_VERSION", "2024-12-01-preview")
        self.model = os.getenv("AZURE_OPENAI_MODEL", "o4-mini")
        
        if not self.api_key or not self.endpoint:
            print("[LLMAgent] UYARI: AZURE_OPENAI ortam değişkenleri bulunamadı. LLM çalışmayacaktır.")
            self.client = None
        else:
            self.client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version
            )

    async def analyze_company_and_school(self, job_post, cv):
        """
        OpenAI (GPT) kullanarak firmanın global mi lokal mi olduğunu, 
        firmanın ülkesini ve okulun bulunduğu ülkeyi belirler.
        """
        if not self.client:
            return {
                "status": "error",
                "message": "OpenAI API Key eksik",
                "global_score": 0.0,
                "employer_country": "Unknown",
                "school_country": "Unknown"
            }

        employer_name = job_post.get("employer", "Unknown")
        target_school = cv.get("education", [{}])[0].get("school_name", "Unknown")

        system_prompt = (
            "You are an expert HR and market analyst. You need to analyze the provided job post and CV details. "
            "1. Determine the global impact of the employer. Provide a 'global_score' as a float between 0.0 and 1.0.\n"
            "   (For example, Google, Microsoft, Meta -> 1.0. Large national leader (e.g. Ford Otosan) -> 0.6. Mid-size national (e.g. Aselsan) -> 0.4. Small local firm -> 0.2)\n"
            "2. Determine the primary headquarters country of the employer. Represent as a 2-letter ISO country code (e.g. 'US', 'TR', 'GB') in 'employer_country'.\n"
            "3. Determine the country where the candidate's university is primarily located. Represent as a 2-letter ISO country code in 'school_country'.\n"
            "If you are not sure about the country, make your best educated guess based on the name.\n"
            "Return ONLY a valid JSON object with the exact keys: 'global_score', 'employer_country', 'school_country'."
        )

        user_content = json.dumps({
            "job_post": job_post,
            "candidate_school": target_school
        }, ensure_ascii=False)

        try:
            print(f"[{self.agent_name}] LLM'e Soruluyor: Firma={employer_name}, Okul={target_school}...")
            # Not: o4-mini format kısıtlamalarına takılmamak için response_format Json değil düz prompt içi kontrol uygulanıyor
            clean_system_prompt = system_prompt + "\nDO EXACTLY AS REQUESTED AND OUTPUT ONLY RAW JSON."
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": f"{clean_system_prompt}\n\n{user_content}"} # Some reasoning models only allow user role
                ]
            )
            
            result_text = response.choices[0].message.content
            # Markdown block'ları (```json ... ```) temizle
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            result_json = json.loads(result_text)
            
            return {
                "status": "success",
                "global_score": float(result_json.get("global_score", 0.0)),
                "employer_country": result_json.get("employer_country", "Unknown"),
                "school_country": result_json.get("school_country", "Unknown")
            }
            
        except Exception as e:
            print(f"[{self.agent_name}] OpenAI Hata: {str(e)}")
            # Fallback
            return {
                "status": "error",
                "message": str(e),
                "global_score": 0.0,
                "employer_country": "Unknown",
                "school_country": "Unknown"
            }
