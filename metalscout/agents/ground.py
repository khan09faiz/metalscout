"""Grounding: the anti-hallucination gate between agents and the database.

Agents see a *digest* of the pages the crawler read, with `### PAGE <url>` markers. Every fact an agent
returns must carry a `quote` copied from that digest. A fact is accepted only if its quote really occurs in
the digest (after normalising whitespace and case); the page containing it becomes the fact's source_url.
`supports()` then checks that the quote actually backs the value (a real but irrelevant quote is not enough).
Rejected facts are counted, never stored.
"""
from __future__ import annotations

import re

from .. import extract as X

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


NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def supports(value, quote: str, kind: str) -> bool:
    """Does `quote` back `value` for this kind of agent fact? (Existence of the quote is locate()'s job.)
    AGENT_MATERIAL: value is the metal key; the quote must match that metal's extractor regex.
    AGENT_VOLUME:   value is the number; it must appear in the quote (commas ignored).
    AGENT_PERSON:   value is the name; it must appear in the quote.
    AGENT_PRODUCT:  value is the name; one of its words of 4+ characters must appear in the quote.
    Other kinds (org type, buying signal) have no value-level rule and pass."""
    quote = str(quote or "")
    if kind == "AGENT_MATERIAL":
        rx = X.METAL_RES.get(str(value))
        return bool(rx and rx.search(quote))
    if kind == "AGENT_VOLUME":
        n = _num(value)
        return n is not None and n in {_num(m) for m in NUM_RE.findall(quote)}
    if kind == "AGENT_PERSON":
        name = _norm(str(value or ""))
        return bool(name) and name in _norm(quote)
    if kind == "AGENT_PRODUCT":
        q = _norm(quote)
        return any(w in q for w in re.findall(r"\w{4,}", _norm(str(value or ""))))
    return True


def unverified_numbers(text: str, facts: str) -> list[str]:
    """Numbers in `text` (e.g. an email draft) that don't occur anywhere in `facts` (commas ignored)."""
    known = {_num(m) for m in NUM_RE.findall(facts or "")}
    out: list[str] = []
    for m in NUM_RE.findall(text or ""):
        m = m.rstrip(",")
        if _num(m) not in known and m not in out:
            out.append(m)
    return out
