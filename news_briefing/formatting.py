from __future__ import annotations

from datetime import datetime

from .models import BriefingItem


DISCORD_LIMIT = 1900


def render_report(items: list[BriefingItem], local_now: datetime, requested_count: int) -> str:
    header = [
        "# AI新聞",
        f"日期：{local_now.strftime('%Y-%m-%d %H:%M')}（Australia/Hobart）",
    ]
    if not items:
        header.append("今天沒有找到符合條件的可靠 AI 新聞。")
        return "\n".join(header)

    sections = ["\n".join(header)]
    for index, item in enumerate(items, start=1):
        sections.append(_render_item(index, item))
    return "\n\n".join(sections)


def split_for_discord(report: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for block in report.split("\n\n"):
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= DISCORD_LIMIT:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(block) <= DISCORD_LIMIT:
            current = block
        else:
            chunks.extend(_split_long_block(block))
            current = ""
    if current:
        chunks.append(current)
    return chunks


def _render_item(index: int, item: BriefingItem) -> str:
    lines = [
        f"## {index}. {item.chinese_title}",
        f"原標題：{item.english_title}",
        f"來源：{item.source}",
        f"時間：{item.published_time}",
        f"連結：{item.url}",
        "",
        "摘要：",
        *_bullet(item.summary),
        "",
        "重點：",
        *_bullet(item.key_points),
        "",
        "內文：",
        *_paragraphs(item.body_paragraphs),
    ]
    return "\n".join(lines)


def _bullet(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items if item]


def _paragraphs(items: list[str]) -> list[str]:
    return [item for item in items if item]


def _split_long_block(block: str) -> list[str]:
    chunks: list[str] = []
    text = block
    while text:
        chunks.append(text[:DISCORD_LIMIT])
        text = text[DISCORD_LIMIT:]
    return chunks
