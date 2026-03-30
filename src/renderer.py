"""
Renders the reading list as a static HTML page using Jinja2.
Writes to docs/index.html, docs/archive/YYYY-MM-DD.html,
and docs/articles/YYYY-MM-DD-NNN.html for each article with full content.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup


TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
DOCS_DIR = Path(__file__).parent.parent / "docs"


def render(sections: list[dict], date: datetime | None = None) -> str:
    if date is None:
        date = datetime.now(tz=timezone.utc)

    date_str = date.strftime("%Y-%m-%d")
    date_display = date.strftime("%-d %B %Y")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "archive").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "articles").mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["format_date"] = _format_date
    env.filters["linkify_footnotes"] = _linkify_footnotes

    # Generate individual article pages
    article_template = env.get_template("article.html.j2")
    article_counter = 0
    for section in sections:
        for article in section["articles"]:
            article_counter += 1
            slug = f"{date_str}-{article_counter:03d}"
            page_filename = f"{slug}.html"
            page_path = f"articles/{page_filename}"

            content = article.get("content", "")
            if content and len(content) > 200:
                article_html = article_template.render(
                    article=article,
                    date_display=date_display,
                    back_url="../index.html",
                )
                (DOCS_DIR / "articles" / page_filename).write_text(article_html, encoding="utf-8")
                article["_page"] = page_path
            else:
                article["_page"] = None

    html = env.get_template("reading_list.html.j2").render(
        sections=sections,
        date=date,
        date_display=date_display,
    )

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    (DOCS_DIR / "archive" / f"{date_str}.html").write_text(html, encoding="utf-8")

    return "docs/index.html"


def _format_date(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%-d %b %Y")


def _linkify_footnotes(text: str) -> Markup:
    """Convert [N] markers in body text to superscript anchor links."""
    def replace(m):
        n = m.group(1)
        return f'<sup><a href="#fn-{n}" id="fnref-{n}" class="fn-ref">{n}</a></sup>'
    return Markup(re.sub(r'\[(\d+)\]', replace, str(text)))
