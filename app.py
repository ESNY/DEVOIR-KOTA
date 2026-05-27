"""
app.py
======
Agrégateur automatisé d'actualités financières — KOTA Investment Club
Interface Streamlit avec DA KOTA (bleu marine, blanc, gold)

Lancer : streamlit run app.py
"""

import os
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from collector import collect_news, enrich_with_full_text, SUBJECTS
from summarizer import summarize_all
from pdf_export import generate_pdf

# ──────────────────────────────────────────────
# Chargement des clés API depuis .env
# ──────────────────────────────────────────────
load_dotenv()
NEWS_API_KEY   = os.getenv("NEWS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Injecter la clé Gemini dans le summarizer si disponible
if GEMINI_API_KEY:
    import summarizer
    from google import genai as _genai
    summarizer._api_key = GEMINI_API_KEY
    summarizer._client  = _genai.Client(api_key=GEMINI_API_KEY)

# ──────────────────────────────────────────────
# Configuration de la page
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="KOTA - Agrégateur Financier",
    page_icon="assets/Kota -logo.png",
    layout="wide",
)

# ──────────────────────────────────────────────
# CSS — DA KOTA
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700;800&family=Barlow+Condensed:wght@700;800&display=swap');

/* ── Variables ── */
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

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif !important;
    background-color: var(--navy) !important;
    color: var(--white) !important;
}

/* ── Fond principal ── */
.stApp {
    background-color: var(--navy) !important;
    background-image:
        radial-gradient(ellipse at 10% 0%, rgba(201,168,76,0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 90% 100%, rgba(26,49,96,0.8) 0%, transparent 60%);
}

/* ── Sidebar ── */
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

/* ── Bouton principal ── */
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

/* ── Link buttons ── */
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

/* ── Métriques ── */
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

/* ── Containers (cartes articles) ── */
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

/* ── Selectbox / Slider ── */
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

/* ── Divider ── */
hr {
    border-color: rgba(201,168,76,0.15) !important;
}

/* ── Progress bar ── */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--gold), var(--gold-light)) !important;
}
.stProgress > div {
    background: rgba(201,168,76,0.15) !important;
}

/* ── Status / spinners ── */
[data-testid="stStatusWidget"] {
    background: var(--navy-light) !important;
    border-color: rgba(201,168,76,0.2) !important;
}

/* ── Info / Warning boxes ── */
[data-testid="stNotification"] {
    background: var(--navy-light) !important;
    border-left-color: var(--gold) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy-light); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--gold); }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Header KOTA
# ──────────────────────────────────────────────
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        st.image("assets/Kota -logo.png", width=64)
    except Exception:
        st.markdown("🦁")
with col_title:
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
    f'Market Intelligence Report — {datetime.now().strftime("%B %d, %Y · %H:%M")}'
    f'</div>',
    unsafe_allow_html=True
)
st.divider()


# ──────────────────────────────────────────────
# Sidebar — configuration uniquement (pas de clés)
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:800;
                text-transform:uppercase;letter-spacing:0.1em;color:#C9A84C;
                padding:16px 0 8px 0;border-bottom:1px solid rgba(201,168,76,0.2);
                margin-bottom:16px">
        ⚙ CONFIGURATION
    </div>
    """, unsafe_allow_html=True)

    nb_articles = st.slider("Nombre d'articles", 5, 50, 15, 5)

    days_back = st.selectbox(
        "Période",
        options=[1, 2, 3, 7],
        format_func=lambda x: "Dernières 24h" if x == 1 else f"Derniers {x} jours",
    )

    filtrage_keywords = True  # Filtrage financier strict activé par défaut

    st.divider()

    sujets_disponibles = ["Tous"] + list(SUBJECTS.keys()) + ["Général"]
    filtre_sujet = st.selectbox("Filtrer par sujet", sujets_disponibles)

    # Filtres IA (toujours visibles, actifs seulement si IA dispo)
    ia_disponible = bool(GEMINI_API_KEY)
    filtre_sentiment  = st.selectbox(
        "Sentiment",
        ["Tous", "positif", "négatif", "neutre"],
        disabled=not ia_disponible,
        help="Disponible avec la clé Gemini configurée.",
    )
    st.divider()

    # Statut des services (discret, sans exposer les clés)
    st.markdown("""
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;
                color:#8DA0BB;margin-bottom:8px;font-weight:700">
        Statut des services
    </div>
    """, unsafe_allow_html=True)

    news_ok   = "🟢" if NEWS_API_KEY   else "🔴"
    gemini_ok = "🟢" if GEMINI_API_KEY else "🟡"
    st.markdown(
        f'<div style="font-size:13px;line-height:2">'
        f'{news_ok} NewsAPI &nbsp;&nbsp; {gemini_ok} Résumé IA'
        f'</div>',
        unsafe_allow_html=True
    )

    if not NEWS_API_KEY:
        st.warning("NEWS_API_KEY manquante dans le fichier .env")

    st.divider()

    lancer = st.button(
        "LANCER LA COLLECTE",
        type="primary",
        use_container_width=True,
        disabled=not NEWS_API_KEY,
    )

    # ── Export PDF ──────────────────────────────
    if "articles" in st.session_state:
        st.divider()
        st.markdown(
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:0.1em;'
            'color:#8DA0BB;margin-bottom:8px;font-weight:700">&#8964; Export</div>',
            unsafe_allow_html=True,
        )

        # Reproduce active filters to get the exact visible list
        _export_list = list(st.session_state["articles"])
        if filtre_sujet != "Tous":
            _export_list = [a for a in _export_list if a.get("subject") == filtre_sujet]
        if st.session_state.get("ia_active") and filtre_sentiment != "Tous":
            _export_list = [a for a in _export_list if a.get("sentiment") == filtre_sentiment]

        # Human-readable filter label for the PDF header
        _parts = []
        if filtre_sujet != "Tous":
            _parts.append(filtre_sujet)
        if st.session_state.get("ia_active") and filtre_sentiment != "Tous":
            _parts.append(filtre_sentiment.capitalize())
        _filter_label = " · ".join(_parts) if _parts else "All articles"

        st.markdown(
            f'<div style="font-size:12px;color:#8DA0BB;margin-bottom:10px">'
            f'{len(_export_list)} article(s) in current view</div>',
            unsafe_allow_html=True,
        )

        if _export_list:
            _ts = datetime.now().strftime("%Y%m%d_%H%M")
            _slug = filtre_sujet.replace(" ", "_").lower() if filtre_sujet != "Tous" else "all"

            try:
                _pdf_bytes = generate_pdf(_export_list, filter_label=_filter_label)
                st.download_button(
                    label="⬇ Export PDF",
                    data=_pdf_bytes,
                    file_name=f"kota_news_{_slug}_{_ts}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as _e:
                st.error(f"PDF generation failed: {_e}")
        else:
            st.caption("No articles match current filters.")


# ──────────────────────────────────────────────
# Logique principale
# ──────────────────────────────────────────────
if lancer and NEWS_API_KEY:

    # Étape 1 : Collecte NewsAPI
    with st.status("Collecte des actualités en cours…", expanded=True) as status:
        st.write("Interrogation de NewsAPI…")
        try:
            articles = collect_news(
                api_key=NEWS_API_KEY,
                max_articles=nb_articles,
                filter_keywords=filtrage_keywords,
                days_back=days_back,
            )
        except Exception as e:
            st.error(f"Erreur lors de la collecte : {e}")
            st.stop()

        if not articles:
            status.update(label="Aucun article récupéré", state="error")
            st.error("Aucun article récupéré. Vérifiez NEWS_API_KEY dans .env ou élargissez la période.")
            st.stop()

        st.write(f"✓ {len(articles)} articles collectés.")
        status.update(label=f"✓ {len(articles)} articles collectés", state="complete")

    # Étape 2 : Web scraping du texte complet
    with st.status("Récupération du texte complet…", expanded=True) as status:
        st.write("Scraping de chaque article pour obtenir le texte intégral…")
        try:
            articles = enrich_with_full_text(articles)
            scraped  = sum(1 for a in articles if a.get("scraped"))
            status.update(
                label=f"✓ Texte enrichi ({scraped}/{len(articles)} articles scrapés)",
                state="complete",
            )
        except Exception as e:
            status.update(label=f"Scraping partiel — {e}", state="error")

    # Étape 3 : Résumé IA
    ia_active = bool(GEMINI_API_KEY)

    if ia_active:
        with st.status("Analyse IA en cours…", expanded=True) as status:
            st.write("Résumé et analyse de sentiment via Gemini…")
            try:
                articles  = summarize_all(articles)
                nb_fb     = sum(1 for a in articles if a.get("_fallback"))
                status.update(
                    label=f"✓ Analyse terminée ({nb_fb} en mode brut)",
                    state="complete",
                )
            except Exception as e:
                st.warning(f"Analyse IA indisponible — mode brut activé. ({e})")
                ia_active = False
    
    if not ia_active:
        for art in articles:
            art.setdefault("_fallback",  True)
            art.setdefault("sentiment",  "neutre")
            art.setdefault("keywords",   [])
            art.setdefault("importance", 1)

    st.session_state["articles"]      = articles
    st.session_state["ia_active"]     = ia_active
    st.session_state["date_collecte"] = datetime.now()


# ──────────────────────────────────────────────
# Affichage des résultats
# ──────────────────────────────────────────────
if "articles" in st.session_state:
    articles  = st.session_state["articles"]
    ia_active = st.session_state.get("ia_active", False)
    date_col  = st.session_state.get("date_collecte", datetime.now())

    st.divider()

    # ── Application des filtres ──────────────────
    affichage = list(articles)

    if filtre_sujet != "Tous":
        affichage = [a for a in affichage if a.get("subject") == filtre_sujet]

    if ia_active:
        if filtre_sentiment != "Tous":
            affichage = [a for a in affichage if a.get("sentiment") == filtre_sentiment]

    if not affichage:
        st.info("Aucun article ne correspond aux filtres sélectionnés.")
        st.stop()

    st.markdown(
        f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:13px;'
        f'text-transform:uppercase;letter-spacing:0.12em;color:#8DA0BB;margin-bottom:16px">'
        f'{len(affichage)} RÉSULTAT(S) — Collecte du {date_col.strftime("%d/%m/%Y à %H:%M")}'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Cartes articles ──────────────────────────
    for art in affichage:
        sentiment  = art.get("sentiment",  "neutre")
        importance = art.get("importance", 1)
        keywords   = art.get("keywords",   [])
        fallback   = art.get("_fallback",  True)
        subject    = art.get("subject",    "Général")
        pub        = art.get("published")
        pub_str    = pub.strftime("%d %b %Y · %H:%M") if hasattr(pub, "strftime") else str(pub)

        # Couleurs sentiment
        sent_color = {"positif": "#2ECC8E", "négatif": "#E05252", "neutre": "#8DA0BB"}.get(sentiment, "#8DA0BB")
        sent_emoji = {"positif": "▲", "négatif": "▼", "neutre": "—"}.get(sentiment, "—")

        with st.container(border=True):
            # En-tête : sujet + sentiment + date
            meta_col1, meta_col2 = st.columns([4, 1])
            with meta_col1:
                st.markdown(
                    f'<span style="font-size:11px;font-weight:700;text-transform:uppercase;'
                    f'letter-spacing:0.12em;color:#C9A84C">{subject}</span>'
                    f'&nbsp;&nbsp;'
                    f'<span style="font-size:11px;color:#8DA0BB">{art["source"]} · {pub_str}</span>',
                    unsafe_allow_html=True
                )
            with meta_col2:
                if ia_active and not fallback:
                    st.markdown(
                        f'<div style="text-align:right;font-size:12px;font-weight:700;color:{sent_color}">'
                        f'{sent_emoji} {sentiment.upper()}</div>',
                        unsafe_allow_html=True
                    )

            # Titre
            st.markdown(
                f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;'
                f'font-weight:700;color:#FFFFFF;line-height:1.3;margin:8px 0 10px 0">'
                f'{art["title"]}</div>',
                unsafe_allow_html=True
            )

            # Texte de l'article
            st.markdown(
                f'<div style="font-size:14px;line-height:1.7;color:#C8D8EE">{art["summary"]}</div>',
                unsafe_allow_html=True
            )

            # Mots-clés + importance
            footer_col1, footer_col2 = st.columns([3, 1])
            with footer_col1:
                if keywords:
                    tags_html = " ".join(
                        f'<span style="background:rgba(201,168,76,0.12);color:#E2C57A;'
                        f'padding:2px 10px;border-radius:3px;font-size:11px;font-weight:600;'
                        f'text-transform:uppercase;letter-spacing:0.06em">{kw}</span>'
                        for kw in keywords
                    )
                    st.markdown(tags_html, unsafe_allow_html=True)
                elif fallback:
                    st.markdown(
                        '<span style="color:#8DA0BB;font-size:11px;'
                        'text-transform:uppercase;letter-spacing:0.08em">Article brut</span>',
                        unsafe_allow_html=True
                    )

            with footer_col2:
                if ia_active and not fallback:
                    st.progress(importance / 5, text=f"Importance {importance}/5")

            st.link_button("Lire l'article →", art.get("link", "#"))


# ──────────────────────────────────────────────
# Page d'accueil (avant le premier lancement)
# ──────────────────────────────────────────────
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
            Collecte automatique des actualités financières,<br>
            classification par thème et analyse de sentiment IA.
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:left;margin-bottom:40px">
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="color:#C9A84C;font-size:20px;margin-bottom:8px">📡</div>
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">Collecte NewsAPI</div>
                <div style="font-size:13px;color:#8DA0BB">Actualités financières en temps réel depuis les grandes sources mondiales</div>
            </div>
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="color:#C9A84C;font-size:20px;margin-bottom:8px">🌐</div>
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">Web Scraping</div>
                <div style="font-size:13px;color:#8DA0BB">Récupération du texte complet de chaque article à la source</div>
            </div>
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="color:#C9A84C;font-size:20px;margin-bottom:8px">🏷️</div>
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">Classification</div>
                <div style="font-size:13px;color:#8DA0BB">Tri automatique par sujet : BCE, Marchés, Matières premières…</div>
            </div>
            <div style="background:rgba(201,168,76,0.06);border:1px solid rgba(201,168,76,0.15);
                        border-radius:8px;padding:16px">
                <div style="color:#C9A84C;font-size:20px;margin-bottom:8px">🤖</div>
                <div style="font-weight:700;font-size:14px;margin-bottom:4px">Analyse IA</div>
                <div style="font-size:13px;color:#8DA0BB">Résumé, mots-clés et sentiment de marché via Gemini</div>
            </div>
        </div>
        <div style="font-size:13px;color:#8DA0BB">
            ← Configurez vos paramètres dans le panneau et lancez la collecte
        </div>
    </div>
    """, unsafe_allow_html=True)