"""Read model: assemble one lead per profiled company from its latest observations + fit."""
from __future__ import annotations

import json
import time

from . import fit
from .db import DB, iso


def _pairs(obs, signal, limit=6):
    out = []
    for o in obs:
        if o["signal"] == signal and o["value"] not in [x["value"] for x in out]:
            out.append({"value": o["value"], "source": o["source_url"], "evidence": o.get("evidence") or ""})
    return out[:limit]


COMPANY_COLS = "id, domain, name, website, status, stage, notes, found_via, first_seen, last_profiled, error, last_profile_run"
SHOWN = ("profiled", "challenged", "failed")


def _load(db: DB) -> tuple[list[dict], dict[int, list[dict]]]:
    """Companies to show + their latest-profile observations, in two queries (no per-company query).
    The join uses ix_obs(company_id, run_id, ...), so no extra index is needed."""
    marks = ",".join("?" * len(SHOWN))
    companies = [dict(r) for r in db.c.execute(f"SELECT {COMPANY_COLS} FROM companies WHERE status IN ({marks})", SHOWN)]  # noqa: S608  # constant column list and '?' placeholders
    obs: dict[int, list[dict]] = {}
    for r in db.c.execute(
            "SELECT o.company_id, o.signal, o.value, o.num, o.source_url, o.evidence, o.observed_at FROM observations o "  # noqa: S608  # '?' placeholders only
            f"JOIN companies c ON c.id = o.company_id AND o.run_id = c.last_profile_run WHERE c.status IN ({marks}) "
            "ORDER BY o.id", SHOWN):
        d = dict(r)
        obs.setdefault(d.pop("company_id"), []).append(d)
    return companies, obs


def _scored(db: DB, cfg: dict):
    """(company, latest observations, fit, org type) for every company shown."""
    companies, by_company = _load(db)
    for c in companies:
        obs = by_company.get(c["id"], [])
        f = fit.score(c, obs, cfg)
        org = next((o["value"] for o in obs if o["signal"] == "ORG_TYPE"), "unknown")
        org = f.get("org") or org  # a confident agent verdict can override the regex classifier
        yield c, obs, f, org


def build(db: DB, cfg: dict, include_traders: bool = True) -> list[dict]:
    out = []
    day_ago = time.time() - 86400
    for c, obs, f, org in _scored(db, cfg):
        if not include_traders and org == "trader":
            continue
        out.append({
            "id": c["id"], "domain": c["domain"], "name": c["name"] or c["domain"], "website": c["website"], "status": c["status"],
            "stage": c["stage"], "notes": c["notes"], "org_type": org, "score": f["score"], "tier": f["tier"], "reasons": f["reasons"],
            "metals": list(dict.fromkeys(o["value"] for o in obs if o["signal"] == "METAL")),
            "quantity": _pairs(obs, "QUANTITY", 4), "emails": _pairs(obs, "EMAIL"), "phones": _pairs(obs, "PHONE", 4),
            "gstin": _pairs(obs, "GSTIN", 2), "cin": _pairs(obs, "CIN", 2), "udyam": _pairs(obs, "UDYAM", 2), "iec": _pairs(obs, "IEC", 2),
            "certifications": [o["value"] for o in obs if o["signal"] == "CERTIFICATION"],
            "contact_page": next((o["value"] for o in obs if o["signal"] == "CONTACT_PAGE"), ""),
            "vendor_page": next((o["value"] for o in obs if o["signal"] == "VENDOR_PAGE"), ""),
            "pages_read": next((o["num"] for o in obs if o["signal"] == "PAGES_READ"), 0),
            "found_via": c["found_via"], "first_seen": iso(c["first_seen"]), "last_profiled": iso(c["last_profiled"]),
            "is_new": (c["first_seen"] or 0) >= day_ago, "error": c["error"],
            "ai": _ai(obs),
        })
    out.sort(key=lambda r: (-r["score"], r["domain"]))
    return out


def summary(db: DB, cfg: dict) -> dict:
    """Dashboard counts from the same two queries as build(), without building every lead dict."""
    day_ago = time.time() - 86400
    n = {"leads": 0, "A": 0, "B": 0, "new_today": 0, "traders": 0, "ai_leads": 0}
    for c, obs, f, org in _scored(db, cfg):
        if org == "trader":
            n["traders"] += 1
            continue
        n["leads"] += 1
        if f["tier"] in ("A", "B"):
            n[f["tier"]] += 1
        n["new_today"] += (c["first_seen"] or 0) >= day_ago
        n["ai_leads"] += _ai(obs)["has_any"]
    return n


def _ai(obs: list[dict]) -> dict:
    """Agent findings for the UI: every item carries the exact quote and the page it was verified on."""
    out = {"org_type": None, "materials": _pairs(obs, "AGENT_MATERIAL", 8), "volume": _pairs(obs, "AGENT_VOLUME", 2),
           "people": _pairs(obs, "AGENT_PERSON", 6), "products": _pairs(obs, "AGENT_PRODUCT", 6),
           "buying_signals": _pairs(obs, "AGENT_BUYING_SIGNAL", 4), "outreach": None}
    for o in obs:
        if o["signal"] == "AGENT_ORG_TYPE":
            out["org_type"] = {"value": o["value"], "confidence": o["num"], "source": o["source_url"], "evidence": o["evidence"]}
        if o["signal"] == "AGENT_OUTREACH":
            try:
                out["outreach"] = json.loads(o["value"])
            except ValueError:
                continue
            ev = o.get("evidence") or ""
            i = ev.find("unverified numbers:")
            out["outreach"]["warning"] = ev[i:] if i >= 0 else ""
    out["has_any"] = bool(out["org_type"] or out["outreach"] or any(out[k] for k in ("materials", "volume", "people", "products", "buying_signals")))
    return out


def signals(db: DB, limit: int = 500) -> list[dict]:
    out = []
    for r in db.c.execute("SELECT * FROM buyer_signals ORDER BY intent DESC, first_seen DESC LIMIT ?", (limit,)):
        d = dict(r)
        for k in ("metals", "quantity", "emails", "phones"):
            try:
                d[k] = json.loads(d[k] or "[]")
            except ValueError:
                d[k] = []
        try:
            d["agent"] = json.loads(d.get("agent") or "{}")
        except ValueError:
            d["agent"] = {}
        d.pop("digest", None)
        d["first_seen"] = iso(d["first_seen"])
        out.append(d)
    return out
