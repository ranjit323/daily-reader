"""
Morning Reading List — orchestrator.

Required env vars:
  FT_EMAIL / FT_PASSWORD
  GMAIL_ADDRESS / GMAIL_APP_PASSWORD
  PAGES_URL
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers import economist, lrb, nlr, ft
from src.filter import select_articles
from src import renderer, mailer


QUOTAS = {
    "Financial Times": 5,
    "The Economist": 5,
    "London Review of Books": 1,
    "New Left Review": 1,
}


def run():
    today = datetime.now(tz=timezone.utc)
    print(f"[main] Starting — {today.strftime('%Y-%m-%d')}")

    print("[main] Fetching FT...")
    ft_raw = ft.fetch(quota=20)

    print("[main] Fetching Economist...")
    economist_raw = economist.fetch(quota=20)

    print("[main] Fetching LRB...")
    lrb_raw = lrb.fetch(quota=10)

    print("[main] Fetching NLR...")
    nlr_raw = nlr.fetch(quota=10)

    sections = []

    # FT first
    ft_selected = select_articles(ft_raw, QUOTAS["Financial Times"])
    if ft_selected:
        sections.append({"source": "Financial Times", "articles": ft_selected})
        print(f"[main] FT: {len(ft_selected)} articles selected")
    else:
        print("[main] Warning: no FT articles selected")

    economist_selected = select_articles(economist_raw, QUOTAS["The Economist"])
    if economist_selected:
        sections.append({"source": "The Economist", "articles": economist_selected})

    lrb_selected = select_articles(lrb_raw, QUOTAS["London Review of Books"])
    if lrb_selected:
        sections.append({"source": "London Review of Books", "articles": lrb_selected})

    nlr_selected = select_articles(nlr_raw, QUOTAS["New Left Review"])
    if nlr_selected:
        sections.append({"source": "New Left Review", "articles": nlr_selected})

    total = sum(len(s["articles"]) for s in sections)
    print(f"[main] {total} articles across {len(sections)} publications")

    if not sections:
        print("[main] No articles — aborting")
        sys.exit(1)

    print("[main] Rendering...")
    renderer.render(sections, date=today)
    print("[main] Written to docs/")

    pages_url = os.environ.get("PAGES_URL", "https://ranjit323.github.io/daily-reader/")
    print(f"[main] Sending email → {pages_url}")
    mailer.send(pages_url, date=today)

    print("[main] Done.")


if __name__ == "__main__":
    run()
