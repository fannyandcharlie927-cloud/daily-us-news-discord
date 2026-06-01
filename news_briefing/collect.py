from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .models import Article, SupportSource
from .sources import PRIMARY_SOURCES, RELIABLE_DOMAINS, NewsSource

LOGGER = logging.getLogger(__name__)
USER_AGENT = "daily-us-news-discord/1.0 (+https://github.com)"


def collect_articles(local_now: datetime, max_articles: int) -> list[Article]:
    candidates: list[Article] = []
    for source in PRIMARY_SOURCES:
        try:
            candidates.extend(_read_feed(source, local_now))
        except Exception as exc:
            LOGGER.warning("Failed to read feed for %s: %s", source.name, exc)

    candidates = _sort_articles(candidates)
    unique = _deduplicate(candidates)

    verified: list[Article] = []
    for article in unique:
        article.article_text = fetch_article_text(article.url)
        article.verification_sources = find_supporting_sources(article)
        article.confidence = confidence_for(article)
        article.verification_note = verification_note_for(article)
        if article.confidence in {"High", "Medium"}:
            verified.append(article)
        if len(verified) >= max_articles:
            break

    return verified


def _read_feed(source: NewsSource, local_now: datetime) -> list[Article]:
    LOGGER.info("Reading feed: %s", source.name)
    parsed = feedparser.parse(source.feed_url, request_headers={"User-Agent": USER_AGENT})
    articles: list[Article] = []
    earliest = local_now - timedelta(days=2)

    for entry in parsed.entries[:30]:
        url = _entry_link(entry)
        if not url or not _domain_allowed(url, source.domains):
            continue

        published_at = _entry_datetime(entry)
        if published_at and published_at.astimezone(local_now.tzinfo) < earliest:
            continue

        title = _clean_text(getattr(entry, "title", ""))
        if not title:
            continue

        articles.append(
            Article(
                title=title,
                source=source.name,
                url=url,
                published_at=published_at,
                summary_hint=_clean_text(getattr(entry, "summary", "")),
            )
        )
    return articles


def fetch_article_text(url: str) -> str:
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("Could not fetch article page %s: %s", url, exc)
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "form"]):
        tag.decompose()

    paragraphs = [_clean_text(p.get_text(" ")) for p in soup.find_all("p")]
    text = "\n".join(p for p in paragraphs if len(p.split()) > 8)
    return text[:6000]


def find_supporting_sources(article: Article) -> list[SupportSource]:
    query = "+".join(re.findall(r"[A-Za-z0-9]+", article.title)[:8])
    feed_url = f"https://news.google.com/rss/search?q={query}+when:2d&hl=en-US&gl=US&ceid=US:en"
    supports: list[SupportSource] = []

    try:
        parsed = feedparser.parse(feed_url, request_headers={"User-Agent": USER_AGENT})
    except Exception as exc:
        LOGGER.info("Verification feed failed for %s: %s", article.title, exc)
        return supports

    for entry in parsed.entries[:20]:
        title = _clean_text(getattr(entry, "title", ""))
        url = _entry_link(entry)
        source_name = _google_news_source(entry)
        if not title or not url:
            continue
        if source_name.lower() == article.source.lower():
            continue
        if not _looks_related(article.title, title):
            continue
        if not (_is_reliable_name(source_name) or _domain_allowed(url, RELIABLE_DOMAINS)):
            continue
        supports.append(
            SupportSource(
                title=title,
                source=source_name,
                url=url,
                published_at=_entry_datetime(entry),
            )
        )
        if len(supports) >= 3:
            break

    return supports


def confidence_for(article: Article) -> str:
    if len(article.verification_sources) >= 2 and article.article_text:
        return "High"
    if article.verification_sources or article.article_text or article.summary_hint:
        return "Medium"
    return "Low"


def verification_note_for(article: Article) -> str:
    checked = ["原始新聞來源、標題、發布時間與網址"]
    if article.article_text:
        checked.append("新聞頁面正文重點")
    if article.verification_sources:
        checked.append("其他可靠媒體的同題報導")
    return "；".join(checked)


def _entry_link(entry: object) -> str:
    link = getattr(entry, "link", "")
    if link:
        return str(link)
    links = getattr(entry, "links", [])
    if links:
        return str(links[0].get("href", ""))
    return ""


def _entry_datetime(entry: object) -> datetime | None:
    for attr in ("published", "updated", "created"):
        value = getattr(entry, attr, None)
        if not value:
            continue
        try:
            return date_parser.parse(value)
        except Exception:
            try:
                return parsedate_to_datetime(value)
            except Exception:
                continue
    return None


def _google_news_source(entry: object) -> str:
    source = getattr(entry, "source", None)
    if isinstance(source, dict):
        return _clean_text(source.get("title", "Google News"))
    return "Google News"


def _domain_allowed(url: str, domains: tuple[str, ...]) -> bool:
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower().removeprefix("www.")
    return any(hostname == domain or hostname.endswith("." + domain) for domain in domains)


def _is_reliable_name(name: str) -> bool:
    normalized = name.lower()
    return any(domain.split(".")[0] in normalized for domain in RELIABLE_DOMAINS)


def _looks_related(first: str, second: str) -> bool:
    first_words = set(_keywords(first))
    second_words = set(_keywords(second))
    if not first_words or not second_words:
        return False
    return len(first_words & second_words) >= 2


def _deduplicate(articles: list[Article]) -> list[Article]:
    seen: list[set[str]] = []
    unique: list[Article] = []
    for article in articles:
        words = set(_keywords(article.title))
        if any(len(words & prior) >= 3 for prior in seen):
            continue
        seen.append(words)
        unique.append(article)
    return unique


def _sort_articles(articles: list[Article]) -> list[Article]:
    return sorted(
        articles,
        key=lambda item: item.published_at.timestamp() if item.published_at else 0,
        reverse=True,
    )


def _keywords(text: str) -> list[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "after",
        "over",
        "into",
        "says",
        "said",
        "will",
        "news",
    }
    return [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]{4,}", text)
        if word.lower() not in stop
    ]


def _clean_text(value: str) -> str:
    text = BeautifulSoup(unescape(value or ""), "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()
