from llm.groq_client import GroqClient

SYSTEM_PROMPT = """
You are a domain classification agent.

Classify the user query into one of these:

- emlak
- araba
- arsa
- is_makinesi
- unknown

Return ONLY the domain name.
"""

class DomainClassifier:

    def __init__(self):
        self.llm = GroqClient()

    def classify(self, query: str):
        response = self.llm.generate(SYSTEM_PROMPT, query)
        return response.strip()
