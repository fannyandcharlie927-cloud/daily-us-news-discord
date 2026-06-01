from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NewsSource:
    name: str
    feed_url: str
    domains: tuple[str, ...]


PRIMARY_SOURCES: tuple[NewsSource, ...] = (
    NewsSource("AP News", "https://apnews.com/hub/us-news?output=atom", ("apnews.com",)),
    NewsSource("Reuters US", "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best", ("reuters.com",)),
    NewsSource("NPR", "https://feeds.npr.org/1001/rss.xml", ("npr.org",)),
    NewsSource("The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", ("nytimes.com",)),
    NewsSource("The Washington Post", "https://feeds.washingtonpost.com/rss/national", ("washingtonpost.com",)),
    NewsSource("The Wall Street Journal", "https://feeds.a.dj.com/rss/RSSWorldNews.xml", ("wsj.com",)),
    NewsSource("Axios", "https://api.axios.com/feed/", ("axios.com",)),
    NewsSource("Politico", "https://rss.politico.com/politics-news.xml", ("politico.com",)),
    NewsSource("CNN", "http://rss.cnn.com/rss/cnn_topstories.rss", ("cnn.com",)),
    NewsSource("NBC News", "https://feeds.nbcnews.com/nbcnews/public/news", ("nbcnews.com",)),
)


RELIABLE_DOMAINS: tuple[str, ...] = tuple(
    domain for source in PRIMARY_SOURCES for domain in source.domains
)
