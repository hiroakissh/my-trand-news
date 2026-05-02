from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .models import NewsItem, TopicDigest


BODY_FONT = "HeiseiKakuGo-W5"


def generate_topic_pdf(digest: TopicDigest, path: Path, generated_at: datetime) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _register_fonts()
    styles = _styles()

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{digest.topic.title} Daily News",
    )

    story: list[object] = [
        Paragraph(escape(digest.topic.title), styles["TitleJP"]),
        Paragraph(
            f"Generated: {escape(generated_at.strftime('%Y-%m-%d %H:%M %Z'))}",
            styles["MetaJP"],
        ),
        Spacer(1, 8),
    ]

    if digest.errors:
        story.append(Paragraph("Fetch warnings", styles["SectionJP"]))
        for error in digest.errors:
            story.append(Paragraph(escape(error), styles["WarningJP"]))
        story.append(Spacer(1, 8))

    if not digest.items:
        story.append(Paragraph("対象期間内のニュースは見つかりませんでした。", styles["BodyJP"]))
    else:
        for index, item in enumerate(digest.items, start=1):
            story.extend(_item_story(index, item, generated_at, styles))

    doc.build(story)
    return path


def _register_fonts() -> None:
    if BODY_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(BODY_FONT))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "TitleJP": ParagraphStyle(
            "TitleJP",
            parent=base["Title"],
            fontName=BODY_FONT,
            fontSize=18,
            leading=24,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "SectionJP": ParagraphStyle(
            "SectionJP",
            parent=base["Heading2"],
            fontName=BODY_FONT,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#333333"),
            wordWrap="CJK",
        ),
        "ItemTitleJP": ParagraphStyle(
            "ItemTitleJP",
            parent=base["Heading3"],
            fontName=BODY_FONT,
            fontSize=11.5,
            leading=15,
            spaceBefore=8,
            spaceAfter=2,
            wordWrap="CJK",
        ),
        "BodyJP": ParagraphStyle(
            "BodyJP",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=9.5,
            leading=14,
            wordWrap="CJK",
        ),
        "MetaJP": ParagraphStyle(
            "MetaJP",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#555555"),
            wordWrap="CJK",
        ),
        "UrlJP": ParagraphStyle(
            "UrlJP",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=7,
            leading=10,
            textColor=colors.HexColor("#315f9b"),
            wordWrap="CJK",
        ),
        "WarningJP": ParagraphStyle(
            "WarningJP",
            parent=base["BodyText"],
            fontName=BODY_FONT,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#9a4b00"),
            wordWrap="CJK",
        ),
    }


def _item_story(
    index: int,
    item: NewsItem,
    generated_at: datetime,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    published = (
        item.published_at.astimezone(generated_at.tzinfo).strftime("%Y-%m-%d %H:%M")
        if item.published_at
        else "日時不明"
    )
    story: list[object] = [
        Paragraph(f"{index}. {escape(item.title)}", styles["ItemTitleJP"]),
        Paragraph(
            f"{escape(item.source)} / {escape(published)}",
            styles["MetaJP"],
        ),
    ]
    if item.summary:
        story.append(Paragraph(escape(item.summary), styles["BodyJP"]))
    story.append(Paragraph(escape(item.url), styles["UrlJP"]))
    story.append(Spacer(1, 6))
    return story
