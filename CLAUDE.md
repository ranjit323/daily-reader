# daily-reader — Claude context

This file is read automatically at the start of every Claude session in this project.
Do not delete it. Keep it up to date when making significant changes.

---

## What this is

A personal morning reading list for Ranjit (and his wife Steph).
- Scrapes FT, The Economist, LRB, NLR, and Substack (via Twitter timeline)
- Scores articles by topic relevance (banking, history, books, quirky/arts)
- Renders a minimal static site to `docs/` (served via GitHub Pages)
- Sends a 7am NZT email to both recipients with a link to the page
- Runs daily via GitHub Actions cron

Live URL: https://ranjit323.github.io/daily-reader/
Repo: https://github.com/ranjit323/daily-reader

---

## Recipients

| Person | Email | Secret |
|---|---|---|
| Ranjit | stored as GMAIL_ADDRESS | also the send account |
| Steph | steph.raill@gmail.com | RECIPIENT_EMAIL_2 |

---

## Article quotas

| Source | Articles | Notes |
|---|---|---|
| Financial Times | 3 | Arts/culture/quirky sections only |
| The Economist | 3 | Finance, books-arts, briefing, leaders |
| London Review of Books | 1 | Full body fetched via Playwright auth |
| New Left Review | 1 | Full body fetched via Playwright auth — no truncation |
| Substack | 3 | Discovered via Ranjit's Twitter timeline (Nitter RSS) |
| **Total** | **11** | ~45–60 min reading |

---

## GitHub Secrets (all stored in ranjit323/daily-reader)

| Secret | Purpose |
|---|---|
| `FT_RSS_URL` | Personal myFT RSS feed URL (from myft.ft.com → Contact prefs → RSS) |
| `GMAIL_ADDRESS` | Gmail send address (also Ranjit's receive address) |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16 chars, from myaccount.google.com/apppasswords) |
| `RECIPIENT_EMAIL_2` | steph.raill@gmail.com |
| `TWITTER_USERNAME` | Ranjit's X/Twitter handle (no @) — for Substack discovery via Nitter |
| `ECONOMIST_EMAIL` | Economist login |
| `ECONOMIST_PASSWORD` | Economist password |
| `LRB_EMAIL` | LRB login |
| `LRB_PASSWORD` | LRB password |
| `NLR_EMAIL` | NLR login |
| `NLR_PASSWORD` | NLR password |

To update secrets: `./set-secrets.sh` or `gh secret set SECRET_NAME --repo ranjit323/daily-reader --body "value"`

---

## File structure

```
daily-reader/
├── CLAUDE.md                           ← you are here
├── SETUP.md                            ← human setup guide
├── set-secrets.sh                      ← interactive secret setter
├── validate-credentials.py             ← test logins work before deploying
├── requirements.txt                    ← pip deps (playwright, feedparser, jinja2, requests, bs4)
├── .github/workflows/morning.yml       ← cron 0 18 * * * UTC (= 7am NZDT)
├── src/
│   ├── main.py                         ← orchestrator: fetch → score → body → render → email
│   ├── filter.py                       ← topic scoring (banking/history/books/quirky keywords)
│   ├── renderer.py                     ← renders index.html + archive + per-article pages
│   ├── mailer.py                       ← Gmail SMTP, sends to both recipients
│   └── scrapers/
│       ├── ft.py                       ← myFT RSS (FT_RSS_URL) + arts/culture public feeds
│       ├── economist.py                ← section RSS feeds
│       ├── lrb.py                      ← lrb.co.uk RSS
│       ├── nlr.py                      ← newleftreview.org RSS, no content truncation
│       ├── fetch_body.py               ← Playwright body fetcher (Economist/LRB/NLR), no limits
│       └── substack.py                 ← Nitter RSS → Substack link extraction → article fetch
├── templates/
│   ├── reading_list.html.j2            ← index page template
│   └── article.html.j2                 ← per-article page template
└── docs/
    ├── index.html                      ← latest reading list (GitHub Pages root)
    ├── archive/YYYY-MM-DD.html         ← daily archives
    └── articles/YYYY-MM-DD-NNN.html   ← full article pages (linked from index)
```

---

## Design

- **Masthead**: "the daily" — lowercase, Nunito Black 900, 96px, tight tracking
- **Headlines**: Helvetica Neue 500, 19px
- **Body / meta / summaries**: Courier Prime (Google Fonts)
- **Date accent**: #c0392b (red)
- **Background**: #ffffff, text #111111
- **Max width**: 660px centered
- **Article links**: go to `docs/articles/` page when full content is available; fall back to external URL

---

## Cron timing

```yaml
cron: '0 18 * * *'   # 7am NZDT (UTC+13), Oct–Apr
```

When NZ daylight saving ends (first Sunday in April), change to `'0 19 * * *'` for 7am NZST (UTC+12).

---

## How to trigger a manual run

```bash
gh workflow run morning.yml --repo ranjit323/daily-reader
```

Watch it:
```bash
gh run list --repo ranjit323/daily-reader --limit 5
gh run view <RUN_ID> --repo ranjit323/daily-reader --log
```

---

## How to run locally

```bash
cd /Users/ranjitjayanandhan/ranjit-workspace/daily-reader
pip3 install -r requirements.txt
/Users/ranjitjayanandhan/Library/Python/3.9/bin/playwright install chromium --with-deps

export FT_RSS_URL="..."
export GMAIL_ADDRESS="..."
export GMAIL_APP_PASSWORD="..."
export RECIPIENT_EMAIL_2="steph.raill@gmail.com"
export TWITTER_USERNAME="..."
export NLR_EMAIL="..." && export NLR_PASSWORD="..."
export LRB_EMAIL="..." && export LRB_PASSWORD="..."
export ECONOMIST_EMAIL="..." && export ECONOMIST_PASSWORD="..."
export PAGES_URL="https://ranjit323.github.io/daily-reader/"

python3 src/main.py
```

Then open `docs/index.html` in a browser to verify.

---

## Known issues and fixes

### ubuntu-latest breaks Playwright
GitHub Actions `ubuntu-latest` moved to 24.04 which is incompatible with Playwright's
Chromium deps. Pinned to `ubuntu-22.04` in `morning.yml`. Do not change this.

### FT login (Playwright)
FT uses a React form — the submit button stays disabled until `input`/`change` events fire.
Standard `.fill()` doesn't trigger these. Must dispatch events via `page.evaluate()`.
Real password field selector: `input[type="password"]:not([id="_notUsed"])` (excludes honeypot).
See `src/scrapers/ft.py` for the current approach.

### FT content
Public feeds (world/markets/companies) return breaking news — not what we want.
Feeds are set to: life-arts, weekend, house-home, books-arts, lunch-with-the-ft, opinion.
If `FT_RSS_URL` (subscriber feed) is set, that is used first and supplemented by public feeds.

### Nitter for Substack discovery
Nitter instances go down. Current list in `src/scrapers/substack.py`:
nitter.net, nitter.cz, nitter.privacydev.net, nitter.1d4.us
If all fail, Substack section is silently skipped (no crash).

### Git push rejected
GitHub Actions commits to the repo after each run. Always `git pull --rebase` before pushing locally.

### python vs python3
macOS does not have `python` in PATH by default. Use `python3` for local runs.
GitHub Actions runner uses `python` (set up by `actions/setup-python`).

---

## What's been built (phase history)

### Phase 1 (complete)
- FT, Economist, LRB, NLR scrapers
- Topic scoring and article selection
- Jinja2 rendering to docs/index.html
- GitHub Pages hosting
- Gmail SMTP email delivery
- GitHub Actions daily cron

### Phase 2 (complete)
- Second email recipient (Steph)
- FT switched to arts/quirky/culture section feeds, quota 3
- NLR full article text — no truncation
- Article body fetching via Playwright (Economist, LRB, NLR)
- Per-article pages at docs/articles/ with full content
- Index page links to article pages (fallback to external URL)
- Substack discovery via Nitter RSS + BeautifulSoup
- Extended quirky keywords in filter.py
- Masthead: "the daily" lowercase, Nunito Black 900, 96px
- set-secrets.sh and workflow updated for new secrets
