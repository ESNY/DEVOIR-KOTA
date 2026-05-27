"""
collector.py
============
Automated financial news aggregator — KOTA Investment Club

Workflow:
  NewsAPI → fetch_articles() → parse_articles() → filter_and_classify() → clean article list

Get a free key (100 req/day, no CC):
  https://newsapi.org/register

Environment variables:
  NEWS_API_KEY = your NewsAPI key
"""

import hashlib
import logging
import os
import re
import requests
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# NewsAPI configuration
# ──────────────────────────────────────────────
NEWSAPI_BASE    = "https://newsapi.org/v2/everything"
NEWSAPI_KEY     = os.environ.get("NEWS_API_KEY", "")
MAX_ARTICLES    = 30
REQUEST_TIMEOUT = 15  # seconds

# ──────────────────────────────────────────────
# Subject classification (keywords → category)
# ──────────────────────────────────────────────
SUBJECTS = {
    "Central Banks": [
        "Federal Reserve", "central bank", "interest rate", "monetary policy",
        "ECB", "European Central Bank", "Fed", "rate hike", "rate cut",
        "Christine Lagarde", "Jerome Powell", "inflation", "disinflation",
        "quantitative easing", "QE", "tapering", "basis points", "FOMC",
    ],
    "Equity Markets": [
        "CAC 40", "Dow Jones", "Nasdaq", "S&P 500", "DAX", "Nikkei", "FTSE",
        "stock market", "equity market", "stock exchange",
        "Wall Street", "market cap", "bull market", "bear market",
        "stock rally", "market selloff", "IPO", "stock index",
    ],
    "Commodities": [
        "crude oil", "oil price", "Brent", "WTI", "OPEC",
        "gold price", "natural gas", "commodities",
        "copper", "lithium", "raw materials", "barrel",
    ],
    "Currencies & Crypto": [
        "EUR/USD", "exchange rate", "forex", "currency",
        "bitcoin", "ethereum", "cryptocurrency", "crypto",
        "blockchain", "stablecoin", "dollar index", "DXY",
    ],
    "Corporate Earnings": [
        "quarterly earnings", "annual results", "revenue", "net profit",
        "earnings per share", "EPS", "dividend", "profit warning",
        "guidance", "beat estimates", "missed expectations",
        "operating income", "gross margin",
    ],
    "Global Economy": [
        "GDP", "economic growth", "recession", "unemployment rate",
        "trade balance", "IMF", "World Bank", "OECD", "G7", "G20",
        "public debt", "tariff", "trade war", "fiscal policy",
        "consumer price index", "CPI", "producer price index", "PPI",
    ],
}

# NewsAPI query — specific enough to get finance articles, broad enough to get volume
# Using exact phrases in quotes and key tickers avoids irrelevant results
QUERY_KEYWORDS = (
    '"stock market" OR "interest rate" OR "Federal Reserve" OR "central bank" OR '
    '"inflation" OR "GDP" OR "earnings" OR "S&P 500" OR "Nasdaq" OR '
    '"crude oil" OR "bitcoin" OR "ECB" OR "tariff" OR "recession"'
)


# ──────────────────────────────────────────────
# 1. Fetch from NewsAPI
# ──────────────────────────────────────────────
def fetch_articles(
    api_key: str = "",
    query: str = QUERY_KEYWORDS,
    max_results: int = MAX_ARTICLES,
    days_back: int = 1,
) -> list[dict]:
    """
    Queries NewsAPI and returns raw articles (English only).

    Edge cases handled:
    - Missing/invalid API key (401)  → clear message + empty list
    - Quota exceeded (429)           → clear message + empty list
    - Network timeout                → 1 retry then empty list
    - Malformed response             → empty list
    """
    key = api_key or NEWSAPI_KEY

    if not key:
        logger.warning("NEWS_API_KEY missing — cannot fetch articles")
        return []

    effective_days = max(days_back, 2)
    from_date = (datetime.now() - timedelta(days=effective_days)).strftime("%Y-%m-%d")

    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "language": "en",
        "pageSize": min(max_results * 3, 100),  # x3 to compensate for filtering
        "apiKey":   key,
    }

    for attempt in range(2):
        try:
            logger.info(f"NewsAPI request (attempt {attempt + 1})…")
            resp = requests.get(NEWSAPI_BASE, params=params, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 401:
                logger.error("Invalid NewsAPI key (401) — check NEWS_API_KEY")
                return []

            if resp.status_code == 429:
                logger.warning("NewsAPI quota exceeded (429) — try again tomorrow")
                return []

            resp.raise_for_status()
            data = resp.json()

            data = resp.json()
            logger.info(f"NewsAPI response status: {data.get('status')} | totalResults: {data.get('totalResults')} | code: {data.get('code')} | message: {data.get('message')}")

            articles = data.get("articles", [])
            logger.info(f"✓ {len(articles)} raw articles fetched from NewsAPI")
            return articles

        except requests.Timeout:
            if attempt == 0:
                logger.warning("NewsAPI timeout, retrying…")
                continue
            logger.error("Persistent NewsAPI timeout")
            return []

        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []

    return []


# ──────────────────────────────────────────────
# 2. Parsing and normalization
# ──────────────────────────────────────────────
def parse_articles(raw_articles: list) -> list[dict]:
    """
    Normalizes raw NewsAPI articles into clean dicts.

    Edge cases handled:
    - Missing title or URL      → article skipped
    - Removed articles          → skipped ("[Removed]")
    - No text at all            → skipped
    - Invalid date              → fallback to datetime.now()
    - Missing source            → "Unknown"
    """
    articles = []

    for raw in raw_articles:
        title       = (raw.get("title")       or "").strip()
        url         = (raw.get("url")         or "").strip()
        description = (raw.get("description") or "").strip()
        content     = (raw.get("content")     or "").strip()
        source_name = raw.get("source", {}).get("name", "Unknown")

        # Skip if mandatory fields are missing
        if not title or not url:
            continue

        # Skip removed articles
        if "[Removed]" in title or title.lower() == "removed":
            continue

        # Use content if longer than description (NewsAPI truncates both)
        if content:
            # Strip the NewsAPI truncation suffix "[+XXXX chars]"
            clean_content = re.sub(r"\[\+\d+ chars?\]$", "", content).strip()
        else:
            clean_content = ""

        # Pick the longest available text as summary
        full_text = max(description, clean_content, key=len) if (description or clean_content) else ""

        # Skip if no usable text at all
        if not full_text or len(full_text) < 20:
            continue

        published = _parse_date(raw.get("publishedAt", ""))

        articles.append({
            "title":     title,
            "link":      url,
            "summary":   full_text,
            "published": published,
            "source":    source_name,
            "image":     raw.get("urlToImage", ""),
        })

    logger.info(f"Valid parsed articles: {len(articles)}")
    return articles


# ──────────────────────────────────────────────
# 3. Filtering and classification
# ──────────────────────────────────────────────
def filter_and_classify(
    articles: list[dict],
    max_articles: int = MAX_ARTICLES,
    filter_keywords: bool = False,
) -> list[dict]:
    """
    Deduplicates, classifies by subject, and limits the list.

    Edge cases handled:
    - Duplicate URLs             → deduplicated by hash
    - Too many articles          → capped at max_articles
    - Article with no clear topic → category "General"
    """
    # Deduplication
    seen, unique = set(), []
    for art in articles:
        fp = _fingerprint(art["link"])
        if fp not in seen:
            seen.add(fp)
            unique.append(art)

    # Optional keyword filter (stricter mode)
    if filter_keywords:
        unique = [
            a for a in unique
            if _is_financial(a["title"] + " " + a["summary"])
        ]
        logger.info(f"After financial filter: {len(unique)} articles")

    # Classify each article
    for art in unique:
        art["subject"] = _classify(art["title"] + " " + art["summary"])

    # Sort by date descending and cap
    unique.sort(key=lambda x: x["published"], reverse=True)
    result = unique[:max_articles]

    logger.info(f"Final articles: {len(result)}")
    return result


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────
def collect_news(
    api_key: str = "",
    max_articles: int = MAX_ARTICLES,
    filter_keywords: bool = False,
    days_back: int = 1,
) -> list[dict]:
    """
    Single entry point: fetch → parse → filter_and_classify.
    Returns a list of articles ready for display or summarization.
    """
    raw     = fetch_articles(api_key, max_results=max_articles, days_back=days_back)
    parsed  = parse_articles(raw)
    cleaned = filter_and_classify(parsed, max_articles, filter_keywords)
    return cleaned


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────
def _parse_date(date_str: str) -> datetime:
    """Parse ISO 8601 date from NewsAPI. Fallback: datetime.now()."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return datetime.now()


def _fingerprint(text: str) -> str:
    normalized = text.lower().strip().split("?")[0]
    return hashlib.md5(normalized.encode()).hexdigest()


def _match_keywords(text: str, keywords: list) -> int:
    """
    Counts how many keywords appear in the text.
    Uses word boundaries for single words, direct match for phrases.
    """
    count = 0
    text_lower = text.lower()
    for kw in keywords:
        kw_lower = kw.lower()
        if " " in kw_lower or "'" in kw_lower or "/" in kw_lower:
            if kw_lower in text_lower:
                count += 1
        else:
            pattern = r"(?<![\w\-])" + re.escape(kw_lower) + r"(?![\w\-])"
            if re.search(pattern, text_lower):
                count += 1
    return count


def _is_financial(text: str) -> bool:
    """Returns True if the text contains at least one financial keyword."""
    all_keywords = [kw for kws in SUBJECTS.values() for kw in kws]
    return _match_keywords(text, all_keywords) > 0


def _classify(text: str) -> str:
    """
    Returns the most relevant subject for a given text.
    Falls back to 'General' if no keywords match.
    """
    scores = {
        subject: _match_keywords(text, keywords)
        for subject, keywords in SUBJECTS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"


# ──────────────────────────────────────────────
# Web scraping for full article text
# ──────────────────────────────────────────────
def scrape_full_text(url: str, max_chars: int = 1500) -> str:
    """
    Fetches the full text of an article via web scraping.

    Strategy:
    - Downloads the HTML page
    - Extracts <p> tags (main content)
    - Filters short paragraphs (menus, footers, ads...)
    - Truncates to max_chars

    Edge cases handled:
    - Unreachable URL / timeout  → returns "" (fallback to description)
    - Page without paragraphs   → returns ""
    - Paywalled content         → returns what is accessible
    - Invalid encoding          → ignores decode errors
    """
    try:
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        paragraphs = [
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 60
        ]

        if not paragraphs:
            return ""

        full_text = " ".join(paragraphs)
        return full_text[:max_chars] + ("…" if len(full_text) > max_chars else "")

    except Exception as e:
        logger.debug(f"Scraping failed for {url[:60]}: {e}")
        return ""


def enrich_with_full_text(articles: list[dict]) -> list[dict]:
    """
    Attempts to fetch the full text for each article via scraping.
    Falls back to the existing NewsAPI description if scraping fails.
    A 0.3s delay between requests avoids overloading servers.
    """
    import time

    for i, art in enumerate(articles):
        logger.info(f"Scraping {i+1}/{len(articles)}: {art['title'][:50]}…")
        full = scrape_full_text(art["link"])
        if full and len(full) > len(art.get("summary", "")):
            art["summary"] = full
            art["scraped"] = True
        else:
            art["scraped"] = False
        time.sleep(0.3)

    scraped_count = sum(1 for a in articles if a.get("scraped"))
    logger.info(f"Scraping done: {scraped_count}/{len(articles)} articles enriched")
    return articles


# ──────────────────────────────────────────────
# Quick test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    articles = collect_news(max_articles=5)
    if not articles:
        print("No articles — check NEWS_API_KEY")
    else:
        print(f"\n{len(articles)} articles collected\n")
        for i, art in enumerate(articles, 1):
            print(f"[{i}] [{art['subject']}] {art['title'][:70]}")
            print(f"     Source: {art['source']} — {art['published'].strftime('%d/%m %H:%M')}")
            print()