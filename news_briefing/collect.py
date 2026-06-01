from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote_plus, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from dateutil import parser as date_parser
import warnings

from .models import Article, SupportSource
from .sources import PRIMARY_SOURCES, RELIABLE_DOMAINS, NewsSource

LOGGER = logging.getLogger(__name__)
USER_AGENT = "daily-us-news-discord/1.0 (+https://github.com)"

PRODUCT_KEYWORDS = (
    "a.i.",
    "artificial intelligence",
    "openai",
    "chatgpt",
    "gpt",
    "anthropic",
    "claude",
    "google gemini",
    "gemini",
    "microsoft copilot",
    "copilot",
    "nvidia",
    "llm",
    "large language model",
    "machine learning",
    "model",
    "agent",
    "agents",
    "app",
    "feature",
    "features",
    "release",
    "launch",
    "update",
    "upgrade",
    "voice",
    "image generation",
    "video generation",
    "browser",
    "search",
    "developer",
    "api",
    "ai pc",
    "gpu",
    "ai chip",
    "ai chips",
    "chip",
    "chips",
    "semiconductor",
    "robotics",
    "robot",
    "device",
    "hardware",
    "laptop",
    "pc",
    "iphone",
    "apple intelligence",
    "qualcomm",
    "amd",
)

SHORT_AI_PATTERN = re.compile(r"(?<![a-z])ai(?![a-z])", re.IGNORECASE)

MAKER_KEYWORDS = (
    "codex",
    "openai codex",
    "built with codex",
    "made with codex",
    "created with codex",
    "codex built",
    "codex-made",
    "codex project",
    "codex app",
    "codex tool",
)

EXCLUDE_KEYWORDS = (
    "billionaire",
    "billionaires",
    "wealth tax",
    "tax",
    "populist",
    "democrat",
    "democrats",
    "republican",
    "senate",
    "congress",
    "election",
    "campaign",
    "regulation",
    "policy",
    "lawsuit",
    "court",
    "copyright",
    "energy",
    "electricity",
    "power grid",
    "layoff",
    "layoffs",
    "workforce",
    "replace your job",
    "too ai-pilled",
    "expulsion",
    "reporter",
    "journalist",
)

AI_SEARCH_QUERIES = (
    "OpenAI ChatGPT new feature OR model OR app",
    "Anthropic Claude new feature OR model OR app",
    "Google Gemini AI new feature OR model OR app",
    "Microsoft Copilot AI new feature OR app",
    "Apple Intelligence AI feature OR iPhone OR Mac",
    "Nvidia AI chip OR GPU OR AI PC OR hardware",
    "AI laptop OR AI PC OR Qualcomm OR AMD OR Nvidia",
)

MAKER_SEARCH_QUERIES = (
    "OpenAI Codex built app OR project OR prototype",
    "Codex AI coding agent built app OR tool",
    "built with OpenAI Codex app OR website OR tool",
    "made with OpenAI Codex app OR project",
    "developer built with Codex OpenAI",
)

SOURCE_PRIORITY = {
    "AP News": 10,
    "Reuters US": 10,
    "Reuters": 10,
    "NPR": 8,
    "The New York Times": 8,
    "The Washington Post": 8,
    "The Wall Street Journal": 8,
    "Axios": 7,
    "Politico": 7,
    "CNN": 7,
    "NBC News": 7,
    "The Verge": 9,
    "TechCrunch": 9,
    "WIRED": 8,
}


def collect_articles(local_now: datetime, max_articles: int) -> list[Article]:
    candidates = _collect_feed_candidates(local_now)
    candidates.extend(_collect_google_news_candidates(local_now, AI_SEARCH_QUERIES, "product"))
    candidates.extend(_collect_google_news_candidates(local_now, MAKER_SEARCH_QUERIES, "maker"))

    unique = _deduplicate(candidates)
    product_candidates = [article for article in unique if _product_score(article) > 0]
    maker_candidates = [article for article in unique if _maker_score(article) > 0]

    product_target = min(5, max_articles)
    maker_target = max(0, max_articles - product_target)
    selected = []
    selected.extend(_select_verified(product_candidates, product_target, _product_article_score))
    selected.extend(_select_verified(maker_candidates, maker_target, _maker_article_score, selected))

    if len(selected) < max_articles:
        remaining = [
            article
            for article in sorted(unique, key=_combined_article_score, reverse=True)
            if article.url not in {item.url for item in selected}
            and (_product_score(article) > 0 or _maker_score(article) > 0)
        ]
        selected.extend(_select_verified(remaining, max_articles - len(selected), _combined_article_score, selected))

    return selected[:max_articles]


def _select_verified(
    candidates: list[Article],
    limit: int,
    score_fn,
    already_selected: list[Article] | None = None,
) -> list[Article]:
    selected_urls = {article.url for article in already_selected or []}
    selected: list[Article] = []
    ranked = sorted(candidates, key=score_fn, reverse=True)
    for article in ranked:
        if article.url in selected_urls:
            continue
        if score_fn(article)[0] <= 0:
            continue
        article.article_text = fetch_article_text(article.url)
        article.verification_sources = find_supporting_sources(article)
        article.confidence = confidence_for(article)
        article.verification_note = verification_note_for(article)
        if article.confidence in {"High", "Medium"}:
            selected.append(article)
            selected_urls.add(article.url)
        if len(selected) >= limit:
            break
    return selected


def _collect_feed_candidates(local_now: datetime) -> list[Article]:
    candidates: list[Article] = []
    for source in PRIMARY_SOURCES:
        try:
            candidates.extend(_read_feed(source, local_now))
        except Exception as exc:
            LOGGER.warning("Failed to read feed for %s: %s", source.name, exc)
    return candidates


def _collect_google_news_candidates(
    local_now: datetime,
    queries: tuple[str, ...],
    topic: str,
) -> list[Article]:
    candidates: list[Article] = []
    earliest = local_now - timedelta(days=3)

    for query in queries:
        feed_url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(f"({query}) when:3d")
            + "&hl=en-US&gl=US&ceid=US:en"
        )
        try:
            parsed = feedparser.parse(feed_url, request_headers={"User-Agent": USER_AGENT})
        except Exception as exc:
            LOGGER.warning("Failed to read Google News AI search feed: %s", exc)
            continue

        for entry in parsed.entries[:20]:
            source_name = _google_news_source(entry)
            if not _is_reliable_name(source_name):
                continue
            published_at = _entry_datetime(entry)
            if published_at and published_at.astimezone(local_now.tzinfo) < earliest:
                continue
            title = _clean_text(getattr(entry, "title", ""))
            url = _entry_link(entry)
            if not title or not url:
                continue
            if "/video/" in url:
                continue
            article_text = _strip_source_from_google_title(title, source_name)
            if topic == "maker" and _maker_score_text(article_text) <= 0:
                continue
            if topic == "product" and _product_score_text(article_text) <= 0:
                continue
            candidates.append(
                Article(
                    title=article_text,
                    source=source_name,
                    url=url,
                    published_at=published_at,
                    summary_hint="",
                    topic=topic,
                )
            )
    return candidates


def _read_feed(source: NewsSource, local_now: datetime) -> list[Article]:
    LOGGER.info("Reading feed: %s", source.name)
    parsed = feedparser.parse(source.feed_url, request_headers={"User-Agent": USER_AGENT})
    articles: list[Article] = []
    earliest = local_now - timedelta(days=3)

    for entry in parsed.entries[:40]:
        url = _entry_link(entry)
        if not url or not _domain_allowed(url, source.domains):
            continue
        if "/video/" in url:
            continue

        published_at = _entry_datetime(entry)
        if published_at and published_at.astimezone(local_now.tzinfo) < earliest:
            continue

        title = _clean_text(getattr(entry, "title", ""))
        summary = _clean_text(getattr(entry, "summary", ""))
        if not title:
            continue

        articles.append(
            Article(
                title=title,
                source=source.name,
                url=url,
                published_at=published_at,
                summary_hint=summary,
                topic="maker" if _maker_score_text(f"{title} {summary}") > 0 else "product",
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
    query = quote_plus(" ".join(re.findall(r"[A-Za-z0-9]+", article.title)[:8]))
    feed_url = f"https://news.google.com/rss/search?q={query}+when:3d&hl=en-US&gl=US&ceid=US:en"
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
                title=_strip_source_from_google_title(title, source_name),
                source=source_name,
                url=url,
                published_at=_entry_datetime(entry),
            )
        )
        if len(supports) >= 3:
            break

    return supports


def confidence_for(article: Article) -> str:
    if len(article.verification_sources) >= 2 and (article.article_text or article.summary_hint):
        return "High"
    if article.verification_sources or article.article_text or article.summary_hint:
        return "Medium"
    return "Low"


def verification_note_for(article: Article) -> str:
    checked = ["original source, headline, published time, and URL"]
    if article.article_text:
        checked.append("article page text")
    if article.verification_sources:
        checked.append("matching coverage from other reliable sources")
    return "; ".join(checked)


def _product_article_score(article: Article) -> tuple[int, float]:
    published_ts = article.published_at.timestamp() if article.published_at else 0
    score = _product_score(article)
    score += SOURCE_PRIORITY.get(article.source, 5)
    score += min(len(article.verification_sources), 3) * 2
    return score, published_ts


def _maker_article_score(article: Article) -> tuple[int, float]:
    published_ts = article.published_at.timestamp() if article.published_at else 0
    score = _maker_score(article)
    score += SOURCE_PRIORITY.get(article.source, 5)
    score += min(len(article.verification_sources), 3) * 2
    return score, published_ts


def _combined_article_score(article: Article) -> tuple[int, float]:
    published_ts = article.published_at.timestamp() if article.published_at else 0
    base_score = max(_product_score(article), _maker_score(article))
    if base_score <= 0:
        return -10, published_ts
    score = base_score
    score += SOURCE_PRIORITY.get(article.source, 5)
    return score, published_ts


def _product_score(article: Article) -> int:
    return _product_score_text(f"{article.title} {article.summary_hint}")


def _product_score_text(text: str) -> int:
    text = text.lower()
    if any(keyword in text for keyword in EXCLUDE_KEYWORDS):
        return -10

    score = 0
    if SHORT_AI_PATTERN.search(text):
        score += 2
    for keyword in PRODUCT_KEYWORDS:
        if keyword in text:
            score += 5 if keyword in {
                "openai",
                "chatgpt",
                "anthropic",
                "claude",
                "gemini",
                "microsoft copilot",
                "copilot",
                "apple intelligence",
                "nvidia",
            } else 2
    if "drone" in text and not any(term in text for term in ("ai", "artificial intelligence", "autonomous", "robotics")):
        score -= 6
    return score


def _maker_score(article: Article) -> int:
    return _maker_score_text(f"{article.title} {article.summary_hint}")


def _maker_score_text(text: str) -> int:
    normalized = text.lower()
    if any(keyword in normalized for keyword in EXCLUDE_KEYWORDS):
        return -10
    if "codex" not in normalized:
        return 0

    score = 0
    for keyword in MAKER_KEYWORDS:
        if keyword in normalized:
            score += 8 if "codex" in keyword else 3
    score += 10
    if any(term in normalized for term in ("built", "made", "created", "launched", "prototype")):
        score += 2
    return score


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


def _strip_source_from_google_title(title: str, source_name: str) -> str:
    suffix = f" - {source_name}"
    if title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title


def _domain_allowed(url: str, domains: tuple[str, ...]) -> bool:
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower().removeprefix("www.")
    return any(hostname == domain or hostname.endswith("." + domain) for domain in domains)


def _is_reliable_name(name: str) -> bool:
    normalized = name.lower()
    reliable_names = {
        "ap news",
        "associated press",
        "reuters",
        "npr",
        "the new york times",
        "the washington post",
        "the wall street journal",
        "wsj",
        "axios",
        "politico",
        "cnn",
        "nbc news",
        "the verge",
        "techcrunch",
        "wired",
    }
    return normalized in reliable_names or any(domain.split(".")[0] in normalized for domain in RELIABLE_DOMAINS)


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
        if any(len(words & prior) >= 2 for prior in seen):
            continue
        seen.append(words)
        unique.append(article)
    return unique


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
        "about",
    }
    return [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]{3,}", text)
        if word.lower() not in stop
    ]


def _clean_text(value: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        text = BeautifulSoup(unescape(value or ""), "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()
