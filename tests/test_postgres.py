"""Same engine + agents + dashboard API against a real Postgres (embedded via `pgserver` when installed).
Set TEST_DATABASE_URL to use your own Postgres instead. Skipped when neither is available."""
import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from metalscout import engine, leads, server
from metalscout.db import DB
from metalscout.net import reg_domain


@pytest.fixture(scope="module")
def pg_url(tmp_path_factory):
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        yield url
        return
    pgserver = pytest.importorskip("pgserver")
    srv = pgserver.get_server(str(tmp_path_factory.mktemp("pg")), cleanup_mode="stop")
    yield srv.get_uri()
    srv.cleanup()


@pytest.fixture
def pg(pg_url, monkeypatch):
    db = DB("", url=pg_url)
    for t in ("observations", "companies", "buyer_signals", "runs", "kv", "agent_runs"):
        db.c.execute(f"DELETE FROM {t}")
    db.c.commit()
    db.close()
    monkeypatch.setenv("DATABASE_URL", pg_url)
    return pg_url


def test_engine_and_dashboard_on_postgres(site, cfg, pg, monkeypatch):
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "CEREBRAS_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9/v1")
    db = engine.open_db(cfg)
    assert db.is_pg
    assert db.add_company(reg_domain(site), site, "test", "manual") is True
    assert db.add_company(reg_domain(site), site, "test", "manual") is False  # ON CONFLICT DO NOTHING
    db.set("query_cursor", "5")
    db.set("query_cursor", "7")              # upsert
    assert db.get("query_cursor") == "7"

    res = engine.run(cfg, "test", stages=("profile", "agents", "export"))
    assert res["status"] == "ok", res["errors"]
    [lead] = leads.build(db, cfg)
    assert lead["tier"] == "A" and lead["emails"]
    assert (db.c.execute("SELECT digest FROM companies").fetchone()[0] or "").startswith("### PAGE")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        st = json.load(urllib.request.urlopen(base + "/api/status"))
        assert st["counts"]["leads"] == 1 and st["running"] is False
        assert json.load(urllib.request.urlopen(base + "/api/agents"))["agents"][0]["name"] == "Orchestrator"
    finally:
        srv.shutdown()


def test_dashboard_password(cfg, pg, monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "s3cret")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(base + "/api/status")
        assert e.value.code == 401
        import base64
        req = urllib.request.Request(base + "/api/status", headers={"Authorization": "Basic " + base64.b64encode(b"me:s3cret").decode()})
        assert json.load(urllib.request.urlopen(req))["mode"] == "local"
    finally:
        srv.shutdown()


def test_pasted_url_with_quotes_and_newline(pg_url):
    db = DB("", url=f'"{pg_url}\n"\n')
    assert db.is_pg and db.get("schema_version")
    db.close()


def test_new_queries_on_postgres(cfg, pg):
    """The single-join leads query, observation pruning and the agent retry queue, on Postgres."""
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from test_performance import CountingConn, seed
    db = engine.open_db(cfg)
    assert db.is_pg
    seed(db, 50, 12, runs=("r1", "r2"))
    db.c.execute("SELECT setval(pg_get_serial_sequence('companies','id'), 1000)")
    inner = db.c
    db.c = CountingConn(inner)
    rows = leads.build(db, cfg)
    assert len(rows) == 50 and len(db.c.calls) <= 3
    assert leads.summary(db, cfg)["leads"] == 50
    db.c = inner

    db.save_profile(1, "r3", "C1", "profiled", [{"signal": "METAL", "value": "steel"}], keep_runs=2)
    assert sorted({r[0] for r in db.c.execute("SELECT run_id FROM observations WHERE company_id=1")}) == ["r2", "r3"]

    db.c.execute("UPDATE companies SET digest='### PAGE x' WHERE id IN (1, 2)")
    db.agent_failed("companies", 1)
    assert [r["id"] for r in db.companies_for_agents(2, 3)][0] == 2
    for _ in range(2):
        db.agent_failed("companies", 1)
    assert 1 not in [r["id"] for r in db.companies_for_agents(100, 3)]
