"""
Economist scraper — public RSS feeds, no auth required.
"""

import re
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


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace(
        "&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s{2,}", " ", text).strip()


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

            # Full content (if available in RSS)
            content = ""
            if entry.get("content"):
                content = _strip_html(entry["content"][0].get("value", ""))[:2000]

            summary_raw = entry.get("summary", "")
            summary = _strip_html(summary_raw)[:280]

            # Use content as summary if summary is empty
            if not summary and content:
                summary = content[:280]

            articles.append({
                "title": entry.get("title", "").strip(),
                "summary": summary,
                "content": content,
                "url": url,
                "author": entry.get("author", "The Economist").strip(),
                "published": _parse_date(entry),
                "source": "The Economist",
            })

    return articles
