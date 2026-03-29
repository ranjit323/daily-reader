"""
Economist scraper — public RSS feeds, no auth required.
Pulls from Finance & Economics and Books & Arts sections.
"""

import feedparser
from dateutil import parser as dateparser
from datetime import timezone

FEEDS = [
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://www.economist.com/books-and-arts/rss.xml",
    "https://www.economist.com/briefing/rss.xml",
    "https://www.economist.com/leaders/rss.xml",
]


def _parse_date(entry):
    for field in ("published", "updated"):
        val = entry.get(field)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    return None


def fetch(quota: int = 5) -> list[dict]:
    articles = []
    seen_urls = set()

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            continue

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            summary = entry.get("summary", "")
            # feedparser sometimes includes HTML tags; strip basic ones
            summary = summary.replace("<p>", "").replace("</p>", " ").strip()

            articles.append({
                "title": entry.get("title", "").strip(),
                "summary": summary[:280],
                "url": url,
                "author": entry.get("author", "The Economist").strip(),
                "published": _parse_date(entry),
                "source": "The Economist",
            })

    return articles
