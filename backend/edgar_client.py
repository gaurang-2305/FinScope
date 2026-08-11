"""
SEC EDGAR client — look up companies by ticker and download 10-K filings.

Respects SEC's fair-access policy:
  - Max 10 requests/second
  - User-Agent header with a real contact email
"""
import io
import time
import logging
from typing import Optional

import httpx

from config import get_settings

logger = logging.getLogger("finscope.edgar")

SEC_BASE = "https://efts.sec.gov/LATEST"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

# Rate limiter: track last request time
_last_request_time = 0.0
_MIN_INTERVAL = 0.12  # ~8 requests/second to stay under SEC's 10/s limit


def _sec_headers() -> dict:
    settings = get_settings()
    email = settings.sec_user_agent_email or "finscope@example.com"
    return {
        "User-Agent": f"FinScope/1.0 ({email})",
        "Accept": "application/json",
    }


def _rate_limited_get(url: str, **kwargs) -> httpx.Response:
    """Make an HTTP GET respecting SEC rate limits."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, headers=_sec_headers(), **kwargs)

    _last_request_time = time.time()
    return response


def lookup_cik(ticker: str) -> Optional[str]:
    """Look up a company's CIK number by ticker symbol."""
    url = f"{SEC_BASE}/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
    try:
        resp = _rate_limited_get(url)
        if resp.status_code != 200:
            # Try the company tickers JSON instead
            return _lookup_cik_from_tickers(ticker)
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        if hits:
            # Extract CIK from the first hit
            source = hits[0].get("_source", {})
            cik = source.get("entity_id") or source.get("ciks", [None])[0]
            if cik:
                return str(cik).lstrip("0")
    except Exception as e:
        logger.warning("EDGAR search failed for %s: %s", ticker, e)

    return _lookup_cik_from_tickers(ticker)


def _lookup_cik_from_tickers(ticker: str) -> Optional[str]:
    """Fallback CIK lookup using SEC's company_tickers.json."""
    try:
        resp = _rate_limited_get("https://www.sec.gov/files/company_tickers.json")
        if resp.status_code != 200:
            return None
        data = resp.json()
        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker") == ticker_upper:
                return str(entry["cik_str"])
    except Exception as e:
        logger.warning("Ticker lookup failed: %s", e)
    return None


def get_latest_10k_url(cik: str) -> Optional[dict]:
    """Get the URL of the latest 10-K filing for a given CIK.

    Returns dict with keys: accession_number, filing_date, document_url
    """
    # Pad CIK to 10 digits for SEC's submissions API
    cik_padded = cik.zfill(10)

    try:
        resp = _rate_limited_get(f"{SEC_SUBMISSIONS}/CIK{cik_padded}.json")
        if resp.status_code != 200:
            logger.error("Failed to get submissions for CIK %s: %d", cik, resp.status_code)
            return None

        data = resp.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])

        # Find the most recent 10-K
        for i, form in enumerate(forms):
            if form == "10-K":
                accession = accessions[i].replace("-", "")
                doc = primary_docs[i]
                return {
                    "accession_number": accessions[i],
                    "filing_date": dates[i],
                    "document_url": f"{SEC_ARCHIVES}/{cik}/{accession}/{doc}",
                    "company_name": data.get("name", ""),
                }

        logger.warning("No 10-K found for CIK %s", cik)
        return None

    except Exception as e:
        logger.error("Failed to get 10-K for CIK %s: %s", cik, e)
        return None


def download_filing(url: str) -> Optional[bytes]:
    """Download a filing document. Returns raw bytes."""
    try:
        resp = _rate_limited_get(url)
        if resp.status_code == 200:
            return resp.content
        logger.error("Failed to download %s: %d", url, resp.status_code)
        return None
    except Exception as e:
        logger.error("Download failed for %s: %s", url, e)
        return None


def fetch_10k_for_ticker(ticker: str) -> Optional[dict]:
    """Main entry point: look up a ticker and download its latest 10-K.

    Returns dict with keys: content (bytes), filing_info (dict), or None on failure.
    """
    logger.info("Looking up EDGAR filings for ticker: %s", ticker)

    cik = lookup_cik(ticker)
    if not cik:
        logger.warning("Could not find CIK for ticker: %s", ticker)
        return None

    filing_info = get_latest_10k_url(cik)
    if not filing_info:
        return None

    logger.info(
        "Found 10-K for %s: %s (filed %s)",
        ticker, filing_info.get("company_name", ""), filing_info.get("filing_date", ""),
    )

    content = download_filing(filing_info["document_url"])
    if not content:
        return None

    return {
        "content": content,
        "filing_info": filing_info,
    }
