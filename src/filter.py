"""
Topic scoring and article selection.
"""

from datetime import datetime, timezone

TOPICS = {
    "banking": [
        "bank", "banks", "banking", "finance", "financial", "fintech",
        "monetary", "credit", "capital", "lending", "regulation", "regulator",
        "interest rate", "central bank", "fed", "boe", "rbnz", "debt",
        "investment", "market", "markets", "asset", "currency", "inflation",
    ],
    "history": [
        "history", "historical", "century", "centuries", "ancient", "medieval",
        "war", "wars", "era", "revolution", "empire", "empires", "past",
        "archive", "origins", "legacy", "colonial", "colonialism", "dynasty",
        "civilisation", "civilization", "archaeology",
    ],
    "books": [
        "book", "books", "novel", "novels", "review", "author", "authors",
        "literature", "literary", "fiction", "memoir", "reading", "poetry",
        "poem", "essay", "essays", "prose", "writer", "writes", "biography",
        "short story", "narrative", "publishing", "published",
    ],
    "quirky": [
        "unusual", "curious", "odd", "surprising", "remarkable", "unexpected",
        "strange", "forgotten", "obsession", "eccentric", "bizarre", "peculiar",
        "absurd", "weird", "niche", "obscure", "hidden", "overlooked", "lesser-known",
        "secret", "mystery", "myth", "legend", "folklore",
    ],
}


def score_article(title: str, summary: str) -> int:
    """Return topic relevance score (0–4) for an article."""
    text = (title + " " + summary).lower()
    score = 0
    for keywords in TOPICS.values():
        if any(kw in text for kw in keywords):
            score += 1
    return score


def select_articles(articles: list[dict], quota: int) -> list[dict]:
    """
    Score, sort, and return the top `quota` articles from a list.

    Each article dict must have: title, summary, url, author, published, source.
    Falls back to most recent if scores are equal.
    """
    def sort_key(a):
        pub = a.get("published")
        if pub is None:
            ts = 0.0
        elif isinstance(pub, datetime):
            ts = pub.replace(tzinfo=timezone.utc).timestamp() if pub.tzinfo is None else pub.timestamp()
        else:
            ts = 0.0
        return (a.get("_score", 0), ts)

    for a in articles:
        a["_score"] = score_article(a.get("title", ""), a.get("summary", ""))

    sorted_articles = sorted(articles, key=sort_key, reverse=True)
    return sorted_articles[:quota]
