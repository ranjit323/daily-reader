"""
Substack discovery via Twitter/X timeline RSS.

Tries multiple RSS proxy services for Twitter timelines, extracts Substack
article links from tweets, fetches those articles with BeautifulSoup.

Requires env var: TWITTER_USERNAME
"""

import os
import re
import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from datetime import timezone


# RSS proxy services that can serve Twitter timelines
# rsshub.app is the most reliable open-source alternative
RSS_TEMPLATES = [
    "https://rsshub.app/twitter/user/{username}",
    "https://nitter.privacydev.net/{username}/rss",
    "https://nitter.cz/{username}/rss",
    "https://nitter.net/{username}/rss",
]

SUBSTACK_PATTERN = re.compile(
    r'https?://[a-z0-9\-]+\.substack\.com/p/[^\s"<>&\)]+'
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _fetch_timeline_feed(username: str) -> list:
    """Try each RSS proxy until one returns entries."""
    for template in RSS_TEMPLATES:
        url = template.format(username=username)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            if feed.entries:
                print(f"[substack] Timeline feed from {url.split('/')[2]}: {len(feed.entries)} entries")
                return feed.entries
        except Exception as e:
            print(f"[substack] {url.split('/')[2]} failed: {e}")
            continue
    print("[substack] All timeline RSS sources failed")
    return []


def _extract_substack_urls(entries: list) -> list[str]:
    """Extract unique Substack article URLs from feed entries."""
    seen = set()
    urls = []
    for entry in entries:
        text = entry.get("summary", "") + entry.get("title", "") + entry.get("content", [{}])[0].get("value", "") if entry.get("content") else entry.get("summary", "") + entry.get("title", "")
        for m in SUBSTACK_PATTERN.finditer(text):
            url = m.group(0).rstrip(".,)")
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def _fetch_substack_article(url: str) -> dict | None:
    """Fetch a Substack article and extract title, author, summary, content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "").strip()
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""

        # Author
        author = ""
        og_author = soup.find("meta", {"name": "author"})
        if og_author:
            author = og_author.get("content", "").strip()
        if not author:
            byline = soup.find(class_=re.compile(r"byline|author", re.I))
            author = byline.get_text(strip=True) if byline else "Substack"

        # Summary
        summary = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            summary = og_desc.get("content", "").strip()

        # Published date
        published = None
        time_tag = soup.find("time")
        if time_tag:
            dt_str = time_tag.get("datetime") or time_tag.get_text(strip=True)
            try:
                published = dateparser.parse(dt_str)
                if published and published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # Full body
        content = ""
        body_div = (
            soup.find(class_="body markup")
            or soup.find(class_=re.compile(r"post-content|available-content|article-body", re.I))
            or soup.find("div", {"data-component-name": "PostContent"})
        )
        if body_div:
            paras = body_div.find_all("p")
            content = "\n\n".join(
                p.get_text(separator=" ", strip=True)
                for p in paras
                if len(p.get_text(strip=True)) > 40
            )

        if not title:
            return None

        return {
            "title": title,
            "summary": summary[:400],
            "content": content,
            "url": url,
            "author": author,
            "published": published,
            "source": "Substack",
        }
    except Exception as e:
        print(f"[substack] Error fetching {url}: {e}")
        return None


def fetch(quota: int = 3) -> list[dict]:
    username = os.environ.get("TWITTER_USERNAME", "")
    if not username:
        print("[substack] TWITTER_USERNAME not set — skipping")
        return []

    print(f"[substack] Fetching timeline for @{username}...")
    entries = _fetch_timeline_feed(username)
    if not entries:
        print("[substack] No timeline entries — skipping Substack")
        return []

    urls = _extract_substack_urls(entries)
    print(f"[substack] Found {len(urls)} Substack links in timeline")
    if not urls:
        print("[substack] No Substack links found in recent tweets")
        return []

    articles = []
    for url in urls[:10]:
        article = _fetch_substack_article(url)
        if article:
            articles.append(article)
            print(f"[substack] Fetched: {article['title'][:60]}")
        if len(articles) >= quota * 3:
            break

    print(f"[substack] {len(articles)} Substack articles fetched")
    return articles
