"""
London Review of Books scraper — public RSS feed.
"""

import feedparser
from dateutil import parser as dateparser
from datetime import timezone

FEED_URL = "https://www.lrb.co.uk/feed/rss"
FALLBACK_FEED_URL = "https://www.lrb.co.uk/blog/feed"


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


def fetch(quota: int = 1) -> list[dict]:
    articles = []

    for feed_url in (FEED_URL, FALLBACK_FEED_URL):
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                break
        except Exception:
            continue

    for entry in feed.entries:
        url = entry.get("link", "")
        if not url:
            continue

        summary = entry.get("summary", "")
        summary = summary.replace("<p>", "").replace("</p>", " ").strip()

        author = entry.get("author", "")
        if not author:
            # LRB often puts author in dc:creator
            author = entry.get("dc_creator", "LRB")

        articles.append({
            "title": entry.get("title", "").strip(),
            "summary": summary[:280],
            "url": url,
            "author": author.strip(),
            "published": _parse_date(entry),
            "source": "London Review of Books",
        })

    return articles
