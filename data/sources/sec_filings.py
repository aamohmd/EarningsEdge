"""
data/sources/sec_filings.py

Fetches the most recent 10-Q (or 10-K) filing for a ticker
from SEC EDGAR's free public API. No API key required.

Pipeline:
    1. EDGAR submissions API → get latest filing accession number
    2. EDGAR filing index    → get the primary document URL
    3. httpx                 → fetch the HTML filing
    4. BeautifulSoup         → extract key sections
    5. Return chunks         → authority=1.0, source_type="filing"

Usage:
    from data.sources.sec_filings import get_filing_chunks
    chunks = get_filing_chunks("NVDA")

SEC EDGAR rate limit: 10 requests/second — we stay well under this.
User-Agent header required by SEC — we include it.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEC_USER_AGENT = "EarningsEdge hackathon@earningsedge.ai"

EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

MAX_CHUNKS_PER_FILING = 8
MIN_CHUNK_LENGTH = 300


async def get_cik(client: httpx.AsyncClient, ticker: str) -> Optional[str]:
    """
    Looks up the CIK number for a ticker using EDGAR company tickers JSON.
    CIK is zero-padded to 10 digits.
    """
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                cik = str(entry["cik_str"]).zfill(10)
                logger.info(f"SEC: found CIK {cik} for {ticker}")
                return cik

        logger.warning(f"SEC: no CIK found for {ticker}")
        return None

    except Exception as e:
        logger.error(f"SEC: CIK lookup failed for {ticker}: {type(e).__name__} - {str(e)}")
        return None


async def get_latest_filing(
    client: httpx.AsyncClient,
    cik: str,
    form_type: str = "10-Q",
) -> Optional[dict]:
    """
    Returns metadata for the most recent filing of the given form type.
    """
    try:
        url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        filings     = data.get("filings", {}).get("recent", {})
        forms       = filings.get("form", [])
        dates       = filings.get("filingDate", [])
        accessions  = filings.get("accessionNumber", [])
        documents   = filings.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form == form_type:
                accession = accessions[i].replace("-", "")
                return {
                    "accession_number": accessions[i],
                    "accession_clean":  accession,
                    "filing_date":      dates[i],
                    "primary_document": documents[i],
                    "form_type":        form,
                    "cik":              cik,
                }

        if form_type == "10-Q":
            logger.info(f"SEC: no 10-Q for CIK {cik} — trying 10-K")
            return await get_latest_filing(client, cik, "10-K")

        return None

    except Exception as e:
        logger.error(f"SEC: filing lookup failed for CIK {cik}: {e}")
        return None


async def fetch_filing_content(
    client: httpx.AsyncClient,
    filing_meta: dict,
) -> Optional[str]:
    """
    Fetches the raw HTML content of the primary filing document.
    """
    try:
        cik       = filing_meta["cik"].lstrip("0")
        accession = filing_meta["accession_clean"]
        document  = filing_meta["primary_document"]

        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"

        response = await client.get(url, timeout=30)
        response.raise_for_status()

        logger.info(f"SEC: fetched {filing_meta['form_type']} ({len(response.text)} chars)")
        return response.text

    except Exception as e:
        logger.error(f"SEC: content fetch failed: {e}")
        return None


def parse_filing_content(
    html: str,
    ticker: str,
    filing_meta: dict,
) -> list[dict]:
    """
    Parses 10-Q/10-K HTML into meaningful chunks.

    iXBRL filings (modern EDGAR) don't have clean <p> tags — the narrative
    prose is embedded in <span> and <td> elements between XBRL-tagged numbers.
    Strategy:
      1. Collapse the full text to one string (remove tags, collapse whitespace)
      2. Find the MD&A narrative start via regex on sentence-opening patterns
         ("Revenue was/increased", "Gross margin", "Data Center revenue", etc.)
         — these only appear in the Results of Operations narrative, not the TOC
      3. Sentence-split an 8,000-char window around that anchor
      4. Filter by keyword density and minimum length
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    full_text = soup.get_text(separator=" ")
    full_text = re.sub(r'\s+', ' ', full_text)

    NARRATIVE_ANCHORS = [
        r'(?:automotive|services|energy|gaming|compute|networking|client|data center).{0,50}\brevenue.{0,50}(?:increased|decreased|was|grew).{0,100}\$',
        r'(?:total|net) revenues?.{0,50}(?:increased|decreased|were|was).{0,100}\$',
        r'\bup \d+%.{0,50}\bfrom a year ago\b',
        r'\b(?:data center|gaming|client|networking|compute).{0,50}\brevenue.{0,50}\b(?:was|increased|grew).{0,100}\b(?:billion|million)\b',
        rf'\b{re.escape(ticker)}\b.{0,50}\brevenue.{0,50}\b(?:was|increased|decreased|grew).{0,100}\b(?:billion|million)\b',
        r'\bgross\s+(?:profit|margin).{0,50}\b(?:increased|decreased|improved).{0,100}\b(?:billion|million|%)\b',
        r'\boperating\s+income.{0,50}\b(?:increased|decreased).{0,100}\b(?:billion|million)\b',
    ]

    anchor_pos = -1
    for pat in NARRATIVE_ANCHORS:
        matches = list(re.finditer(pat, full_text, re.IGNORECASE))
        if matches:
            candidates = matches[-3:]
            best = max(
                candidates,
                key=lambda m: len(re.findall(r'[a-zA-Z]', full_text[m.start(): m.start() + 500])),
            )
            anchor_pos = best.start()
            logger.info(f"SEC: MD&A narrative anchor found at char {anchor_pos} for {ticker} (pattern={pat[:40]!r})")
            break

    if anchor_pos == -1:
        logger.warning(f"SEC: no narrative anchor found for {ticker} — trying paragraph fallback")
        return _parse_filing_fallback(full_text, ticker, filing_meta)

    window_start = max(0, anchor_pos - 200)
    window_end   = min(len(full_text), anchor_pos + 15000)
    window_text  = full_text[window_start:window_end]

    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\$])', window_text)

    finance_keywords = [
        ticker.lower(), "revenue", "earnings", "margin", "guidance",
        "quarter", "billion", "million", "growth", "profit", "loss",
        "operating", "diluted", "eps", "outlook", "demand", "supply",
        "year-over-year", "sequentially", "increased", "decreased",
        "compared to", "fiscal", "results", "segment", "gross profit",
        "net income", "operating income", "data center", "cloud",
    ]

    skip_patterns = [
        "pursuant to", "incorporated by reference",
        "table of contents", "forward-looking statements safe harbor",
        "generally accepted accounting", "u.s. gaap",
        "critical accounting", "accounting policies",
        "notes to condensed", "see note", "refer to note",
        "without incurring", "repatriate",
    ]

    filing_date = filing_meta.get("filing_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    form_type   = filing_meta.get("form_type", "10-Q")
    cik         = filing_meta.get("cik", "")
    url         = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}"

    chunks = []
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()

        if len(sentence) < MIN_CHUNK_LENGTH:
            continue

        sent_lower = sentence.lower()

        if any(skip in sent_lower for skip in skip_patterns):
            continue

        kw_hits = sum(1 for kw in finance_keywords if kw in sent_lower)
        if kw_hits < 3:
            continue

        if len(re.findall(r'[a-zA-Z]', sentence)) < 80:
            continue

        chunks.append({
            "id":           f"sec_{ticker}_{form_type}_{anchor_pos}_{i}",
            "chunk":        sentence,
            "source":       f"SEC {form_type} — {ticker} ({filing_date})",
            "url":          url,
            "date":         filing_date,
            "source_type":  "filing",
            "authority":    1.0,
            "fetch_method": "sec_edgar",
        })

        if len(chunks) >= MAX_CHUNKS_PER_FILING:
            break

    logger.info(f"SEC: extracted {len(chunks)} chunks from {form_type} MD&A narrative")
    return chunks


def _parse_filing_fallback(
    full_text: str,
    ticker: str,
    filing_meta: dict,
) -> list[dict]:
    """
    Fallback when no narrative anchor is found — splits on MDA_MARKERS
    and uses the paragraph approach from the original implementation.
    """
    paragraphs = [p.strip() for p in full_text.split(".") if p.strip()]

    finance_keywords = [
        ticker.lower(), "revenue", "earnings", "margin",
        "billion", "million", "growth", "profit", "quarter",
    ]

    filing_date = filing_meta.get("filing_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    form_type   = filing_meta.get("form_type", "10-Q")
    cik         = filing_meta.get("cik", "")
    url         = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}"

    chunks = []
    for i, para in enumerate(paragraphs):
        if len(para) < MIN_CHUNK_LENGTH:
            continue
        kw_hits = sum(1 for kw in finance_keywords if kw in para.lower())
        if kw_hits < 2:
            continue
        chunks.append({
            "id":           f"sec_{ticker}_{form_type}_fb_{i}",
            "chunk":        para,
            "source":       f"SEC {form_type} — {ticker} ({filing_date})",
            "url":          url,
            "date":         filing_date,
            "source_type":  "filing",
            "authority":    1.0,
            "fetch_method": "sec_edgar_fallback",
        })
        if len(chunks) >= MAX_CHUNKS_PER_FILING:
            break

    logger.info(f"SEC: fallback extracted {len(chunks)} chunks")
    return chunks



async def get_filing_chunks(
    ticker: str,
    form_type: str = "10-Q",
) -> list[dict]:
    """
    Full pipeline: ticker → EDGAR → parsed chunks.
    Returns empty list if anything fails — never crashes the pipeline.
    """
    headers = {"User-Agent": SEC_USER_AGENT}

    async with httpx.AsyncClient(headers=headers, http2=False) as client:
        cik = await get_cik(client, ticker)
        if not cik:
            return []

        filing_meta = await get_latest_filing(client, cik, form_type)
        if not filing_meta:
            logger.warning(f"SEC: no {form_type} found for {ticker}")
            return []

        logger.info(
            f"SEC: {filing_meta['form_type']} filed "
            f"{filing_meta['filing_date']} for {ticker}"
        )

        html = await fetch_filing_content(client, filing_meta)
        if not html:
            return []

        return parse_filing_content(html, ticker, filing_meta)


if __name__ == "__main__":
    import json
    import os
    logging.basicConfig(level=logging.INFO)

    async def test():
        for ticker in ["NVDA", "TSLA", "AMD"]:
            print(f"\n{'='*60}")
            print(f"  SEC FILING TEST — {ticker}")
            print(f"{'='*60}")

            chunks = await get_filing_chunks(ticker)
            print(f"\nTotal chunks: {len(chunks)}")
            for c in chunks[:2]:
                print(f"\n  [{c['source_type']}] {c['source']}")
                print(f"  {c['chunk'][:300]}...")
                print(f"  authority={c['authority']} | date={c['date']}")

        nvda_chunks = await get_filing_chunks("NVDA")
        os.makedirs("mock", exist_ok=True)
        with open("mock/sec_filing_output.json", "w") as f:
            json.dump(nvda_chunks, f, indent=2)
        print("\n✓ Saved to mock/sec_filing_output.json")

    asyncio.run(test())
