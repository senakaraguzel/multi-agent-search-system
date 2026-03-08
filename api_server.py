import sys
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LISTING_FILE = os.path.join(BASE_DIR, "listing_details.json")
METADATA_FILE = os.path.join(BASE_DIR, "search_metadata.json")

# Domain → varsayılan 7 header (main.py çalışmadan önce fallback olarak)
DEFAULT_HEADERS = {
    "emlak": [
        {"key": "title",         "label": "Başlık"},
        {"key": "price",         "label": "Fiyat / Kira"},
        {"key": "location",      "label": "İl / İlçe"},
        {"key": "oda_sayisi",    "label": "Oda Sayısı"},
        {"key": "m2_net",        "label": "m² (Net)"},
        {"key": "bina_yasi",     "label": "Bina Yaşı"},
        {"key": "bulundugu_kat", "label": "Bulunduğu Kat"},
        {"key": "url",           "label": "URL"},
    ],
    "araba": [
        {"key": "title",       "label": "Başlık"},
        {"key": "price",       "label": "Fiyat"},
        {"key": "marka",       "label": "Marka"},
        {"key": "seri",        "label": "Seri"},
        {"key": "model",       "label": "Model"},
        {"key": "yil",         "label": "Yıl"},
        {"key": "yakit_tipi",  "label": "Yakıt Tipi"},
        {"key": "vites",       "label": "Vites"},
        {"key": "arac_durumu", "label": "Araç Durumu"},
        {"key": "km",          "label": "KM"},
        {"key": "url",         "label": "URL"},
    ],
}


@app.post("/search")
def run_agents(data: dict):

    query = data.get("query", "").strip()

    if not query:
        return {"status": "error", "message": "Sorgu boş olamaz", "data": [], "headers": []}

    print(f"\n[API] Sorgu alındı: {query}")

    try:
        # PYTHONIOENCODING=utf-8 → Windows'ta Türkçe çıktının doğru encode edilmesi için
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        result = subprocess.run(
            [sys.executable, "-X", "utf8", "main.py", query],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        print("[API] main.py stdout:", result.stdout[-500:] if result.stdout else "")
        if result.returncode != 0:
            print("[API] main.py stderr:", result.stderr[-300:] if result.stderr else "")

    except Exception as e:
        print(f"[API] subprocess hatası: {e}")
        return {"status": "error", "message": str(e), "data": [], "headers": []}

    # search_metadata.json oku (domain + headers)
    headers = []
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
            headers = meta.get("headers", [])
        except Exception as e:
            print(f"[API] Metadata okuma hatası: {e}")

    # listing_details.json oku
    if os.path.exists(LISTING_FILE):
        try:
            with open(LISTING_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
            return {
                "status": "success",
                "data": results,
                "headers": headers
            }
        except Exception as e:
            print(f"[API] JSON okuma hatası: {e}")
            return {"status": "error", "message": "Veri dosyası okunamadı", "data": [], "headers": []}

    return {"status": "error", "message": "listing_details.json bulunamadı", "data": [], "headers": []}