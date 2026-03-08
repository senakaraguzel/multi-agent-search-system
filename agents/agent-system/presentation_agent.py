"""
Presentation Agent (Agent 7) - v2
FastAPI backend — result.json okur, LLM özet üretir, pipeline tetikler.
"""

import json, os, time, subprocess, sys
from pathlib import Path
from openai import AzureOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    raise RuntimeError("pip install fastapi uvicorn")

BASE_DIR    = Path(__file__).parent.parent
RESULT_JSON = BASE_DIR / "data" / "result.json"
SEARCH_JSON = BASE_DIR / "data" / "search.json"
PYTHON_EXE  = str(sys.executable)

_cache  = {"data": None, "mtime": 0.0, "summary": ""}
_status = {"running": False, "error": ""}

app = FastAPI(title="Presentation Agent", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── LLM ──────────────────────────────────────────────────────────────────────
def _llm_summary(result: dict) -> str:
    try:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://genarion-deep-search-source-1.openai.azure.com/")
        client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            azure_endpoint=endpoint,
            api_version="2024-12-01-preview",
        )
        prompt = (
            "You are a UI assistant. Summarize the following JSON search result in 2-3 sentences. "
            "Use ONLY the data in the JSON. Be concise, factual, and include numbers where available. Write in Turkish.:\n\n"
            + json.dumps(result, ensure_ascii=False)[:3000]
        )
        r = client.chat.completions.create(
            model="o4-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"[PresentationAgent] LLM hata: {e}")
        return ""

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _load_result() -> dict:
    try:
        mtime = RESULT_JSON.stat().st_mtime
    except FileNotFoundError:
        return {}
    if mtime != _cache["mtime"]:
        with open(RESULT_JSON, encoding="utf-8") as f:
            data = json.load(f)
        _cache.update({"data": data, "mtime": mtime, "summary": _llm_summary(data)})
    return _cache["data"] or {}

def _query_type() -> str:
    try:
        with open(SEARCH_JSON, encoding="utf-8") as f:
            s = json.load(f)
        p = s.get("pipeline", "")
        if "Lokal"     in p: return "local"
        if "Kategorik" in p: return "categoric"
        if "Platform"  in p: return "platform"
        return "specific"
    except Exception:
        return "generic"

def _make_response(extra=None):
    data = _load_result()
    r = {
        "raw_result": data,
        "llm_summary": _cache["summary"],
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_cache["mtime"])),
        "query_type": _query_type(),
        "search_running": _status["running"],
        "error": _status["error"],
    }
    if extra:
        r.update(extra)
    return r

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.get("/api/result")
def get_result():
    return _make_response()

class SearchReq(BaseModel):
    query: str

@app.post("/api/search")
def run_search(req: SearchReq):
    if _status["running"]:
        raise HTTPException(409, "Arama zaten çalışıyor.")
    if not req.query.strip():
        raise HTTPException(400, "Sorgu boş olamaz.")

    submitted_query = req.query.strip()
    _status["running"] = True
    _status["error"]   = ""
    
    # İşleme başlamadan önceki dosya mtime'ı
    start_mtime = 0.0
    try:
        start_mtime = RESULT_JSON.stat().st_mtime
    except FileNotFoundError:
        pass

    try:
        # Binary modda çalıştır — Windows'ta encoding sorunu olmaması için
        proc = subprocess.run(
            [PYTHON_EXE, "-m", "main"],
            input=(submitted_query + "\n").encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR), timeout=600,
        )
        # Çıktıyı utf-8 ile decode et, sorunlu karakterleri yoksay
        stdout_text = proc.stdout.decode("utf-8", errors="replace")
        stderr_text = proc.stderr.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            _status["error"] = stderr_text[-400:]
    except subprocess.TimeoutExpired:
        _status["error"] = "Zaman aşımı (600s)."
    except Exception as e:
        _status["error"] = str(e)
    finally:
        _status["running"] = False

    # Pipeline bittikten sonra mtime kontrolü — dosya değişmiş mi?
    end_mtime = 0.0
    try:
        end_mtime = RESULT_JSON.stat().st_mtime
    except FileNotFoundError:
        pass

    is_stale = (end_mtime <= start_mtime)

    # Veriyi zorla oku (cache sıfırlayarak)
    _cache["mtime"] = 0.0
    data = _load_result()

    r = {
        "raw_result":       data,
        "llm_summary":      _cache["summary"],
        "last_updated":     time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_cache["mtime"])),
        "query_type":       _query_type(),
        "search_running":   False,
        "error":            _status["error"],
        "submitted_query":  submitted_query,
        "stale_result":     is_stale,
    }
    return r



@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/resume")
def resume_from_scrape():
    """Agent 1-2-3'ü atlayarak sadece Scraper + Filtering çalıştırır."""
    if _status["running"]:
        raise HTTPException(409, "Zaten bir işlem çalışıyor.")

    _status["running"] = True
    _status["error"] = ""

    start_mtime = 0.0
    try:
        start_mtime = RESULT_JSON.stat().st_mtime
    except FileNotFoundError:
        pass

    try:
        # run_from_scrape.py varsa onu çalıştır, yoksa inline olarak çalıştır
        resume_script = BASE_DIR / "run_from_scrape.py"
        if resume_script.exists():
            proc = subprocess.run(
                [PYTHON_EXE, str(resume_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(BASE_DIR), timeout=600,
            )
        else:
            # Inline fallback
            proc = subprocess.run(
                [PYTHON_EXE, "-c",
                 "import asyncio; from agents.scraper_agent import ScraperAgent; asyncio.run(ScraperAgent().execute()); from agents.filtering_agent import FilteringAgent; FilteringAgent().execute()"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(BASE_DIR), timeout=600,
            )
        stderr_text = proc.stderr.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            _status["error"] = stderr_text[-400:]
    except subprocess.TimeoutExpired:
        _status["error"] = "Zaman aşımı (600s)."
    except Exception as e:
        _status["error"] = str(e)
    finally:
        _status["running"] = False

    _cache["mtime"] = 0.0
    data = _load_result()

    end_mtime = 0.0
    try:
        end_mtime = RESULT_JSON.stat().st_mtime
    except FileNotFoundError:
        pass

    return {
        "raw_result": data,
        "llm_summary": _cache["summary"],
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_cache["mtime"])),
        "query_type": _query_type(),
        "search_running": False,
        "error": _status["error"],
        "stale_result": end_mtime <= start_mtime,
    }

if __name__ == "__main__":
    print("[PresentationAgent] http://localhost:8000  |  UI: http://localhost:5173")
    uvicorn.run("agents.presentation_agent:app", host="0.0.0.0", port=8000, reload=False)
