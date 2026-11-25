"""FIT: one 0-100 score per company, with reasons. Computed on read from the latest observations,
so changing weights in metalscout.yaml re-ranks everything instantly. Nothing is stored.

    manufacturer / end user   30   (trader: score capped at 15)
    sells-what-we-sell        20   METAL observed that is in business.sells
    quantity stated           15
    reachable: email          15   own-domain email 15, other-domain 10
    reachable: phone          10
    registration printed       5   GSTIN / CIN / UDYAM / IEC
    buying intent              5   vendor page / RFQ / tender wording
Do-not-contact match -> 0.
"""
from __future__ import annotations


def _dnc(domain: str, emails: list[str], dnc: list[str]) -> bool:
    pats = [p.lower().strip() for p in dnc if p.strip()]
    return any(p == domain or domain.endswith("." + p) or p in emails for p in pats)


def score(company: dict, obs: list[dict], cfg: dict) -> dict:
    w = cfg["fit"]
    sig = {}
    for o in obs:
        sig.setdefault(o["signal"], []).append(o)
    vals = lambda s: [o["value"] for o in sig.get(s, [])]
    emails = vals("EMAIL")
    if _dnc(company["domain"], emails, cfg["compliance"]["do_not_contact"]):
        return {"score": 0, "tier": "X", "reasons": ["on do-not-contact list"]}

    s, why = 0, []
    org = (vals("ORG_TYPE") or ["unknown"])[0]
    if org == "manufacturer":
        s += w["manufacturer"]; why.append("manufacturer / end user")
    elif org == "unknown":
        why.append("type unclear")
    sells = set(cfg["business"]["sells"])
    matched = [m for m in dict.fromkeys(vals("METAL")) if m in sells]
    if matched:
        s += w["metal_match"]; why.append("uses " + ", ".join(matched))
    if sig.get("QUANTITY"):
        big = max(sig["QUANTITY"], key=lambda o: o.get("num") or 0)
        s += w["quantity"]; why.append(f"quantity: {big['value']}")
    own = [o for o in sig.get("EMAIL", []) if o.get("evidence") == "own domain"]
    if own:
        s += w["email"]; why.append("company email")
    elif emails:
        s += int(w["email"] * 2 / 3); why.append("email (other domain)")
    if sig.get("PHONE"):
        s += w["phone"]
    if any(sig.get(k) for k in ("GSTIN", "CIN", "UDYAM", "IEC")):
        s += w["registration"]; why.append("registration no. printed")
    if sig.get("VENDOR_PAGE") or sig.get("BUYER_INTENT"):
        s += w["intent"]; why.append("vendor/RFQ wording")
    if org == "trader":
        s = min(s, 15); why.insert(0, "looks like a trader/dealer")
    if not emails and not sig.get("PHONE"):
        why.append("no contact found yet")
    s = max(0, min(100, s))
    tier = "A" if s >= w["tier_a"] else "B" if s >= w["tier_b"] else "C"
    return {"score": s, "tier": tier, "reasons": why}
