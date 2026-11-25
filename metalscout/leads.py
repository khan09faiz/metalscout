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


def build(db: DB, cfg: dict, include_traders: bool = True) -> list[dict]:
    out = []
    day_ago = time.time() - 86400
    rows = db.c.execute("SELECT * FROM companies WHERE status IN ('profiled','challenged','failed')").fetchall()
    for c in rows:
        c = dict(c)
        obs = db.latest_observations(c["id"], c["last_profile_run"])
        f = fit.score(c, obs, cfg)
        org = next((o["value"] for o in obs if o["signal"] == "ORG_TYPE"), "unknown")
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
        })
    out.sort(key=lambda r: (-r["score"], r["domain"]))
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
        d["first_seen"] = iso(d["first_seen"])
        out.append(d)
    return out
