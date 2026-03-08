import requests

def fetch_data(query=None):
    """
    Google Maps API veya scraping ile veri çeker.
    query: arama terimi
    """
    if query is None:
        query = "restaurant"
    print(f"{query} verisi çekiliyor...")
    # Buraya API çağrısı veya scraping kodu gelecek
    return []

def process_data(data):
    """
    Çekilen veriyi işler.
    """
    print("Veriler işleniyor...")
    # Buraya veri işleme kodu gelecek
    return data
