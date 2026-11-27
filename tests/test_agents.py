"""Agent crew against a fake OpenAI-compatible server: no network, no keys, no cost."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from metalscout import engine, leads
from metalscout.agents import ground
from metalscout.agents.llm import Router
from metalscout.net import reg_domain

ANALYST = {
    "products": [{"name": "crankshafts", "quote": "We manufacture crankshafts"}],
    "raw_materials": [{"metal": "steel", "form": "EN8 alloy steel", "quote": "Raw material: alloy steel EN8"},
                      {"metal": "copper", "form": "copper cathode", "quote": "we buy 900 MT of copper cathode"}],  # invented
    "volume": {"value": 120, "unit": "MT", "period": "month", "quote": "We require 120 MT per month of alloy steel"},
    "people": [{"name": "R. Patel", "title": "Purchase Head", "quote": "Mr R. Patel, Purchase Head"}],  # invented
    "buying_signals": [{"text": "vendor registration open", "quote": "Become a supplier: vendor registration form"}],
}
REPLIES = {
    "Sorter": {"org_type": "manufacturer", "confidence": 0.9, "quote": "Manufacturers of forged auto components", "reason": "plant"},
    "Material Analyst": ANALYST,
    "Outreach Writer": {"subject": "Alloy steel for your forgings", "body": "Hello, we supply EN8 alloy steel bars..."},
    "Tender Scout": {"is_buyer_request": True, "buyer": {"name": "ABC Railways", "quote": "ABC Railways invites bids"},
                     "items": [{"metal": "copper", "spec": "cathode", "quantity": "50 MT", "quote": "Supply of 50 MT copper cathode"}],
                     "deadline": None, "location": None},
}


def fake_server(fail_first=0, replies=None):
    state = {"calls": 0, "fail": fail_first}
    replies = REPLIES if replies is None else replies

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._json(200, {"data": [{"id": "qwen2.5:7b"}, {"id": "nomic-embed-text"}]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["calls"] += 1
            if state["fail"] > 0:
                state["fail"] -= 1
                return self._json(429, {"error": "rate limited"})
            system = body["messages"][0]["content"]
            reply = next(v for k, v in replies.items() if f"**{k}**" in system)
            self._json(200, {"choices": [{"message": {"content": json.dumps(reply)}}], "usage": {"total_tokens": 42}})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, state


@pytest.fixture
def llm(monkeypatch):
    srv, state = fake_server()
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "CEREBRAS_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    yield state
    srv.shutdown()


def test_ground_rejects_invented_quotes():
    d = "### PAGE https://a.in/contact\nCall our purchase team. We require 120 MT per month.\n### PAGE https://a.in/\nHome"
    assert ground.locate("We require 120 MT per month", d) == "https://a.in/contact"
    assert ground.locate("we require   120 mt PER month.", d) == "https://a.in/contact"  # whitespace/case tolerant
    assert ground.locate("We require 900 MT per month", d) is None
    assert ground.locate("short", d) is None


def test_router_discovers_models_and_skips_embeddings(cfg, llm):
    r = Router(cfg)
    assert r.available and r.roster() == [{"provider": "ollama", "small": "qwen2.5:7b", "large": "qwen2.5:7b"}]


def test_router_survives_rate_limit_then_reports(cfg, llm):
    llm["fail"] = 5
    r = Router(cfg)
    with pytest.raises(RuntimeError, match="ollama:429"):
        r.complete("small", "**Sorter**", "x")


def test_crew_end_to_end(site, cfg, llm):
    cfg["crawl"]["allow_private_hosts"] = True
    db = engine.open_db(cfg)
    db.add_company(reg_domain(site), site, "test", "manual")
    db.add_signal(dict(url="https://bidplus.gem.gov.in/b/1", title="Copper tender", snippet="", kind="tender", host="gem.gov.in",
                       metals=[], quantity=[], emails=[], phones=[], intent=1, opened=1, restricted=0, query="t",
                       digest="ABC Railways invites bids. Supply of 50 MT copper cathode to Delhi."))
    res = engine.run(cfg, "test", stages=("profile", "agents"))
    assert res["status"] == "ok", res["errors"]
    st = res["stats"]
    assert st["agent_companies"] == 1 and st["agent_signals"] == 1
    assert st["agent_rejected"] == 2  # the invented copper quote and the invented person

    [lead] = leads.build(db, cfg)
    ai = lead["ai"]
    assert [m["value"] for m in ai["materials"]] == ["steel: EN8 alloy steel"]
    assert ai["materials"][0]["source"].endswith("index.html")
    assert ai["volume"][0]["value"] == "120 MT per month"
    assert ai["volume"][0]["source"].endswith("vendor-registration.html")
    assert ai["people"] == []
    assert ai["outreach"]["subject"] == "Alloy steel for your forgings"
    assert lead["tier"] == "A"

    sig = leads.signals(db)[0]
    assert sig["agent"]["buyer"] == "ABC Railways" and sig["agent"]["items"][0]["quantity"] == "50 MT"

    # second run: nothing new to analyse, no extra model calls
    calls = llm["calls"]
    engine.run(cfg, "test", stages=("agents",))
    assert llm["calls"] == calls


def test_agents_skip_cleanly_without_any_provider(cfg, monkeypatch):
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "CEREBRAS_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9/v1")  # nothing listening
    res = engine.run(cfg, "test", stages=("agents",))
    assert res["status"] == "ok" and res["stats"]["agents"].startswith("skipped")


def test_retired_model_falls_back_to_working_one(cfg, monkeypatch):
    """A model that answers 404 (retired, like gemini-2.5-flash in Nov 2026) is skipped for the run."""
    seen = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._json(200, {"data": [{"id": "mistral:7b"}, {"id": "llama3.1:8b"}]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body["model"])
            if body["model"] == "mistral:7b":
                return self._json(404, {"error": "model not found"})
            self._json(200, {"choices": [{"message": {"content": '{"ok": true}'}}]})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    for k in ("GROQ_API_KEY", "GEMINI_API_KEY", "CEREBRAS_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    try:
        r = Router(cfg)
        res = r.complete("large", "x", "y")
        assert res.model == "llama3.1:8b" and res.data == {"ok": True}
        r.complete("large", "x", "y")
        assert seen == ["mistral:7b", "llama3.1:8b", "llama3.1:8b"]  # the 404 model is not retried
    finally:
        srv.shutdown()


def test_failed_call_is_retried_and_redo_resets(site, cfg, llm):
    db = engine.open_db(cfg)
    db.add_company(reg_domain(site), site, "test", "manual")
    llm["fail"] = 100  # every model call rate-limited
    cfg["agents"]["max_wait_s"] = 0  # don't wait out cooldowns in this test
    res = engine.run(cfg, "test", stages=("profile", "agents"))
    assert res["stats"].get("agent_retry_later") == 1 and res["stats"]["agent_companies"] == 0
    assert len(db.companies_for_agents(10)) == 1  # not marked done -> retried next run
    llm["fail"] = 0
    engine.run(cfg, "test", stages=("agents",))
    assert leads.build(db, cfg)[0]["ai"]["has_any"]
    engine.run(cfg, "test", stages=("redo-agents",))
    assert not leads.build(db, cfg)[0]["ai"]["has_any"] and len(db.companies_for_agents(10)) == 1


def test_transient_503_waits_and_recovers(cfg, llm, monkeypatch):
    """One provider, a temporary 503: the router waits out the short cooldown instead of failing every call."""
    import metalscout.agents.llm as L
    slept = []
    monkeypatch.setattr(L.time, "sleep", lambda s: slept.append(s))
    real_time = L.time.time
    clock = {"t": real_time()}
    monkeypatch.setattr(L.time, "time", lambda: clock["t"])
    monkeypatch.setattr(L.time, "sleep", lambda s: (slept.append(s), clock.__setitem__("t", clock["t"] + s)))
    llm["fail"] = 1
    r = Router(cfg)
    res = r.complete("small", "**Sorter**", "x")
    assert res.data["org_type"] == "manufacturer"
    assert any(25 <= s <= 61 for s in slept)  # waited out the cooldown
