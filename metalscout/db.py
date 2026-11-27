"""State: SQLite locally, or any Postgres (free Neon) when DATABASE_URL is set.
The database is the asset: every fact is an observation with its source URL.

Stages never hand lists to each other. Each stage *queries* for what needs doing, so a crashed
run resumes by itself and re-profiling on a schedule turns facts into a time series.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone

SCHEMA_VERSION = 4
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
CREATE TABLE IF NOT EXISTS agent_runs(
  id INTEGER PRIMARY KEY, run_id TEXT, company_id INTEGER, agent TEXT, provider TEXT, model TEXT,
  ok INTEGER, latency_ms INTEGER, tokens INTEGER, rejected INTEGER DEFAULT 0, error TEXT, at REAL);
CREATE INDEX IF NOT EXISTS ix_agent_runs ON agent_runs(run_id);
"""
# columns added after v1 (ALTER TABLE ... ADD COLUMN, applied if missing)
MIGRATIONS = [("companies", "digest", "TEXT DEFAULT ''"), ("companies", "agents_run", "TEXT DEFAULT ''"),
              ("buyer_signals", "digest", "TEXT DEFAULT ''"), ("buyer_signals", "agent", "TEXT DEFAULT ''"),
              ("buyer_signals", "agent_checked", "INTEGER DEFAULT 0"),
              ("companies", "agent_attempts", "INTEGER DEFAULT 0"), ("buyer_signals", "agent_attempts", "INTEGER DEFAULT 0"),
              ("runs", "heartbeat", "REAL")]
RUN_STALE_S = 20 * 60  # a 'running' run with no heartbeat for this long is treated as dead


class Row(dict):
    """Dict row that also supports positional access (r[0]), like sqlite3.Row."""
    def __init__(self, names, values):
        super().__init__(zip(names, values))
        self._values = values

    def __getitem__(self, k):
        return self._values[k] if isinstance(k, int) else super().__getitem__(k)


def _pg_sql(sql: str) -> str:
    """Translate the small SQLite dialect used in this codebase to Postgres."""
    s = sql.replace("?", "%s")
    if re.match(r"\s*INSERT OR REPLACE INTO kv", s):
        s = s.replace("INSERT OR REPLACE INTO", "INSERT INTO") + " ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value"
    elif re.match(r"\s*INSERT OR IGNORE INTO", s):
        s = s.replace("INSERT OR IGNORE INTO", "INSERT INTO", 1) + " ON CONFLICT DO NOTHING"
    s = s.replace("INTEGER PRIMARY KEY", "BIGSERIAL PRIMARY KEY").replace(" REAL", " DOUBLE PRECISION")
    return s


class PgConn:
    """Minimal sqlite3-connection lookalike over psycopg (execute / executemany / executescript / commit)."""
    def __init__(self, url: str):
        import psycopg
        # autocommit: every statement is its own transaction, so reads never sit "idle in transaction"
        # holding locks (which would block other connections, e.g. the dashboard during a run)
        # connect_timeout: fail fast instead of hanging a serverless request when Neon is waking up or unreachable
        self.pg = psycopg.connect(url, autocommit=True, prepare_threshold=None, connect_timeout=10)

    @staticmethod
    def _factory(cur):
        names = [c.name for c in cur.description] if cur.description else []
        return lambda values: Row(names, values)

    def execute(self, sql, params=()):
        cur = self.pg.cursor(row_factory=self._factory)
        cur.execute(_pg_sql(sql), tuple(params))
        return cur

    def executemany(self, sql, seq):
        cur = self.pg.cursor()
        cur.executemany(_pg_sql(sql), [tuple(x) for x in seq])
        return cur

    def executescript(self, script):
        for stmt in [x.strip() for x in script.split(";")]:
            if stmt:
                self.pg.execute(_pg_sql(stmt))

    def commit(self):
        pass  # autocommit

    def close(self):
        self.pg.close()


def now() -> float:
    return time.time()


def iso(ts: float | None) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M") if ts else ""


class DB:
    """`path` is a SQLite file. If DATABASE_URL (postgres://...) is set it wins, so the same code runs
    on a laptop (SQLite) and in GitHub Actions / Vercel (Neon Postgres)."""

    def __init__(self, path: str, url: str | None = None):
        url = url if url is not None else os.getenv("DATABASE_URL", "")
        url = url.strip().strip("\"'").strip()  # tolerate a pasted value with quotes or a trailing newline
        self.is_pg = url.startswith(("postgres://", "postgresql://"))
        if self.is_pg:
            self.c = PgConn(url)
            # DDL only when the schema is missing or older; skips table locks on every dashboard request
            try:
                ver = self.c.execute("SELECT value FROM kv WHERE key='schema_version'").fetchone()
                current = ver is not None and ver[0] == str(SCHEMA_VERSION)
            except Exception:
                current = False
            if current:
                return
        else:
            self.c = sqlite3.connect(path, timeout=30, check_same_thread=False)
            self.c.row_factory = sqlite3.Row
            self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript(SCHEMA)
        self._migrate()
        self.set("schema_version", str(SCHEMA_VERSION))

    def _migrate(self) -> None:
        for table, col, decl in MIGRATIONS:
            if self.is_pg:
                self.c.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {decl}")
            else:
                cols = [r[1] for r in self.c.execute(f"PRAGMA table_info({table})")]
                if col not in cols:
                    self.c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        self.c.commit()

    def close(self) -> None:
        self.c.close()

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

    def save_profile(self, company_id: int, run_id: str, name: str, status: str, obs: list[dict], error: str = "",
                     keep_runs: int = 3) -> None:
        t = now()
        self.c.executemany(
            "INSERT INTO observations(company_id,run_id,signal,value,num,source_url,evidence,observed_at) VALUES(?,?,?,?,?,?,?,?)",
            [(company_id, run_id, o["signal"], str(o.get("value", "")), o.get("num"), o.get("source_url", ""),
              (o.get("evidence") or "")[:400], t) for o in obs])
        self.c.execute("UPDATE companies SET name=COALESCE(NULLIF(?,''),name), status=?, last_profiled=?, last_profile_run=?, error=?, "
                       "agent_attempts=0 WHERE id=?",
                       (name, status, t, run_id, error, company_id))
        self.c.commit()
        if keep_runs > 0:
            self.prune_observations(company_id, keep_runs)

    def prune_observations(self, company_id: int, keep_runs: int) -> int:
        """Delete this company's observations (agent facts included) outside its last `keep_runs` profile runs."""
        runs = [r[0] for r in self.c.execute(
            "SELECT run_id FROM observations WHERE company_id=? AND run_id IS NOT NULL GROUP BY run_id "
            "ORDER BY MIN(observed_at) DESC, run_id DESC", (company_id,))]
        if len(runs) <= keep_runs:
            return 0
        keep = runs[:keep_runs]
        cur = self.c.execute(f"DELETE FROM observations WHERE company_id=? AND (run_id IS NULL OR run_id NOT IN ({','.join('?' * len(keep))}))",
                             (company_id, *keep))
        self.c.commit()
        return cur.rowcount

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
        t = now()
        self.c.execute("INSERT INTO runs(id,trigger,started,heartbeat,status,stats,errors) VALUES(?,?,?,?,?,?,?)",
                       (rid, trigger, t, t, "running", "{}", "[]"))
        self.c.commit()
        return rid

    def finish_run(self, rid: str, status: str, stats: dict, errors: list[str]) -> None:
        self.c.execute("UPDATE runs SET finished=?, status=?, stats=?, errors=? WHERE id=?",
                       (now(), status, json.dumps(stats), json.dumps(errors[-50:]), rid))
        self.c.commit()

    def update_run_stats(self, rid: str, stats: dict) -> None:
        self.c.execute("UPDATE runs SET stats=?, heartbeat=? WHERE id=?", (json.dumps(stats), now(), rid))
        self.c.commit()

    def heartbeat(self, rid: str) -> None:
        """Tell the dashboard (and the next run) that this run is still alive."""
        self.c.execute("UPDATE runs SET heartbeat=? WHERE id=?", (now(), rid))
        self.c.commit()

    def mark_running_failed(self, reason: str) -> str | None:
        """Mark the latest 'running' run as failed (the process died or was cancelled). Returns its id."""
        r = self.c.execute("SELECT id, errors FROM runs WHERE status='running' ORDER BY started DESC LIMIT 1").fetchone()
        if not r:
            return None
        errors = json.loads(r["errors"] or "[]") + [reason]
        self.c.execute("UPDATE runs SET status='failed', finished=?, errors=? WHERE id=?", (now(), json.dumps(errors[-50:]), r["id"]))
        self.c.commit()
        return r["id"]

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

    def running_run(self, stale_s: float = RUN_STALE_S) -> dict | None:
        """The active run, if any: status 'running' and a heartbeat within `stale_s` (a crashed or cancelled
        run stops beating, so it stops blocking new runs and the dashboard's "running" state)."""
        r = self.c.execute("SELECT * FROM runs WHERE status='running' AND COALESCE(heartbeat, started) > ? "
                           "ORDER BY started DESC LIMIT 1", (now() - stale_s,)).fetchone()
        return dict(r) if r else None

    # ---- agents
    def save_digest(self, company_id: int, digest: str) -> None:
        self.c.execute("UPDATE companies SET digest=? WHERE id=?", (digest[:12000], company_id))
        self.c.commit()

    def companies_for_agents(self, limit: int, max_attempts: int = 3) -> list:
        """Profiled companies whose latest profile has not been through the agents yet. Rows whose model calls
        failed `max_attempts` times are left out; fewer failures go first, so they can't starve new work."""
        return self.c.execute(
            "SELECT * FROM companies WHERE status='profiled' AND COALESCE(digest,'')<>'' "
            "AND COALESCE(agents_run,'')<>COALESCE(last_profile_run,'') AND COALESCE(agent_attempts,0) < ? "
            "ORDER BY COALESCE(agent_attempts,0), last_profiled DESC LIMIT ?", (max_attempts, limit)).fetchall()

    def signals_for_agents(self, limit: int, max_attempts: int = 3) -> list:
        return self.c.execute("SELECT * FROM buyer_signals WHERE COALESCE(agent_checked,0)=0 AND opened<>-1 "
                              "AND COALESCE(agent_attempts,0) < ? "
                              "ORDER BY COALESCE(agent_attempts,0), intent DESC, first_seen DESC LIMIT ?",
                              (max_attempts, limit)).fetchall()

    def agent_failed(self, table: str, row_id: int) -> None:
        """Count one failed agent attempt on a company or buyer signal."""
        if table not in ("companies", "buyer_signals"):
            raise ValueError(table)
        self.c.execute(f"UPDATE {table} SET agent_attempts=COALESCE(agent_attempts,0)+1 WHERE id=?", (row_id,))
        self.c.commit()

    def add_observations(self, company_id: int, run_id: str, obs: list[dict]) -> None:
        t = now()
        self.c.executemany(
            "INSERT INTO observations(company_id,run_id,signal,value,num,source_url,evidence,observed_at) VALUES(?,?,?,?,?,?,?,?)",
            [(company_id, run_id, o["signal"], str(o.get("value", "")), o.get("num"), o.get("source_url", ""),
              (o.get("evidence") or "")[:400], t) for o in obs])
        self.c.commit()

    def reset_agents(self) -> None:
        """Forget all agent output so the crew re-analyses everything on the next 'agents' stage."""
        self.c.execute("DELETE FROM observations WHERE substr(signal, 1, 6) = 'AGENT_'")
        self.c.execute("UPDATE companies SET agents_run = '', agent_attempts = 0")
        self.c.execute("UPDATE buyer_signals SET agent_checked = 0, agent = '', agent_attempts = 0")
        self.c.commit()

    def mark_agents_done(self, company_id: int, profile_run: str) -> None:
        self.c.execute("UPDATE companies SET agents_run=?, agent_attempts=0 WHERE id=?", (profile_run, company_id))
        self.c.commit()

    def log_agent(self, run_id: str, company_id: int | None, agent: str, provider: str, model: str, ok: bool,
                  latency_ms: int, tokens: int = 0, rejected: int = 0, error: str = "") -> None:
        self.c.execute("INSERT INTO agent_runs(run_id,company_id,agent,provider,model,ok,latency_ms,tokens,rejected,error,at) "
                       "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (run_id, company_id, agent, provider, model, int(ok), latency_ms, tokens, rejected, error[:300], now()))
        self.c.commit()

    def agent_stats(self, limit_runs: int = 10) -> list[dict]:
        return [dict(r) for r in self.c.execute(
            "SELECT agent, provider, model, COUNT(*) AS calls, SUM(ok) AS ok, SUM(rejected) AS rejected, "
            "AVG(latency_ms) AS avg_ms FROM agent_runs GROUP BY agent, provider, model ORDER BY calls DESC LIMIT 50")]
