"""Deterministic extractors. Pure functions over page text/HTML; no network, no model.

Every extractor returns values *with the evidence snippet* so the caller can store
(value, source_url, evidence) as an observation. Nothing here guesses: an email that
isn't printed on the page is never produced.
"""
from __future__ import annotations

import html as htmllib
import re

import phonenumbers

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
OBFUSCATED_RE = re.compile(
    r"([A-Za-z0-9._%+\-]+)\s*[\[\(\{]\s*at\s*[\]\)\}]\s*([A-Za-z0-9\-]+(?:\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*[A-Za-z0-9\-]+)+)",
    re.I)
DOT_RE = re.compile(r"\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*", re.I)
CF_EMAIL_RE = re.compile(r'data-cfemail="([0-9a-fA-F]+)"')
JUNK_EMAIL = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|css|js|woff2?)$|sentry|wixpress|example\.(com|org)|your(email|name)|@domain\.|"
    r"@sentry|noreply|no-reply|u003e|@2x\.|^(name|email|user|your|abc|xyz|test)@(company|domain|email|example|yoursite|website)\.", re.I)
GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")
CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
UDYAM_RE = re.compile(r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", re.I)
IEC_RE = re.compile(r"\bIEC(?:\s*(?:No\.?|Code|:))?\s*[:\-]?\s*([A-Z0-9]{10})\b", re.I)
QTY_RE = re.compile(
    r"(\d[\d,]*\.?\d*)\s*(MTPA|TPA|TPM|MT|M\.T\.?|metric\s+tons?|metric\s+tonnes?|tonnes?|tons?|kgs?|kilograms?|quintals?)\b"
    r"(?:\s*(?:per|/|a|each)\s*(month|year|annum|week|day))?", re.I)
# Equipment ratings ("3 ton hammer", "500 tonne press") are not material volumes.
EQUIPMENT_RE = re.compile(r"press|hammer|crane|hoist|forklift|furnace|lifting|load|weigh|upset|machine|capacity\s+of\s+(?:the\s+)?(?:press|hammer)", re.I)
VOLUME_CTX_RE = re.compile(r"consum|requir|need|procure|purchase|production|produce|output|installed capacity|melting capacity|"
                           r"per (?:month|annum|year)|annual|monthly|\btpa\b|\btpm\b|tender|quantity|qty", re.I)
UNIT_PERIOD = {"tpa": "year", "mtpa": "year", "tpm": "month"}
CHALLENGE_RE = re.compile(r"just a moment|checking your browser|sgcaptcha|cf-chl|attention required|verify you are human", re.I)

METALS = {
    "steel": r"\b(mild steel|ms plates?|hr coils?|cr coils?|hot rolled|cold rolled|steel billets?|tmt|wire rods?|steel scrap|hms|alloy steel|carbon steel|en ?\d{1,2}[a-z]?|steel)\b",
    "stainless": r"\b(stainless|ss ?304|ss ?316l?|ss ?202|ss ?430)\b",
    "aluminium": r"\b(alumini?um|aluminum|al ingots?|adc ?12|lm ?6|lm ?25|ec grade)\b",
    "copper": r"\b(copper|cathodes?|cu rods?|ccr rods?)\b",
    "brass": r"\b(brass)\b",
    "zinc": r"\b(zinc|zn ingots?|shg zinc)\b",
    "nickel": r"\b(nickel|ferro ?nickel)\b",
    "pig_iron": r"\b(pig iron|sponge iron|dri|cast iron|sg iron|ductile iron)\b",
    "ferro_alloy": r"\b(ferro ?(silicon|manganese|chrome|alloys?)|silico ?manganese)\b",
    "lead_tin": r"\b(lead ingots?|tin ingots?)\b",
}
METAL_RES = {k: re.compile(v, re.I) for k, v in METALS.items()}

MANUFACTURER = [r"manufactur(?:er|ers|ing|e)s? of", r"we manufacture", r"our (?:plant|factory|facility|unit|works)",
                r"production capacity", r"installed capacity", r"\bfoundry\b", r"\bforging", r"\bcastings?\b", r"\bextrusion",
                r"rolling mill", r"iso ?9001", r"\biatf", r"\bplant\b", r"machin(?:e|ing) shop", r"\bfabricat", r"wire drawing",
                r"induction furnace", r"\bcnc\b", r"in-house", r"heat treatment", r"press(?:es)? of \d+", r"tonnes? per (?:month|annum)"]
TRADER = [r"\btraders?\b", r"\bdealers?\b", r"stockists?", r"wholesal", r"distributors?", r"trading (?:company|co)",
          r"exporter and (?:trader|supplier)", r"\bimporters?\b", r"commission agent", r"ex-?stock", r"ready stock",
          r"metal merchants?", r"scrap (?:dealer|merchant)", r"authori[sz]ed dealer"]
INTENT = [r"looking for", r"\brequire(?:ment|d|s)?\b", r"\brfq\b", r"request for quotation", r"\btenders?\b",
          r"\bprocurement\b", r"\benquiry\b", r"supplier registration", r"vendor registration", r"vendor development",
          r"approved vendors?", r"purchase order", r"expression of interest", r"\beoi\b", r"become a (?:supplier|vendor)"]
CERTS = [r"iso ?9001(?::\s?20\d\d)?", r"iso ?14001", r"iatf ?16949", r"\bbis\b", r"\bped\b", r"ibr approved", r"nadcap", r"as ?9100"]
_c = lambda L: [re.compile(p, re.I) for p in L]
MAN_RES, TRD_RES, INT_RES, CERT_RES = _c(MANUFACTURER), _c(TRADER), _c(INTENT), _c(CERTS)


def _ctx(text: str, start: int, end: int, pad: int = 70) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - pad): end + pad]).strip()


def _decode_cf(hexstr: str) -> str:
    try:
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except ValueError:
        return ""


def emails(text: str, html: str = "") -> list[str]:
    """Emails printed on the page (incl. mailto:, [at]/[dot] and Cloudflare-protected). Never guessed."""
    found: list[str] = []
    raw = text + " " + htmllib.unescape(html)
    for m in EMAIL_RE.findall(raw):
        found.append(m.lower().strip(".,;:"))
    for user, rest in OBFUSCATED_RE.findall(text):
        found.append(f"{user}@{DOT_RE.sub('.', rest)}".lower())
    for h in CF_EMAIL_RE.findall(html):
        d = _decode_cf(h)
        if EMAIL_RE.fullmatch(d):
            found.append(d.lower())
    out = []
    for e in found:
        if not JUNK_EMAIL.search(e) and e not in out:
            out.append(e)
    return out


def phones(text: str) -> list[str]:
    out = []
    for m in phonenumbers.PhoneNumberMatcher(text, "IN"):
        if phonenumbers.is_valid_number(m.number):
            f = phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
            if f not in out:
                out.append(f)
    return out


def registrations(text: str) -> dict[str, list[str]]:
    t = text.upper()
    return {"GSTIN": sorted(set(GSTIN_RE.findall(t))), "CIN": sorted(set(CIN_RE.findall(t))),
            "UDYAM": sorted(set(UDYAM_RE.findall(t))), "IEC": sorted(set(IEC_RE.findall(t)))}


def to_kg(val: float, unit: str) -> float:
    u = unit.lower()
    # "MTPA" on SME sites means metric tonnes per annum (big steel plants write "million tonnes").
    if u.startswith(("mt", "m.t", "metric", "tonne", "ton", "tpa", "tpm")):
        return val * 1000
    if u.startswith("quintal"):
        return val * 100
    return val


def quantities(text: str, limit: int = 6, min_kg: float = 100, strict: bool = True) -> list[dict]:
    """[{value:'120 MT per month', kg:120000, period:'month', evidence:'...'}]

    strict (company sites): keep only volumes with a period, or with consumption/production wording nearby,
    and drop equipment ratings (press/hammer tonnage). Non-strict (tender/RFQ text): any volume counts.
    """
    out = []
    for m in QTY_RE.finditer(text):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        kg = to_kg(v, m.group(2))
        if v <= 0 or kg < min_kg:
            continue
        period = (m.group(3) or UNIT_PERIOD.get(m.group(2).lower(), "")).lower()
        if strict:
            before, after = text[max(0, m.start() - 60): m.start()], text[m.end(): m.end() + 25]
            if EQUIPMENT_RE.search(before[-30:] + " " + after):
                continue
            if not period and not VOLUME_CTX_RE.search(before + " " + after):
                continue
        out.append({"value": re.sub(r"\s+", " ", m.group(0)).strip(), "kg": kg, "period": period,
                    "evidence": _ctx(text, m.start(), m.end())})
        if len(out) >= limit:
            break
    return out


def metals_in(text: str) -> dict[str, str]:
    """{metal_key: evidence}"""
    out = {}
    for k, r in METAL_RES.items():
        m = r.search(text)
        if m:
            out[k] = _ctx(text, m.start(), m.end(), 50)
    return out


def _hits(res, text):
    hits = []
    for r in res:
        m = r.search(text)
        if m:
            hits.append(m.group(0).lower())
    return hits


def classify(text: str) -> dict:
    """Manufacturer vs trader vs unknown, with the phrases that decided it."""
    man, trd, intent = _hits(MAN_RES, text), _hits(TRD_RES, text), _hits(INT_RES, text)
    if len(man) >= 2 and len(man) > len(trd):
        kind = "manufacturer"
    elif len(trd) >= 2 and len(trd) >= len(man):
        kind = "trader"
    else:
        kind = "unknown"
    return {"org_type": kind, "manufacturer_hits": man, "trader_hits": trd, "intent_hits": intent}


def certifications(text: str) -> list[str]:
    return sorted({h.upper() for h in _hits(CERT_RES, text)})


def is_challenge(text: str, html: str = "") -> bool:
    return bool(CHALLENGE_RE.search(text[:3000])) or "cf-chl" in html[:5000]


def page_title(html: str) -> str:
    for pat in (r'<meta[^>]+property="og:site_name"[^>]+content="([^"]+)"', r"<title[^>]*>(.*?)</title>"):
        m = re.search(pat, html, re.I | re.S)
        if m:
            t = htmllib.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
            t = re.split(r"\s[|\-–—:]\s", t)[0].strip()
            if t:
                return t[:120]
    return ""
