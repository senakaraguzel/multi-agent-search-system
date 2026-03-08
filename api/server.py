import sys
import os
import json
import subprocess
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI(title="Genarion Searcher API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proje kök dizini (api/ klasörünün bir üstü)
ROOT_DIR     = Path(__file__).parent.parent
DATA_DIR     = ROOT_DIR / "data"
DETAILS_FILE = DATA_DIR / "listing_details.json"
URLS_FILE    = DATA_DIR / "listing_urls.json"
MAIN_PY      = ROOT_DIR / "main.py"

# Global scraper durumu
scraper_state = {
    "running"      : False,
    "query"        : "",
    "urls_found"   : 0,
    "results_count": 0,
    "error"        : None,
    "phase"        : "idle",   # idle | searching | extracting | done | error
}


class SearchRequest(BaseModel):
    query      : str
    max_scrolls: int = 30


# ─────────────────────────────────────────────────────────────────────────────
# Scraper Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_scraper(query: str, max_scrolls: int):
    """main.py'yi alt süreç olarak çalıştırır ve stdout'u izler."""
    global scraper_state

    # Yeni arama başladığında eski sonuçları temizle
    if DETAILS_FILE.exists():
        DETAILS_FILE.unlink()
    if URLS_FILE.exists():
        URLS_FILE.unlink()

    scraper_state.update({
        "running"      : True,
        "query"        : query,
        "error"        : None,
        "phase"        : "searching",
        "urls_found"   : 0,
        "results_count": 0,
    })

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        proc = subprocess.Popen(
            [sys.executable, str(MAIN_PY), query, str(max_scrolls)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT_DIR),
            env=env,
        )

        # stdout'u satır satır oku ve durumu güncelle
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            print(f"[SCRAPER] {line}", flush=True)

            if line.startswith("PHASE:"):
                scraper_state["phase"] = line.split(":", 1)[1]
            elif line.startswith("URLS_FOUND:"):
                scraper_state["urls_found"] = int(line.split(":", 1)[1])
            elif line.startswith("RESULTS_COUNT:"):
                scraper_state["results_count"] = int(line.split(":", 1)[1])
            elif line.startswith("ERROR:"):
                scraper_state["error"] = line.split(":", 1)[1]

        proc.wait()

        if proc.returncode != 0:
            stderr_out = proc.stderr.read()
            if not scraper_state["error"]:
                scraper_state["error"] = stderr_out[:500]
            scraper_state["phase"] = "error"
        else:
            scraper_state["phase"] = "done"

    except Exception as e:
        scraper_state["error"] = str(e)
        scraper_state["phase"] = "error"
    finally:
        scraper_state["running"] = False


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Genarion Searcher API v2 is running"}


@app.post("/api/search")
def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    """Scraper'ı arka planda başlatır."""
    if scraper_state["running"]:
        raise HTTPException(status_code=409, detail="Scraper zaten çalışıyor.")

    background_tasks.add_task(run_scraper, req.query, req.max_scrolls)
    return {"message": f"'{req.query}' için arama başlatıldı.", "query": req.query}


@app.get("/api/status")
def get_status():
    """Anlık scraper durumunu döner."""
    return {
        "running"      : scraper_state["running"],
        "query"        : scraper_state["query"],
        "phase"        : scraper_state["phase"],
        "urls_found"   : scraper_state["urls_found"],
        "results_count": scraper_state["results_count"],
        "error"        : scraper_state["error"],
    }


@app.get("/api/results")
def get_results():
    """listing_details.json içeriğini döner."""
    if not DETAILS_FILE.exists():
        return {"results": [], "count": 0}

    try:
        with open(DETAILS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"results": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya okunamadı: {e}")


@app.delete("/api/results")
def clear_results():
    """Sonuçları ve URL listesini temizler, durumu sıfırlar."""
    if DETAILS_FILE.exists():
        DETAILS_FILE.unlink()
    if URLS_FILE.exists():
        URLS_FILE.unlink()

    scraper_state.update({
        "running": False, "query": "", "urls_found": 0,
        "results_count": 0, "error": None, "phase": "idle",
    })
    return {"message": "Sonuçlar temizlendi."}
