from __future__ import annotations

from datetime import datetime

from .models import BriefingItem


DISCORD_LIMIT = 1900


def render_report(items: list[BriefingItem], local_now: datetime, requested_count: int) -> str:
    found = len(items)
    header = [
        "# 已查證每日美國新聞簡報",
        f"日期：{local_now.strftime('%Y-%m-%d %H:%M')}（Australia/Hobart）",
        f"已找到並查證新聞：{found}/{requested_count} 則",
    ]
    if found < requested_count:
        header.append("可靠且可查證的新聞不足 5 則，因此未補齊或捏造內容。")
    if found == 0:
        header.append("今天未找到符合條件且可查證的新聞。")
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
        f"原始英文標題：{item.english_title}",
        f"來源：{item.source}",
        f"發布時間：{item.published_time}",
        f"URL：{item.url}",
        "",
        "摘要：",
        *_bullet(item.summary),
        "",
        "重點：",
        *_bullet(item.key_points),
        "",
        f"重要性：{item.why_it_matters}",
        "",
        "實際意義：",
        *_bullet(item.practical_meaning),
        "",
        "查證：",
        *_bullet(item.verified_information),
        "支持來源：",
        *_bullet(item.supporting_sources),
        f"信心等級：{item.confidence}",
    ]
    if item.warning:
        lines.append(f"提醒：{item.warning}")
    return "\n".join(lines)


def _bullet(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items if item]


def _split_long_block(block: str) -> list[str]:
    chunks: list[str] = []
    text = block
    while text:
        chunks.append(text[:DISCORD_LIMIT])
        text = text[DISCORD_LIMIT:]
    return chunks
