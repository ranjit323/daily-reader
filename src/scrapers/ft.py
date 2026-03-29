"""
Financial Times scraper — uses Playwright (Chromium headless) to authenticate
and extract article metadata from selected sections.

Requires env vars: FT_EMAIL, FT_PASSWORD
"""

import os
import re
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


FT_LOGIN_URL = "https://accounts.ft.com/login"
FT_SECTIONS = [
    "https://www.ft.com/banking",
    "https://www.ft.com/companies/banks",
    "https://www.ft.com/world/global-economy",
    "https://www.ft.com/arts",
    "https://www.ft.com/books",
    "https://www.ft.com/world",
]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_articles_from_page(page) -> list[dict]:
    """Extract article cards visible on the current FT page."""
    articles = []

    # FT uses various article card selectors depending on the section
    selectors = [
        "div[data-trackable='article']",
        "li[class*='headline']",
        "div[class*='story-card']",
        "article",
    ]

    for selector in selectors:
        cards = page.query_selector_all(selector)
        if cards:
            for card in cards:
                try:
                    # Title
                    title_el = card.query_selector("a[data-trackable='heading-link'], h3 a, h2 a, .o-teaser__heading a")
                    if not title_el:
                        continue
                    title = _clean_text(title_el.inner_text())
                    url = title_el.get_attribute("href") or ""
                    if url and not url.startswith("http"):
                        url = "https://www.ft.com" + url

                    # Summary / standfirst
                    summary_el = card.query_selector(
                        ".o-teaser__standfirst, [data-trackable='standfirst'], p[class*='standfirst']"
                    )
                    summary = _clean_text(summary_el.inner_text()) if summary_el else ""

                    # Author
                    author_el = card.query_selector(
                        ".o-teaser__author, [data-trackable='author'], a[href*='/stream/authorsId']"
                    )
                    author = _clean_text(author_el.inner_text()) if author_el else "FT"

                    # Timestamp
                    time_el = card.query_selector("time")
                    published = None
                    if time_el:
                        dt_attr = time_el.get_attribute("datetime")
                        if dt_attr:
                            try:
                                published = datetime.fromisoformat(dt_attr.replace("Z", "+00:00"))
                            except ValueError:
                                pass

                    if title and url and "ft.com" in url:
                        articles.append({
                            "title": title,
                            "summary": summary[:280],
                            "url": url,
                            "author": author,
                            "published": published,
                            "source": "Financial Times",
                        })
                except Exception:
                    continue
            if articles:
                break

    return articles


def fetch(quota: int = 5) -> list[dict]:
    email = os.environ.get("FT_EMAIL", "")
    password = os.environ.get("FT_PASSWORD", "")

    if not email or not password:
        print("[FT] Warning: FT_EMAIL or FT_PASSWORD not set — skipping FT scrape")
        return []

    all_articles = []
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

        # --- Login ---
        try:
            page.goto(FT_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            page.fill('input[type="email"], input[name="email"]', email)
            page.click('button[type="submit"], input[type="submit"]')
            # After email submission FT may redirect to password step
            page.wait_for_load_state("domcontentloaded", timeout=15000)

            # Check if we're now on a password page
            if page.query_selector('input[type="password"]'):
                page.fill('input[type="password"]', password)
                page.click('button[type="submit"], input[type="submit"]')
                page.wait_for_load_state("domcontentloaded", timeout=20000)

        except PlaywrightTimeout:
            print("[FT] Login timed out")
            browser.close()
            return []
        except Exception as e:
            print(f"[FT] Login error: {e}")
            browser.close()
            return []

        # Brief wait for session cookies to settle
        time.sleep(2)

        # --- Scrape sections ---
        for section_url in FT_SECTIONS:
            if len(all_articles) >= quota * 3:
                break
            try:
                page.goto(section_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)
                articles = _extract_articles_from_page(page)
                for a in articles:
                    if a["url"] not in seen_urls:
                        seen_urls.add(a["url"])
                        all_articles.append(a)
            except Exception as e:
                print(f"[FT] Error scraping {section_url}: {e}")
                continue

        browser.close()

    return all_articles
