"""
Renders the reading list as a static HTML page using Jinja2.
Writes to docs/index.html and docs/archive/YYYY-MM-DD.html.
"""

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
DOCS_DIR = Path(__file__).parent.parent / "docs"


def render(sections: list[dict], date: datetime | None = None) -> str:
    if date is None:
        date = datetime.now(tz=timezone.utc)

    date_str = date.strftime("%Y-%m-%d")
    date_display = date.strftime("%-d %B %Y")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "archive").mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["format_date"] = _format_date

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
