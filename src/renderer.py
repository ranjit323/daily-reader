"""
Renders the reading list as a static HTML page using Jinja2.
Writes to docs/index.html (always the latest) and docs/archive/YYYY-MM-DD.html.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
DOCS_DIR = Path(__file__).parent.parent / "docs"


def render(sections: list[dict], date: datetime | None = None) -> str:
    """
    Render the reading list to HTML and write to docs/.

    sections: list of dicts like:
      {
        "source": "Financial Times",
        "articles": [ { title, summary, url, author, published, source } ]
      }

    Returns the GitHub Pages URL path.
    """
    if date is None:
        date = datetime.now(tz=timezone.utc)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    env.filters["format_date"] = _format_date

    template = env.get_template("reading_list.html.j2")
    html = template.render(
        sections=sections,
        date=date,
        date_display=date.strftime("%-d %B %Y"),
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    archive_dir = DOCS_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Write latest
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")

    # Write archive copy
    archive_path = archive_dir / f"{date.strftime('%Y-%m-%d')}.html"
    archive_path.write_text(html, encoding="utf-8")

    return f"docs/index.html"


def _format_date(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt
    return dt.strftime("%-d %b %Y")
