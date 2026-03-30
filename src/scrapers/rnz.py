"""
Radio New Zealand scraper — public RSS feeds.
Uses in-depth, political, and national feeds for substantive NZ journalism.
"""

import re
import feedparser
from dateutil import parser as dateparser
from datetime import timezone


FEEDS = [
    "https://www.rnz.co.nz/rss/in-depth.xml",
    "https://www.rnz.co.nz/rss/political.xml",
    "https://www.rnz.co.nz/rss/national.xml",
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


def fetch(quota: int = 2) -> list[dict]:
    seen_urls = set()
    articles = []

    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"[rnz] Feed error {feed_url}: {e}")
            continue

        for entry in feed.entries:
            url = entry.get("link", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            summary = _strip_html(entry.get("summary", ""))[:400]
            content = ""
            if entry.get("content"):
                content = _strip_html(entry["content"][0].get("value", ""))

            author = entry.get("author", "") or entry.get("dc_creator", "RNZ")

            articles.append({
                "title": entry.get("title", "").strip(),
                "summary": summary,
                "content": content,
                "url": url,
                "author": author.strip(),
                "published": _parse_date(entry),
                "source": "RNZ",
            })

    print(f"[rnz] {len(articles)} total candidates")
    return articles
