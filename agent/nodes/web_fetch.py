"""
agent/nodes/web_fetch.py

Fetches live data from the web using Bright Data.
Three sources run across two phases via asyncio:

  Phase 1 (parallel):  SERP search + Transcript scrape
                            ↓
  Phase 2 (parallel):  Full article fetch for top 3 SERP URLs

Output: full articles + remaining snippets + transcript chunks
Full articles replace their snippet versions — no duplicates.
If a full fetch fails for any URL, the snippet fallback stays in output.

Input:  {"ticker": "NVDA", "days_to_earnings": 7, "recency_mode": "standard"}
Output: list of chunks (same shape as RAG output — ready for pre_synthesis)

Environment variables required:
  BRIGHT_DATA_API_KEY       — your Bright Data API key
  BRIGHT_DATA_SERP_URL      — SERP API endpoint (default provided)
  BRIGHT_DATA_UNLOCKER_URL  — Web Unlocker endpoint (default provided)
  BRIGHT_DATA_SERP_ZONE     — your SERP zone name (e.g. serp_api)
  BRIGHT_DATA_UNLOCKER_ZONE — your Web Unlocker zone name (e.g. web_unlocker)
"""

import asyncio
import json as _json
import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BRIGHT_DATA_API_KEY       = os.getenv("BRIGHT_DATA_API_KEY")
BRIGHT_DATA_SERP_URL      = os.getenv("BRIGHT_DATA_SERP_URL")
BRIGHT_DATA_UNLOCKER_URL  = os.getenv("BRIGHT_DATA_UNLOCKER_URL")
BRIGHT_DATA_SERP_ZONE     = os.getenv("BRIGHT_DATA_SERP_ZONE")
BRIGHT_DATA_UNLOCKER_ZONE = os.getenv("BRIGHT_DATA_UNLOCKER_ZONE")

SERP_TIMEOUT    = 60
REQUEST_TIMEOUT = 15

SERP_MAX_RESULTS        = 8
MAX_FULL_ARTICLES       = 2
MIN_ARTICLE_PARA_LENGTH = 80

RECENCY_WINDOWS = {
    "aggressive":  7,
    "standard":    30,
    "historical":  90,
}

AUTHORITY_MAP = {
    "sec.gov":           1.0,
    "seekingalpha.com":  0.95,
    "reuters.com":       0.85,
    "bloomberg.com":     0.85,
    "ft.com":            0.85,
    "wsj.com":           0.85,
    "cnbc.com":          0.75,
    "marketwatch.com":   0.70,
    "fool.com":          0.60,
}

def get_authority(url: str) -> float:
    for domain, score in AUTHORITY_MAP.items():
        if domain in url:
            return score
    return 0.65


async def fetch_serp_news(
    client: httpx.AsyncClient,
    ticker: str,
    recency_days: int,
) -> tuple[list[dict], list[dict]]:
    query = quote_plus(f"{ticker} earnings revenue guidance stock analyst")

    payload = {
        "zone":   BRIGHT_DATA_SERP_ZONE,
        "url":    f"https://www.google.com/search?q={query}&tbm=nws&num={SERP_MAX_RESULTS}",
        "format": "json",
    }
    headers = {
        "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
        "Content-Type":  "application/json",
    }

    try:
        response = await client.post(
            BRIGHT_DATA_SERP_URL,
            json=payload,
            headers=headers,
            timeout=SERP_TIMEOUT,
        )
        response.raise_for_status()

        envelope = response.json()
        body_raw = envelope.get("body", "")
        data = _json.loads(body_raw) if isinstance(body_raw, str) else body_raw

        snippet_chunks = []
        top_urls = []
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=recency_days)

        results = data.get("news", data.get("organic", data.get("results", [])))
        skip_full_fetch = ["twitter.com", "x.com", "reddit.com", "youtube.com"]

        for item in results:
            title    = item.get("title", "")
            snippet  = item.get("description", item.get("snippet", ""))
            url      = item.get("link", item.get("url", ""))
            date_str = item.get("date", "")

            if not snippet or not url:
                continue

            pub_date = _parse_date(date_str)

            if pub_date and pub_date < cutoff_date:
                continue

            text = f"{title}. {snippet}".strip()

            snippet_chunks.append({
                "id":           f"serp_{hash(url) % 100000}",
                "chunk":        text,
                "source":       _extract_domain(url),
                "url":          url,
                "date":         pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "source_type":  "news",
                "authority":    get_authority(url),
                "fetch_method": "serp_snippet",
            })

            if len(top_urls) < MAX_FULL_ARTICLES and not any(d in url for d in skip_full_fetch):
                top_urls.append({
                    "url":       url,
                    "date":      pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "authority": get_authority(url),
                })

        return snippet_chunks, top_urls

    except httpx.TimeoutException:
        return [], []
    except Exception:
        return [], []


async def fetch_full_articles(
    client: httpx.AsyncClient,
    ticker: str,
    top_urls: list[dict],
) -> list[dict]:
    if not top_urls:
        return []

    async def fetch_one_article(url_meta: dict) -> list[dict]:
        url       = url_meta["url"]
        date      = url_meta["date"]
        authority = url_meta["authority"]

        payload = {
            "zone":   BRIGHT_DATA_UNLOCKER_ZONE,
            "url":    url,
            "format": "raw",
        }
        headers = {
            "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
            "Content-Type":  "application/json",
        }

        # Retry up to 2 times on 502 — Bright Data is non-deterministic
        for attempt in range(3):
            try:
                response = await client.post(
                    BRIGHT_DATA_UNLOCKER_URL,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code == 502 and attempt < 2:
                    wait = 2 ** attempt  # 1s, 2s
                    logger.warning(f"502 on {url} attempt {attempt+1} — retrying in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return _parse_article_html(response.text, ticker, url, date, authority)

            except httpx.TimeoutException:
                logger.warning(f"Timeout on {url} attempt {attempt+1}")
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return []
            except Exception as e:
                logger.warning(f"Failed {url}: {e}")
                return []

        return []

    results = await asyncio.gather(
        *[fetch_one_article(u) for u in top_urls],
        return_exceptions=True,
    )

    chunks = []
    for r in results:
        if isinstance(r, Exception):
            continue
        chunks.extend(r)

    return chunks


def _parse_article_html(
    html: str,
    ticker: str,
    url: str,
    date: str,
    authority: float,
) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "button", "iframe", "noscript"]):
        tag.decompose()

    article = (
        soup.find("article")
        or soup.find("div", {"role": "main"})
        or soup.find("div", class_=re.compile(r"article|story|content|body|post", re.I))
        or soup.find("main")
        or soup.body
    )

    if not article:
        return []

    paragraphs = article.get_text(separator="\n").split("\n")

    skip_patterns = [
        "subscribe", "sign up", "log in", "newsletter", "cookie",
        "privacy policy", "terms of service", "all rights reserved",
        "advertisement", "click here", "read more", "follow us",
        "share this", "related articles", "you may also like",
        "comments", "leave a reply", "print this",
        "our favorite", "we enjoy", "we love", "don't miss",
        "tune in", "stay tuned", "check out", "worth noting",
    ]

    finance_keywords = [
        ticker.lower(), "revenue", "earnings", "margin", "guidance",
        "analyst", "quarter", "billion", "growth", "profit", "eps",
        "beat", "miss", "forecast", "outlook", "demand", "supply",
    ]

    HAS_VERB = re.compile(
        r'\b(is|are|was|were|has|have|had|will|would|said|reported|expects|'
        r'beat|missed|grew|fell|rose|declined)\b', re.I
    )

    chunks = []
    domain = _extract_domain(url)

    for i, para in enumerate(paragraphs):
        para = para.strip()

        if len(para) < MIN_ARTICLE_PARA_LENGTH:
            continue

        para_lower = para.lower()

        if any(skip in para_lower for skip in skip_patterns):
            continue

        kw_hits = sum(1 for kw in finance_keywords if kw in para_lower)
        min_hits = 1 if len(para) > 200 else 2
        if kw_hits < min_hits:
            continue

        if not HAS_VERB.search(para):
            continue

        chunks.append({
            "id":           f"article_{hash(url) % 100000}_{i}",
            "chunk":        para,
            "source":       domain,
            "url":          url,
            "date":         date,
            "source_type":  "news",
            "authority":    authority,
            "fetch_method": "web_unlocker_full",
        })

    return chunks[:5]


async def fetch_transcript(
    client: httpx.AsyncClient,
    ticker: str,
) -> list[dict]:
    sa_url = f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts"

    payload = {
        "zone":   BRIGHT_DATA_UNLOCKER_ZONE,
        "url":    sa_url,
        "format": "raw",
    }
    headers = {
        "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
        "Content-Type":  "application/json",
    }

    try:
        response = await client.post(
            BRIGHT_DATA_UNLOCKER_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        html = response.text

        transcript_url = _extract_latest_transcript_url(html, ticker)
        if not transcript_url:
            return []

        transcript_url = transcript_url.split("#")[0]
        payload["url"] = transcript_url
        transcript_response = await client.post(
            BRIGHT_DATA_UNLOCKER_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        transcript_response.raise_for_status()

        return _parse_transcript_html(transcript_response.text, ticker, transcript_url)

    except httpx.TimeoutException:
        return []
    except Exception:
        return []


def _extract_latest_transcript_url(html: str, ticker: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "earnings-call-transcript" in href and ticker.lower() in href.lower():
            resolved = f"https://seekingalpha.com{href}" if href.startswith("/") else href
            return resolved

    return f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts"


def _parse_transcript_html(html: str, ticker: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    article = (
        soup.find("div", {"data-test-id": "article-content"})
        or soup.find("div", class_=re.compile(r"article|content|transcript", re.I))
        or soup.find("main")
        or soup.body
    )

    if not article:
        return []

    pub_date = _extract_date_from_soup(soup)
    date_str = pub_date.strftime("%Y-%m-%d") if pub_date else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    skip_patterns = [
        "operator instructions", "subscribe to", "premium content",
        "sign up", "log in", "copyright", "seeking alpha",
        "forward-looking statements", "safe harbor", "[operator]",
        "welcome to", "conference call", "webcast", "replay until",
        "written consent", "good afternoon", "good morning", "good evening",
        "with me today", "investor relations",
    ]

    chunks = []
    for i, para in enumerate(article.get_text(separator="\n").split("\n")):
        para = para.strip()

        if len(para) < 80:
            continue

        if any(skip in para.lower() for skip in skip_patterns):
            continue

        chunks.append({
            "id":           f"transcript_{ticker}_{i}",
            "chunk":        para,
            "source":       f"Seeking Alpha — {ticker} Earnings Transcript",
            "url":          url,
            "date":         date_str,
            "source_type":  "transcript",
            "authority":    0.95,
            "fetch_method": "web_unlocker",
        })

    return chunks[:15]


def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _extract_date_from_soup(soup: BeautifulSoup) -> Optional[datetime]:
    for attr in ["article:published_time", "datePublished", "pubdate"]:
        tag = soup.find("meta", attrs={"property": attr}) or soup.find("meta", attrs={"name": attr})
        if tag and tag.get("content"):
            return _parse_date(tag["content"][:10])

    time_tag = soup.find("time")
    if time_tag:
        return _parse_date(time_tag.get("datetime", "")[:10])

    return None


def _extract_domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else url


async def run_web_fetch(
    ticker: str,
    days_to_earnings: int = 14,
    recency_mode: str = "standard",
) -> list[dict]:
    recency_days = RECENCY_WINDOWS.get(recency_mode, 30)

    if not BRIGHT_DATA_API_KEY:
        return []

    async with httpx.AsyncClient() as client:

        serp_result, transcript_chunks = await asyncio.gather(
            fetch_serp_news(client, ticker, recency_days),
            fetch_transcript(client, ticker),
            return_exceptions=True,
        )

        if isinstance(serp_result, Exception):
            snippet_chunks, top_urls = [], []
        else:
            snippet_chunks, top_urls = serp_result

        if isinstance(transcript_chunks, Exception):
            transcript_chunks = []

        full_article_chunks = await fetch_full_articles(client, ticker, top_urls)

    fetched_urls = {c["url"] for c in full_article_chunks}
    filtered_snippets = [c for c in snippet_chunks if c["url"] not in fetched_urls]

    combined = full_article_chunks + filtered_snippets + transcript_chunks

    print(
        f"\n[web_fetch] {ticker} → "
        f"{len(full_article_chunks)} full articles + "
        f"{len(filtered_snippets)} snippets + "
        f"{len(transcript_chunks)} transcript chunks "
        f"= {len(combined)} total"
    )

    return combined


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)

    async def test():
        print("\n" + "=" * 60)
        print("WEB FETCH TEST — NVDA")
        print("=" * 60)

        chunks = await run_web_fetch(
            ticker="NVDA",
            days_to_earnings=7,
            recency_mode="standard",
        )

        print(f"\nTotal chunks returned: {len(chunks)}")
        print("\nSample chunks:")
        for c in chunks[:3]:
            print(f"\n  [{c['source_type']}] {c['source']}")
            print(f"  {c['chunk'][:120]}...")
            print(f"  authority={c['authority']} | date={c['date']}")

        with open("mock/web_fetch_output.json", "w") as f:
            json.dump(chunks, f, indent=2)
        print("\n✓ Full output saved to mock/web_fetch_output.json")

    asyncio.run(test())
