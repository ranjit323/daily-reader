"""
Article body fetcher using Playwright.
Attempts unauthenticated fetch first; falls back to authenticated if credentials set.
"""

import os
import re
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def _dismiss_consent(page):
    for selector in (
        "#onetrust-accept-btn-handler",
        "button[id*='accept']",
        "button[class*='consent']",
        "button[class*='cookie']",
        "[class*='gdpr'] button",
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
    """Try common article body selectors, return cleaned text."""
    selectors = [
        # Economist
        ".article__body-text p",
        "[data-test-id='Article'] p",
        ".ds-layout-grid p",
        # LRB
        ".article-body p",
        ".lrb-readmore p",
        ".article__body p",
        # NLR
        ".article-body p",
        ".entry-content p",
        ".post-content p",
        # Generic
        "article p",
        "main p",
        ".content p",
        ".body p",
    ]
    for selector in selectors:
        try:
            paras = page.query_selector_all(selector)
            if paras:
                text = "\n\n".join(
                    re.sub(r"\s+", " ", p.inner_text()).strip()
                    for p in paras[:60]
                    if len(p.inner_text().strip()) > 40
                )
                if len(text) > 200:
                    return text[:12000]
        except Exception:
            continue
    return ""


LOGIN_CONFIGS = {
    "economist": {
        "login_url": "https://myaccount.economist.com/s/login",
        "email_env": "ECONOMIST_EMAIL",
        "password_env": "ECONOMIST_PASSWORD",
        "email_selector": 'input[type="email"], input[name="username"]',
    },
    "lrb": {
        "login_url": "https://www.lrb.co.uk/login",
        "email_env": "LRB_EMAIL",
        "password_env": "LRB_PASSWORD",
        "email_selector": 'input[type="email"], input[name="email"], input[name="username"]',
    },
    "nlr": {
        "login_url": "https://newleftreview.org/my-account/login",
        "email_env": "NLR_EMAIL",
        "password_env": "NLR_PASSWORD",
        "email_selector": 'input[type="email"], input[name="email"], input[name="log"]',
    },
}


def _login(page, cfg: dict) -> bool:
    email = os.environ.get(cfg["email_env"], "")
    password = os.environ.get(cfg["password_env"], "")
    if not email or not password:
        return False
    try:
        page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        _dismiss_consent(page)

        email_input = page.query_selector(cfg["email_selector"])
        if not email_input:
            return False
        email_input.fill(email)

        pw_input = page.query_selector('input[type="password"]')
        if not pw_input:
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            pw_input = page.query_selector('input[type="password"]')

        if not pw_input:
            return False

        pw_input.fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
        return True
    except Exception as e:
        print(f"  Login error: {e}")
        return False


def fetch_bodies(articles: list[dict], site_key: str) -> list[dict]:
    """
    Fetch full article bodies. Tries unauthenticated first, then authenticated
    if credentials are available. Always returns articles (with whatever content
    was retrievable).
    """
    cfg = LOGIN_CONFIGS.get(site_key)
    has_credentials = cfg and os.environ.get(cfg["email_env"]) and os.environ.get(cfg["password_env"])

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

        # Authenticate if credentials available
        if has_credentials:
            print(f"[{site_key}] Logging in...")
            logged_in = _login(page, cfg)
            if not logged_in:
                print(f"[{site_key}] Login failed — trying unauthenticated")
        else:
            print(f"[{site_key}] No credentials — fetching open content")

        for article in articles:
            # Skip if we already have substantial content from RSS
            if article.get("content") and len(article["content"]) > 400:
                continue
            try:
                print(f"[{site_key}] Fetching body: {article['title'][:55]}")
                page.goto(article["url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2000)
                _dismiss_consent(page)
                body = _extract_body(page)
                if body:
                    article["content"] = body
                    print(f"[{site_key}]   → {len(body)} chars")
                else:
                    print(f"[{site_key}]   → no body extracted (may be paywalled)")
                time.sleep(1)
            except Exception as e:
                print(f"[{site_key}] Error fetching {article['url']}: {e}")
                continue

        browser.close()

    return articles
