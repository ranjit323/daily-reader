"""
New Left Review scraper — public RSS feed.
"""

import feedparser
from dateutil import parser as dateparser
from datetime import timezone

FEED_URL = "https://newleftreview.org/feed"


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

    try:
        feed = feedparser.parse(FEED_URL)
    except Exception:
        return []

    for entry in feed.entries:
        url = entry.get("link", "")
        if not url:
            continue

        summary = entry.get("summary", "")
        summary = summary.replace("<p>", "").replace("</p>", " ").strip()

        author = entry.get("author", "")
        if not author:
            author = entry.get("dc_creator", "New Left Review")

        articles.append({
            "title": entry.get("title", "").strip(),
            "summary": summary[:280],
            "url": url,
            "author": author.strip(),
            "published": _parse_date(entry),
            "source": "New Left Review",
        })

    return articles
