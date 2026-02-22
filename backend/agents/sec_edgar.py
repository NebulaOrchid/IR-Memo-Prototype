"""Earnings call transcript agent with 5-tier fallback strategy.

Tier 1: SEC EDGAR EFTS full-text search
Tier 2: SEC EDGAR Submissions API + exhibit crawl
Tier 3: Financial Modeling Prep (FMP) API
Tier 4: DuckDuckGo web search + page scraping
Tier 5: Local transcript file fallback (bundled demo data)
"""
import asyncio
import logging
import re

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

from config import (
    SEC_EDGAR_USER_AGENT,
    COMPANY_CIKS,
    FMP_API_KEY,
    TRANSCRIPT_PATH,
)

logger = logging.getLogger(__name__)

SEC_HEADERS = {
    "User-Agent": SEC_EDGAR_USER_AGENT,
    "Accept": "application/json",
}


async def _fetch_url(url: str, headers: dict | None = None, timeout: int = 15) -> requests.Response | None:
    """Fetch a URL in a thread."""
    try:
        h = headers or SEC_HEADERS
        resp = await asyncio.to_thread(
            lambda: requests.get(url, headers=h, timeout=timeout)
        )
        return resp if resp.status_code == 200 else None
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


# ---- Tier 1: EFTS Full-Text Search ----

async def _search_efts(company_name: str) -> tuple[str | None, str]:
    """Search EFTS for 8-K filings that might contain earnings transcripts."""
    try:
        params = {
            "q": f'"question-and-answer" "{company_name}"',
            "forms": "8-K",
            "dateRange": "custom",
            "startdt": "2024-01-01",
            "enddt": "2026-12-31",
        }
        resp = await asyncio.to_thread(
            lambda: requests.get(
                "https://efts.sec.gov/LATEST/search-index",
                params=params,
                headers=SEC_HEADERS,
                timeout=15,
            )
        )
        if resp.status_code != 200:
            return None, ""

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        for hit in hits:
            source = hit.get("_source", {})
            file_url = source.get("file_url")
            if file_url:
                content_resp = await _fetch_url(file_url)
                if content_resp and "question" in content_resp.text.lower() and "answer" in content_resp.text.lower():
                    return content_resp.text, file_url
    except Exception as e:
        logger.warning(f"EFTS search failed: {e}")
    return None, ""


# ---- Tier 2: Submissions API + Exhibit Crawl ----

async def _search_submissions(cik: str) -> tuple[str | None, str]:
    """Check recent 8-K filings via submissions API for transcript content."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = await _fetch_url(url)
    if not resp:
        return None, ""

    try:
        data = resp.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form != "8-K" or i >= 10:
                break
            accession = accessions[i].replace("-", "")
            primary_doc = primary_docs[i]

            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{primary_doc}"
            filing_resp = await _fetch_url(index_url)
            if not filing_resp:
                continue

            text = filing_resp.text
            if "question-and-answer" in text.lower() or "q&a session" in text.lower():
                return text, index_url

            await asyncio.sleep(0.2)

    except Exception as e:
        logger.warning(f"Submissions API search failed: {e}")
    return None, ""


# ---- Tier 3: Financial Modeling Prep API ----

async def _search_fmp(ticker: str) -> tuple[str | None, str]:
    """Fetch the most recent earnings call transcript from FMP API."""
    if not FMP_API_KEY:
        logger.info("FMP API key not configured — skipping tier 3")
        return None, ""

    # Try fetching the most recent transcript
    url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}"
    params = {"apikey": FMP_API_KEY}

    try:
        resp = await asyncio.to_thread(
            lambda: requests.get(url, params=params, timeout=20)
        )
        if resp.status_code != 200:
            logger.warning(f"FMP API returned status {resp.status_code}")
            return None, ""

        data = resp.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning("FMP API returned no transcripts")
            return None, ""

        # Take the most recent transcript
        transcript = data[0]
        content = transcript.get("content", "")
        quarter = transcript.get("quarter", "?")
        year = transcript.get("year", "?")
        date = transcript.get("date", "")

        if content and len(content) > 500:
            # Prepend metadata header
            header = (
                f"Morgan Stanley ({ticker}) Q{quarter} {year} Earnings Call Transcript\n"
                f"Date: {date}\n"
                f"Source: Financial Modeling Prep API\n"
                f"{'=' * 60}\n\n"
            )
            source_url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{ticker}?quarter={quarter}&year={year}"
            return header + content, source_url

    except Exception as e:
        logger.warning(f"FMP API request failed: {e}")
    return None, ""


# ---- Tier 4: DuckDuckGo Web Fallback ----

async def _search_transcript_web(company_name: str, ticker: str) -> tuple[str | None, str]:
    """Search for earnings call transcript via DuckDuckGo."""
    queries = [
        f'"{company_name}" earnings call transcript Q&A 2025 OR 2026',
        f'{ticker} earnings call transcript "question-and-answer"',
    ]

    for query in queries:
        try:
            results = await asyncio.to_thread(
                lambda q=query: DDGS().text(q, max_results=5)
            )
            for r in results:
                url = r.get("href", "")
                if any(domain in url for domain in ["seekingalpha.com", "fool.com", "gurufocus.com"]):
                    page_resp = await _fetch_url(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    )
                    if page_resp:
                        soup = BeautifulSoup(page_resp.text, "lxml")
                        article = soup.find("article") or soup.find("div", class_=re.compile(r"article|content|transcript"))
                        if article:
                            text = article.get_text(separator="\n", strip=True)
                            if "question" in text.lower() and len(text) > 1000:
                                return text, url
        except Exception as e:
            logger.warning(f"Web transcript search failed for '{query}': {e}")
        await asyncio.sleep(1)

    # Don't return DuckDuckGo snippets here — let tier 5 (local file) run first.
    # Snippets are a last resort collected separately if all tiers fail.
    return None, ""


# ---- Tier 5: Local Transcript File Fallback ----

async def _read_local_transcript() -> tuple[str | None, str]:
    """Read bundled local transcript file as last-resort fallback."""
    try:
        if TRANSCRIPT_PATH.exists():
            text = TRANSCRIPT_PATH.read_text(encoding="utf-8")
            if text and len(text) > 100:
                logger.info(f"Using local transcript file: {TRANSCRIPT_PATH.name}")
                return text, f"Local file ({TRANSCRIPT_PATH.name})"
    except Exception as e:
        logger.warning(f"Failed to read local transcript: {e}")
    return None, ""


# ---- Main Entrypoint ----

async def get_transcript(ticker: str, company_name: str = "Morgan Stanley") -> dict:
    """Retrieve earnings call transcript using 5-tier fallback.

    Returns:
        {
            "status": "success"/"error",
            "transcript_text": str,
            "source": str,
            "source_url": str,
            "tier": int,
        }
    """
    cik = COMPANY_CIKS.get(ticker)

    # Tier 1: EFTS search
    logger.info("Tier 1: Searching EFTS for transcript...")
    text, source_url = await _search_efts(company_name)
    if text:
        return {
            "status": "success",
            "transcript_text": text,
            "source": "SEC EDGAR (EFTS)",
            "source_url": source_url,
            "tier": 1,
        }

    # Tier 2: Submissions API
    if cik:
        logger.info("Tier 2: Checking submissions API...")
        text, source_url = await _search_submissions(cik)
        if text:
            return {
                "status": "success",
                "transcript_text": text,
                "source": "SEC EDGAR (8-K filing)",
                "source_url": source_url,
                "tier": 2,
            }

    # Tier 3: FMP API
    logger.info("Tier 3: Querying Financial Modeling Prep API...")
    text, source_url = await _search_fmp(ticker)
    if text:
        return {
            "status": "success",
            "transcript_text": text,
            "source": "Financial Modeling Prep API",
            "source_url": source_url,
            "tier": 3,
        }

    # Tier 4: Web fallback
    logger.info("Tier 4: Searching web for transcript...")
    text, source_url = await _search_transcript_web(company_name, ticker)
    if text:
        return {
            "status": "success",
            "transcript_text": text,
            "source": "Web search",
            "source_url": source_url,
            "tier": 4,
        }

    # Tier 5: Local file fallback
    logger.info("Tier 5: Reading local transcript file...")
    text, source_label = await _read_local_transcript()
    if text:
        return {
            "status": "success",
            "transcript_text": text,
            "source": source_label,
            "source_url": "",
            "tier": 5,
        }

    # All tiers failed
    return {
        "status": "error",
        "transcript_text": "",
        "source": "none",
        "source_url": "",
        "tier": 0,
        "error": "[Earnings call transcript not available from public sources]",
    }
