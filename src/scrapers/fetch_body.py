"""
Generic article body fetcher using Playwright.
Used by Economist, LRB, NLR scrapers when credentials are available.
"""

import os
import re
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace(
        "&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s{2,}", " ", text).strip()


def _dismiss_consent(page):
    for selector in (
        "#onetrust-accept-btn-handler",
        "button[id*='accept']",
        "button[class*='consent']",
        "button[class*='cookie']",
    ):
        try:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(600)
                return
        except Exception:
            pass


def _extract_body(page) -> str:
    """Try common article body selectors."""
    selectors = [
        # Economist
        ".article__body-text p",
        "[data-test-id='Article'] p",
        # LRB
        ".article-body p",
        ".lrb-readmore p",
        # NLR
        ".article-body p",
        ".entry-content p",
        # Generic
        "article p",
        "main p",
        ".content p",
        ".body p",
    ]
    for selector in selectors:
        paras = page.query_selector_all(selector)
        if paras:
            text = "\n\n".join(
                re.sub(r"\s+", " ", p.inner_text()).strip()
                for p in paras[:20]
                if len(p.inner_text().strip()) > 40
            )
            if len(text) > 200:
                return text[:3000]
    return ""


LOGIN_CONFIGS = {
    "economist": {
        "login_url": "https://myaccount.economist.com/s/login",
        "email_env": "ECONOMIST_EMAIL",
        "password_env": "ECONOMIST_PASSWORD",
    },
    "lrb": {
        "login_url": "https://www.lrb.co.uk/login",
        "email_env": "LRB_EMAIL",
        "password_env": "LRB_PASSWORD",
    },
    "nlr": {
        "login_url": "https://newleftreview.org/my-account/login",
        "email_env": "NLR_EMAIL",
        "password_env": "NLR_PASSWORD",
    },
}


def fetch_bodies(articles: list[dict], site_key: str) -> list[dict]:
    """
    Fetch full article bodies for a list of articles using Playwright.
    `site_key` must be one of: economist, lrb, nlr.

    If credentials are not set, returns articles unchanged.
    """
    cfg = LOGIN_CONFIGS.get(site_key)
    if not cfg:
        return articles

    email = os.environ.get(cfg["email_env"], "")
    password = os.environ.get(cfg["password_env"], "")

    if not email or not password:
        print(f"[{site_key}] No credentials — using RSS content only")
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

        # Login
        try:
            page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            _dismiss_consent(page)

            email_input = page.query_selector('input[type="email"], input[name="email"], input[name="username"]')
            if email_input:
                email_input.fill(email)
                page.keyboard.press("Tab")
                pw_input = page.query_selector('input[type="password"]')
                if pw_input:
                    pw_input.fill(password)
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("domcontentloaded", timeout=20000)
                    page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[{site_key}] Login error: {e}")
            browser.close()
            return articles

        # Fetch each article body
        for article in articles:
            if article.get("content") and len(article["content"]) > 300:
                continue  # Already have good content from RSS
            try:
                print(f"[{site_key}] Fetching: {article['title'][:60]}")
                page.goto(article["url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2000)
                _dismiss_consent(page)
                body = _extract_body(page)
                if body:
                    article["content"] = body
                time.sleep(1)
            except Exception as e:
                print(f"[{site_key}] Body fetch error: {e}")
                continue

        browser.close()

    return articles
