"""
Validate login credentials for all Daily Reader publications.
Run before set-secrets.sh to confirm everything works.

Usage:
  python validate-credentials.py
"""

import getpass
import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


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


def check_ft(page, email, password) -> tuple[bool, str]:
    try:
        page.goto("https://www.ft.com/login?location=https://www.ft.com",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        _dismiss_consent(page)

        email_input = page.query_selector('input[type="email"], input[name="email"]')
        if not email_input:
            return False, "Could not find email input"
        email_input.fill(email)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.wait_for_timeout(1500)

        pw_input = page.query_selector('input[type="password"]')
        if not pw_input:
            submit = page.query_selector('button[type="submit"]')
            if submit:
                submit.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                page.wait_for_timeout(1500)
            pw_input = page.query_selector('input[type="password"]')

        if not pw_input:
            return False, "Could not find password input"

        pw_input.fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)

        # Check for logged-in indicators
        if page.query_selector('a[href*="logout"], a[href*="sign-out"], [data-trackable="navigation-user-account"]'):
            return True, "Logged in"
        # Check we're not still on login page
        if "login" in page.url or "accounts.ft" in page.url:
            return False, "Still on login page — wrong password?"
        return True, "Logged in (unverified)"

    except PlaywrightTimeout:
        return False, "Timed out"
    except Exception as e:
        return False, str(e)


def check_economist(page, email, password) -> tuple[bool, str]:
    try:
        page.goto("https://myaccount.economist.com/s/login",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        _dismiss_consent(page)

        email_input = page.query_selector('input[type="email"], input[name="username"]')
        if not email_input:
            return False, "Could not find email input"
        email_input.fill(email)

        pw_input = page.query_selector('input[type="password"]')
        if not pw_input:
            page.keyboard.press("Enter")
            page.wait_for_timeout(1500)
            pw_input = page.query_selector('input[type="password"]')

        if not pw_input:
            return False, "Could not find password input"

        pw_input.fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)

        if "login" in page.url or "error" in page.url.lower():
            return False, "Login failed — check credentials"
        if page.query_selector('a[href*="logout"], a[href*="sign-out"]'):
            return True, "Logged in"
        return True, "Logged in (unverified)"

    except PlaywrightTimeout:
        return False, "Timed out"
    except Exception as e:
        return False, str(e)


def check_lrb(page, email, password) -> tuple[bool, str]:
    try:
        page.goto("https://www.lrb.co.uk/login",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        _dismiss_consent(page)

        email_input = page.query_selector('input[type="email"], input[name="email"], input[name="username"]')
        if not email_input:
            return False, "Could not find email input"
        email_input.fill(email)

        pw_input = page.query_selector('input[type="password"]')
        if not pw_input:
            return False, "Could not find password input"
        pw_input.fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)

        if "login" in page.url:
            error_el = page.query_selector(".error, .alert, [class*='error']")
            msg = error_el.inner_text() if error_el else "Login failed"
            return False, msg
        return True, "Logged in"

    except PlaywrightTimeout:
        return False, "Timed out"
    except Exception as e:
        return False, str(e)


def check_nlr(page, email, password) -> tuple[bool, str]:
    try:
        page.goto("https://newleftreview.org/my-account/login",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        _dismiss_consent(page)

        email_input = page.query_selector('input[type="email"], input[name="email"], input[name="username"], input[name="log"]')
        if not email_input:
            return False, "Could not find email input"
        email_input.fill(email)

        pw_input = page.query_selector('input[type="password"]')
        if not pw_input:
            return False, "Could not find password input"
        pw_input.fill(password)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(2000)

        if "login" in page.url or "my-account/login" in page.url:
            return False, "Still on login page — wrong credentials?"
        return True, "Logged in"

    except PlaywrightTimeout:
        return False, "Timed out"
    except Exception as e:
        return False, str(e)


SITES = [
    {
        "key": "ft",
        "name": "Financial Times",
        "required": True,
        "checker": check_ft,
    },
    {
        "key": "economist",
        "name": "The Economist",
        "required": False,
        "checker": check_economist,
    },
    {
        "key": "lrb",
        "name": "London Review of Books",
        "required": False,
        "checker": check_lrb,
    },
    {
        "key": "nlr",
        "name": "New Left Review",
        "required": False,
        "checker": check_nlr,
    },
]


def main():
    print()
    print("Daily Reader — Credential Validation")
    print("─────────────────────────────────────")
    print("Enter credentials to test. Leave blank to skip optional sites.")
    print()

    credentials = {}
    for site in SITES:
        tag = "(required)" if site["required"] else "(optional)"
        print(f"── {site['name']} {tag}")
        email = input(f"   Email: ").strip()
        if not email:
            if site["required"]:
                print("   ✗ Required — cannot skip FT")
                sys.exit(1)
            else:
                print("   — skipped")
                print()
                continue
        password = input(f"   Password: ").strip()
        credentials[site["key"]] = (email, password)
        print()

    if not credentials:
        print("Nothing to validate.")
        sys.exit(0)

    print("Launching browser...")
    print()

    results = {}
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

        for site in SITES:
            key = site["key"]
            if key not in credentials:
                continue
            email, password = credentials[key]
            print(f"Testing {site['name']}...", end=" ", flush=True)
            page = context.new_page()
            ok, msg = site["checker"](page, email, password)
            page.close()
            results[key] = (ok, msg)
            print("✓ OK" if ok else f"✗ Failed: {msg}")
            time.sleep(1)

        browser.close()

    print()
    print("─────────────────────────────────────")
    all_ok = all(ok for ok, _ in results.values())
    failed = [(k, msg) for k, (ok, msg) in results.items() if not ok]

    if all_ok:
        print("All credentials valid. Run ./set-secrets.sh to save them to GitHub.")
    else:
        print("Some credentials failed:")
        for key, msg in failed:
            name = next(s["name"] for s in SITES if s["key"] == key)
            print(f"  ✗ {name}: {msg}")
        print()
        print("Fix the above, then re-run this script before running ./set-secrets.sh")

    print()


if __name__ == "__main__":
    main()
