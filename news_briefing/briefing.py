from __future__ import annotations

import re

from .models import Article, BriefingItem


def build_briefing_items(articles: list[Article]) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for article in articles:
        summary_source = article.summary_hint or article.article_text or article.title
        summary = _extract_sentences(summary_source, 4)
        key_points = _extract_key_points(article, summary)
        supports = [
            f"{source.source}: {source.title} ({source.url})"
            for source in article.verification_sources
        ]

        warning = None
        if not article.verification_sources:
            warning = "此新聞目前可用支持來源有限，請以原始來源與後續可靠報導為準。"

        items.append(
            BriefingItem(
                chinese_title=f"英文新聞：{article.title}",
                english_title=article.title,
                source=article.source,
                published_time=_published(article),
                url=article.url,
                summary=summary
                or [
                    "此免費版本不使用付費 AI 摘要服務，因此保留原始英文標題與來源資訊。",
                    "請點開原文連結閱讀完整內容。",
                ],
                key_points=key_points,
                why_it_matters=(
                    "此新聞來自可靠新聞來源，可能反映美國政治、經濟、社會、科技或國際關係的最新變化。"
                ),
                practical_meaning=[
                    "一般讀者可先留意此事件是否影響生活成本、公共安全、工作市場、政策或國際局勢。",
                    "這則新聞反映的趨勢需要搭配後續可靠媒體報導持續觀察。",
                    "建議優先確認原文、發布時間、來源，以及是否有其他可靠媒體跟進。",
                ],
                verified_information=[article.verification_note],
                supporting_sources=supports or [f"{article.source}: {article.url}"],
                confidence=article.confidence,
                warning=warning,
            )
        )
    return items


def _extract_sentences(text: str, limit: int) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    result = [sentence.strip() for sentence in sentences if len(sentence.split()) >= 5]
    return result[:limit]


def _extract_key_points(article: Article, summary: list[str]) -> list[str]:
    points: list[str] = []
    points.append(f"Source: {article.source}")
    points.append(f"Original headline: {article.title}")
    if article.published_at:
        points.append(f"Published: {_published(article)}")
    if summary:
        points.extend(summary[:2])
    return points[:5]


def _published(article: Article) -> str:
    return article.published_at.isoformat() if article.published_at else "未提供"
