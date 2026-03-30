"""
Article body fetcher using Playwright.
Attempts unauthenticated fetch first; falls back to authenticated if credentials set.
NLR articles get special treatment: footnotes extracted separately.
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
                    for p in paras
                    if len(p.inner_text().strip()) > 40
                )
                if len(text) > 200:
                    return text
        except Exception:
            continue
    return ""


def _extract_nlr_body_and_footnotes(page) -> tuple[str, list[str]]:
    """
    NLR-specific extraction. Returns (body_text, footnotes_list).
    - body_text: paragraphs joined by double newlines, with [N] markers for footnotes
    - footnotes_list: list of footnote strings, index 0 = footnote 1
    """
    # --- Extract footnotes first ---
    footnotes = []
    fn_selectors = [
        ".footnotes li",
        ".article-footnotes li",
        "#footnotes li",
        ".endnotes li",
        "ol.footnotes li",
        ".fn-group li",
        "section.footnotes li",
    ]
    for sel in fn_selectors:
        try:
            items = page.query_selector_all(sel)
            if items:
                footnotes = [
                    re.sub(r"\s+", " ", item.inner_text()).strip()
                    for item in items
                    if item.inner_text().strip()
                ]
                break
        except Exception:
            continue

    # --- Extract body paragraphs, preserving [N] footnote markers ---
    paragraphs = []
    body_selectors = [
        ".article-body p",
        ".entry-content p",
        ".post-content p",
        ".article__body p",
        "article p",
        "main p",
    ]
    for sel in body_selectors:
        try:
            paras = page.query_selector_all(sel)
            if not paras:
                continue
            for p in paras:
                # Get inner HTML so we can see <sup> tags
                try:
                    html = p.inner_html()
                except Exception:
                    html = p.inner_text()
                # Convert <sup>N</sup> or <sup><a ...>N</a></sup> → [N]
                html = re.sub(
                    r'<sup[^>]*>\s*(?:<a[^>]*>)?\s*(\d+)\s*(?:</a>)?\s*</sup>',
                    r'[\1]',
                    html,
                )
                # Strip remaining HTML tags
                text = re.sub(r"<[^>]+>", " ", html)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 40:
                    paragraphs.append(text)
            if paragraphs:
                break
        except Exception:
            continue

    # Fall back to plain _extract_body if nothing found
    if not paragraphs:
        plain = _extract_body(page)
        return plain, footnotes

    return "\n\n".join(paragraphs), footnotes


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
    if credentials are available. NLR gets footnote extraction.
    """
    cfg = LOGIN_CONFIGS.get(site_key)
    has_credentials = cfg and os.environ.get(cfg["email_env"]) and os.environ.get(cfg["password_env"])
    is_nlr = site_key == "nlr"

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

        if has_credentials:
            print(f"[{site_key}] Logging in...")
            logged_in = _login(page, cfg)
            if not logged_in:
                print(f"[{site_key}] Login failed — trying unauthenticated")
        else:
            print(f"[{site_key}] No credentials — fetching open content")

        for article in articles:
            if article.get("content") and len(article["content"]) > 400:
                continue
            try:
                print(f"[{site_key}] Fetching body: {article['title'][:55]}")
                page.goto(article["url"], wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(2000)
                _dismiss_consent(page)

                if is_nlr:
                    body, footnotes = _extract_nlr_body_and_footnotes(page)
                    if body:
                        article["content"] = body
                        article["footnotes"] = footnotes
                        print(f"[{site_key}]   → {len(body)} chars, {len(footnotes)} footnotes")
                    else:
                        print(f"[{site_key}]   → no body extracted")
                else:
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
