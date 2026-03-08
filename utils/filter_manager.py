import urllib.parse
from typing import Dict, List, Any, Optional

class RoomTypeMapper:
    """Oda tiplerini Sahibinden.com ID'lerine dönüştürür."""
    
    MAPPING = {
        "1+1": "38465",
        "2+1": "38470",
        "3+1": "38475",
        "4+1": "38480",
        "5+1": "38485",
        # İhtiyaç duyulursa diğer tipler eklenebilir
    }

    @classmethod
    def get_id(cls, room_type: str) -> Optional[str]:
        """Verilen oda tipi string'inin ID karşılığını döner (örn: '2+1' -> '38470')."""
        if not room_type:
            return None
        # Boşlukları temizle ve map içinde ara
        normalized = room_type.replace(" ", "")
        return cls.MAPPING.get(normalized)

class BuildingAgeMapper:
    """Bina yaşlarını Sahibinden.com ID'lerine dönüştürür."""
    
    # 0-10 yaş arası için gerekli tüm ID'ler
    AGE_0_10_IDS = [
        "40602",   # 0
        "40603",   # 1
        "40604",   # 2
        "40605",   # 3
        "1297865", # 4
        "1297863", # 5
        "40606"    # 6-10 arası
    ]

    @classmethod
    def get_ids_for_age_range(cls, age_desc: str) -> List[str]:
        """
        Bina yaşı açıklamasına göre ID listesi döner.
        Şu an için varsayılan olarak 0-10 yaş talep edildiğinde tüm ilgili ID'leri dönüyoruz.
        """
        if not age_desc:
            return []
            
        # Basit mantık: Eğer kullanıcı yeni/genç bina istiyorsa 0-10 yaş aralığını ver
        # İleride "5-10" gibi spesifik aralıklar için burası geliştirilebilir.
        # Kullanıcının talebi: "10 yıldan eski olmayan" -> 0,1,2,3,4,5,6-10
        ages = age_desc.lower()
        if any(x in ages for x in ["0", "yeni", "10", "genç", "sıfır"]):
             return cls.AGE_0_10_IDS
             
        return []

class UrlBuilder:
    """URL parametrelerini güvenli bir şekilde yönetir ve oluşturur."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def add_params(self, url: str, params: Dict[str, Any]) -> str:
        """Mevcut URL'e yeni parametreleri ekler veya günceller."""
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Yeni parametreleri ekle
        for key, value in params.items():
            if value is None:
                continue
            
            # Liste ise (örn: a812 birden fazla olabilir) extend et veya değiştir
            if isinstance(value, list):
                # Filtrelerde çoklu seçim (checkbox) mantığı olduğu için,
                # eğer bir filtre anahtarı (örn a812) gelirse, mevcutları silip yenilerini ekliyoruz.
                query_params[key] = value
            else:
                query_params[key] = [str(value)]
                
        # Query string'i oluştur
        # doseq=True, listeleri a=1&a=2 şeklinde encode eder
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        
        # Yeni URL'i oluştur
        new_url = urllib.parse.urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return new_url

class FilterProcessor:
    """LLM çıktısını işleyip URL parametrelerine dönüştürür."""
    
    @staticmethod
    def process(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM çıktısını (parsed_data) işleyip URL parametreleri dictionary'si döner."""
        params = {}
        
        # 1. Fiyat
        if parsed_data.get("price_max"):
            params["price_max"] = parsed_data["price_max"]
            
        # 2. Oda Sayısı (a20)
        room_type = parsed_data.get("rooms")
        room_id = RoomTypeMapper.get_id(room_type)
        if room_id:
            params["a20"] = room_id
            
        # 3. Bina Yaşı (a812)
        # Kullanıcının "10 yıldan eski olmayan" talebi üzerine,
        # eğer prompt içinde yaş belirtilmişse veya varsayılan isteniyorsa bu uygulanabilir.
        # Şu an LLM çıktısında "building_age" alanı varsa onu kullanırız,
        # yoksa ve kullanıcı genel bir kural istediyse manuel ekleyebiliriz.
        # Şimdilik LLM'den gelen veriyi baz alıyoruz.
        
        building_age_desc = parsed_data.get("building_age")
        if building_age_desc:
            age_ids = BuildingAgeMapper.get_ids_for_age_range(str(building_age_desc))
            if age_ids:
                params["a812"] = age_ids
        
        # EĞER KONUT FİLTRELERİ VARSA KATEGORİYİ ZORLA (16624 = Konut)
        # Oda sayısı (a20) veya Bina Yaşı (a812) varsa, Konut kategorisinde olmalıyız.
        if "a20" in params or "a812" in params:
             params["category"] = "16624"
        
        return params

if __name__ == "__main__":
    # Test
    builder = UrlBuilder("https://www.sahibinden.com")
    test_url = "https://www.sahibinden.com/kiralik?query_text=istanbul"
    
    print("Orijinal URL:", test_url)
    
    # Filtre testi
    llm_output = {
        "location": "İstanbul Şişli",
        "rooms": "2+1",
        "price_max": 30000,
        "building_age": "10" # Simüle edilmiş LLM çıktısı
    }
    
    filter_params = FilterProcessor.process(llm_output)
    print("Filtre Parametreleri:", filter_params)
    
    new_url = builder.add_params(test_url, filter_params)
    print("Yeni URL:", new_url)
