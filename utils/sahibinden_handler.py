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
    }

    @classmethod
    def get_id(cls, room_type: str) -> Optional[str]:
        if not room_type: return None
        return cls.MAPPING.get(room_type.replace(" ", ""))

class BuildingAgeMapper:
    """Bina yaşlarını Sahibinden.com ID'lerine dönüştürür."""
    AGE_0_10_IDS = ["40602","40603","40604","40605","1297865","1297863","40606"]

    @classmethod
    def get_ids_for_age_range(cls, age_desc: str) -> List[str]:
        if not age_desc: return []
        ages = age_desc.lower()
        if any(x in ages for x in ["0", "yeni", "10", "genç", "sıfır"]):
             return cls.AGE_0_10_IDS
        return []

class SahibindenHandler:
    """
    Sahibinden'e özel arama (query) oluşturma ve LLM tabanlı filtreleri 
    URL parametresi haline getirme sınıfıdır.
    """
    BASE_URL = "https://www.sahibinden.com"

    @classmethod
    def build_search_url(cls, search_data: dict) -> str:
        """
        LLM'den gelen parsed_data içerisinden genel arama metnini çıkarıp
        filtreleri Sahibinden URL parametreleri olarak bind eder.
        """
        parsed_data = search_data.get("parsed_data", {})
        query = parsed_data.get("query", search_data.get("original_query", ""))
        
        # Eğer domain 'araba'/'vasita' veya 'emlak' ise buna göre keyword eklenebilir.
        # Biz doğrudan user query veya LLM query string'ini alıyoruz.
        
        search_url = f"{cls.BASE_URL}/arama?query_text={urllib.parse.quote_plus(query)}"
        
        # Filtreleri uygula
        filters = parsed_data.get("filters", {})
        if filters:
             return cls._add_params(search_url, cls._process_filters(filters))
        
        # Filtre yoksa ham query'i döndür
        return search_url

    @classmethod
    def _process_filters(cls, filters: Dict[str, Any]) -> Dict[str, Any]:
        """LLM JSON filtlerini (price_max, rooms) Sahibinden GET parametrelerine çevirir (a20, a812 vb.)"""
        params = {}
        
        # Fiyat
        if filters.get("price_max"):
            params["price_max"] = filters["price_max"]
            
        # Oda Sayısı
        room_id = RoomTypeMapper.get_id(filters.get("rooms"))
        if room_id:
            params["a20"] = room_id
            
        # Bina Yaşı
        age_ids = BuildingAgeMapper.get_ids_for_age_range(str(filters.get("building_age", "")))
        if age_ids:
            params["a812"] = age_ids
        
        # Konut Kategori Zorlaması (Oda/Yaş varsa bu bir evdir)
        if "a20" in params or "a812" in params:
             params["category"] = "16624"
             
        return params

    @classmethod
    def _add_params(cls, url: str, params: Dict[str, Any]) -> str:
        """urllib kullanarak URL'ye güvenli GET parametresi ekler."""
        if not params: return url
        
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        for key, value in params.items():
            if value is None: continue
            if isinstance(value, list):
                query_params[key] = value
            else:
                query_params[key] = [str(value)]
                
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        return urllib.parse.urlunparse((
            parsed_url.scheme, parsed_url.netloc, parsed_url.path,
            parsed_url.params, new_query, parsed_url.fragment
        ))
