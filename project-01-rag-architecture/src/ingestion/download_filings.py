"""
Download SEC 10-K filings from EDGAR using the official submissions JSON API.
Uses data.sec.gov/submissions — no HTML scraping, no index.json needed.
The submissions JSON includes primaryDocument directly.
"""

import time
import json
import requests
from pathlib import Path
from typing import Optional

EDGAR_DATA = "https://data.sec.gov/submissions"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
RAW_DATA_DIR = Path(__file__).parents[2] / "data" / "raw"

HEADERS = {
    "User-Agent": "RAG-POC-Research dave@scheiderman.com",
    "Accept-Encoding": "gzip, deflate",
}

# CIKs zero-padded to 10 digits — stable EDGAR identifiers
TARGET_COMPANIES = [
    ("Apple_Inc", "0000320193"),
    ("Microsoft_Corp", "0000789019"),
    ("JPMorgan_Chase", "0000019617"),
    ("Goldman_Sachs", "0000886982"),
    ("Bank_of_America", "0000070858"),
    ("Citigroup", "0000831001"),
    ("Wells_Fargo", "0000072971"),
    ("Morgan_Stanley", "0000895421"),
    ("BlackRock", "0001364742"),
    ("Charles_Schwab", "0000316888"),
]


def get_submissions(cik: str) -> dict:
    url = f"{EDGAR_DATA}/CIK{cik}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def find_latest_10k(submissions: dict) -> Optional[dict]:
    """Find most recent 10-K from submissions JSON, using primaryDocument field."""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    acc_nos = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form in ("10-K", "10-K/A"):
            return {
                "accession_number": acc_nos[i],
                "filing_date": dates[i],
                "form": form,
                "primary_document": primary_docs[i] if i < len(primary_docs) else None,
            }
    return None


def build_doc_url(cik: str, accession_number: str, primary_document: str) -> str:
    cik_clean = cik.lstrip("0")
    acc_clean = accession_number.replace("-", "")
    return f"{EDGAR_ARCHIVES}/{cik_clean}/{acc_clean}/{primary_document}"


def download_filing(company: str, cik: str) -> Optional[Path]:
    out_dir = RAW_DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [{company}] Fetching submissions...")
    try:
        submissions = get_submissions(cik)
        time.sleep(0.15)

        filing = find_latest_10k(submissions)
        if not filing:
            print(f"  [{company}] No 10-K found in submissions")
            return None

        year = filing["filing_date"][:4]
        primary_doc = filing.get("primary_document")
        if not primary_doc:
            print(f"  [{company}] No primaryDocument in submissions data")
            return None

        print(f"  [{company}] 10-K filed {filing['filing_date']} — doc: {primary_doc}")

        doc_url = build_doc_url(cik, filing["accession_number"], primary_doc)

        # Determine file extension from primary document name
        ext = Path(primary_doc).suffix or ".htm"
        out_path = out_dir / f"{company}_{year}_10K{ext}"

        if out_path.exists():
            print(f"  [{company}] Already downloaded, skipping")
            return out_path

        print(f"  [{company}] Downloading {doc_url}")
        resp = requests.get(doc_url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        time.sleep(0.15)

        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                f.write(chunk)

        size_kb = out_path.stat().st_size // 1024
        print(f"  [{company}] OK — {out_path.name} ({size_kb} KB)")
        return out_path

    except Exception as e:
        print(f"  [{company}] ERROR: {e}")
        return None


def main():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    print(f"Downloading {len(TARGET_COMPANIES)} 10-K filings\n")

    for company, cik in TARGET_COMPANIES:
        path = download_filing(company, cik)
        results.append({
            "company": company,
            "cik": cik,
            "path": str(path) if path else None,
        })

    manifest_path = RAW_DATA_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)

    successful = sum(1 for r in results if r["path"])
    print(f"\nDone: {successful}/{len(TARGET_COMPANIES)} downloaded")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
