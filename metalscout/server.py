"""Dashboard: stdlib HTTP server + static files in web/. No framework, no build step.
Binds to 127.0.0.1 by default (local tool, no auth). Runs are spawned as subprocesses, so the UI stays responsive.
"""
from __future__ import annotations

import json
import mimetypes
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import export, leads as L, scheduler
from .config import path
from .db import iso
from .engine import is_running, open_db
from .net import reg_domain

WEB = Path(__file__).parent / "web"


def status(cfg: dict) -> dict:
    db = open_db(cfg)
    rows = L.build(db, cfg)
    non_traders = [r for r in rows if r["org_type"] != "trader"]
    last = db.runs(1)
    nr = scheduler.next_run(cfg)
    q = lambda sql: db.c.execute(sql).fetchone()[0]
    return {
        "running": is_running(cfg),
        "last_run": (last[0] | {"started_h": iso(last[0]["started"]), "finished_h": iso(last[0]["finished"])}) if last else None,
        "next_run": nr.strftime("%Y-%m-%d %H:%M") if nr else "disabled",
        "counts": {"companies": q("SELECT COUNT(*) FROM companies"), "queued": q("SELECT COUNT(*) FROM companies WHERE status='new'"),
                   "leads": len(non_traders), "A": sum(r["tier"] == "A" for r in non_traders), "B": sum(r["tier"] == "B" for r in non_traders),
                   "new_today": sum(r["is_new"] for r in non_traders), "traders": len(rows) - len(non_traders),
                   "signals": q("SELECT COUNT(*) FROM buyer_signals")},
        "query_progress": f"{db.get('query_cursor', '0')}/{db.get('query_total', '?')}",
        "business": cfg["business"]["name"],
    }


def tail_log(cfg: dict, n: int = 80) -> list[str]:
    p = path(cfg, "logs", "metalscout.log")
    if not p.exists():
        return []
    with open(p, encoding="utf-8", errors="replace") as f:
        return list(deque(f, n))


def make_handler(cfg: dict):
    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, body, ctype="application/json", headers=None):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, default=str)).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(b)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        def do_GET(self):
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            try:
                if u.path == "/api/status":
                    return self._send(200, status(cfg))
                if u.path == "/api/leads":
                    return self._send(200, L.build(open_db(cfg), cfg, include_traders=qs.get("all") == ["1"]))
                if u.path == "/api/signals":
                    return self._send(200, L.signals(open_db(cfg)))
                if u.path == "/api/runs":
                    return self._send(200, open_db(cfg).runs(30))
                if u.path == "/api/log":
                    return self._send(200, tail_log(cfg))
                if u.path == "/api/export":
                    out = export.write_xlsx(open_db(cfg), cfg, path(cfg, cfg["export"]["dir"], "leads_download.xlsx"))
                    return self._send(200, out.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                      {"Content-Disposition": "attachment; filename=metalscout_leads.xlsx"})
                f = (WEB / ("index.html" if u.path in ("/", "") else u.path.lstrip("/"))).resolve()
                if f.is_file() and WEB.resolve() in f.parents:
                    return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
                return self._send(404, {"error": "not found"})
            except Exception as e:
                return self._send(500, {"error": str(e)})

        def do_POST(self):
            u = urlparse(self.path)
            b = self._body()
            try:
                if u.path == "/api/run":
                    if is_running(cfg):
                        return self._send(409, {"error": "a run is already in progress"})
                    extra = ["--stages", b["stages"]] if b.get("stages") else []
                    scheduler.spawn_run(cfg, "manual", extra)
                    return self._send(202, {"started": True})
                if u.path.startswith("/api/lead/"):
                    open_db(cfg).update_company(int(u.path.rsplit("/", 1)[1]), **{k: b[k] for k in ("stage", "notes") if k in b})
                    return self._send(200, {"ok": True})
                if u.path == "/api/add":
                    db = open_db(cfg)
                    added = 0
                    for url in b.get("urls", []):
                        url = url.strip()
                        if not url:
                            continue
                        url = url if url.startswith("http") else "https://" + url
                        added += db.add_company(reg_domain(url), url, "manual", "manual")
                    return self._send(200, {"added": added})
                return self._send(404, {"error": "not found"})
            except Exception as e:
                return self._send(500, {"error": str(e)})

        def log_message(self, *a):
            pass

    return H


def serve(cfg: dict, heartbeat: bool = True) -> None:
    host, port = cfg["web"]["host"], cfg["web"]["port"]
    if heartbeat:
        scheduler.start_heartbeat(cfg)
    print(f"MetalScout dashboard: http://localhost:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer((host, port), make_handler(cfg)).serve_forever()
