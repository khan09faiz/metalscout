"""Security regressions: workflow injection, stage allowlist, CSRF / DNS rebinding, error leaks,
login rate limit, pinned actions, and SSRF past the seed URL."""
import asyncio
import base64
import json
import re
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from metalscout import net, server
from metalscout.__main__ import main as cli

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


# ---------- 1. shell injection / stage allowlist
def test_workflows_never_interpolate_expressions_into_scripts():
    for wf in WORKFLOWS:
        for job in yaml.safe_load(wf.read_text())["jobs"].values():
            for step in job["steps"]:
                assert "${{" not in step.get("run", ""), f"{wf.name}: {step.get('name')} interpolates into bash"


def test_workflow_rejects_malicious_stages():
    steps = yaml.safe_load((ROOT / ".github/workflows/engine.yml").read_text())["jobs"]["run"]["steps"]
    script = next(s["run"] for s in steps if s.get("name") == "Run")
    script = script.replace("python -m metalscout", "echo would-run")
    def run(stages):
        return subprocess.run(["bash", "-c", script], env={"STAGES": stages, "TRIGGER": "manual", "PATH": "/usr/bin:/bin"},
                              capture_output=True, text=True)
    bad = run('profile"; touch /tmp/pwned; echo "')
    assert bad.returncode == 1 and "would-run" not in bad.stdout
    assert run("$(id)").returncode == 1
    ok = run("profile,redo-agents,export")
    assert ok.returncode == 0 and "would-run" in ok.stdout


def test_start_run_rejects_unknown_stage(cfg, monkeypatch):
    spawned = []
    monkeypatch.setattr(server.scheduler, "spawn_run", lambda *a: spawned.append(a))
    db = server.open_db(cfg)
    code, body = server.start_run(cfg, db, "profile;rm -rf /")
    assert code == 400 and "allowed" in body and not spawned
    assert server.start_run(cfg, db, "profile,bogus")[0] == 400
    code, _ = server.start_run(cfg, db, "profile, export")
    assert code == 202 and spawned[0][2] == ["--stages", "profile,export"]


def test_cli_rejects_unknown_stage(cfg, capsys):
    with pytest.raises(SystemExit) as e:
        cli(["--config", cfg["_path"], "run", "--stages", "profile,$(id)"])
    assert e.value.code == 2 and "unknown stage" in capsys.readouterr().err


# ---------- 2. CSRF / DNS rebinding, 4. error leak, 5. login rate limit
@pytest.fixture
def dash(cfg):
    def start(**env):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cfg))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        started.append(srv)
        return f"http://127.0.0.1:{srv.server_port}"
    started = []
    yield start
    for s in started:
        s.shutdown()


def call(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def test_post_needs_json_same_origin_and_local_host(dash):
    base = dash()
    body = json.dumps({"urls": []}).encode()
    assert call(base + "/api/add", body, {"Content-Type": "application/json"}) == (200, {"added": 0})
    assert call(base + "/api/add", body, {"Content-Type": "application/json; charset=utf-8", "Origin": base})[0] == 200
    assert call(base + "/api/add", body, {"Content-Type": "text/plain"})[0] == 403
    assert call(base + "/api/add", body, {"Content-Type": "application/x-www-form-urlencoded"})[0] == 403
    assert call(base + "/api/add", body, {"Content-Type": "application/json", "Origin": "https://evil.example"})[0] == 403
    assert call(base + "/api/add", body, {"Content-Type": "application/json", "Origin": "null"})[0] == 403
    port = base.rsplit(":", 1)[1]
    assert call(base + "/api/add", body, {"Content-Type": "application/json", "Host": f"evil.example:{port}"})[0] == 403
    # DNS rebinding: a GET under an attacker's hostname must not read lead data either
    assert call(base + "/api/leads", headers={"Host": f"rebind.evil.example:{port}"})[0] == 403
    assert call(base + "/api/leads", headers={"Host": f"localhost:{port}"})[0] == 200


def test_allowed_hosts_config(cfg, dash):
    cfg["web"]["allowed_hosts"] = ["metalscout.lan"]
    base = dash()
    port = base.rsplit(":", 1)[1]
    assert call(base + "/api/leads", headers={"Host": f"metalscout.lan:{port}"})[0] == 200


def test_500_does_not_leak_exception_text(dash, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("password=hunter2 at /secret/path")
    monkeypatch.setattr(server.L, "build", boom)
    base = dash()
    code, body = call(base + "/api/leads")
    assert code == 500 and body == {"error": "internal error"}
    assert "hunter2" in caplog.text  # still logged in full for the operator


def test_login_rate_limit(dash, monkeypatch):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "s3cret")
    base = dash()
    auth = lambda pw: {"Authorization": "Basic " + base64.b64encode(f"me:{pw}".encode()).decode()}
    assert call(base + "/api/status", headers=auth("s3cret"))[0] == 200
    for _ in range(server.LOGIN_MAX_FAILS):
        assert call(base + "/api/status", headers=auth("wrong"))[0] == 401
    assert call(base + "/api/status", headers=auth("wrong"))[0] == 429
    assert call(base + "/api/status", headers=auth("s3cret"))[0] == 429  # locked out: no oracle


def test_login_limiter_window_expires(monkeypatch):
    t = {"now": 1000.0}
    monkeypatch.setattr(server.time, "time", lambda: t["now"])
    lim = server.LoginLimiter(max_fails=2, window_s=60)
    lim.fail("1.2.3.4")
    lim.fail("1.2.3.4")
    assert lim.retry_after("1.2.3.4") > 0 and lim.retry_after("5.6.7.8") == 0
    t["now"] += 61
    assert lim.retry_after("1.2.3.4") == 0


# ---------- 6. pinned actions
def test_actions_pinned_to_full_sha():
    for wf in WORKFLOWS:
        for line in wf.read_text().splitlines():
            m = re.search(r"uses:\s*(\S+)", line)
            if m:
                assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", m.group(1)), line
                assert re.search(r"#\s*v\d", line), f"missing version comment: {line}"


# ---------- 3. SSRF beyond the seed URL
class Recorder(ThreadingHTTPServer):
    def __init__(self, routes):
        self.hits, self.routes = [], routes
        srv = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                srv.hits.append(self.path)
                code, headers, body = srv.routes.get(self.path, (404, {}, b"no"))
                self.send_response(code)
                for k, v in headers.items():
                    self.send_header(k, v.replace("PORT", str(srv.server_port)) if isinstance(v, str) else v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        super().__init__(("127.0.0.1", 0), H)
        threading.Thread(target=self.serve_forever, daemon=True).start()


@pytest.fixture
def only_127_is_public(monkeypatch):
    """Pretend 127.0.0.1 is a public host and `localhost` is the private network."""
    monkeypatch.setattr(net, "host_is_public", lambda h: h == "127.0.0.1")


def test_robots_never_fetched_from_private_host():
    priv = Recorder({"/robots.txt": (200, {}, b"User-agent: *\nAllow: /")})
    try:
        r = net.Robots()
        assert asyncio.run(r.allowed(f"http://127.0.0.1:{priv.server_port}/page")) is False
        assert priv.hits == []
    finally:
        priv.shutdown()


def test_robots_redirect_to_private_host_is_not_followed(only_127_is_public):
    priv = Recorder({"/robots.txt": (200, {}, b"User-agent: *\nAllow: /")})
    pub = Recorder({"/robots.txt": (302, {"Location": f"http://localhost:{priv.server_port}/robots.txt"}, b"")})
    try:
        r = net.Robots()
        assert asyncio.run(r.allowed(f"http://127.0.0.1:{pub.server_port}/page")) is False
        assert pub.hits == ["/robots.txt"] and priv.hits == []
    finally:
        priv.shutdown()
        pub.shutdown()


def test_host_is_public_rejects_internal_addresses():
    net.host_is_public.cache_clear()
    for h in ("127.0.0.1", "localhost", "10.0.0.1", "169.254.169.254", "0.0.0.0", "::1", "::ffff:127.0.0.1", "100.64.0.1", ""):
        assert net.host_is_public(h) is False, h


def test_browser_drops_redirect_to_private_host_and_blocks_subrequests(cfg, only_127_is_public):
    pytest.importorskip("playwright")
    from metalscout.browser import Surfer
    priv = Recorder({"/secret": (200, {"Content-Type": "text/html"}, b"<html><body>internal admin secret</body></html>"),
                     "/pixel.js": (200, {"Content-Type": "text/javascript"}, b"1"), "/robots.txt": (404, {}, b"")})
    pp = priv.server_port
    home = (f'<html><body><h1>Shree Forge</h1><a href="/about-us">About us</a>'
            f'<script src="http://localhost:{pp}/pixel.js"></script></body></html>').encode()
    pub = Recorder({"/": (200, {"Content-Type": "text/html"}, home), "/robots.txt": (404, {}, b""),
                    "/about-us": (302, {"Location": f"http://localhost:{pp}/secret"}, b"")})
    cfg["crawl"]["allow_private_hosts"] = False

    async def go():
        async with Surfer(cfg) as s:
            pages = await s.crawl(f"http://127.0.0.1:{pub.server_port}/")
            single = await s.open(f"http://127.0.0.1:{pub.server_port}/about-us")
        return pages, single
    try:
        pages, single = asyncio.run(go())
        assert [p["url"] for p in pages] == [f"http://127.0.0.1:{pub.server_port}/"]
        assert not any("secret" in p["text"] for p in pages)
        assert single is None
        print("private host saw:", priv.hits)
        assert "/pixel.js" not in priv.hits  # in-page request to a private host was blocked by the route handler
    finally:
        priv.shutdown()
        pub.shutdown()
