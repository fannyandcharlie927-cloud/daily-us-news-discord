from __future__ import annotations

import logging
import re

import requests

from .models import Article, BriefingItem

LOGGER = logging.getLogger(__name__)
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


def build_briefing_items(articles: list[Article]) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for article in articles:
        summary_source = article.summary_hint or article.article_text or article.title
        english_summary = _extract_sentences(summary_source, 5) or [article.title]
        body_source = article.article_text or article.summary_hint or article.title

        items.append(
            BriefingItem(
                chinese_title=_translate_to_zh_tw(article.title),
                english_title=article.title,
                source=article.source,
                published_time=_published(article),
                url=article.url,
                summary=[_translate_to_zh_tw(sentence) for sentence in english_summary],
                key_points=_build_key_points(article, english_summary),
                body_paragraphs=_build_body_paragraphs(body_source),
                why_it_matters="",
                practical_meaning=[],
                verified_information=[],
                supporting_sources=[f"{article.source}: {article.url}"],
                confidence=article.confidence,
                warning=None,
            )
        )
    return items


def _build_key_points(article: Article, summary: list[str]) -> list[str]:
    points = summary[:5]
    if article.verification_sources and len(points) < 5:
        sources = "、".join(source.source for source in article.verification_sources[:2])
        points.append(f"其他來源也有相關報導：{sources}。")
    return [_translate_to_zh_tw(point) for point in points[:5]]


def _build_body_paragraphs(text: str) -> list[str]:
    sentences = _extract_sentences(text, 8)
    if not sentences:
        return []

    first = " ".join(sentences[:4]).strip()
    second = " ".join(sentences[4:8]).strip()
    paragraphs = [paragraph for paragraph in (first, second) if paragraph]
    return [_translate_to_zh_tw(paragraph) for paragraph in paragraphs[:2]]


def _translate_to_zh_tw(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return ""

    try:
        response = requests.get(
            TRANSLATE_URL,
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "zh-TW",
                "dt": "t",
                "q": cleaned,
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0])
        return translated.strip() or cleaned
    except Exception as exc:
        LOGGER.warning("Translation failed; keeping original text: %s", exc)
        return cleaned


def _extract_sentences(text: str, limit: int) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []

    protected = (
        cleaned.replace("A.I.", "AI")
        .replace("U.S.", "US")
        .replace("Mr.", "Mr")
        .replace("Ms.", "Ms")
        .replace("Dr.", "Dr")
    )
    sentences = re.split(r"(?<=[.!?])\s+", protected)
    result = [sentence.strip() for sentence in sentences if len(sentence.split()) >= 7]
    return result[:limit]


def _published(article: Article) -> str:
    return article.published_at.isoformat() if article.published_at else "未提供"
