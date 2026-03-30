# daily-reader — Setup

Morning reading list from FT, The Economist, LRB, NLR, and Substack.
Delivered at 7am NZT via email. Hosted on GitHub Pages.

Live: https://ranjit323.github.io/daily-reader/

---

## Secrets

Run the interactive secret setter:

```bash
./set-secrets.sh
```

| Secret | What it is |
|---|---|
| `FT_RSS_URL` | Your personal myFT RSS URL — myft.ft.com → Contact preferences → RSS |
| `GMAIL_ADDRESS` | Gmail address (send account and Ranjit's receive address) |
| `GMAIL_APP_PASSWORD` | Gmail App Password — myaccount.google.com/apppasswords |
| `RECIPIENT_EMAIL_2` | Second receive address (Steph) |
| `TWITTER_USERNAME` | X/Twitter handle without @ — for Substack discovery |
| `ECONOMIST_EMAIL` | Economist login |
| `ECONOMIST_PASSWORD` | Economist password |
| `LRB_EMAIL` | LRB login |
| `LRB_PASSWORD` | LRB password |
| `NLR_EMAIL` | NLR login |
| `NLR_PASSWORD` | NLR password |

---

## Trigger a manual run

```bash
gh workflow run morning.yml --repo ranjit323/daily-reader
```

---

## Timezone

Cron runs at `18:00 UTC`:
- **NZDT (UTC+13, Oct–Apr):** 7am ✓
- **NZST (UTC+12, Apr–Oct):** 6am — change cron to `0 19 * * *` in April

Edit `.github/workflows/morning.yml` to change the time.

---

## Local run

```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium --with-deps

export GMAIL_ADDRESS="..."
export GMAIL_APP_PASSWORD="..."
export PAGES_URL="https://ranjit323.github.io/daily-reader/"
# add other secrets as needed

python3 src/main.py
```

---

## Pages setup (one-time)

If GitHub Pages is not yet enabled:
- Repository → Settings → Pages
- Source: Deploy from a branch → `main` → `/docs`
- Save

---

## File structure

```
daily-reader/
├── src/
│   ├── main.py                  orchestrator
│   ├── filter.py                topic scoring
│   ├── renderer.py              HTML generation (index + article pages)
│   ├── mailer.py                Gmail SMTP
│   └── scrapers/
│       ├── ft.py                FT (myFT RSS + arts/culture public feeds)
│       ├── economist.py         Economist RSS
│       ├── lrb.py               LRB RSS
│       ├── nlr.py               NLR RSS
│       ├── fetch_body.py        Playwright body fetcher
│       └── substack.py          Nitter → Substack discovery
├── templates/
│   ├── reading_list.html.j2     index page
│   └── article.html.j2          per-article page
├── docs/
│   ├── index.html               latest list (GitHub Pages)
│   ├── archive/                 daily archives
│   └── articles/                full article pages
├── .github/workflows/morning.yml
├── set-secrets.sh
├── validate-credentials.py
└── CLAUDE.md                    full technical context (for Claude)
```
