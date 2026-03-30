"""
Morning Reading List — orchestrator.

Required env vars:
  GMAIL_ADDRESS / GMAIL_APP_PASSWORD
  PAGES_URL
  RECIPIENT_EMAIL_2 (optional second recipient)
  TWITTER_USERNAME (optional, for Substack discovery)
  ECONOMIST_EMAIL / ECONOMIST_PASSWORD (optional)
  LRB_EMAIL / LRB_PASSWORD (optional)
  NLR_EMAIL / NLR_PASSWORD (optional)
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers import economist, lrb, nlr, substack
from src.scrapers.fetch_body import fetch_bodies
from src.filter import select_articles
from src import renderer, mailer


QUOTAS = {
    "The Economist": 2,
    "London Review of Books": 2,
    "New Left Review": 2,
    "Substack": 3,
}


def run():
    today = datetime.now(tz=timezone.utc)
    print(f"[main] Starting — {today.strftime('%Y-%m-%d')}")

    print("[main] Fetching Economist...")
    economist_raw = economist.fetch(quota=20)

    print("[main] Fetching LRB...")
    lrb_raw = lrb.fetch(quota=10)

    print("[main] Fetching NLR...")
    nlr_raw = nlr.fetch(quota=10)

    print("[main] Fetching Substack...")
    substack_raw = substack.fetch(quota=QUOTAS["Substack"])

    sections = []

    economist_selected = select_articles(economist_raw, QUOTAS["The Economist"])
    if economist_selected:
        sections.append({"source": "The Economist", "articles": economist_selected})
        print(f"[main] Economist: {len(economist_selected)} articles selected")

    lrb_selected = select_articles(lrb_raw, QUOTAS["London Review of Books"])
    if lrb_selected:
        sections.append({"source": "London Review of Books", "articles": lrb_selected})
        print(f"[main] LRB: {len(lrb_selected)} articles selected")

    nlr_selected = select_articles(nlr_raw, QUOTAS["New Left Review"])
    if nlr_selected:
        sections.append({"source": "New Left Review", "articles": nlr_selected})
        print(f"[main] NLR: {len(nlr_selected)} articles selected")

    substack_selected = select_articles(substack_raw, QUOTAS["Substack"])
    if substack_selected:
        sections.append({"source": "Substack", "articles": substack_selected})
        print(f"[main] Substack: {len(substack_selected)} articles selected")

    total = sum(len(s["articles"]) for s in sections)
    print(f"[main] {total} articles across {len(sections)} publications")

    if not sections:
        print("[main] No articles — aborting")
        sys.exit(1)

    # Fetch full article bodies for all paywalled sources
    for section in sections:
        source = section["source"]
        articles = section["articles"]
        if source == "The Economist":
            print("[main] Fetching Economist article bodies...")
            fetch_bodies(articles, "economist")
        elif source == "London Review of Books":
            print("[main] Fetching LRB article bodies...")
            fetch_bodies(articles, "lrb")
        elif source == "New Left Review":
            print("[main] Fetching NLR article bodies...")
            fetch_bodies(articles, "nlr")

    print("[main] Rendering...")
    renderer.render(sections, date=today)
    print("[main] Written to docs/")

    pages_url = os.environ.get("PAGES_URL", "https://ranjit323.github.io/daily-reader/")
    print(f"[main] Sending email → {pages_url}")
    mailer.send(pages_url, date=today)

    print("[main] Done.")


if __name__ == "__main__":
    run()
