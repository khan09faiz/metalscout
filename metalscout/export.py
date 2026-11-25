"""Excel / CSV / Google Sheets output. Every contact column has a matching source-URL column."""
from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import leads as L
from .config import path
from .db import DB

j = lambda xs, k="value": "\n".join(str(x.get(k, "")) for x in xs)
COLUMNS = [
    ("Tier", lambda r: r["tier"]), ("Score", lambda r: r["score"]), ("Company", lambda r: r["name"]), ("Type", lambda r: r["org_type"]),
    ("Metals", lambda r: ", ".join(r["metals"])), ("Quantity", lambda r: j(r["quantity"])),
    ("Quantity evidence", lambda r: j(r["quantity"], "evidence")), ("Quantity source", lambda r: j(r["quantity"], "source")),
    ("Email", lambda r: j(r["emails"])), ("Email source", lambda r: j(r["emails"], "source")),
    ("Phone", lambda r: j(r["phones"])), ("Phone source", lambda r: j(r["phones"], "source")),
    ("Website", lambda r: r["website"]), ("Contact page", lambda r: r["contact_page"]), ("Vendor page", lambda r: r["vendor_page"]),
    ("GSTIN", lambda r: j(r["gstin"])), ("CIN", lambda r: j(r["cin"])), ("Udyam", lambda r: j(r["udyam"])), ("IEC", lambda r: j(r["iec"])),
    ("Certifications", lambda r: ", ".join(r["certifications"])), ("Why", lambda r: "; ".join(r["reasons"])),
    ("Found via", lambda r: r["found_via"]), ("First seen", lambda r: r["first_seen"]), ("Last checked", lambda r: r["last_profiled"]),
    ("New today", lambda r: "yes" if r["is_new"] else ""), ("Stage", lambda r: r["stage"]), ("Notes", lambda r: r["notes"]),
]
SIGNAL_COLUMNS = [("Intent hits", "intent"), ("Kind", "kind"), ("Title", "title"), ("URL (source)", "url"), ("Metals", "metals"),
                  ("Quantity", "quantity"), ("Emails", "emails"), ("Phones", "phones"), ("Snippet", "snippet"),
                  ("Opened", "opened"), ("Restricted host", "restricted"), ("Query", "query"), ("First seen", "first_seen")]
README = [
    "MetalScout lead sheet. Every email, phone and quantity has the URL of the page it was read from.",
    "Nothing is guessed: an empty cell means it was not printed on the pages read.",
    "Tier A >= 65, B >= 40, C below. Score = manufacturer 30, metal match 20, quantity 15, email 15, phone 10, registration 5, intent 5.",
    "Traders/dealers are capped at 15 points. Leads sheet excludes them; see 'All companies'.",
    "Buyer signals = marketplace / tender / social pages from search. Restricted hosts were not opened (snippet only).",
    "Before outreach: business contacts only; follow DPDP Act 2023 and TRAI TCCCPR (DND) rules.",
]


def _style(ws):
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F3864")
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions
    for i in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 26
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")


def _cell(v):
    if isinstance(v, list):
        return "\n".join(map(str, v))
    return v


def write_xlsx(db: DB, cfg: dict, out: Path) -> Path:
    rows = L.build(db, cfg)
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append([c[0] for c in COLUMNS])
    for r in rows:
        if r["org_type"] != "trader" and r["tier"] != "X":
            ws.append([f(r) for _, f in COLUMNS])
    ws_all = wb.create_sheet("All companies")
    ws_all.append([c[0] for c in COLUMNS])
    for r in rows:
        ws_all.append([f(r) for _, f in COLUMNS])
    ws2 = wb.create_sheet("Buyer signals")
    ws2.append([c[0] for c in SIGNAL_COLUMNS])
    for s in L.signals(db):
        ws2.append([_cell(s.get(k)) for _, k in SIGNAL_COLUMNS])
    ws3 = wb.create_sheet("Runs")
    ws3.append(["Run", "Trigger", "Status", "Stats", "Errors"])
    for r in db.runs(60):
        ws3.append([r["id"], r["trigger"], r["status"], str(r["stats"]), "\n".join(r["errors"][:10])])
    ws4 = wb.create_sheet("README")
    for line in README:
        ws4.append([line])
    ws4.column_dimensions["A"].width = 130
    for w in (ws, ws_all, ws2, ws3):
        _style(w)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def write_csv(db: DB, cfg: dict, out: Path) -> Path:
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([c[0] for c in COLUMNS])
        for r in L.build(db, cfg):
            w.writerow([f(r) for _, f in COLUMNS])
    return out


def daily(db: DB, cfg: dict) -> dict:
    d = path(cfg, cfg["export"]["dir"], "x").parent
    stamp = datetime.now().strftime("%Y-%m-%d")
    dated = write_xlsx(db, cfg, d / f"leads_{stamp}.xlsx")
    latest = write_xlsx(db, cfg, d / "leads_latest.xlsx")
    write_csv(db, cfg, d / "leads_latest.csv")
    keep = cfg["export"]["keep_days"] * 86400
    for old in d.glob("leads_20*.xlsx"):
        if time.time() - old.stat().st_mtime > keep:
            old.unlink(missing_ok=True)
    res = {"xlsx": str(dated), "latest": str(latest)}
    if cfg["export"]["gsheet_id"]:
        res["gsheet"] = push_gsheet(db, cfg)
    return res


def push_gsheet(db: DB, cfg: dict) -> str:
    import gspread  # optional dependency
    sh = gspread.service_account(filename=cfg["export"]["gsheet_creds"]).open_by_key(cfg["export"]["gsheet_id"])
    titles = [w.title for w in sh.worksheets()]
    ws = sh.worksheet("Leads") if "Leads" in titles else sh.add_worksheet("Leads", 5000, len(COLUMNS))
    rows = [r for r in L.build(db, cfg) if r["org_type"] != "trader"]
    ws.clear()
    ws.update([[c[0] for c in COLUMNS]] + [[f(r) for _, f in COLUMNS] for r in rows])
    return f"https://docs.google.com/spreadsheets/d/{cfg['export']['gsheet_id']}"
