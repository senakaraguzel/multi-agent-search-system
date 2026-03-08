import re
import json
import os

class DataAgent:
    def __init__(self, raw_path="scraping_results.json", output_path="linkedin_scoring.json"):
        self.raw_path = raw_path
        self.output_path = output_path

    def normalize_location(self, raw_loc):
        if not raw_loc:
            return ""
        
        # 1. Temel temizlik: Yeni satır, fazladan boşluk ve çöp metinler
        loc = re.sub(r'\s+', ' ', raw_loc).strip()
        loc = re.sub(r'(\d+,?\s?TR\s?için\s?yol\s?tarifi\s?al.*|yol\s?tarifi\s?al.*)', '', loc, flags=re.I).strip()
        loc = loc.rstrip(',').strip()
        
        if not loc:
            return ""

        # 2. Şehir ve İlçe tespiti
        # LinkedIn formatı: "Mecidiyeköy, İstanbul" veya "İstanbul, İstanbul /Mecidiyeköy"
        # "İstanbul, İstanbul /Mecidiyeköy" -> Split ile ["İstanbul", " İstanbul /Mecidiyeköy"]
        parts = [p.strip() for p in loc.split(',') if p.strip()]
        
        # "İstanbul /Mecidiyeköy" gibi slashlı yapıları temizle
        refined_parts = []
        for p in parts:
            if '/' in p:
                refined_parts.extend([sp.strip() for sp in p.split('/') if sp.strip()])
            else:
                refined_parts.append(p)
        
        # "İstanbul, İstanbul" gibi tekrarları engelle
        final_parts = []
        for p in refined_parts:
            if p not in final_parts:
                final_parts.append(p)
        
        # 3. Son iki anlamlı parçayı al (İlçe, İl)
        if len(final_parts) >= 2:
            norm_loc = f"{final_parts[-2]}, {final_parts[-1]}"
        else:
            norm_loc = final_parts[0] if final_parts else ""

        # 4. Büyük/Küçük Harf Normalizasyonu (Proper Case)
        # ISTANBUL -> İstanbul, kKadıköy -> Kadıköy
        def title_case_tr(text):
            # Türkçe karakter duyarlı title case
            mapping = {"I": "ı", "İ": "i"}
            for upper, lower in mapping.items():
                text = text.replace(upper, lower)
            words = text.lower().split()
            title_words = []
            for w in words:
                if not w: continue
                # İlk harfi bul ve büyüt
                first = w[0].upper().replace("i", "İ").replace("ı", "I")
                title_words.append(first + w[1:])
            return " ".join(title_words)

        return title_case_tr(norm_loc)

    def parse_company_size(self, size_str):
        """
        '10,001+ employees' veya '51-200 employees' veya '1 bin-5 bin çalışan'
        gibi metinleri sayısal orta noktaya çevirir.
        """
        if not size_str or size_str == "Unknown":
            return 0
        try:
            # Türkçe "bin" -> "000" dönüşümü
            size_clean = size_str.lower().replace('.', '').replace(',', '')
            size_clean = size_clean.replace('bin', '000').replace('milyon', '000000')
            
            # Rakamları ve aralığı bul
            numbers = re.findall(r'[\d]+', size_clean)
            if not numbers:
                return 0
            
            # "10,001+" durumu
            if '+' in size_str:
                return int(numbers[0])
            
            # "51-200" durumu
            if len(numbers) >= 2:
                start = int(numbers[0])
                end = int(numbers[1])
                return (start + end) // 2
            
            return int(numbers[0])
        except:
            return 0

    def clean_followers(self, followers):
        if not followers:
            return 0
        try:
            # Sadece rakamları ve K/M/bin/milyon kısımlarını temizleyip sayıya çevir
            val_str = str(followers).lower()
            multiplier = 1
            if 'bin' in val_str or 'k' in val_str:
                multiplier = 1000
            elif 'milyon' in val_str or 'm' in val_str:
                multiplier = 1000000
                
            # Sadece rakamları (ve nokta/virgül) al
            clean_str = re.sub(r'[^\d]', '', val_str)
            if not clean_str:
                return 0
            
            return int(float(clean_str) * multiplier)
        except:
            return 0

    def transform_for_scoring(self, raw_data):
        result = []
        for company in raw_data:
            # 1. Lokasyonları normalize et ve tekilleştir
            raw_locations = company.get("locations", [])
            normalized_locations = []
            for l in raw_locations:
                n_l = self.normalize_location(l)
                if n_l and n_l not in normalized_locations:
                    normalized_locations.append(n_l)
            
            # 2. HQ'yu normalize et
            hq = company.get("headquarters", "")
            norm_hq = self.normalize_location(hq) if hq else ""
            
            # HQ'yu locations listesinin başına koy (eğer yoksa)
            if norm_hq and norm_hq not in normalized_locations:
                normalized_locations.insert(0, norm_hq)

            # 3. Founded normalizasyonu
            founded = company.get("founded", "").strip()
            if not founded or founded == "0":
                founded = "Unknown"

            # 4. Sayısal veriler
            raw_size = company.get("company_size", "Unknown")
            parsed_size = self.parse_company_size(raw_size)
            followers_count = self.clean_followers(company.get("followers"))

            item = {
                "name": company.get("name", "Unknown"),
                "industry": company.get("industry", "Unknown"),
                "company_size": raw_size,
                "company_size_numeric": parsed_size,
                "headquarters": norm_hq if norm_hq else "Unknown",
                "locations": normalized_locations,
                "employees_on_linkedin": company.get("employees_on_linkedin", "Unknown"),
                "followers": followers_count,
                "founded": founded
            }
            result.append(item)
        return result

    def run(self):
        if not os.path.exists(self.raw_path):
            print(f"HATA: {self.raw_path} bulunamadı.")
            return []

        with open(self.raw_path, "r", encoding="utf-8") as f:
            try:
                raw_data = json.load(f)
            except:
                print(f"HATA: {self.raw_path} okunurken JSON hatası oluştu.")
                return []

        scoring_ready = self.transform_for_scoring(raw_data)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(scoring_ready, f, ensure_ascii=False, indent=2)

        print(f"✓ {len(scoring_ready)} şirket verisi normalize edildi: {self.output_path}")
        return scoring_ready

if __name__ == "__main__":
    agent = DataAgent()
    agent.run()
