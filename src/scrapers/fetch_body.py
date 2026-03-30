"""
Article body fetcher using Playwright.
Attempts unauthenticated fetch first; falls back to authenticated if credentials set.
NLR articles get special treatment: always fetched via Playwright, footnotes extracted.
"""

import os
import re
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


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


def _clean_html_to_text(html: str) -> str:
    """Strip all HTML tags, collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body(page) -> str:
    """Try common article body selectors, return cleaned text."""
    selectors = [
        ".article__body-text p",
        "[data-test-id='Article'] p",
        ".ds-layout-grid p",
        ".article-body p",
        ".lrb-readmore p",
        ".article__body p",
        ".entry-content p",
        ".post-content p",
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


def _parse_nlr_paragraph(html: str) -> str:
    """
    Parse a single NLR paragraph's inner HTML using BeautifulSoup.
    - Removes <a class="*note-ref*"> wrappers (and their text) entirely.
    - Converts <sup>N</sup> → [N] markers.
    - Returns clean plain text.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove NLR footnote anchor wrappers — these contain the word "footnote"
    # and are immediately followed by <sup>N</sup>. We want only [N], not the word.
    for tag in soup.find_all("a"):
        classes = " ".join(tag.get("class") or [])
        if "note-ref" in classes:
            tag.decompose()

    # Replace <sup> containing only a digit with [N]
    for sup in soup.find_all("sup"):
        text = sup.get_text(strip=True)
        if text.isdigit():
            sup.replace_with(f"[{text}]")
        else:
            # sup contains an <a> link — extract just the digit from it
            inner = re.sub(r"\D", "", text)
            if inner:
                sup.replace_with(f"[{inner}]")
            else:
                sup.decompose()

    return re.sub(r"\s+", " ", soup.get_text()).strip()


def _extract_nlr_body_and_footnotes(page) -> tuple[str, list[str]]:
    """
    NLR-specific extraction.
    Returns (body_text, footnotes_list).

    Uses BeautifulSoup for paragraph parsing so NLR's multiline/complex
    href attributes don't break the note-ref anchor removal.
    Footnotes live in .article-body__notes or similar containers.
    """

    # Scroll to bottom twice to trigger lazy-loaded content
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # --- Extract footnotes ---
    footnotes = []
    fn_selectors = [
        ".article-body__notes li",
        ".article-body__notes p",
        ".footnotes li",
        ".article-footnotes li",
        "#footnotes li",
        ".endnotes li",
        "ol.footnotes li",
        ".fn-group li",
        "section.footnotes li",
        "[class*='notes'] li",
    ]
    for sel in fn_selectors:
        try:
            items = page.query_selector_all(sel)
            if items:
                candidates = [
                    re.sub(r"\s+", " ", item.inner_text()).strip()
                    for item in items
                    if len(item.inner_text().strip()) > 10
                ]
                if candidates:
                    footnotes = candidates
                    print(f"[nlr]   footnotes via {sel}: {len(footnotes)} found")
                    break
        except Exception:
            continue

    # --- Extract body paragraphs ---
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
                try:
                    html = p.inner_html()
                    text = _parse_nlr_paragraph(html)
                except Exception:
                    text = re.sub(r"\s+", " ", p.inner_text()).strip()
                if len(text) > 40:
                    paragraphs.append(text)
            if paragraphs:
                break
        except Exception:
            continue

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
        "login_url": "https://newleftreview.org/sign_in",
        "email_env": "NLR_EMAIL",
        "password_env": "NLR_PASSWORD",
        "email_selector": 'input[type="email"], input[type="text"], input[name="email"], input[name="log"]',
    },
}


def _login(page, cfg: dict) -> bool:
    email = os.environ.get(cfg["email_env"], "")
    password = os.environ.get(cfg["password_env"], "")
    if not email or not password:
        print(f"  Login: credentials not set")
        return False
    try:
        print(f"  Login: navigating to {cfg['login_url']}")
        page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        _dismiss_consent(page)
        print(f"  Login: page URL is {page.url}")

        email_input = page.query_selector(cfg["email_selector"])
        if not email_input:
            print(f"  Login: email input not found (selector: {cfg['email_selector']})")
            return False
        email_input.fill(email)
        print(f"  Login: email filled")

        pw_input = page.query_selector('input[type="password"]')
        if not pw_input:
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            pw_input = page.query_selector('input[type="password"]')

        if not pw_input:
            print(f"  Login: password input not found")
            return False

        pw_input.fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)
        print(f"  Login: post-login URL is {page.url}")
        return True
    except Exception as e:
        print(f"  Login error: {e}")
        return False


def fetch_bodies(articles: list[dict], site_key: str) -> list[dict]:
    """
    Fetch full article bodies.
    - NLR: always fetches via Playwright (never skips based on RSS content length)
      and extracts footnotes separately.
    - Others: skip if RSS already provided >400 chars of content.
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
            # NLR: always fetch full page (RSS only gives abstract)
            # Others: skip if RSS already gave substantial content
            if not is_nlr and article.get("content") and len(article["content"]) > 400:
                continue
            try:
                print(f"[{site_key}] Fetching body: {article['title'][:55]}")
                page.goto(article["url"], wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
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
