"""Dashboard: stdlib HTTP handler + static files in web/. No framework, no build step.

The same handler runs in two places:
  - locally:  `python -m metalscout serve` (127.0.0.1, runs spawned as subprocesses)
  - Vercel:   api/index.py exposes it as a serverless function; "Find leads now" dispatches the
              GitHub Actions engine workflow, and data comes from the shared Postgres (Neon).
Set DASHBOARD_PASSWORD to require HTTP Basic auth (always set it when the dashboard is public).
"""
from __future__ import annotations

import base64
import hmac
import json
import logging
import mimetypes
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from . import export, leads as L, scheduler
from .config import path
from .db import DB, iso
from .engine import STAGES, is_running, open_db, parse_stages
from .net import reg_domain

log = logging.getLogger("metalscout.server")
WEB = Path(__file__).parent / "web"
LOGIN_MAX_FAILS, LOGIN_WINDOW_S = 10, 600  # per client IP
PROVIDER_KEYS = {"groq": "GROQ_API_KEY", "cerebras": "CEREBRAS_API_KEY", "gemini": "GEMINI_API_KEY",
                 "openrouter": "OPENROUTER_API_KEY", "ollama": "OLLAMA_BASE_URL"}
AGENTS = [
    {"name": "Orchestrator", "tier": "rules", "job": "Decides which agents run for each lead and enforces the call budget. No model."},
    {"name": "Sorter", "tier": "small", "job": "Manufacturer, trader, both or service, when the regex classifier is unsure."},
    {"name": "Analyst", "tier": "large", "job": "Raw materials, forms, monthly volume, people and buying signals."},
    {"name": "Writer", "tier": "large", "job": "First-email draft for Tier A/B leads. Never sent."},
    {"name": "Scout", "tier": "small", "job": "Reads tender and buy-lead pages: buyer, items, quantity, deadline."},
]


def cloud_dispatch() -> tuple[str, str] | None:
    tok, repo = os.getenv("GITHUB_DISPATCH_TOKEN", ""), os.getenv("GITHUB_REPO", "")
    return (tok, repo) if tok and repo else None


def status(cfg: dict, db: DB) -> dict:
    rows = L.build(db, cfg)
    non_traders = [r for r in rows if r["org_type"] != "trader"]
    last = db.runs(1)
    q = lambda sql: db.c.execute(sql).fetchone()[0]
    if cloud_dispatch():
        next_run = f"daily {cfg['schedule']['daily_at']} UTC (GitHub Actions)"
    else:
        nr = scheduler.next_run(cfg)
        next_run = nr.strftime("%Y-%m-%d %H:%M") if nr else "disabled"
    return {
        "running": is_running(cfg, db),
        "last_run": (last[0] | {"started_h": iso(last[0]["started"]), "finished_h": iso(last[0]["finished"])}) if last else None,
        "next_run": next_run,
        "counts": {"companies": q("SELECT COUNT(*) FROM companies"), "queued": q("SELECT COUNT(*) FROM companies WHERE status='new'"),
                   "leads": len(non_traders), "A": sum(r["tier"] == "A" for r in non_traders), "B": sum(r["tier"] == "B" for r in non_traders),
                   "new_today": sum(r["is_new"] for r in non_traders), "traders": len(rows) - len(non_traders),
                   "signals": q("SELECT COUNT(*) FROM buyer_signals"), "ai_leads": sum(r["ai"]["has_any"] for r in non_traders)},
        "query_progress": f"{db.get('query_cursor', '0')}/{db.get('query_total', '?')}",
        "business": cfg["business"]["name"],
        "mode": "cloud" if cloud_dispatch() else "local",
    }


def agents_view(db: DB) -> dict:
    stats = db.agent_stats()
    return {
        "agents": [{**a, "calls": sum(s["calls"] or 0 for s in stats if s["agent"] == a["name"].lower()),
                    "ok": sum(s["ok"] or 0 for s in stats if s["agent"] == a["name"].lower()),
                    "rejected": sum(s["rejected"] or 0 for s in stats if s["agent"] == a["name"].lower()),
                    "models": sorted({f"{s['provider']}/{s['model']}" for s in stats if s["agent"] == a["name"].lower() and s["model"]})}
                   for a in AGENTS],
        "providers": [{"name": n, "configured": bool(os.getenv(k)) or n == "ollama"} for n, k in PROVIDER_KEYS.items()],
        "by_model": stats,
    }


def tail_log(cfg: dict, n: int = 80) -> list[str]:
    p = path(cfg, "logs", "metalscout.log")
    if not p.exists():
        return []
    with open(p, encoding="utf-8", errors="replace") as f:
        return list(deque(f, n))


def start_run(cfg: dict, db: DB, stages: str = "") -> tuple[int, dict]:
    if stages:
        try:
            stages = ",".join(parse_stages(stages))
        except ValueError:
            return 400, {"error": "invalid stages", "allowed": list(STAGES)}
    if is_running(cfg, db):
        return 409, {"error": "a run is already in progress"}
    cd = cloud_dispatch()
    if cd:
        tok, repo = cd
        inputs = {"stages": stages} if stages else {}
        r = httpx.post(f"https://api.github.com/repos/{repo}/actions/workflows/engine.yml/dispatches", timeout=15,
                       headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
                       json={"ref": os.getenv("GITHUB_REF_NAME", "main"), "inputs": inputs})
        if r.status_code >= 300:
            return 502, {"error": f"GitHub dispatch failed ({r.status_code}): {r.text[:200]}"}
        return 202, {"started": True, "where": "github-actions"}
    if os.getenv("VERCEL"):
        return 400, {"error": "Cloud runs need GITHUB_DISPATCH_TOKEN and GITHUB_REPO set in Vercel."}
    scheduler.spawn_run(cfg, "manual", ["--stages", stages] if stages else [])
    return 202, {"started": True, "where": "local"}


class LoginLimiter:
    """Failed Basic-auth attempts per client IP in a sliding window (in memory, per process)."""

    def __init__(self, max_fails: int = LOGIN_MAX_FAILS, window_s: float = LOGIN_WINDOW_S):
        self.max_fails, self.window_s = max_fails, window_s
        self.fails: dict[str, deque] = {}
        self.lock = threading.Lock()

    def _prune(self, ip: str, t: float) -> deque:
        d = self.fails.setdefault(ip, deque())
        while d and d[0] <= t - self.window_s:
            d.popleft()
        return d

    def retry_after(self, ip: str) -> int:
        """Seconds until this IP may try again; 0 if it is not locked out."""
        t = time.time()
        with self.lock:
            d = self._prune(ip, t)
            return int(d[0] + self.window_s - t) + 1 if len(d) >= self.max_fails else 0

    def fail(self, ip: str) -> None:
        t = time.time()
        with self.lock:
            if len(self.fails) > 10_000:  # bound memory: forget IPs with no recent failures
                for k in [k for k, d in self.fails.items() if not d or d[-1] <= t - self.window_s]:
                    del self.fails[k]
            self._prune(ip, t).append(t)

    def ok(self, ip: str) -> None:
        with self.lock:
            self.fails.pop(ip, None)


def make_handler(cfg: dict):
    password = os.getenv("DASHBOARD_PASSWORD", "")
    limiter = LoginLimiter()

    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, body, ctype="application/json", headers=None):
            b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, default=str)).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(b)

        def _client_ip(self) -> str:
            if os.getenv("VERCEL"):  # Vercel's proxy sets these and overwrites client-supplied values
                fwd = self.headers.get("X-Real-IP") or (self.headers.get("X-Forwarded-For") or "").split(",")[0]
                if fwd.strip():
                    return fwd.strip()
            return self.client_address[0] if self.client_address else ""

        def _own_hosts(self) -> set[str]:
            hosts = {(self.headers.get("Host") or "").strip().lower()}
            if os.getenv("VERCEL"):
                hosts.add((self.headers.get("X-Forwarded-Host") or "").strip().lower())
            return hosts - {""}

        def _guard(self, post: bool) -> bool:
            """DNS-rebinding and CSRF checks. Sends 403 and returns False when the request must be refused."""
            reason = ""
            if not os.getenv("VERCEL"):
                port = self.server.server_address[1]
                names = {"localhost", "127.0.0.1", str(cfg["web"]["host"]).lower(),
                         *(str(h).lower() for h in cfg["web"].get("allowed_hosts") or [])}
                allowed = {f"{n}:{port}" for n in names} | (names if port == 80 else set())
                if (self.headers.get("Host") or "").strip().lower() not in allowed:
                    reason = "unexpected Host header"
            origin = self.headers.get("Origin")
            if not reason and origin is not None and urlparse(origin).netloc.lower() not in self._own_hosts():
                reason = "cross-origin request"
            if not reason and post and self.headers.get_content_type() != "application/json":
                reason = "Content-Type must be application/json"
            if reason:
                self._send(403, {"error": reason})
                return False
            return True

        def _authed(self) -> bool:
            if not password:
                if os.getenv("VERCEL"):  # never serve lead data on a public URL without a password
                    self._send(503, {"error": "Set DASHBOARD_PASSWORD in Vercel (Settings -> Environment Variables), then redeploy."})
                    return False
                return True
            ip = self._client_ip()
            wait = limiter.retry_after(ip)
            if wait:  # locked out: refuse even a correct password, so the lockout can't be used as an oracle
                self._send(429, {"error": "too many failed logins, try again later"}, headers={"Retry-After": str(wait)})
                return False
            h = self.headers.get("Authorization", "")
            if h.startswith("Basic "):
                try:
                    _, _, pw = base64.b64decode(h[6:]).decode("utf-8", "replace").partition(":")
                except ValueError:
                    pw = ""
                if hmac.compare_digest(pw.encode(), password.encode()):
                    limiter.ok(ip)
                    return True
                limiter.fail(ip)
            self._send(401, {"error": "login required"}, headers={"WWW-Authenticate": 'Basic realm="MetalScout"'})
            return False

        def _route(self):
            """(path, query) of the request. On Vercel every URL is rewritten to /api/index?__path=<original>."""
            u = urlparse(self.path)
            qs = parse_qs(u.query)
            path = qs.pop("__path", [u.path])[0] or "/"
            if path in ("/api/index", "/api/index.py"):
                path = "/"
            return path, qs

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        def do_GET(self):
            if not self._guard(post=False) or not self._authed():
                return
            route, qs = self._route()
            if not route.startswith("/api/"):
                f = (WEB / ("index.html" if route in ("/", "") else route.lstrip("/"))).resolve()
                if f.is_file() and WEB.resolve() in f.parents:
                    return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
                return self._send(404, {"error": "not found"})
            db = None
            try:
                db = open_db(cfg)
                if route == "/api/status":
                    return self._send(200, status(cfg, db))
                if route == "/api/leads":
                    return self._send(200, L.build(db, cfg, include_traders=qs.get("all") == ["1"]))
                if route == "/api/signals":
                    return self._send(200, L.signals(db))
                if route == "/api/runs":
                    return self._send(200, db.runs(30))
                if route == "/api/agents":
                    return self._send(200, agents_view(db))
                if route == "/api/log":
                    return self._send(200, tail_log(cfg))
                if route == "/api/export":
                    out = export.write_xlsx(db, cfg, path(cfg, cfg["export"]["dir"], "leads_download.xlsx"))
                    return self._send(200, out.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                      {"Content-Disposition": "attachment; filename=metalscout_leads.xlsx"})
                return self._send(404, {"error": "not found"})
            except Exception:
                log.exception("%s %s failed", self.command, route)
                return self._send(500, {"error": "internal error"})
            finally:
                if db:
                    db.close()

        def do_POST(self):
            if not self._guard(post=True) or not self._authed():
                return
            route, _ = self._route()
            b = self._body()
            db = None
            try:
                db = open_db(cfg)
                if route == "/api/run":
                    code, body = start_run(cfg, db, str(b.get("stages") or ""))
                    return self._send(code, body)
                if route.startswith("/api/lead/"):
                    db.update_company(int(route.rsplit("/", 1)[1]), **{k: b[k] for k in ("stage", "notes") if k in b})
                    return self._send(200, {"ok": True})
                if route == "/api/add":
                    added = 0
                    for url in b.get("urls", []):
                        url = str(url).strip()
                        if not url:
                            continue
                        url = url if url.startswith("http") else "https://" + url
                        added += db.add_company(reg_domain(url), url, "manual", "manual")
                    return self._send(200, {"added": added})
                return self._send(404, {"error": "not found"})
            except Exception:
                log.exception("%s %s failed", self.command, route)
                return self._send(500, {"error": "internal error"})
            finally:
                if db:
                    db.close()

        def log_message(self, *a):
            pass

    return H


def serve(cfg: dict, heartbeat: bool = True) -> None:
    host, port = cfg["web"]["host"], cfg["web"]["port"]
    if heartbeat:
        scheduler.start_heartbeat(cfg)
    print(f"MetalScout dashboard: http://localhost:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer((host, port), make_handler(cfg)).serve_forever()
