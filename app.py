"""
app.py
======
Automated financial news aggregator - KOTA Investment Club.
Streamlit interface with KOTA branding (navy, white, gold).

Run: streamlit run app.py
"""

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from collector import SUBJECTS, collect_news, enrich_with_full_text
from pdf_export import generate_pdf
from summarizer import summarize_all

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Inject the Gemini key into the summarizer when available.
if GEMINI_API_KEY:
    import summarizer
    from google import genai as _genai

    summarizer._api_key = GEMINI_API_KEY
    summarizer._client = _genai.Client(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="KOTA - Financial Aggregator",
    page_icon="assets/Kota -logo.png",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700;800&family=Barlow+Condensed:wght@700;800&display=swap');

:root {
    --navy:      #0B1E3D;
    --navy-mid:  #122348;
    --navy-light:#1A3160;
    --gold:      #C9A84C;
    --gold-light:#E2C57A;
    --white:     #FFFFFF;
    --off-white: #F0F4FA;
    --muted:     #8DA0BB;
    --positive:  #2ECC8E;
    --negative:  #E05252;
    --neutral:   #8DA0BB;
}

html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif !important;
    background-color: var(--navy) !important;
    color: var(--white) !important;
}

.stApp {
    background-color: var(--navy) !important;
    background-image:
        radial-gradient(ellipse at 10% 0%, rgba(201,168,76,0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 90% 100%, rgba(26,49,96,0.8) 0%, transparent 60%);
}

[data-testid="stSidebar"] {
    background-color: var(--navy-mid) !important;
    border-right: 1px solid rgba(201,168,76,0.2) !important;
}
[data-testid="stSidebar"] * {
    color: var(--white) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stToggle label {
    color: var(--muted) !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--gold), var(--gold-light)) !important;
    color: var(--navy) !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 800 !important;
    font-size: 15px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 12px 24px !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(201,168,76,0.35) !important;
}

.stLinkButton a {
    background: transparent !important;
    border: 1px solid rgba(201,168,76,0.4) !important;
    color: var(--gold-light) !important;
    font-size: 12px !important;
    border-radius: 4px !important;
    font-family: 'Barlow', sans-serif !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stLinkButton a:hover {
    border-color: var(--gold) !important;
    background: rgba(201,168,76,0.08) !important;
}

[data-testid="metric-container"] {
    background: var(--navy-mid) !important;
    border: 1px solid rgba(201,168,76,0.15) !important;
    border-radius: 8px !important;
    padding: 16px !important;
}
[data-testid="metric-container"] label {
    color: var(--muted) !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 600 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--white) !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--navy-mid) !important;
    border: 1px solid rgba(201,168,76,0.12) !important;
    border-radius: 8px !important;
    padding: 4px !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(201,168,76,0.35) !important;
}

[data-testid="stSelectbox"] > div > div,
.stSlider {
    background: transparent !important;
}
.stSelectbox select,
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: var(--navy-light) !important;
    border-color: rgba(201,168,76,0.2) !important;
    color: var(--white) !important;
}

hr {
    border-color: rgba(201,168,76,0.15) !important;
}

.stProgress > div > div {
    background: linear-gradient(90deg, var(--gold), var(--gold-light)) !important;
}
.stProgress > div {
    background: rgba(201,168,76,0.15) !important;
}

[data-testid="stStatusWidget"] {
    background: var(--navy-light) !important;
    border-color: rgba(201,168,76,0.2) !important;
}

[data-testid="stNotification"] {
    background: var(--navy-light) !important;
    border-left-color: var(--gold) !important;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy-light); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }
</style>
""", unsafe_allow_html=True)

logo_col, title_col = st.columns([1, 6])
with logo_col:
    try:
        st.image("assets/Kota -logo.png", width=64)
    except Exception:
        st.markdown("KOTA")
with title_col:
    st.markdown("""
    <div style="padding-top:6px">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;
                    letter-spacing:0.2em;text-transform:uppercase;color:#C9A84C;margin-bottom:2px">
            KOTA INVESTMENT CLUB
        </div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:800;
                    text-transform:uppercase;letter-spacing:0.05em;color:#FFFFFF;line-height:1">
            FINANCIAL NEWS AGGREGATOR
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(
    f'<div style="font-size:12px;color:#8DA0BB;margin-top:4px;margin-bottom:16px">'
    f'Market Intelligence Report - {datetime.now().strftime("%B %d, %Y at %H:%M")}'
    f'</div>',
    unsafe_allow_html=True,
)
st.divider()

with st.sidebar:
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:800;
                text-transform:uppercase;letter-spacing:0.1em;color:#C9A84C;
                padding:16px 0 8px 0;border-bottom:1px solid rgba(201,168,76,0.2);
                margin-bottom:16px">
        CONFIGURATION
    </div>
    """, unsafe_allow_html=True)

    article_count = st.slider("Number of articles", 5, 50, 15, 5)

    days_back = st.selectbox(
        "Period",
        options=[1, 2, 3, 7],
        format_func=lambda value: "Last 24 hours" if value == 1 else f"Last {value} days",
    )

    keyword_filtering = True

    st.divider()

    available_subjects = ["All"] + list(SUBJECTS.keys()) + ["General"]
    subject_filter = st.selectbox("Filter by subject", available_subjects)

    ai_available = bool(GEMINI_API_KEY)
    sentiment_filter = st.selectbox(
        "Sentiment",
        ["All", "positive", "negative", "neutral"],
        disabled=not ai_available,
        help="Available when the Gemini key is configured.",
    )
    st.divider()

    st.markdown("""
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;
                color:#8DA0BB;margin-bottom:8px;font-weight:700">
        Service status
    </div>
    """, unsafe_allow_html=True)

    news_status = "OK" if NEWS_API_KEY else "MISSING"
    gemini_status = "OK" if GEMINI_API_KEY else "OFF"
    st.markdown(
        f'<div style="font-size:13px;line-height:2">'
        f'{news_status} NewsAPI &nbsp;&nbsp; {gemini_status} AI summary'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not NEWS_API_KEY:
        st.warning("NEWS_API_KEY is missing from the .env file")

    st.divider()

    run_collection = st.button(
        "START COLLECTION",
        type="primary",
        use_container_width=True,
        disabled=not NEWS_API_KEY,
    )

    if "articles" in st.session_state:
        st.divider()
        st.markdown(
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;'
            'color:#8DA0BB;margin-bottom:8px;font-weight:700">Export</div>',
            unsafe_allow_html=True,
        )

        export_articles = list(st.session_state["articles"])
        if subject_filter != "All":
            export_articles = [article for article in export_articles if article.get("subject") == subject_filter]
        if st.session_state.get("ai_active") and sentiment_filter != "All":
            export_articles = [article for article in export_articles if article.get("sentiment") == sentiment_filter]

        filter_parts = []
        if subject_filter != "All":
            filter_parts.append(subject_filter)
        if st.session_state.get("ai_active") and sentiment_filter != "All":
            filter_parts.append(sentiment_filter.capitalize())
        filter_label = " - ".join(filter_parts) if filter_parts else "All articles"

        st.markdown(
            f'<div style="font-size:12px;color:#8DA0BB;margin-bottom:10px">'
            f'{len(export_articles)} article(s) in current view</div>',
            unsafe_allow_html=True,
        )

        if export_articles:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            slug = subject_filter.replace(" ", "_").lower() if subject_filter != "All" else "all"

            try:
                pdf_bytes = generate_pdf(export_articles, filter_label=filter_label)
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"kota_news_{slug}_{timestamp}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as error:
                st.error(f"PDF generation failed: {error}")
        else:
            st.caption("No articles match current filters.")

if run_collection and NEWS_API_KEY:
    with st.status("Collecting news...", expanded=True) as status:
        st.write("Querying NewsAPI...")
        try:
            articles = collect_news(
                api_key=NEWS_API_KEY,
                max_articles=article_count,
                filter_keywords=keyword_filtering,
                days_back=days_back,
            )
        except Exception as error:
            st.error(f"Collection failed: {error}")
            st.stop()

        if not articles:
            status.update(label="No articles retrieved", state="error")
            st.error("No articles retrieved. Check NEWS_API_KEY in .env or widen the period.")
            st.stop()

        st.write(f"{len(articles)} articles collected.")
        status.update(label=f"{len(articles)} articles collected", state="complete")

    with st.status("Retrieving full text...", expanded=True) as status:
        st.write("Scraping each article to retrieve the full text...")
        try:
            articles = enrich_with_full_text(articles)
            scraped_count = sum(1 for article in articles if article.get("scraped"))
            status.update(
                label=f"Text enriched ({scraped_count}/{len(articles)} articles scraped)",
                state="complete",
            )
        except Exception as error:
            status.update(label=f"Partial scraping - {error}", state="error")

    ai_active = bool(GEMINI_API_KEY)

    if ai_active:
        with st.status("Running AI analysis...", expanded=True) as status:
            st.write("Summarizing and analyzing sentiment with Gemini...")
            try:
                articles = summarize_all(articles)
                fallback_count = sum(1 for article in articles if article.get("_fallback"))
                status.update(
                    label=f"Analysis complete ({fallback_count} in raw mode)",
                    state="complete",
                )
            except Exception as error:
                st.warning(f"AI analysis unavailable - raw mode enabled. ({error})")
                ai_active = False

    if not ai_active:
        for article in articles:
            article.setdefault("_fallback", True)
            article.setdefault("sentiment", "neutral")
            article.setdefault("keywords", [])
            article.setdefault("importance", 1)

    st.session_state["articles"] = articles
    st.session_state["ai_active"] = ai_active
    st.session_state["collection_date"] = datetime.now()

if "articles" in st.session_state:
    articles = st.session_state["articles"]
    ai_active = st.session_state.get("ai_active", False)
    collection_date = st.session_state.get("collection_date", datetime.now())

    st.divider()

    displayed_articles = list(articles)

    if subject_filter != "All":
        displayed_articles = [article for article in displayed_articles if article.get("subject") == subject_filter]

    if ai_active and sentiment_filter != "All":
        displayed_articles = [article for article in displayed_articles if article.get("sentiment") == sentiment_filter]

    if not displayed_articles:
        st.info("No articles match the selected filters.")
        st.stop()

    st.markdown(
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:13px;'
        f'text-transform:uppercase;letter-spacing:0.12em;color:#8DA0BB;margin-bottom:16px">'
        f'{len(displayed_articles)} RESULT(S) - Collected on {collection_date.strftime("%m/%d/%Y at %H:%M")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    for article in displayed_articles:
        sentiment = article.get("sentiment", "neutral")
        importance = article.get("importance", 1)
        keywords = article.get("keywords", [])
        fallback = article.get("_fallback", True)
        subject = article.get("subject", "General")
        published_at = article.get("published")
        published_text = (
            published_at.strftime("%d %b %Y at %H:%M")
            if hasattr(published_at, "strftime")
            else str(published_at)
        )

        sentiment_color = {"positive": "#2ECC8E", "negative": "#E05252", "neutral": "#8DA0BB"}.get(
            sentiment,
            "#8DA0BB",
        )
        sentiment_marker = {"positive": "UP", "negative": "DOWN", "neutral": "FLAT"}.get(sentiment, "FLAT")

        with st.container(border=True):
            meta_col, sentiment_col = st.columns([4, 1])
            with meta_col:
                st.markdown(
                    f'<span style="font-size:11px;font-weight:700;text-transform:uppercase;'
                    f'letter-spacing:0.12em;color:#C9A84C">{subject}</span>'
                    f'&nbsp;&nbsp;'
                    f'<span style="font-size:11px;color:#8DA0BB">{article["source"]} - {published_text}</span>',
                    unsafe_allow_html=True,
                )
            with sentiment_col:
                if ai_active and not fallback:
                    st.markdown(
                        f'<div style="text-align:right;font-size:12px;font-weight:700;color:{sentiment_color}">'
                        f'{sentiment_marker} {sentiment.upper()}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown(
                f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;'
                f'font-weight:700;color:#FFFFFF;line-height:1.3;margin:8px 0 10px 0">'
                f'{article["title"]}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div style="font-size:14px;line-height:1.7;color:#C8D8EE">{article["summary"]}</div>',
                unsafe_allow_html=True,
            )

            footer_col, importance_col = st.columns([3, 1])
            with footer_col:
                if keywords:
                    tags_html = " ".join(
                        f'<span style="background:rgba(201,168,76,0.12);color:#E2C57A;'
                        f'padding:2px 10px;border-radius:3px;font-size:11px;font-weight:600;'
                        f'text-transform:uppercase;letter-spacing:0.06em">{keyword}</span>'
                        for keyword in keywords
                    )
                    st.markdown(tags_html, unsafe_allow_html=True)
                elif fallback:
                    st.markdown(
                        '<span style="color:#8DA0BB;font-size:11px;'
                        'text-transform:uppercase;letter-spacing:0.08em">Raw article</span>',
                        unsafe_allow_html=True,
                    )

            with importance_col:
                if ai_active and not fallback:
                    st.progress(importance / 5, text=f"Importance {importance}/5")

            st.link_button("Read article", article.get("link", "#"))

else:
    st.markdown("""
    <div style="max-width:600px;margin:60px auto;text-align:center">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;
                    text-transform:uppercase;letter-spacing:0.2em;color:#C9A84C;margin-bottom:16px">
            KOTA Investment Club
        </div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:40px;font-weight:800;
                    text-transform:uppercase;color:#FFFFFF;line-height:1.1;margin-bottom:24px">
            Market Intelligence<br>Automated
        </div>
        <div style="font-size:15px;color:#8DA0BB;line-height:1.8;margin-bottom:40px">
            Automated financial news collection,<br>
            subject classification, and AI sentiment analysis.
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:left;margin-bottom:40px">
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">NewsAPI Collection</div>
                <div style="font-size:13px;color:#8DA0BB">Real-time financial news from major global sources</div>
            </div>
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">Web Scraping</div>
                <div style="font-size:13px;color:#8DA0BB">Full-text retrieval from each article source</div>
            </div>
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">Classification</div>
                <div style="font-size:13px;color:#8DA0BB">Automatic subject sorting: ECB, markets, commodities...</div>
            </div>
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">AI Analysis</div>
                <div style="font-size:13px;color:#8DA0BB">Summary, keywords, and market sentiment through Gemini</div>
            </div>
        </div>
        <div style="font-size:13px;color:#8DA0BB">
            Configure your settings in the sidebar and start the collection
        </div>
    </div>
    """, unsafe_allow_html=True)
