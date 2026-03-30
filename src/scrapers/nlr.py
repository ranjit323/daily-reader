"""
New Left Review scraper — public RSS feed.
"""

import re
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


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace(
        "&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s{2,}", " ", text).strip()


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

        content = ""
        if entry.get("content"):
            content = _strip_html(entry["content"][0].get("value", ""))

        summary = _strip_html(entry.get("summary", ""))[:400]
        if not summary and content:
            summary = content[:400]

        author = entry.get("author", "") or entry.get("dc_creator", "New Left Review")

        articles.append({
            "title": entry.get("title", "").strip(),
            "summary": summary,
            "content": content,
            "url": url,
            "author": author.strip(),
            "published": _parse_date(entry),
            "source": "New Left Review",
        })

    return articles
