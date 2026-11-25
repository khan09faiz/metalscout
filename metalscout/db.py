"""SQLite state. The database is the asset: every fact is an observation with its source URL.

Stages never hand lists to each other. Each stage *queries* for what needs doing, so a crashed
run resumes by itself and re-profiling on a schedule turns facts into a time series.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(
  id INTEGER PRIMARY KEY, domain TEXT UNIQUE NOT NULL, website TEXT, name TEXT,
  found_via TEXT, source TEXT, first_seen REAL, last_profiled REAL, last_profile_run TEXT,
  status TEXT DEFAULT 'new',          -- new | profiled | failed | challenged | blocked
  stage TEXT DEFAULT 'lead',          -- lead | contacted | replied | quoted | won | lost | not_fit
  notes TEXT DEFAULT '', error TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS observations(
  id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, run_id TEXT, signal TEXT NOT NULL,
  value TEXT, num REAL, source_url TEXT, evidence TEXT, observed_at REAL);
CREATE INDEX IF NOT EXISTS ix_obs ON observations(company_id, run_id, signal);
CREATE TABLE IF NOT EXISTS buyer_signals(
  id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, snippet TEXT, kind TEXT, host TEXT,
  metals TEXT, quantity TEXT, emails TEXT, phones TEXT, intent INTEGER DEFAULT 0,
  opened INTEGER DEFAULT 0, restricted INTEGER DEFAULT 0, query TEXT, first_seen REAL, run_id TEXT);
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY, trigger TEXT, started REAL, finished REAL, status TEXT, stats TEXT, errors TEXT);
CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
"""


def now() -> float:
    return time.time()


def iso(ts: float | None) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M") if ts else ""


class DB:
    def __init__(self, path: str):
        self.c = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript(SCHEMA)
        self.set("schema_version", str(SCHEMA_VERSION))

    # ---- kv
    def get(self, key: str, default: str = "") -> str:
        r = self.c.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set(self, key: str, value: str) -> None:
        self.c.execute("INSERT OR REPLACE INTO kv(key,value) VALUES(?,?)", (key, value))
        self.c.commit()

    # ---- companies
    def add_company(self, domain: str, website: str, found_via: str, source: str) -> bool:
        cur = self.c.execute(
            "INSERT OR IGNORE INTO companies(domain,website,found_via,source,first_seen) VALUES(?,?,?,?,?)",
            (domain, website, found_via, source, now()))
        self.c.commit()
        return cur.rowcount > 0

    def companies_needing_profile(self, limit: int, stale_days: float) -> list[sqlite3.Row]:
        cutoff = now() - stale_days * 86400
        return self.c.execute(
            "SELECT * FROM companies WHERE status='new' OR (status IN ('profiled','failed') AND COALESCE(last_profiled,0) < ?) "
            "ORDER BY CASE status WHEN 'new' THEN 0 ELSE 1 END, first_seen LIMIT ?", (cutoff, limit)).fetchall()

    def save_profile(self, company_id: int, run_id: str, name: str, status: str, obs: list[dict], error: str = "") -> None:
        t = now()
        self.c.executemany(
            "INSERT INTO observations(company_id,run_id,signal,value,num,source_url,evidence,observed_at) VALUES(?,?,?,?,?,?,?,?)",
            [(company_id, run_id, o["signal"], str(o.get("value", "")), o.get("num"), o.get("source_url", ""),
              (o.get("evidence") or "")[:400], t) for o in obs])
        self.c.execute("UPDATE companies SET name=COALESCE(NULLIF(?,''),name), status=?, last_profiled=?, last_profile_run=?, error=? WHERE id=?",
                       (name, status, t, run_id, error, company_id))
        self.c.commit()

    def latest_observations(self, company_id: int, run_id: str | None) -> list[dict]:
        if not run_id:
            return []
        return [dict(r) for r in self.c.execute(
            "SELECT signal,value,num,source_url,evidence,observed_at FROM observations WHERE company_id=? AND run_id=? ORDER BY id",
            (company_id, run_id))]

    def update_company(self, cid: int, **fields) -> None:
        allowed = {k: v for k, v in fields.items() if k in ("stage", "notes")}
        if allowed:
            sets = ",".join(f"{k}=?" for k in allowed)
            self.c.execute(f"UPDATE companies SET {sets} WHERE id=?", (*allowed.values(), cid))
            self.c.commit()

    # ---- buyer signals
    def add_signal(self, row: dict) -> bool:
        row = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in row.items()}
        row.setdefault("first_seen", now())
        cols = ",".join(row)
        cur = self.c.execute(f"INSERT OR IGNORE INTO buyer_signals({cols}) VALUES({','.join('?' * len(row))})", list(row.values()))
        self.c.commit()
        return cur.rowcount > 0

    def update_signal(self, sid: int, **row) -> None:
        row = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in row.items()}
        self.c.execute(f"UPDATE buyer_signals SET {','.join(f'{k}=?' for k in row)} WHERE id=?", (*row.values(), sid))
        self.c.commit()

    def signals_to_open(self, limit: int) -> list[sqlite3.Row]:
        return self.c.execute("SELECT * FROM buyer_signals WHERE opened=0 AND restricted=0 ORDER BY first_seen LIMIT ?", (limit,)).fetchall()

    # ---- runs
    def start_run(self, trigger: str) -> str:
        rid = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.c.execute("INSERT INTO runs(id,trigger,started,status,stats,errors) VALUES(?,?,?,?,?,?)",
                       (rid, trigger, now(), "running", "{}", "[]"))
        self.c.commit()
        return rid

    def finish_run(self, rid: str, status: str, stats: dict, errors: list[str]) -> None:
        self.c.execute("UPDATE runs SET finished=?, status=?, stats=?, errors=? WHERE id=?",
                       (now(), status, json.dumps(stats), json.dumps(errors[-50:]), rid))
        self.c.commit()

    def update_run_stats(self, rid: str, stats: dict) -> None:
        self.c.execute("UPDATE runs SET stats=? WHERE id=?", (json.dumps(stats), rid))
        self.c.commit()

    def runs(self, limit: int = 30) -> list[dict]:
        out = []
        for r in self.c.execute("SELECT * FROM runs ORDER BY started DESC LIMIT ?", (limit,)):
            d = dict(r)
            d["stats"], d["errors"] = json.loads(d["stats"] or "{}"), json.loads(d["errors"] or "[]")
            out.append(d)
        return out

    def last_run(self, statuses=("ok", "partial")) -> dict | None:
        q = f"SELECT * FROM runs WHERE status IN ({','.join('?' * len(statuses))}) ORDER BY started DESC LIMIT 1"
        r = self.c.execute(q, statuses).fetchone()
        return dict(r) if r else None
