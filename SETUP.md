# Daily Reader — Setup

A morning reading list from FT, The Economist, London Review of Books, and New Left Review. Delivered at 7am via email. Hosted on GitHub Pages.

---

## One-time setup

### 1. Create a GitHub repository

```bash
cd daily-reader
git init
git add .
git commit -m "initial commit"
gh repo create daily-reader --private --source=. --push
```

### 2. Enable GitHub Pages

In your repository on GitHub:
- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/docs`
- Save

Your reading list will be available at:
`https://YOUR-USERNAME.github.io/daily-reader/`

### 3. Get a Gmail App Password

Your Gmail account must have 2-Step Verification enabled.

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create a new App Password — name it "daily-reader"
3. Copy the 16-character password (spaces don't matter)

### 4. Add GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `FT_EMAIL` | Your FT account email |
| `FT_PASSWORD` | Your FT account password |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | The App Password from step 3 |

### 5. Test it manually

In your repository: **Actions → Morning Reading List → Run workflow**

Watch the run — it should complete in ~3 minutes, then:
- Check `docs/index.html` was updated in the repo
- Check your Gmail inbox for the email

---

## Timezone

The cron runs at `18:00 UTC`:
- **NZDT (UTC+13, Oct–Apr):** arrives at 7am ✓
- **NZST (UTC+12, Apr–Oct):** arrives at 6am — change cron to `0 19 * * *` in April

To update: edit `.github/workflows/morning.yml` and change `'0 18 * * *'` to `'0 19 * * *'`.

---

## Local testing

```bash
cd daily-reader
pip install -r requirements.txt
playwright install chromium --with-deps

export FT_EMAIL="your@email.com"
export FT_PASSWORD="yourpassword"
export GMAIL_ADDRESS="your@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
export PAGES_URL="https://YOUR-USERNAME.github.io/daily-reader/"

python src/main.py
```

Then open `docs/index.html` in your browser to verify the design.

---

## File structure

```
daily-reader/
├── .github/workflows/morning.yml   # Daily cron + email
├── src/
│   ├── main.py                     # Orchestrator
│   ├── filter.py                   # Topic scoring (history, books, banking, quirky)
│   ├── renderer.py                 # HTML generation
│   ├── mailer.py                   # Gmail SMTP
│   └── scrapers/
│       ├── ft.py                   # Playwright (requires FT credentials)
│       ├── economist.py            # Public RSS
│       ├── lrb.py                  # Public RSS
│       └── nlr.py                  # Public RSS
├── templates/reading_list.html.j2  # Page design
├── docs/
│   ├── index.html                  # Latest reading list (GitHub Pages)
│   └── archive/YYYY-MM-DD.html     # Archive
└── requirements.txt
```

---

## Adjusting topics

Edit `src/filter.py` — the `TOPICS` dict controls which keywords score articles higher. Add or remove keywords from any bucket.

---

## Adding LRB/NLR credentials (optional)

If the public RSS feeds return too few articles, add authenticated scraping:
- Add secrets `LRB_EMAIL`, `LRB_PASSWORD`, `NLR_EMAIL`, `NLR_PASSWORD`
- Extend `src/scrapers/lrb.py` and `nlr.py` with Playwright login (same pattern as `ft.py`)
