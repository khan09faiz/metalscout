"""DISCOVER: who exists. Search providers + CSV import.

Queries are the cartesian product template x metal x industry x cluster, in a *fixed* order.
A cursor in the kv table advances `queries_per_run` each day, so daily runs sweep the whole
space instead of repeating the same searches. Hits are routed:
  company site  -> companies table (profiled later)
  signal host   -> buyer_signals (marketplace / tender / social page)
  skip host     -> dropped (directories, encyclopedias, job boards, ad redirects)
"""
from __future__ import annotations

import csv
import itertools
import logging
import os
import random
import re
import time

import httpx

from . import extract as X
from .db import DB
from .net import host_matches, reg_domain

log = logging.getLogger("metalscout.sources")
JUNK_URL = re.compile(r"aclick|/ads?/|doubleclick|googleadservices|/search\?|bing\.com/ck", re.I)
TENDER_HOSTS = ("gem.gov.in", "eprocure.gov.in", "tender", "bid", "nic.in", "gov.in")


def all_queries(cfg: dict) -> list[str]:
    s = cfg["search"]
    out = []
    for tpl, metal, ind, city in itertools.product(s["templates"], s["metals"], s["industries"], s["clusters"] or [""]):
        out.append(re.sub(r"\s+", " ", tpl.format(metal=metal, industry=ind, city=city)).strip())
    return list(dict.fromkeys(out))


def next_batch(db: DB, cfg: dict) -> list[str]:
    qs = all_queries(cfg)
    if not qs:
        return []
    n = min(cfg["search"]["queries_per_run"], len(qs))
    cur = int(db.get("query_cursor", "0")) % len(qs)
    batch = [qs[(cur + i) % len(qs)] for i in range(n)]
    db.set("query_cursor", str((cur + n) % len(qs)))
    db.set("query_total", str(len(qs)))
    return batch


def provider_name(cfg: dict) -> str:
    p = cfg["search"]["provider"]
    if p == "auto":
        return "serper" if os.getenv("SERPER_API_KEY") else "duckduckgo"
    return p


def search(q: str, cfg: dict) -> list[dict]:
    n = cfg["search"]["results_per_query"]
    prov = provider_name(cfg)
    for attempt in range(3):
        try:
            if prov == "serper":
                r = httpx.post("https://google.serper.dev/search", timeout=20,
                               headers={"X-API-KEY": os.environ["SERPER_API_KEY"]}, json={"q": q, "gl": "in", "num": n})
                r.raise_for_status()
                return [{"url": x["link"], "title": x.get("title", ""), "snippet": x.get("snippet", "")} for x in r.json().get("organic", [])]
            from ddgs import DDGS
            return [{"url": x["href"], "title": x.get("title", ""), "snippet": x.get("body", "")}
                    for x in DDGS().text(q, region="in-en", max_results=n)]
        except Exception as e:  # rate limits, network blips: back off and retry
            msg = str(e)
            if "No results" in msg:
                return []
            log.warning("search attempt %d failed for %r: %s", attempt + 1, q, msg[:120])
            time.sleep(5 * (attempt + 1) + random.random() * 3)
    raise RuntimeError(f"search failed 3x: {q}")


def signal_kind(url: str) -> str:
    h = reg_domain(url)
    if any(t in url.lower() for t in TENDER_HOSTS):
        return "tender"
    if h in ("linkedin.com", "facebook.com", "x.com", "twitter.com", "reddit.com", "quora.com", "youtube.com", "instagram.com"):
        return "social"
    return "marketplace"


def route(hit: dict, cfg: dict) -> str:
    url = hit["url"]
    d = cfg["domains"]
    if JUNK_URL.search(url) or not url.startswith("http"):
        return "skip"
    if host_matches(url, d["skip"]):
        return "skip"
    if host_matches(url, d["signal"]) or host_matches(url, d["restricted"]):
        return "signal"
    return "company"


def discover(db: DB, cfg: dict, run_id: str, stats: dict, errors: list[str]) -> None:
    batch = next_batch(db, cfg)
    stats.update(queries=0, new_companies=0, new_signals=0, provider=provider_name(cfg))
    fails = 0
    for q in batch:
        try:
            hits = search(q, cfg)
        except Exception as e:
            errors.append(f"discover: {e}")
            fails += 1
            if fails >= 5:
                errors.append("discover: stopped after 5 failed searches (provider throttling?)")
                break
            continue
        stats["queries"] += 1
        for h in hits:
            kind = route(h, cfg)
            if kind == "company":
                if db.add_company(reg_domain(h["url"]), h["url"], q, "search"):
                    stats["new_companies"] += 1
            elif kind == "signal":
                txt = f"{h['title']} {h['snippet']}"
                cls = X.classify(txt)
                if db.add_signal(dict(url=h["url"], title=h["title"], snippet=h["snippet"], kind=signal_kind(h["url"]),
                                      host=reg_domain(h["url"]), metals=list(X.metals_in(txt)),
                                      quantity=[x["value"] for x in X.quantities(txt, strict=False)], emails=[], phones=[],
                                      intent=len(cls["intent_hits"]), restricted=int(host_matches(h["url"], cfg["domains"]["restricted"])),
                                      query=q, run_id=run_id)):
                    stats["new_signals"] += 1
        time.sleep(random.uniform(1.5, 3.5))


def import_csv(db: DB, cfg: dict, path: str) -> tuple[int, int]:
    """Import rows you exported yourself (GeM/CPPP/aggregator/trade-show lists).
    A row with `website` becomes a company to profile; a row with `url` becomes a buyer signal."""
    comp = sig = 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            text = " ".join(r.values())
            if r.get("website"):
                w = r["website"] if r["website"].startswith("http") else "https://" + r["website"]
                comp += db.add_company(reg_domain(w), w, f"csv:{os.path.basename(path)}", "csv")
            if r.get("url"):
                cls = X.classify(text)
                sig += db.add_signal(dict(url=r["url"], title=r.get("title", ""), snippet=text[:400], kind="csv", host=reg_domain(r["url"]),
                                          metals=list(X.metals_in(text)), quantity=[x["value"] for x in X.quantities(text, strict=False)],
                                          emails=X.emails(text), phones=X.phones(text), intent=len(cls["intent_hits"]),
                                          opened=1, query=f"csv:{os.path.basename(path)}"))
    return comp, sig
