"""Robustness: stuck runs (heartbeat + mark-failed), run status vs warnings, and small fixes
(cron quoting, phone reason, domain do-not-contact)."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from metalscout import db as D
from metalscout import engine, fit, scheduler, sources
from metalscout.__main__ import main as cli

ROOT = Path(__file__).resolve().parent.parent


# ---------- 17. stuck runs
def test_running_run_needs_a_recent_heartbeat(cfg):
    db = engine.open_db(cfg)
    rid = db.start_run("test")
    assert db.running_run()["id"] == rid
    db.c.execute("UPDATE runs SET heartbeat=? WHERE id=?", (D.now() - D.RUN_STALE_S - 60, rid))
    db.c.commit()
    assert db.running_run() is None and not engine.is_running(cfg, db)
    db.update_run_stats(rid, {"x": 1})  # stats updates beat the heartbeat
    assert db.running_run()["id"] == rid
    db.c.execute("UPDATE runs SET heartbeat=NULL, started=? WHERE id=?", (D.now() - D.RUN_STALE_S - 60, rid))
    db.c.commit()
    assert db.running_run() is None  # pre-heartbeat rows fall back to `started`


def test_stale_run_does_not_block_a_new_one(cfg):
    db = engine.open_db(cfg)
    stuck = db.start_run("schedule")
    db.c.execute("UPDATE runs SET heartbeat=? WHERE id=?", (D.now() - 3600, stuck))
    db.c.commit()
    assert engine.run(cfg, "test", stages=("redo-agents",))["status"] == "ok"


def test_mark_failed_cli(cfg, capsys):
    Path(cfg["_path"]).write_text("{}\n")  # so the CLI resolves its data dir to this test's tmp dir, not the cwd
    db = engine.open_db(cfg)
    old = db.start_run("schedule")
    db.finish_run(old, "ok", {}, [])
    rid = db.start_run("schedule")
    cli(["--config", cfg["_path"], "mark-failed"])
    assert f"marked run {rid} as failed" in capsys.readouterr().out
    r = {x["id"]: x for x in db.runs()}
    assert r[rid]["status"] == "failed" and r[rid]["finished"] and "marked failed" in r[rid]["errors"][-1]
    assert r[old]["status"] == "ok"
    cli(["--config", cfg["_path"], "mark-failed"])
    assert "no running run" in capsys.readouterr().out


def test_engine_workflow_marks_failed_on_failure_or_cancel():
    steps = yaml.safe_load((ROOT / ".github/workflows/engine.yml").read_text())["jobs"]["run"]["steps"]
    names = [s.get("name") for s in steps]
    step = steps[names.index("Mark the run failed")]
    assert names.index("Mark the run failed") > names.index("Run")
    assert step["if"] == "failure() || cancelled()" and "mark-failed" in step["run"]


def test_long_stages_beat_the_heartbeat(cfg, monkeypatch):
    db = engine.open_db(cfg)
    rid = db.start_run("test")
    beats = []
    monkeypatch.setattr(db, "heartbeat", lambda r: beats.append(r))
    monkeypatch.setattr(sources, "search", lambda q, cfg: [])
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    cfg["search"]["queries_per_run"] = 3
    sources.discover(db, cfg, rid, {}, [])
    assert beats == [rid] * 3


# ---------- 18. status and warnings
def test_site_failure_is_a_warning_not_an_error(cfg):
    db = engine.open_db(cfg)
    db.add_company("127.0.0.1", "http://127.0.0.1:9/", "test", "manual")
    res = engine.run(cfg, "test", stages=("profile",))
    assert res["status"] == "ok" and res["errors"] == []
    assert res["stats"]["profile_failed"] == 1


def test_profile_exception_goes_to_warnings(cfg, monkeypatch):
    db = engine.open_db(cfg)
    db.add_company("a.in", "https://a.in/", "test", "manual")
    monkeypatch.setattr(engine.profile, "observe", lambda *a: (_ for _ in ()).throw(ValueError("parser broke")))
    res = engine.run(cfg, "test", stages=("profile",))
    assert res["status"] == "ok" and res["errors"] == []
    assert any("parser broke" in w for w in res["stats"]["warnings"]) and res["stats"]["warnings_total"] == 1
    stored = engine.open_db(cfg).runs(1)[0]
    assert stored["errors"] == [] and stored["stats"]["warnings"] == res["stats"]["warnings"]


def test_status_partial_and_failed(cfg, monkeypatch):
    monkeypatch.setattr(engine.export, "daily", lambda db, cfg: (_ for _ in ()).throw(OSError("disk full")))
    res = engine.run(cfg, "test", stages=("redo-agents", "export"))
    assert res["status"] == "partial" and res["errors"] == ["export: disk full"]
    res = engine.run(cfg, "test", stages=("export",))
    assert res["status"] == "failed"


def test_discover_with_every_search_failing_fails_the_stage(cfg, monkeypatch):
    monkeypatch.setattr(sources, "search", lambda q, cfg: (_ for _ in ()).throw(RuntimeError("429")))
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    res = engine.run(cfg, "test", stages=("discover",))
    assert res["status"] == "failed" and res["errors"][0].startswith("discover: stopped after 5 failed searches")
    assert res["stats"]["warnings_total"] == 5


def test_some_searches_failing_are_warnings(cfg, monkeypatch):
    calls = {"n": 0}
    def flaky(q, cfg):
        calls["n"] += 1
        if calls["n"] % 2:
            raise RuntimeError("blip")
        return []
    monkeypatch.setattr(sources, "search", flaky)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    cfg["search"]["queries_per_run"] = 4
    res = engine.run(cfg, "test", stages=("discover",))
    assert res["status"] == "ok" and res["stats"]["queries"] == 2 and res["stats"]["warnings_total"] == 2


def test_warnings_are_capped():
    stats = {}
    w = engine.Warnings(stats, cap=50)
    for i in range(60):
        w.append(f"site {i} " + "x" * 400)
    assert len(stats["warnings"]) == 50 and stats["warnings_total"] == 60 and len(stats["warnings"][0]) == 300
    assert json.loads(json.dumps(stats))["warnings"][0].startswith("site 0")


# ---------- dashboard rendering (runs warnings + draft warning), executed in Node with hostile input
def _js_functions(*names):
    js = (ROOT / "metalscout" / "web" / "app.js").read_text()
    out = []
    for n in ("esc", "safeUrl", "src"):
        out.append(re.search(rf"^const {n} = .*?;$", js, re.M).group(0))
    for n in names:
        m = re.search(rf"^function {n}\(.*?^}}$", js, re.M | re.S)
        out.append(m.group(0))
    return "\n".join(out)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_dashboard_escapes_warnings_and_draft_warning():
    evil = '<img src=x onerror=alert(1)>"\''
    script = _js_functions("list", "aiSection", "warnCell") + f"""
const evil = {json.dumps(evil)};
const html = warnCell({{warnings: [evil, "b", "c"], warnings_total: 3}}) +
  aiSection({{has_any: true, org_type: null, materials: [], volume: [], products: [], people: [], buying_signals: [],
             outreach: {{subject: "Hi", body: "x", warning: "unverified numbers: " + evil}}}});
process.stdout.write(html);
"""
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    assert "<img" not in out and "&lt;img src=x onerror=alert(1)&gt;" in out
    assert "3 warnings" in out and "unverified numbers: &lt;img" in out


# ---------- 19. small fixes
def test_cron_line_quotes_paths(cfg, monkeypatch):
    cfg["_home"] = "/home/me/My Leads; rm -rf ~"
    monkeypatch.setattr(sys, "executable", "/opt/py 3/bin/python")
    line = scheduler.cron_line(cfg)
    assert "cd '/home/me/My Leads; rm -rf ~' && '/opt/py 3/bin/python' -m metalscout" in line


def test_phone_reason(cfg):
    o = [{"signal": "PHONE", "value": "+919825012345", "num": None, "source_url": "u", "evidence": ""}]
    r = fit.score({"domain": "x.com"}, o, cfg)
    assert r["score"] == cfg["fit"]["phone"] and "phone" in r["reasons"]
    cfg["fit"]["phone"] = 0
    assert "phone" not in fit.score({"domain": "x.com"}, o, cfg)["reasons"]


@pytest.mark.parametrize("entry,email,blocked", [
    ("acme.in", "sales@acme.in", True),
    ("acme.in", "Sales@Mail.Acme.In", True),       # subdomain, any case
    ("acme.in", "sales@notacme.in", False),        # not a suffix match on the label
    ("acme.in", "acme.in@gmail.com", False),
    ("sales@acme.in", "sales@acme.in", True),      # exact email entries still work
    ("sales@acme.in", "info@acme.in", False),
])
def test_dnc_domain_matches_emails(cfg, entry, email, blocked):
    cfg["compliance"]["do_not_contact"] = [entry]
    o = [{"signal": "EMAIL", "value": email, "num": None, "source_url": "u", "evidence": "other domain"},
         {"signal": "ORG_TYPE", "value": "manufacturer", "num": None, "source_url": "u", "evidence": ""}]
    r = fit.score({"domain": "other-site.in"}, o, cfg)
    assert (r["tier"] == "X") is blocked
