"""PROFILE: what a company is. Turns crawled pages into observations (signal, value, source_url, evidence).

Signal catalog (see docs/SIGNALS.md):
  NAME ORG_TYPE MANUFACTURER_PHRASE TRADER_PHRASE METAL QUANTITY EMAIL PHONE GSTIN CIN UDYAM IEC
  CERTIFICATION BUYER_INTENT VENDOR_PAGE CONTACT_PAGE PAGES_READ CHALLENGED UNREACHABLE
"""
from __future__ import annotations

import re

from . import extract as X
from .net import reg_domain

VENDOR_URL = re.compile(r"vendor|supplier[-_ ]?reg|procure|tender|rfq|purchase", re.I)


def observe(seed: str, pages: list[dict]) -> tuple[str, str, list[dict]]:
    """Return (name, status, observations). status: profiled | challenged | failed."""
    if not pages:
        return "", "failed", [{"signal": "UNREACHABLE", "value": "no page could be loaded", "source_url": seed}]
    first = pages[0]
    if X.is_challenge(first["text"], first["html"]) and len(pages) == 1:
        return "", "challenged", [{"signal": "CHALLENGED", "value": "bot challenge page", "source_url": first["url"]}]

    dom = reg_domain(seed)
    obs: list[dict] = []
    seen: set[tuple] = set()

    def add(signal, value, url, evidence="", num=None):
        key = (signal, str(value).lower())
        if key in seen:
            return
        seen.add(key)
        obs.append({"signal": signal, "value": value, "num": num, "source_url": url, "evidence": evidence})

    name = X.page_title(first["html"]) or dom
    add("NAME", name, first["url"])
    add("PAGES_READ", len(pages), first["url"], num=len(pages))

    all_text = "\n".join(p["text"] for p in pages)
    cls = X.classify(all_text)
    add("ORG_TYPE", cls["org_type"], first["url"],
        f"manufacturer: {', '.join(cls['manufacturer_hits'][:6])} | trader: {', '.join(cls['trader_hits'][:6])}")

    for p in pages:
        url, text, html = p["url"], p["text"], p["html"]
        pc = X.classify(text)
        for h in pc["manufacturer_hits"]:
            add("MANUFACTURER_PHRASE", h, url)
        for h in pc["trader_hits"]:
            add("TRADER_PHRASE", h, url)
        for h in pc["intent_hits"]:
            add("BUYER_INTENT", h, url)
        for metal, ev in X.metals_in(text).items():
            add("METAL", metal, url, ev)
        for q in X.quantities(text):
            add("QUANTITY", q["value"], url, q["evidence"], num=q["kg"])
        for e in X.emails(text, html):
            add("EMAIL", e, url, "own domain" if e.split("@")[-1].endswith(dom) else "other domain")
        for ph in X.phones(text):
            add("PHONE", ph, url)
        for kind, vals in X.registrations(text).items():
            for v in vals:
                add(kind, v, url)
        for cert in X.certifications(text):
            add("CERTIFICATION", cert, url)
        if re.search(r"contact", url, re.I):
            add("CONTACT_PAGE", url, url)
        if VENDOR_URL.search(url):
            add("VENDOR_PAGE", url, url)
    return name, "profiled", obs
