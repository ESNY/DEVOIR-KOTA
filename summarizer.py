"""
summarizer.py
=============
Part 2: Intelligent article summarization via the Google Gemini API.

Workflow:
  Raw article -> build_prompt() -> Gemini API -> parse_response() -> enriched summary

Each article is returned with:
  - summary    : 2-3 sentence English summary
  - keywords   : list of 3-5 financial keywords
  - sentiment  : "positive" | "negative" | "neutral"
  - importance : score from 1 to 5 (5 = very important for markets)

Get a free key: https://aistudio.google.com
"""

import json
import logging
import os
import re
import time
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)

MODEL = "gemini-2.0-flash"   # Fast free-tier model
MAX_RETRIES = 1              # One retry for transient errors
RETRY_DELAY = 2              # Seconds between attempts
MAX_TEXT_LEN = 800           # Input text truncation length

# Initialize the Gemini client from GEMINI_API_KEY in the environment.
_api_key = os.environ.get("GEMINI_API_KEY", "")
_client = genai.Client(api_key=_api_key) if _api_key else None


def build_prompt(article: dict) -> str:
    """
    Build the prompt sent to Gemini to summarize an article.

    Edge case: overly long text is truncated to MAX_TEXT_LEN characters to avoid
    exceeding the context window and to keep costs predictable.
    """
    title = article.get("title", "Untitled")
    text = article.get("summary", "")
    source = article.get("source", "Unknown")

    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN] + "..."
        logger.debug(f"Text truncated to {MAX_TEXT_LEN} chars for: {title[:40]}")

    prompt = f"""You are a senior financial analyst. Summarize the following article in a concise, structured way.

SOURCE: {source}
TITLE : {title}
TEXT  : {text}

Reply ONLY with a valid JSON object (no markdown, no backticks) that exactly follows this format:
{{
  "summary":    "Summary in 2-3 sentences maximum, in English, focused on market impact.",
  "keywords":   ["keyword1", "keyword2", "keyword3"],
  "sentiment":  "positive" | "negative" | "neutral",
  "importance": 3
}}

Rules:
- summary    : 2-3 sentences max, factual, no personal opinion
- keywords   : 3 to 5 relevant financial keywords (company, index, theme...)
- sentiment  : perceived impact on financial markets
- importance : integer from 1 (minor) to 5 (major market event)
"""
    return prompt


def call_gemini(prompt: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """
    Send the prompt to Gemini and return the raw response text.

    Handled edge cases:
    - Missing API key                 -> immediate fallback (no-AI mode)
    - Invalid key (401/403)           -> clear log message + fallback
    - Quota exceeded (429)            -> fallback None (raw summary used)
    - Timeout / network error         -> one retry, then None
    - Generic error                   -> log + None
    """
    if not _api_key or _client is None:
        logger.warning("GEMINI_API_KEY missing - switching to fallback mode (raw summary)")
        return None

    for attempt in range(retries + 1):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text

        except Exception as error:
            error_text = str(error).lower()

            if "401" in error_text or "403" in error_text or "api_key" in error_text or "invalid" in error_text:
                logger.error("Invalid Gemini API key - check GEMINI_API_KEY")
                return None

            if "429" in error_text or "quota" in error_text or "resource_exhausted" in error_text:
                logger.warning("Gemini quota exceeded - switching to fallback mode")
                return None

            if attempt < retries:
                logger.warning(f"Gemini error, retrying ({attempt + 1}/{retries}): {error}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Persistent Gemini error: {error}")
                return None

    return None


def _normalize_sentiment(value: str) -> str:
    sentiment = (value or "").strip().lower()
    return {
        "negative": "negative",
        "positive": "positive",
        "neutral": "neutral",
    }.get(sentiment, "neutral")


def parse_response(raw_text: str, article: dict) -> dict:
    """
    Extract the structured JSON returned by Gemini.

    Handled edge cases:
    - Direct valid JSON               -> standard parsing
    - JSON wrapped in backticks        -> cleanup then parsing
    - Invalid JSON / empty response    -> fallback with default values
    - Missing JSON fields              -> completed with default values
    """
    fallback = {
        "summary": article.get("summary", "")[:300],
        "keywords": [],
        "sentiment": "neutral",
        "importance": 1,
        "_fallback": True,
    }

    if not raw_text or not raw_text.strip():
        logger.warning("Empty API response - fallback enabled")
        return fallback

    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).replace("```", "").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("JSON not found in response - fallback enabled")
                return fallback
        else:
            logger.warning("No JSON in response - fallback enabled")
            return fallback

    return {
        "summary": str(data.get("summary", fallback["summary"])),
        "keywords": list(data.get("keywords", [])),
        "sentiment": _normalize_sentiment(str(data.get("sentiment", "neutral"))),
        "importance": _safe_importance(data.get("importance", 1)),
        "_fallback": False,
    }


def summarize_article(article: dict) -> dict:
    """
    Full pipeline for one article: build_prompt -> call_gemini -> parse_response.
    Returns the original article enriched with AI fields.
    """
    prompt = build_prompt(article)
    raw = call_gemini(prompt)

    if raw is None:
        ai_fields = {
            "summary": article.get("summary", "")[:300],
            "keywords": [],
            "sentiment": "neutral",
            "importance": 1,
            "_fallback": True,
        }
    else:
        ai_fields = parse_response(raw, article)

    return {**article, **ai_fields}


def summarize_all(articles: list[dict], delay: float = 0.5) -> list[dict]:
    """
    Summarize all articles sequentially with a delay between calls to respect
    the free Gemini API rate limit.

    Args:
        articles: list returned by collector.collect_news()
        delay: pause in seconds between API calls
    """
    results = []
    total = len(articles)
    fallback_count = 0

    for index, article in enumerate(articles, 1):
        logger.info(f"Summary {index}/{total}: {article['title'][:50]}...")

        enriched = summarize_article(article)
        results.append(enriched)

        if enriched.get("_fallback"):
            fallback_count += 1

        if index < total:
            time.sleep(delay)

    logger.info(
        f"Summaries complete: {total} articles "
        f"({fallback_count} in fallback mode)"
    )
    return results


def _safe_importance(value) -> int:
    """
    Convert the importance value to an integer between 1 and 5.
    Edge case: out-of-range or non-numeric value -> 1.
    """
    try:
        number = int(value)
        return max(1, min(5, number))
    except (ValueError, TypeError):
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    test_article = {
        "title": "The ECB keeps its benchmark rates at 4.5%",
        "summary": (
            "The European Central Bank decided at its Thursday meeting to keep "
            "benchmark interest rates unchanged at 4.5%, in line with market "
            "expectations. Christine Lagarde said monetary policy would remain "
            "restrictive for as long as needed to bring inflation back toward "
            "the 2% target."
        ),
        "source": "Reuters Finance",
        "link": "https://reuters.com/example",
        "published": "2025-05-26",
    }

    print("Testing the Gemini summarizer with a sample article...\n")
    result = summarize_article(test_article)

    print(f"Title     : {result['title']}")
    print(f"AI summary: {result['summary']}")
    print(f"Keywords  : {result['keywords']}")
    print(f"Sentiment : {result['sentiment']}")
    print(f"Importance: {result['importance']}/5")
    print(f"Fallback  : {result['_fallback']}")
