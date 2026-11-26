"""Agent crew against a fake OpenAI-compatible server: no network, no keys, no cost."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from metalscout import engine, leads
from metalscout.agents import ground
from metalscout.agents.crew import Crew
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


def fake_server(fail_first=0):
    state = {"calls": 0, "fail": fail_first}

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
            reply = next(v for k, v in REPLIES.items() if f"**{k}**" in system)
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
