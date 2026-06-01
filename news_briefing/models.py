from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    title: str
    source: str
    url: str
    published_at: datetime | None
    summary_hint: str
    topic: str = "product"
    article_text: str = ""
    verification_sources: list["SupportSource"] = field(default_factory=list)
    confidence: str = "Low"
    verification_note: str = ""


@dataclass(frozen=True)
class SupportSource:
    title: str
    source: str
    url: str
    published_at: datetime | None


@dataclass(frozen=True)
class BriefingItem:
    chinese_title: str
    english_title: str
    source: str
    published_time: str
    url: str
    summary: list[str]
    key_points: list[str]
    body_paragraphs: list[str]
    why_it_matters: str
    practical_meaning: list[str]
    verified_information: list[str]
    supporting_sources: list[str]
    confidence: str
    warning: str | None
