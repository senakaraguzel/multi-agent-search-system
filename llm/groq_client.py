import os
from groq import Groq
from dotenv import load_dotenv


class GroqClient:

    def __init__(self, api_key=None):
        load_dotenv()

        if api_key is None:
            api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY bulunamadı. .env dosyasını kontrol et.")

        self.client = Groq(api_key=api_key)

        # Modeli burada merkezi olarak belirliyoruz
        self.model = "llama-3.3-70b-versatile"


    def generate(self, system_prompt: str, user_prompt: str):

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )

        return completion.choices[0].message.content

    def parse_query(self, user_prompt: str):
        """
        Kullanıcı girdisinden şehir, ilçe, oda sayısı ve ilan tipini ayıklar.
        """
        system_prompt = """
        Sen bir emlak asistanısın. Kullanıcının girdiği metinden aşağıdaki bilgileri JSON formatında çıkar:
        - city (Şehir - İl)
        - district (İlçe)
        - rooms (Oda Sayısı - örn: 2+1, 3+1)
        - listing_type (İlan Tipi - kiralık/satılık)
        - price_min (Minimum Fiyat - sayısal)
        - price_max (Maksimum Fiyat - sayısal)
        - building_age (Bina Yaşı - örn: 0, 1, 2, 3, 4, 5-10 arası, 11-15 arası, 16-20 arası)

        Önemli Notlar:
        - Eğer şehir belirtilmemişse "İstanbul" varsay.
        - Eğer ilçe belirtilmemişse null döndür.
        - Fiyatları sadece sayı olarak döndür (TL, bin, milyon yazma).
        Sadece JSON döndür, başka açıklama yapma.
        """
        
        response = self.generate(system_prompt, user_prompt)
        
        try:
            import json
            # Markdown code block varsa temizle
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            return json.loads(response)
        except Exception as e:
            print(f"JSON parse hatası: {e}")
            return None
