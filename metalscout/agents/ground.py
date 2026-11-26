"""Grounding: the anti-hallucination gate between agents and the database.

Agents see a *digest* of the pages the crawler read, with `### PAGE <url>` markers. Every fact an agent
returns must carry a `quote` copied from that digest. A fact is accepted only if its quote really occurs in
the digest (after normalising whitespace and case); the page containing it becomes the fact's source_url.
Rejected facts are counted, never stored.
"""
from __future__ import annotations

import re

PAGE_RE = re.compile(r"^### PAGE (\S+)\s*$", re.M)
PRIORITY = [r"contact", r"about|company|profile", r"product|range|application", r"infra|plant|facilit|capacity|quality",
            r"vendor|supplier|procure|tender|purchase", r"client|customer|industr"]


def _norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"[\s ]+", " ", re.sub(r"[^\w@.+%/'\"-]+", " ", s)).strip()


def build_digest(pages: list[dict], limit: int = 12000, per_page: int = 3500) -> str:
    """Most useful pages first (home, contact, about, products, plant, vendor), each trimmed."""
    def rank(p):
        if p.get("depth", 1) == 0:
            return -1
        for i, pat in enumerate(PRIORITY):
            if re.search(pat, p["url"], re.I):
                return i
        return len(PRIORITY)
    out, used = [], 0
    for p in sorted(pages, key=rank):
        text = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", p["text"])).strip()[:per_page]
        block = f"### PAGE {p['url']}\n{text}\n"
        if used + len(block) > limit:
            block = block[: max(0, limit - used)]
        if not block.strip():
            break
        out.append(block)
        used += len(block)
        if used >= limit:
            break
    return "\n".join(out)


def split_pages(digest: str) -> list[tuple[str, str]]:
    parts = PAGE_RE.split(digest)
    # parts = [pre, url1, text1, url2, text2, ...]
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def locate(quote: str, digest: str, min_len: int = 8) -> str | None:
    """Return the URL of the page whose text contains `quote`, or None if the quote is not really there."""
    q = _norm(quote or "")
    if len(q) < min_len:
        return None
    for url, text in split_pages(digest):
        if q in _norm(text):
            return url
    return None
