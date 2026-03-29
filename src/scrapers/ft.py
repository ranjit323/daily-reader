"""
Financial Times scraper — Playwright (Chromium headless).
Authenticates, scrapes section pages for candidates, then fetches
article bodies for the selected articles.

Requires env vars: FT_EMAIL, FT_PASSWORD
"""

import os
import re
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


FT_SECTIONS = [
    "https://www.ft.com/world/global-economy",
    "https://www.ft.com/companies/banks",
    "https://www.ft.com/banking",
    "https://www.ft.com/books-arts",
    "https://www.ft.com/arts",
    "https://www.ft.com/world",
    "https://www.ft.com/technology",
]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace(
        "&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s{2,}", " ", text).strip()


def _dismiss_consent(page):
    for selector in (
        "#onetrust-accept-btn-handler",
        "button[id*='accept']",
        "button[class*='consent']",
    ):
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return
        except Exception:
            pass


def _login(page, email: str, password: str) -> bool:
    try:
        page.goto("https://www.ft.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
        _dismiss_consent(page)

        page.goto("https://accounts.ft.com/login", wait_until="domcontentloaded", timeout=40000)
        page.wait_for_timeout(3000)
        _dismiss_consent(page)
        page.wait_for_timeout(1000)

        # Fill and submit email
        page.wait_for_selector("#enter-email", timeout=15000)
        page.locator("#enter-email").fill(email)
        page.wait_for_timeout(500)
        page.locator('button[type="submit"]').click(force=True)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        print(f"[FT] After email submit, URL: {page.url}")

        # Password page
        page.wait_for_selector('input[type="password"]:not([id="_notUsed"])', timeout=15000)
        page.locator('input[type="password"]:not([id="_notUsed"])').fill(password)
        page.wait_for_timeout(500)
        page.locator('button[type="submit"]').click(force=True)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        print(f"[FT] After password submit, URL: {page.url}")

        # Verify login succeeded by checking for sign-out link or user nav
        logged_in = page.query_selector(
            'a[href*="logout"], a[href*="sign-out"], [data-trackable="navigation-user-account"]'
        )
        if not logged_in:
            print("[FT] Login may not have succeeded — continuing anyway")

        return True

    except PlaywrightTimeout as e:
        print(f"[FT] Login timeout: {e}")
        return False
    except Exception as e:
        print(f"[FT] Login error: {e}")
        return False


def _extract_candidates(page) -> list[dict]:
    """Extract article cards from an FT section page."""
    articles = []

    # Wait for content
    try:
        page.wait_for_selector("h3, h2, article", timeout=8000)
    except Exception:
        pass

    # Broad selector: any element containing a headline link
    cards = page.query_selector_all(
        "div[data-trackable='article'], "
        "li[class*='story'], "
        "div[class*='story-card'], "
        "div[class*='teaser'], "
        "article"
    )

    if not cards:
        # Fallback: grab all headline links directly
        links = page.query_selector_all("h3 a[href*='/content/'], h2 a[href*='/content/']")
        for link in links:
            title = _clean(link.inner_text())
            url = link.get_attribute("href") or ""
            if url and not url.startswith("http"):
                url = "https://www.ft.com" + url
            if title and url:
                articles.append({
                    "title": title,
                    "summary": "",
                    "content": "",
                    "url": url,
                    "author": "FT",
                    "published": None,
                    "source": "Financial Times",
                })
        return articles

    for card in cards:
        try:
            title_el = card.query_selector(
                "a[data-trackable='heading-link'], "
                ".o-teaser__heading a, "
                "h3 a, h2 a, h4 a"
            )
            if not title_el:
                continue
            title = _clean(title_el.inner_text())
            url = title_el.get_attribute("href") or ""
            if url and not url.startswith("http"):
                url = "https://www.ft.com" + url
            if not title or not url or "ft.com" not in url:
                continue

            summary_el = card.query_selector(
                ".o-teaser__standfirst, "
                "[data-trackable='standfirst'], "
                "p[class*='standfirst']"
            )
            summary = _clean(summary_el.inner_text()) if summary_el else ""

            author_el = card.query_selector(
                ".o-teaser__author, "
                "[data-trackable='author'], "
                "a[href*='/stream/authorsId']"
            )
            author = _clean(author_el.inner_text()) if author_el else "FT"

            time_el = card.query_selector("time")
            published = None
            if time_el:
                dt_attr = time_el.get_attribute("datetime")
                if dt_attr:
                    try:
                        published = datetime.fromisoformat(dt_attr.replace("Z", "+00:00"))
                    except ValueError:
                        pass

            articles.append({
                "title": title,
                "summary": summary[:280],
                "content": "",
                "url": url,
                "author": author,
                "published": published,
                "source": "Financial Times",
            })
        except Exception:
            continue

    return articles


def _fetch_article_body(page, url: str) -> str:
    """Navigate to an FT article and extract the body text."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(2000)
        _dismiss_consent(page)

        # FT article body selectors
        body_selectors = [
            ".article__content-body p",
            ".article-body p",
            "[class*='article__content'] p",
            "[class*='body-text'] p",
            ".n-content-body p",
        ]

        for selector in body_selectors:
            paras = page.query_selector_all(selector)
            if paras:
                text = " ".join(_clean(p.inner_text()) for p in paras[:12] if p.inner_text().strip())
                if len(text) > 100:
                    return text[:12000]

    except Exception as e:
        print(f"[FT] Body fetch error for {url}: {e}")

    return ""


def fetch(quota: int = 5) -> list[dict]:
    email = os.environ.get("FT_EMAIL", "")
    password = os.environ.get("FT_PASSWORD", "")

    if not email or not password:
        print("[FT] FT_EMAIL or FT_PASSWORD not set — skipping")
        return []

    all_candidates = []
    seen_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        if not _login(page, email, password):
            browser.close()
            return []

        # Scrape section pages for candidates
        for section_url in FT_SECTIONS:
            if len(all_candidates) >= quota * 4:
                break
            try:
                page.goto(section_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)
                _dismiss_consent(page)
                articles = _extract_candidates(page)
                for a in articles:
                    if a["url"] not in seen_urls:
                        seen_urls.add(a["url"])
                        all_candidates.append(a)
            except Exception as e:
                print(f"[FT] Section error {section_url}: {e}")
                continue

        print(f"[FT] {len(all_candidates)} candidates found")
        browser.close()

    return all_candidates


def fetch_selected_bodies(articles: list[dict]) -> list[dict]:
    """
    Fetch full article bodies for already-selected FT articles.
    Call this after filter.select_articles() so we only fetch bodies for the final 5.
    """
    email = os.environ.get("FT_EMAIL", "")
    password = os.environ.get("FT_PASSWORD", "")
    if not email or not password:
        return articles

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        if not _login(page, email, password):
            browser.close()
            return articles

        for a in articles:
            print(f"[FT] Fetching body: {a['title'][:60]}")
            a["content"] = _fetch_article_body(page, a["url"])
            time.sleep(1)

        browser.close()

    return articles
