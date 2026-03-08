import os
from openai import AzureOpenAI

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
