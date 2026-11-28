"""Performance and storage: no N+1 in leads.build, status without build(), observation retention,
Postgres connect timeout, and crawls seeded from the homepage."""
import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from metalscout import engine, leads, server, sources
from metalscout.db import DB


class CountingConn:
    """Wraps db.c and counts execute() calls (sqlite3.Connection attributes are read-only, so wrap, don't patch)."""
    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def execute(self, sql, params=()):
        self.calls.append(sql)
        return self.inner.execute(sql, params)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def seed(db, n_companies, n_obs, runs=("r1",)):
    t = time.time()
    db.c.executemany("INSERT INTO companies(id,domain,website,status,first_seen,last_profile_run,name) VALUES(?,?,?,?,?,?,?)",
                     [(i, f"c{i}.example", f"https://c{i}.example/", "profiled", t, runs[-1], f"C{i}") for i in range(1, n_companies + 1)])
    sigs = ["ORG_TYPE", "METAL", "EMAIL", "PHONE", "QUANTITY", "GSTIN", "CERTIFICATION", "MANUFACTURER_PHRASE", "AGENT_MATERIAL", "PAGES_READ"]
    rows = []
    for run in runs:
        for i in range(1, n_companies + 1):
            for k in range(n_obs):
                s = sigs[k % len(sigs)]
                v = {"ORG_TYPE": "manufacturer", "METAL": "steel", "EMAIL": f"k{k}@c{i}.example", "AGENT_MATERIAL": "steel: EN8"}.get(s, f"v{k}")
                rows.append((i, run, s, v, 120000.0 if s == "QUANTITY" else None, f"https://c{i}.example/", "own domain", t))
    db.c.executemany("INSERT INTO observations(company_id,run_id,signal,value,num,source_url,evidence,observed_at) VALUES(?,?,?,?,?,?,?,?)", rows)
    db.c.commit()


def test_build_is_not_n_plus_one(cfg):
    db = engine.open_db(cfg)
    seed(db, 2000, 20)
    db.c = CountingConn(db.c)
    t0 = time.perf_counter()
    rows = leads.build(db, cfg)
    took = time.perf_counter() - t0
    assert len(rows) == 2000 and rows[0]["tier"] == "A" and len(rows[0]["emails"]) == 2
    assert len(db.c.calls) <= 3, db.c.calls
    print(f"build(): 2,000 companies x 20 observations in {took:.2f}s, {len(db.c.calls)} queries")
    assert took < 15  # generous: catches a return of per-company queries, not machine speed

    db.c.calls.clear()
    assert leads.summary(db, cfg) == {"leads": 2000, "A": 2000, "B": 0, "new_today": 2000, "traders": 0, "ai_leads": 2000}
    assert len(db.c.calls) <= 3


def test_join_uses_existing_index(cfg):
    db = engine.open_db(cfg)
    plan = " ".join(str(tuple(r)) for r in db.c.execute(
        "EXPLAIN QUERY PLAN SELECT o.signal FROM observations o JOIN companies c "
        "ON c.id = o.company_id AND o.run_id = c.last_profile_run WHERE c.status IN ('profiled')"))
    assert "ix_obs" in plan, plan


def test_build_reads_only_the_latest_profile_run(cfg):
    db = engine.open_db(cfg)
    seed(db, 3, 4, runs=("r1", "r2"))
    db.c.execute("UPDATE observations SET value='trader' WHERE run_id='r1' AND signal='ORG_TYPE'")
    db.c.commit()
    assert {r["org_type"] for r in leads.build(db, cfg)} == {"manufacturer"}


def test_status_does_not_build_every_lead(cfg, monkeypatch):
    db = engine.open_db(cfg)
    seed(db, 5, 10)
    monkeypatch.setattr(server.L, "build", lambda *a, **k: (_ for _ in ()).throw(AssertionError("status called build()")))
    st = server.status(cfg, db)
    assert st["counts"]["leads"] == 5 and st["counts"]["A"] == 5 and st["counts"]["companies"] == 5


def test_summary_matches_build(site, cfg):
    db = engine.open_db(cfg)
    seed(db, 30, 12)
    db.c.execute("UPDATE observations SET value='trader' WHERE company_id <= 4 AND signal='ORG_TYPE'")
    db.c.execute("DELETE FROM observations WHERE company_id BETWEEN 5 AND 9 AND signal IN ('EMAIL','QUANTITY')")
    db.c.execute("DELETE FROM observations WHERE company_id BETWEEN 10 AND 12 AND signal LIKE 'AGENT_%'")
    db.c.commit()
    rows = leads.build(db, cfg)
    nt = [r for r in rows if r["org_type"] != "trader"]
    assert leads.summary(db, cfg) == {"leads": len(nt), "A": sum(r["tier"] == "A" for r in nt), "B": sum(r["tier"] == "B" for r in nt),
                                      "new_today": sum(r["is_new"] for r in nt), "traders": len(rows) - len(nt),
                                      "ai_leads": sum(r["ai"]["has_any"] for r in nt)}


# ---------- 14. retention
def test_old_profile_runs_are_pruned(cfg):
    db = engine.open_db(cfg)
    db.add_company("a.example", "https://a.example/", "t", "manual")
    for i in range(1, 6):
        db.save_profile(1, f"run{i}", "A", "profiled", [{"signal": "METAL", "value": "steel"}, {"signal": "EMAIL", "value": "x@a.example"}],
                        keep_runs=3)
        db.add_observations(1, f"run{i}", [{"signal": "AGENT_MATERIAL", "value": "steel: EN8"}])
        time.sleep(0.01)
    runs = sorted({r[0] for r in db.c.execute("SELECT run_id FROM observations")})
    assert runs == ["run3", "run4", "run5"]
    # agent facts of the dropped runs went with them; those of the kept runs stay
    assert sorted(r[0] for r in db.c.execute("SELECT run_id FROM observations WHERE signal='AGENT_MATERIAL'")) == ["run3", "run4", "run5"]
    assert db.c.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 3 * 2 + 3


def test_engine_passes_keep_profile_runs(site, cfg):
    from metalscout.net import reg_domain
    cfg["pipeline"].update(keep_profile_runs=1, reprofile_after_days=0)
    db = engine.open_db(cfg)
    db.add_company(reg_domain(site), site, "test", "manual")
    engine.run(cfg, "test", stages=("profile",))
    engine.run(cfg, "test", stages=("profile",))
    assert db.c.execute("SELECT COUNT(DISTINCT run_id) FROM observations").fetchone()[0] == 1
    assert len(leads.build(db, cfg)[0]["emails"]) == 2


# ---------- 15. Postgres connect timeout
def test_pg_connect_timeout(monkeypatch):
    psycopg = pytest.importorskip("psycopg")
    seen = {}

    class Stop(Exception):
        pass

    def fake_connect(url, **kw):
        seen.update(kw)
        raise Stop
    monkeypatch.setattr(psycopg, "connect", fake_connect)
    with pytest.raises(Stop):
        DB("", url="postgresql://u:p@ep-x-pooler.example.neon.tech/db?sslmode=require")
    assert seen["connect_timeout"] == 10 and seen["prepare_threshold"] is None


# ---------- 16. crawl from the homepage
def test_discover_seeds_homepage_and_keeps_hit_url(cfg, monkeypatch):
    hit = "https://www.Shree-Forge.in/products/crankshafts.html?ref=1"
    monkeypatch.setattr(sources, "search", lambda q, cfg: [{"url": hit, "title": "Forge", "snippet": ""}])
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    cfg["search"]["queries_per_run"] = 1
    db = engine.open_db(cfg)
    sources.discover(db, cfg, "r", {}, [])
    row = db.c.execute("SELECT domain, website, found_via, source FROM companies").fetchone()
    assert row["website"] == "https://www.shree-forge.in/" and row["domain"] == "shree-forge.in"
    assert row["source"] == f"search:{hit}" and row["found_via"]


def test_api_add_seeds_homepage(cfg):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/api/add", method="POST",
                                     data=json.dumps({"urls": ["acme.in/about/team", "http://user@www.b.co.in:8080/x"]}).encode(),
                                     headers={"Content-Type": "application/json"})
        assert json.load(urllib.request.urlopen(req)) == {"added": 2}
    finally:
        srv.shutdown()
    db = engine.open_db(cfg)
    rows = {r["domain"]: (r["website"], r["source"]) for r in db.c.execute("SELECT * FROM companies")}
    assert rows["acme.in"] == ("https://acme.in/", "manual:https://acme.in/about/team")
    assert rows["b.co.in"] == ("http://www.b.co.in:8080/", "manual:http://user@www.b.co.in:8080/x")
