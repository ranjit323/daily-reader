"""
London Review of Books scraper — public RSS feed.
"""

import re
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


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace(
        "&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s{2,}", " ", text).strip()


def fetch(quota: int = 1) -> list[dict]:
    articles = []
    feed = None

    for feed_url in (FEED_URL, FALLBACK_FEED_URL):
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                break
        except Exception:
            continue

    if not feed or not feed.entries:
        return []

    for entry in feed.entries:
        url = entry.get("link", "")
        if not url:
            continue

        content = ""
        if entry.get("content"):
            content = _strip_html(entry["content"][0].get("value", ""))[:2000]

        summary = _strip_html(entry.get("summary", ""))[:280]
        if not summary and content:
            summary = content[:280]

        author = entry.get("author", "") or entry.get("dc_creator", "LRB")

        articles.append({
            "title": entry.get("title", "").strip(),
            "summary": summary,
            "content": content,
            "url": url,
            "author": author.strip(),
            "published": _parse_date(entry),
            "source": "London Review of Books",
        })

    return articles
