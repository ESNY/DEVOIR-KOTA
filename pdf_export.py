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
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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

NAVY_MID = colors.HexColor("#122348")
GOLD = colors.HexColor("#C9A84C")
WHITE = colors.white
DARK_TEXT = colors.HexColor("#1A1A1A")
MUTED = colors.HexColor("#555555")
POSITIVE = colors.HexColor("#1a8a5a")
NEGATIVE = colors.HexColor("#c0392b")
NEUTRAL = colors.HexColor("#555555")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "Kota -logo.png")


def _sentiment_color(sentiment: str) -> colors.Color:
    return {
        "positive": POSITIVE,
        "negative": NEGATIVE,
        "neutral": NEUTRAL,
    }.get((sentiment or "").lower(), NEUTRAL)


def _sentiment_marker(sentiment: str) -> str:
    return {
        "positive": "UP",
        "negative": "DOWN",
        "neutral": "FLAT",
    }.get((sentiment or "").lower(), "FLAT")


def _make_page_template(doc, filter_label: str, generated_at: str):
    def draw_header_footer(canvas, doc):
        canvas.saveState()
        width, height = A4

        canvas.setFillColor(NAVY_MID)
        canvas.rect(0, height - 22 * mm, width, 22 * mm, fill=1, stroke=0)

        logo_drawn = False
        if os.path.exists(LOGO_PATH):
            try:
                logo_height = 14 * mm
                logo_width = logo_height
                canvas.drawImage(
                    LOGO_PATH,
                    MARGIN,
                    height - 19 * mm,
                    width=logo_width,
                    height=logo_height,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                logo_drawn = True
            except Exception:
                pass

        text_x = MARGIN + (16 * mm if logo_drawn else 0)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(GOLD)
        canvas.drawString(text_x, height - 9 * mm, "KOTA INVESTMENT CLUB")

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(WHITE)
        canvas.drawCentredString(width / 2, height - 10 * mm, "FINANCIAL NEWS REPORT")

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#8DA0BB"))
        canvas.drawRightString(width - MARGIN, height - 10 * mm, filter_label)

        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.8)
        canvas.line(0, height - 22 * mm, width, height - 22 * mm)

        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 8 * mm, f"Generated {generated_at}")
        canvas.drawCentredString(width / 2, 8 * mm, "KOTA Investment Club - Confidential")
        canvas.drawRightString(width - MARGIN, 8 * mm, f"Page {doc.page}")

        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, 13 * mm, width - MARGIN, 13 * mm)

        canvas.restoreState()

    frame = Frame(
        MARGIN,
        16 * mm,
        PAGE_W - 2 * MARGIN,
        PAGE_H - 38 * mm,
        leftPadding=0,
        rightPadding=0,
        topPadding=4,
        bottomPadding=4,
    )
    return PageTemplate(id="main", frames=[frame], onPage=draw_header_footer)


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


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _truncate(text: str, max_chars: int = 450) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def _format_date(published_at) -> str:
    if hasattr(published_at, "strftime"):
        return published_at.strftime("%b %d, %Y at %H:%M")
    return str(published_at) if published_at else ""


def generate_pdf(articles: list[dict], filter_label: str = "All articles") -> bytes:
    """
    Build and return a PDF report as bytes.

    Parameters
    ----------
    articles: list of article dicts from collector.py
    filter_label: human-readable label of the active filter shown in the header

    Returns
    -------
    bytes: raw PDF content, ready for st.download_button()
    """
    buffer = io.BytesIO()
    generated_at = datetime.now().strftime("%B %d, %Y at %H:%M")

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=26 * mm,
        bottomMargin=18 * mm,
        title="KOTA Financial News Report",
        author="KOTA Investment Club",
    )
    doc.addPageTemplates([_make_page_template(doc, filter_label, generated_at)])

    styles = _styles()
    story = []
    usable_width = PAGE_W - 2 * MARGIN
    article_count = len(articles)
    subjects = sorted({article.get("subject", "General") for article in articles})

    story.append(Spacer(1, 4 * mm))

    column_width = usable_width / 4
    stats_data = [[
        Paragraph(f"<b>{article_count}</b>", styles["stat"]),
        Paragraph(f"<b>{len(subjects)}</b>", styles["stat"]),
        Paragraph(f"<b>{_escape(filter_label)}</b>", styles["stat"]),
        Paragraph(f"<b>{datetime.now().strftime('%b %d, %Y')}</b>", styles["stat"]),
    ], [
        Paragraph("ARTICLES", styles["stat_label"]),
        Paragraph("SUBJECTS", styles["stat_label"]),
        Paragraph("FILTER", styles["stat_label"]),
        Paragraph("DATE", styles["stat_label"]),
    ]]

    stats_table = Table(stats_data, colWidths=[column_width] * 4)
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FA")),
        ("BOX", (0, 0), (-1, -1), 0.8, GOLD),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E6EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=1.2, color=GOLD, spaceAfter=6 * mm))

    for index, article in enumerate(articles, 1):
        title = _escape(article.get("title", "Untitled"))
        source = _escape(article.get("source", "Unknown"))
        subject = _escape(article.get("subject", "General"))
        published_text = _format_date(article.get("published"))
        link = article.get("link", "")
        summary = _escape(_truncate(article.get("summary", ""), 450))
        sentiment = article.get("sentiment", "")
        ai_active = not article.get("_fallback", True)

        meta_left = Paragraph(
            f'<font color="#C9A84C"><b>{subject.upper()}</b></font>'
            f'&nbsp;&nbsp;'
            f'<font color="#777777">{source} - {published_text}</font>',
            styles["meta"],
        )

        if ai_active and sentiment:
            sentiment_color = _sentiment_color(sentiment)
            marker = _sentiment_marker(sentiment)
            red = int(sentiment_color.red * 255)
            green = int(sentiment_color.green * 255)
            blue = int(sentiment_color.blue * 255)
            hex_color = f"#{red:02X}{green:02X}{blue:02X}"
            meta_right = Paragraph(
                f'<font color="{hex_color}"><b>{marker} {sentiment.upper()}</b></font>',
                styles["sentiment"],
            )
        else:
            meta_right = Paragraph("", styles["sentiment"])

        meta_table = Table(
            [[meta_left, meta_right]],
            colWidths=[usable_width * 0.75, usable_width * 0.25],
        )
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(meta_table)

        story.append(Paragraph(f"<b>{title}</b>", styles["title"]))

        if summary:
            story.append(Paragraph(summary, styles["summary"]))

        if link:
            safe_link = link.replace("&", "&amp;")
            story.append(Paragraph(
                f'<link href="{safe_link}"><u>Read full article</u></link>',
                styles["link"],
            ))

        story.append(Spacer(1, 5 * mm))
        if index < article_count:
            story.append(HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#CCCCCC"),
                spaceAfter=5 * mm,
            ))

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=3 * mm))
    story.append(Paragraph(
        f'<font color="#777777" size="8">End of report - {article_count} articles - KOTA Investment Club</font>',
        styles["meta"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
