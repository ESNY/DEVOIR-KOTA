# 📰 KOTA Financial News Aggregator

> **KOTA Investment Club — Mini Projet Quant**  
> Automated financial news collection, classification, AI summarization, and PDF export.

---

## Overview

This project automates the morning market intelligence workflow: instead of analysts manually browsing financial news sites, the app fetches, filters, classifies, and summarizes articles automatically — and lets you export the results as a branded PDF report.

---

## Project Structure

```
DEVOIR-KOTA/
├── app.py            # Streamlit interface (main entry point)
├── collector.py      # NewsAPI fetching, parsing, classification
├── summarizer.py     # AI summarization via Google Gemini
├── pdf_export.py     # PDF report generation (ReportLab)
├── assets/
│   └── Kota -logo.png
└── .env              # API keys (not committed to git)
```

---

## Setup

### 1. Install dependencies

```bash
pip install streamlit requests python-dotenv beautifulsoup4 reportlab google-genai
```

### 2. Create a `.env` file

```env
NEWS_API_KEY=your_newsapi_key_here
GEMINI_API_KEY=your_gemini_key_here   # optional — enables AI summaries
```

Get a free NewsAPI key (100 req/day, no credit card): https://newsapi.org/register

### 3. Run the app

```bash
python -m streamlit run app.py
```

---

## How It Works

The pipeline runs in three sequential steps when you click **"Lancer la collecte"**:

```
NewsAPI → fetch_articles()
       → parse_articles()        # normalize + filter junk
       → filter_and_classify()   # deduplicate + assign subject
       → enrich_with_full_text() # web scraping for full content
       → summarize_all()         # Gemini AI (if key configured)
       → Streamlit display + PDF export
```

### Step 1 — News Collection (`collector.py`)

Queries the NewsAPI `/v2/everything` endpoint with a curated set of financial keywords using quoted phrases for precision:

```python
'"stock market" OR "interest rate" OR "Federal Reserve" OR "central bank" OR
 "inflation" OR "GDP" OR "earnings" OR "S&P 500" OR "Nasdaq" OR
 "crude oil" OR "bitcoin" OR "ECB" OR "tariff" OR "recession"'
```

**Key design decisions:**
- English only (`language=en`) — major financial sources (Reuters, Bloomberg, WSJ) publish in English
- `from` date set to minimum 2 days back — the free NewsAPI plan blocks articles from the last 24h
- `pageSize` = `max_results × 3` to compensate for downstream filtering
- 1 automatic retry on timeout

**Edge cases handled:**
- Missing API key → clear warning, empty list returned
- HTTP 401 (invalid key) → logged, stops gracefully
- HTTP 429 (quota exceeded) → logged with "try again tomorrow" message
- Network timeout → 1 retry, then empty list
- Malformed JSON response → caught, empty list returned

### Step 2 — Parsing & Classification (`collector.py`)

Articles are normalized into a clean dict format and classified into 6 subjects by keyword matching:

| Subject | Example keywords |
|---|---|
| **Central Banks** | Federal Reserve, ECB, interest rate, FOMC, rate hike |
| **Equity Markets** | S&P 500, Nasdaq, Wall Street, IPO, bull market |
| **Commodities** | crude oil, Brent, gold price, OPEC, lithium |
| **Currencies & Crypto** | EUR/USD, bitcoin, forex, stablecoin, DXY |
| **Corporate Earnings** | EPS, quarterly earnings, revenue, dividend, guidance |
| **Global Economy** | GDP, recession, IMF, tariff, CPI, trade war |

Classification uses word-boundary regex to avoid false positives (e.g. "or" inside "record").  
Articles matching no subject are labeled **"General"**.

**Filters applied during parsing:**
- Missing title or URL → skipped
- `[Removed]` articles (NewsAPI placeholder) → skipped
- No usable text (description + content both empty or < 20 chars) → skipped
- Deduplication by URL hash

### Step 3 — Web Scraping (`collector.py`)

For each article, attempts to fetch the full text from the source page:
- Strips `<script>`, `<style>`, `<nav>`, `<footer>` tags
- Extracts `<p>` paragraphs longer than 60 characters
- Truncates to 1500 characters
- 0.3s delay between requests to avoid server overload
- Falls back to the NewsAPI description if scraping fails (paywall, timeout, etc.)

### Step 4 — AI Summarization (`summarizer.py`)

If `GEMINI_API_KEY` is configured, each article is processed by Google Gemini to produce:
- A concise summary
- Keywords
- Sentiment: `positif`, `négatif`, or `neutre`
- Importance score (1–5)

Without Gemini, articles are displayed in raw mode with the scraped text as-is.

---

## Interface (`app.py`)

Built with **Streamlit**, styled with the KOTA brand identity (navy `#0B1E3D`, gold `#C9A84C`, Barlow font family).

### Sidebar controls

| Control | Description |
|---|---|
| **Nombre d'articles** | Slider 5–50, default 15 |
| **Période** | Last 24h / 2 days / 3 days / 7 days |
| **Filtrer par sujet** | Filter displayed articles by subject category |
| **Sentiment** | Filter by sentiment (active only with Gemini key) |
| **Statut des services** | 🟢/🔴 live status for NewsAPI and Gemini |
| **Lancer la collecte** | Triggers the full pipeline |
| **Export PDF** | Downloads a PDF of the currently filtered articles |

### Article cards

Each card displays:
- Subject tag (gold) + source + publication date
- Title
- Summary or raw text excerpt
- Keywords (if AI active)
- Sentiment indicator with color (▲ green / ▼ red / — grey)
- Importance progress bar (if AI active)
- "Read article" link button

---

## PDF Export (`pdf_export.py`)

Generates a branded A4 PDF report with **ReportLab**.

The export respects the active filters — if you filter by "Equity Markets", only those articles are exported.

### Report structure

1. **Header** (every page) — KOTA logo + club name, report title, active filter label, gold rule
2. **Summary stats block** — article count, subject count, filter name, date
3. **Article cards** — one per article:
   - Subject tag in gold + source + date
   - Title in bold (14pt)
   - Introduction excerpt (up to 450 characters, 10pt)
   - Clickable "Read full article →" link
   - Sentiment indicator if AI was active
4. **Footer** (every page) — generation timestamp, "Confidential", page number

### File naming

```
kota_news_equity_markets_20260527_0045.pdf   ← filtered export
kota_news_all_20260527_0045.pdf              ← no filter applied
```

---

## Edge Cases & Robustness

| Scenario | Handling |
|---|---|
| NewsAPI free plan 24h blackout | `from` date forced to minimum 2 days back |
| Articles with no description | Falls back to `content` field |
| Web scraping fails / paywall | Uses NewsAPI description as fallback |
| Gemini unavailable | Raw mode activated, no crash |
| Logo file missing | Header renders text-only, no crash |
| No articles after filtering | Informative message, no export button shown |
| Special characters in titles | XML-escaped before ReportLab rendering |

---

## Dependencies

| Package | Role |
|---|---|
| `streamlit` | Web interface |
| `requests` | NewsAPI calls + web scraping |
| `beautifulsoup4` | HTML parsing for full article text |
| `python-dotenv` | Load API keys from `.env` |
| `reportlab` | PDF generation |
| `google-genai` | Gemini AI summarization (optional) |

---

## Known Limitations

- **NewsAPI free plan**: 100 requests/day, articles delayed by ~24h, no access to full article content (truncated at ~200 chars — hence the web scraping step)
- **Web scraping**: Many major financial sources (Bloomberg, FT, WSJ) are behind paywalls — the scraper will fall back to the NewsAPI excerpt for those
- **Gemini**: Summarization adds latency (~1–2s per article); on large batches consider rate limits

---

*KOTA Investment Club — Mini Projet Quant*