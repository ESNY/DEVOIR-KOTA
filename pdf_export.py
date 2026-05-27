"""
pdf_export.py
=============
Generates a branded PDF report of financial news articles for KOTA Investment Club.

Each article includes:
- Subject tag + source + date
- Title
- Summary / introduction excerpt
- Clickable URL to the full article
"""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand colours ─────────────────────────────
NAVY        = colors.HexColor("#0B1E3D")
NAVY_MID    = colors.HexColor("#122348")
NAVY_LIGHT  = colors.HexColor("#1A3160")
GOLD        = colors.HexColor("#C9A84C")
GOLD_LIGHT  = colors.HexColor("#E2C57A")
WHITE       = colors.white
BLACK       = colors.black
DARK_TEXT   = colors.HexColor("#1A1A1A")
MUTED       = colors.HexColor("#555555")
POSITIVE    = colors.HexColor("#1a8a5a")
NEGATIVE    = colors.HexColor("#c0392b")
NEUTRAL     = colors.HexColor("#555555")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

# Logo path — relative to app.py location
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "Kota -logo.png")


# ── Sentiment helpers ─────────────────────────
def _sentiment_color(sentiment: str) -> colors.Color:
    return {"positif": POSITIVE, "négatif": NEGATIVE, "positive": POSITIVE,
            "negative": NEGATIVE}.get((sentiment or "").lower(), NEUTRAL)

def _sentiment_arrow(sentiment: str) -> str:
    return {"positif": "▲", "négatif": "▼", "positive": "▲",
            "negative": "▼"}.get((sentiment or "").lower(), "—")


# ── Page template with header & footer ────────
def _make_page_template(doc, filter_label: str, generated_at: str):
    def draw_header_footer(canvas, doc):
        canvas.saveState()
        w, h = A4

        # ── Header bar (navy background) ──
        canvas.setFillColor(NAVY_MID)
        canvas.rect(0, h - 22 * mm, w, 22 * mm, fill=1, stroke=0)

        # Logo top-left (if available)
        logo_drawn = False
        if os.path.exists(LOGO_PATH):
            try:
                logo_h = 14 * mm
                logo_w = logo_h  # assume square; ReportLab will scale proportionally
                canvas.drawImage(
                    LOGO_PATH,
                    MARGIN, h - 19 * mm,
                    width=logo_w, height=logo_h,
                    preserveAspectRatio=True, mask="auto",
                )
                logo_drawn = True
            except Exception:
                pass

        # Club name — right of logo if drawn, else at margin
        text_x = MARGIN + (16 * mm if logo_drawn else 0)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(GOLD)
        canvas.drawString(text_x, h - 9 * mm, "KOTA INVESTMENT CLUB")

        # Report title (centre)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(WHITE)
        canvas.drawCentredString(w / 2, h - 10 * mm, "FINANCIAL NEWS REPORT")

        # Filter label (right)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#8DA0BB"))
        canvas.drawRightString(w - MARGIN, h - 10 * mm, filter_label)

        # Gold rule under header
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.8)
        canvas.line(0, h - 22 * mm, w, h - 22 * mm)

        # ── Footer ──
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 8 * mm, f"Generated {generated_at}")
        canvas.drawCentredString(w / 2, 8 * mm, "KOTA Investment Club — Confidential")
        canvas.drawRightString(w - MARGIN, 8 * mm, f"Page {doc.page}")

        # Gold rule above footer
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 13 * mm, w - MARGIN, 13 * mm)

        canvas.restoreState()

    frame = Frame(
        MARGIN, 16 * mm,
        PAGE_W - 2 * MARGIN, PAGE_H - 38 * mm,
        leftPadding=0, rightPadding=0,
        topPadding=4, bottomPadding=4,
    )
    return PageTemplate(id="main", frames=[frame], onPage=draw_header_footer)


# ── Style definitions ─────────────────────────
def _styles():
    base = getSampleStyleSheet()

    meta = ParagraphStyle(
        "Meta",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=MUTED,
        spaceAfter=3,
        leading=13,
    )
    article_title = ParagraphStyle(
        "ArticleTitle",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=DARK_TEXT,
        spaceAfter=5,
        leading=18,
    )
    summary_style = ParagraphStyle(
        "Summary",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=DARK_TEXT,
        spaceAfter=5,
        leading=15,
    )
    link_style = ParagraphStyle(
        "Link",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#1a5fa8"),
        spaceAfter=0,
    )
    sentiment_style = ParagraphStyle(
        "Sentiment",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        spaceAfter=0,
        alignment=TA_RIGHT,
    )
    stat_style = ParagraphStyle(
        "Stat",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=GOLD,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    stat_label = ParagraphStyle(
        "StatLabel",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=MUTED,
        spaceAfter=0,
        alignment=TA_CENTER,
    )
    return {
        "meta": meta,
        "title": article_title,
        "summary": summary_style,
        "link": link_style,
        "sentiment": sentiment_style,
        "stat": stat_style,
        "stat_label": stat_label,
    }


# ── Helpers ───────────────────────────────────
def _escape(text: str) -> str:
    return (text or "").\
        replace("&", "&amp;").\
        replace("<", "&lt;").\
        replace(">", "&gt;").\
        replace('"', "&quot;")


def _truncate(text: str, max_chars: int = 450) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def _format_date(pub) -> str:
    if hasattr(pub, "strftime"):
        return pub.strftime("%b %d, %Y · %H:%M")
    return str(pub) if pub else ""


# ── Main export function ──────────────────────
def generate_pdf(articles: list[dict], filter_label: str = "All articles") -> bytes:
    """
    Build and return a PDF report as bytes.

    Parameters
    ----------
    articles     : list of article dicts (from collector.py)
    filter_label : human-readable label of the active filter (shown in header)

    Returns
    -------
    bytes — the raw PDF content, ready for st.download_button()
    """
    buf = io.BytesIO()
    generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=26 * mm,
        bottomMargin=18 * mm,
        title="KOTA Financial News Report",
        author="KOTA Investment Club",
    )
    doc.addPageTemplates([_make_page_template(doc, filter_label, generated_at)])

    st = _styles()
    story = []
    usable_w = PAGE_W - 2 * MARGIN
    nb_articles = len(articles)
    subjects    = sorted({a.get("subject", "General") for a in articles})

    # ── Summary stats block ───────────────────
    story.append(Spacer(1, 4 * mm))

    col_w = usable_w / 4
    stats_data = [[
        Paragraph(f"<b>{nb_articles}</b>", st["stat"]),
        Paragraph(f"<b>{len(subjects)}</b>", st["stat"]),
        Paragraph(f"<b>{_escape(filter_label)}</b>", st["stat"]),
        Paragraph(f"<b>{datetime.now().strftime('%b %d, %Y')}</b>", st["stat"]),
    ],[
        Paragraph("ARTICLES", st["stat_label"]),
        Paragraph("SUBJECTS", st["stat_label"]),
        Paragraph("FILTER", st["stat_label"]),
        Paragraph("DATE", st["stat_label"]),
    ]]

    stats_tbl = Table(stats_data, colWidths=[col_w] * 4)
    stats_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#F5F7FA")),
        ("BOX",           (0, 0), (-1, -1), 0.8, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E6EF")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(stats_tbl)
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=1.2, color=GOLD, spaceAfter=6 * mm))

    # ── Article cards ─────────────────────────
    for idx, art in enumerate(articles, 1):
        title     = _escape(art.get("title", "Untitled"))
        source    = _escape(art.get("source", "Unknown"))
        subject   = _escape(art.get("subject", "General"))
        pub_str   = _format_date(art.get("published"))
        link      = art.get("link", "")
        summary   = _escape(_truncate(art.get("summary", ""), 450))
        sentiment = art.get("sentiment", "")
        ia_active = not art.get("_fallback", True)

        # ── Meta row: subject · source · date | sentiment ──
        meta_left = Paragraph(
            f'<font color="#C9A84C"><b>{subject.upper()}</b></font>'
            f'&nbsp;&nbsp;'
            f'<font color="#777777">{source} · {pub_str}</font>',
            st["meta"]
        )

        if ia_active and sentiment:
            sc  = _sentiment_color(sentiment)
            arr = _sentiment_arrow(sentiment)
            r, g, b = int(sc.red * 255), int(sc.green * 255), int(sc.blue * 255)
            hex_col = f"#{r:02X}{g:02X}{b:02X}"
            meta_right = Paragraph(
                f'<font color="{hex_col}"><b>{arr} {sentiment.upper()}</b></font>',
                st["sentiment"]
            )
        else:
            meta_right = Paragraph("", st["sentiment"])

        meta_tbl = Table(
            [[meta_left, meta_right]],
            colWidths=[usable_w * 0.75, usable_w * 0.25]
        )
        meta_tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_tbl)

        # ── Article title ──
        story.append(Paragraph(f"<b>{title}</b>", st["title"]))

        # ── Summary excerpt ──
        if summary:
            story.append(Paragraph(summary, st["summary"]))

        # ── Clickable link ──
        if link:
            safe_link = link.replace("&", "&amp;")
            story.append(Paragraph(
                f'<link href="{safe_link}"><u>Read full article →</u></link>',
                st["link"]
            ))

        story.append(Spacer(1, 5 * mm))
        if idx < nb_articles:
            story.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#CCCCCC"),
                spaceAfter=5 * mm,
            ))

    # ── End of report ────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=3 * mm))
    story.append(Paragraph(
        f'<font color="#777777" size="8">End of report · {nb_articles} articles · KOTA Investment Club</font>',
        st["meta"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()