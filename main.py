import asyncio
import json
import os
from datetime import datetime
from agents.url_agent import URLAgent
from agents.validation_agent import ValidationAgent
from agents.scraping_agent import ScrapingAgent
from agents.data_agent import DataAgent
from agents.scoring_agent import ScoringAgent

# ======================================================
# CONFIGURATION & CONSTANTS
# ======================================================
INPUT_DATA_FILE = "input_data.json"
URL_CANDIDATES_FILE = "url_candidates.json"
VALIDATED_COMPANIES_FILE = "validated_companies.json"
SCRAPED_COMPANIES_FILE = "scraped_companies.json"
COMPANY_FEATURES_FILE = "company_features.json"
SCORING_RESULTS_FILE = "scoring_results.json"
RECRUITERS_DATA_FILE = "recruiters_data.json"

# ======================================================
# UTILITIES
# ======================================================
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return [] if path.endswith('.json') else {}
    return [] if path.endswith('.json') else {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_to_json_list(path, candidate_id, key, item):
    data = load_json(path)
    if not isinstance(data, list): data = []
    
    found = False
    for entry in data:
        if isinstance(entry, dict) and entry.get("candidate_id") == candidate_id:
            if key in entry and isinstance(entry[key], list):
                item_name = item.get("name", "").lower() if isinstance(item, dict) else ""
                if not any(isinstance(x, dict) and x.get("name", "").lower() == item_name for x in entry[key]) if item_name else item not in entry[key]:
                    entry[key].append(item)
            else:
                entry[key] = [item]
            found = True
            break
    
    if not found:
        data.append({"candidate_id": candidate_id, key: [item]})
    save_json(path, data)

def parse_ym(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m")
    except:
        return datetime.now()

def compute_experience_meta(experiences: list) -> list:
    enriched = []
    for exp in experiences:
        if "months" in exp and "order" in exp:
            enriched.append(exp)
            continue
            
        start_date = exp.get("start_date")
        end_date = exp.get("end_date")
        if start_date and end_date:
            start = parse_ym(start_date)
            end = parse_ym(end_date)
            months = (end.year - start.year) * 12 + (end.month - start.month)
            enriched.append({**exp, "months": max(1, months), "_end_dt": end})
        else:
            enriched.append({**exp, "months": exp.get("months", 12), "_end_dt": datetime.now()})

    if any("_end_dt" in e for e in enriched):
        enriched.sort(key=lambda x: x.get("_end_dt", datetime.now()), reverse=True)
        for i, exp in enumerate(enriched):
            if "order" not in exp: exp["order"] = i + 1
            if "_end_dt" in exp: del exp["_end_dt"]
    return enriched

# ======================================================
# CORE LOGIC
# ======================================================
async def collect_linkedin_data(candidate, url_agent, val_agent, scrap_agent):
    candidate_id = candidate["id"]
    experiences = candidate["experiences"]
    
    for exp in experiences[:3]:
        company = exp["company"]
        city = exp["city"]

        existing_scraped = load_json(SCRAPED_COMPANIES_FILE)
        cand_scraped = next((c for c in existing_scraped if isinstance(c, dict) and c.get("candidate_id") == candidate_id), None)
        if cand_scraped and any(s.get("name", "").lower() == company.lower() for s in cand_scraped.get("companies", [])):
            print(f"  ⏭ {company} already scraped, skipping.")
            continue

        print(f"\n  🔍 Searching for {company} ({city})...")
        search_result = await url_agent.run(company, city)
        candidates_raw = search_result.get("candidates", [])
        
        url_candidate_record = {
            "company_name": company,
            "search_query": f"linkedin {company} {city} company page",
            "candidates": [{"url": u, "title": "LinkedIn Company", "source": "linkedin"} for u in candidates_raw]
        }
        append_to_json_list(URL_CANDIDATES_FILE, candidate_id, "companies", url_candidate_record)

        if not candidates_raw:
            print(f"  ⚠ No candidates found on Google for: {company}")
            continue

        val = await val_agent.run(company, candidates_raw, city, exp.get("role", ""))
        validated_record = {
            "company_name": company,
            "linkedin_url": val.get("linkedin_url"),
            "is_valid": val.get("is_valid", False),
            "confidence": val.get("confidence", 0.0)
        }
        append_to_json_list(VALIDATED_COMPANIES_FILE, candidate_id, "validated_companies", validated_record)

        if not val.get("is_valid"):
            print(f"  ❌ Validation failed: {company} - {val.get('reason', 'No reason provided')}")
            continue

        url = val["linkedin_url"]
        print(f"  ✅ Validated: {url}")

        raw_scraped = await scrap_agent.run(url)
        if not raw_scraped.get("error"):
            append_to_json_list(SCRAPED_COMPANIES_FILE, candidate_id, "companies", raw_scraped)
            print(f"  📦 Data scraped: {raw_scraped.get('name')}")

        print("  ⏳ Waiting 5 seconds...")
        await asyncio.sleep(5)

async def main():
    print("\n" + "=" * 70)
    print("   COMPANY SCORING PIPELINE")
    print("=" * 70)

    # Initialize data
    input_data = load_json(INPUT_DATA_FILE)
    if not input_data:
        print(f"❌ Error: {INPUT_DATA_FILE} not found or empty.")
        return

    # Reset output files for a fresh run
    for f in [URL_CANDIDATES_FILE, VALIDATED_COMPANIES_FILE, SCRAPED_COMPANIES_FILE, COMPANY_FEATURES_FILE, SCORING_RESULTS_FILE, RECRUITERS_DATA_FILE]:
        save_json(f, [])
        print(f"[*] {f} cleared.")

    # Initialize Agents
    url_agent = URLAgent(headless=False)
    val_agent = ValidationAgent(headless=False)
    scrap_agent = ScrapingAgent(headless=False)
    data_agent = DataAgent(raw_path=SCRAPED_COMPANIES_FILE, output_path=COMPANY_FEATURES_FILE)
    score_agent = ScoringAgent()

    # PHASE 1: Recruiter Data
    print("\n[*] Collecting recruiter data...")
    recruiters_raw = []
    for job in input_data.get("job_listings", []):
        if not any(r.get("name", "").lower() == job["company"].lower() for r in recruiters_raw):
            print(f"  🌐 Scraping {job['company']}...")
            raw_scraped = await scrap_agent.run(job["linkedin"])
            if not raw_scraped.get("error"):
                recruiters_raw.append(raw_scraped)
    save_json(RECRUITERS_DATA_FILE, recruiters_raw)
    recruiters_features = data_agent.transform_for_scoring(recruiters_raw)
    
    job_index = {j["id"]: j for j in input_data.get("job_listings", [])}

    # PHASE 2: Candidate Processing
    for candidate in input_data.get("candidates", []):
        job = job_index.get(candidate["job_id"])
        if not job: continue
        
        candidate_id = candidate["id"]
        print(f"\n\n{'='*70}\n  CANDIDATE: {candidate['name']}\n  TARGET: {job['position']} @ {job['company']}\n{'='*70}")

        # Recruiter context for scoring
        job_company_feat = next((r for r in recruiters_features if job["company"].lower() in r.get("name", "").lower() or r.get("name", "").lower() in job["company"].lower()), {})
        job_info = {
            "name": job["company"],
            "position": job["position"],
            "industry": job_company_feat.get("industry", "Unknown"),
            "company_size_numeric": job_company_feat.get("company_size_numeric", 0),
            "followers": job_company_feat.get("followers", 0),
            "required_experience_months": job.get("required_experience_months", 24)
        }

        # 1-3. Data Collection
        await collect_linkedin_data(candidate, url_agent, val_agent, scrap_agent)

        # 4. Normalization
        print(f"\n  🔧 Normalizing data...")
        raw_scraped_data = load_json(SCRAPED_COMPANIES_FILE)
        candidate_raw = next((item for item in raw_scraped_data if isinstance(item, dict) and item.get("candidate_id") == candidate_id), None)
        
        if candidate_raw:
            normalized_list = data_agent.transform_for_scoring(candidate_raw.get("companies", []))
            features_all = load_json(COMPANY_FEATURES_FILE)
            entry = {"candidate_id": candidate_id, "companies": normalized_list}
            idx = next((i for i, x in enumerate(features_all) if x.get("candidate_id") == candidate_id), -1)
            if idx > -1: features_all[idx] = entry
            else: features_all.append(entry)
            save_json(COMPANY_FEATURES_FILE, features_all)

        # 5. Scoring
        print(f"\n  🏅 Calculating scores...")
        features_all = load_json(COMPANY_FEATURES_FILE)
        candidate_features = next((item for item in features_all if item.get("candidate_id") == candidate_id), None)
        
        if candidate_features:
            enriched_exp = compute_experience_meta(candidate["experiences"])
            score_res = score_agent.run(job_info=job_info, experiences=enriched_exp, company_data=candidate_features.get("companies", []), top_n=3)
            
            final_record = {
                "candidate_id": candidate_id,
                "job_id": job["id"],
                "job_info": job_info,
                "scores": score_res["company_scores"],
                "final_score": score_res["final_score"]
            }
            
            scores_all = load_json(SCORING_RESULTS_FILE)
            idx = next((i for i, x in enumerate(scores_all) if x.get("candidate_id") == candidate_id), -1)
            if idx > -1: scores_all[idx] = final_record
            else: scores_all.append(final_record)
            save_json(SCORING_RESULTS_FILE, scores_all)
            print(f"\n  🏆 {candidate['name']} → {score_res['final_score']} / 20")

    print(f"\n{'='*70}\n      PIPELINE COMPLETED\n{'='*70}")

if __name__ == "__main__":
    asyncio.run(main())
