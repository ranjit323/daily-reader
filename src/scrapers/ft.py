"""
Financial Times scraper — uses subscriber myFT RSS feed.

Requires env var: FT_RSS_URL (your personal myFT RSS URL from myft.ft.com)
Falls back to public section RSS feeds if not set.
"""

import os
import re
import feedparser
from dateutil import parser as dateparser
from datetime import timezone


PUBLIC_FEEDS = [
    "https://www.ft.com/world?format=rss",
    "https://www.ft.com/companies?format=rss",
    "https://www.ft.com/markets?format=rss",
    "https://www.ft.com/opinion?format=rss",
    "https://www.ft.com/firstft?format=rss",
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


def _parse_feed(feed_url: str, seen_urls: set) -> list[dict]:
    articles = []
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"[FT] Feed error {feed_url}: {e}")
        return []

    for entry in feed.entries:
        url = entry.get("link", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        summary = _strip_html(entry.get("summary", ""))[:280]

        author = entry.get("author", "")
        if not author:
            author = entry.get("dc_creator", "FT")

        articles.append({
            "title": entry.get("title", "").strip(),
            "summary": summary,
            "content": "",
            "url": url,
            "author": author.strip(),
            "published": _parse_date(entry),
            "source": "Financial Times",
        })

    return articles


def fetch(quota: int = 5) -> list[dict]:
    seen_urls = set()
    all_articles = []

    rss_url = os.environ.get("FT_RSS_URL", "")
    if rss_url:
        print(f"[FT] Using subscriber myFT RSS feed")
        all_articles = _parse_feed(rss_url, seen_urls)
        print(f"[FT] {len(all_articles)} articles from myFT feed")
    else:
        print("[FT] FT_RSS_URL not set — using public section feeds")

    # Supplement with public feeds if needed
    if len(all_articles) < quota * 2:
        for feed_url in PUBLIC_FEEDS:
            if len(all_articles) >= quota * 4:
                break
            extras = _parse_feed(feed_url, seen_urls)
            all_articles.extend(extras)
            print(f"[FT] {len(extras)} articles from {feed_url}")

    print(f"[FT] {len(all_articles)} total candidates")
    return all_articles
