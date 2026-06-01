from __future__ import annotations

import json
import logging

from openai import OpenAI

from .models import Article, BriefingItem

LOGGER = logging.getLogger(__name__)


SYSTEM_PROMPT = """
你是嚴謹的每日新聞簡報編輯。請只根據提供的資料撰寫，不得加入未提供或無法驗證的資訊。
輸出必須使用繁體中文，但保留原始英文標題。這不是社群內容，不要產生貼文、標籤、影片點子或審稿字樣。
每則新聞都要清楚說明已查證的資訊、支持來源與信心等級。
""".strip()


def build_briefing_items(articles: list[Article], api_key: str, model: str) -> list[BriefingItem]:
    client = OpenAI(api_key=api_key)
    items: list[BriefingItem] = []

    for article in articles:
        LOGGER.info("Generating Traditional Chinese briefing for: %s", article.title)
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _article_prompt(article)},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        items.append(_parse_item(raw, article))

    return items


def fallback_briefing_items(articles: list[Article]) -> list[BriefingItem]:
    items: list[BriefingItem] = []
    for article in articles:
        summary_source = article.article_text or article.summary_hint or article.title
        sentences = _simple_sentences(summary_source, 4)
        supports = [f"{source.source}: {source.title} ({source.url})" for source in article.verification_sources]
        items.append(
            BriefingItem(
                chinese_title=f"待翻譯：{article.title}",
                english_title=article.title,
                source=article.source,
                published_time=_published(article),
                url=article.url,
                summary=sentences or ["此新聞已通過來源檢查，但未能產生完整中文摘要。"],
                key_points=sentences[:3] or [article.title],
                why_it_matters="此新聞來自可靠來源，可能涉及美國公共政策、經濟、社會或國際影響。",
                practical_meaning=[
                    "一般讀者可留意此事件是否影響生活成本、公共服務、安全或工作環境。",
                    "此事件反映正在發展中的美國社會、政策或市場趨勢。",
                    "後續應注意可靠媒體是否補充更多事實與官方說明。",
                ],
                verified_information=[article.verification_note],
                supporting_sources=supports or [f"{article.source}: {article.url}"],
                confidence=article.confidence,
                warning="未設定 OPENAI_API_KEY，因此使用非生成式備援摘要；請以原文連結為準。",
            )
        )
    return items


def _article_prompt(article: Article) -> str:
    support_lines = "\n".join(
        f"- {source.source}: {source.title} | {source.url}" for source in article.verification_sources
    )
    return f"""
請把以下已篩選新聞整理成一則 JSON 物件。JSON 欄位必須完全符合：
chinese_title, english_title, source, published_time, url, summary, key_points, why_it_matters,
practical_meaning, verified_information, supporting_sources, confidence, warning

規則：
- summary 是 3 到 5 句繁體中文。
- key_points 是 3 到 5 個繁體中文重點。
- practical_meaning 是 3 個項目，分別涵蓋：對普通人的影響、反映的趨勢或議題、我應注意什麼。
- verified_information 說明已查證的資訊。
- supporting_sources 列出支持來源，格式含來源名稱與 URL。
- confidence 只能是 High、Medium、Low。
- 若支持來源有限，warning 必須提醒「此新聞目前可用支持來源有限」；否則 warning 可為 null。

原始英文標題：{article.title}
來源：{article.source}
發布時間：{_published(article)}
URL：{article.url}
信心等級：{article.confidence}
已查證資訊：{article.verification_note}
RSS 摘要：{article.summary_hint}
正文摘錄：
{article.article_text[:4500]}

支持來源：
{support_lines or "- 無額外支持來源"}
""".strip()


def _parse_item(raw: str, article: Article) -> BriefingItem:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        LOGGER.warning("Model returned invalid JSON for %s", article.title)
        return fallback_briefing_items([article])[0]

    return BriefingItem(
        chinese_title=str(data.get("chinese_title") or article.title),
        english_title=str(data.get("english_title") or article.title),
        source=str(data.get("source") or article.source),
        published_time=str(data.get("published_time") or _published(article)),
        url=str(data.get("url") or article.url),
        summary=_as_list(data.get("summary"), 5),
        key_points=_as_list(data.get("key_points"), 5),
        why_it_matters=str(data.get("why_it_matters") or ""),
        practical_meaning=_as_list(data.get("practical_meaning"), 3),
        verified_information=_as_list(data.get("verified_information"), 5),
        supporting_sources=_as_list(data.get("supporting_sources"), 5),
        confidence=str(data.get("confidence") or article.confidence),
        warning=data.get("warning"),
    )


def _as_list(value: object, limit: int) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:limit]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _simple_sentences(text: str, limit: int) -> list[str]:
    chunks = [chunk.strip() for chunk in text.replace("\n", " ").split(".") if chunk.strip()]
    return [chunk + "." for chunk in chunks[:limit]]


def _published(article: Article) -> str:
    return article.published_at.isoformat() if article.published_at else "未提供"
