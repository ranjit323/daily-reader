"""
Renders the reading list and individual article pages using Jinja2.

Outputs:
  docs/index.html                    — latest reading list
  docs/archive/YYYY-MM-DD.html       — dated archive copy
  docs/articles/YYYY-MM-DD-NNN.html  — individual article pages
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
DOCS_DIR = Path(__file__).parent.parent / "docs"


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    env.filters["format_date"] = _format_date
    return env


def _format_date(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%-d %b %Y")


def _slug(title: str, index: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower())[:40].strip("-")
    return f"{index:03d}-{s}"


def render(sections: list[dict], date: datetime | None = None) -> str:
    if date is None:
        date = datetime.now(tz=timezone.utc)

    date_str = date.strftime("%Y-%m-%d")
    date_display = date.strftime("%-d %B %Y")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "archive").mkdir(parents=True, exist_ok=True)
    articles_dir = DOCS_DIR / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    env = _make_env()

    # ── Generate individual article pages ──────────────────────────────────
    article_tmpl = env.get_template("article.html.j2")
    article_index = 0

    for section in sections:
        for article in section["articles"]:
            article_index += 1
            slug = _slug(article.get("title", "article"), article_index)
            filename = f"{date_str}-{slug}.html"
            article["_page"] = f"articles/{filename}"

            html = article_tmpl.render(
                article=article,
                date_display=date_display,
            )
            (articles_dir / filename).write_text(html, encoding="utf-8")

    # ── Generate index ─────────────────────────────────────────────────────
    index_tmpl = env.get_template("reading_list.html.j2")
    index_html = index_tmpl.render(
        sections=sections,
        date=date,
        date_display=date_display,
    )

    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")
    (DOCS_DIR / "archive" / f"{date_str}.html").write_text(index_html, encoding="utf-8")

    return "docs/index.html"
