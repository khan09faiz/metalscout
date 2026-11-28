"""Tooling and identity: lock files cover the requirements, CI installs from them, Dependabot is set up,
and the crawler identifies itself (robots.txt, httpx, browser)."""
import asyncio
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from metalscout import __version__, net

ROOT = Path(__file__).resolve().parent.parent


def _names(path):
    out = set()
    for line in Path(path).read_text().splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith("-"):
            out.add(re.split(r"[\[<>=!~; ]", line)[0].lower().replace("_", "-"))
    return out


# ---------- 21. locks + dependabot
def test_lock_files_pin_every_requirement_with_hashes():
    for lock, reqs in (("requirements.lock", ["requirements.txt"]),
                       ("requirements-engine.lock", ["requirements.txt", "requirements-engine.txt"])):
        text = (ROOT / lock).read_text()
        pinned = {m.group(1).lower().replace("_", "-") for m in re.finditer(r"^([A-Za-z0-9_.\-]+)==", text, re.M)}
        wanted = set().union(*(_names(ROOT / r) for r in reqs))
        assert wanted <= pinned, f"{lock} is stale; missing {wanted - pinned}"
        for block in re.split(r"\n(?=[A-Za-z])", text):
            if "==" in block.split("\n")[0]:
                assert "--hash=sha256:" in block, block.split("\n")[0]


def test_engine_installs_from_lock_with_hashes():
    steps = yaml.safe_load((ROOT / ".github/workflows/engine.yml").read_text())["jobs"]["run"]["steps"]
    install = next(s["run"] for s in steps if s.get("name") == "Install")
    assert "pip install --require-hashes -r requirements-engine.lock" in install
    assert "requirements.txt" not in install


def test_ci_runs_ruff_and_mypy():
    runs = [s.get("run", "") for s in yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())["jobs"]["test"]["steps"]]
    assert "ruff check ." in runs and "mypy" in runs


def test_dependabot_weekly_pip_and_actions():
    cfg = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    eco = {u["package-ecosystem"]: u["schedule"]["interval"] for u in cfg["updates"]}
    assert eco == {"pip": "weekly", "github-actions": "weekly"}


# ---------- 22. honest crawler identity
class UAServer(ThreadingHTTPServer):
    def __init__(self, robots: bytes):
        self.uas, srv = [], self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                srv.uas.append((self.path, self.headers.get("User-Agent", "")))
                body = robots if self.path == "/robots.txt" else b"<html><body><h1>Shree Forge</h1>We manufacture forgings.</body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain" if self.path == "/robots.txt" else "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        super().__init__(("127.0.0.1", 0), H)
        threading.Thread(target=self.serve_forever, daemon=True).start()


def test_default_identity(cfg):
    bot, browser = net.user_agents(cfg)
    assert bot == f"MetalScoutBot/{__version__} (+https://github.com/khan09faiz/metalscout)"
    assert browser.startswith("Mozilla/5.0") and browser.endswith(bot)
    cfg["crawl"].update(user_agent="AcmeBot/1 (+https://acme.in/bot)", browser_user_agent="Custom/2")
    assert net.user_agents(cfg) == ("AcmeBot/1 (+https://acme.in/bot)", "Custom/2")


def test_robots_uses_bot_ua_and_its_own_rules():
    srv = UAServer(b"User-agent: MetalScoutBot\nDisallow: /private\n\nUser-agent: *\nDisallow: /\n")
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        r = net.Robots(allow_private=True)
        assert asyncio.run(r.allowed(base + "/products")) is True      # MetalScoutBot's group, not '*'
        assert asyncio.run(r.allowed(base + "/private/x")) is False
        assert srv.uas[0] == ("/robots.txt", net.BOT_UA)
        # the old Chrome UA matched only the '*' group, so per-bot rules never applied
        assert asyncio.run(net.Robots(allow_private=True, ua=net.CHROME_UA).allowed(base + "/products")) is False
    finally:
        srv.shutdown()


def test_browser_sends_configured_identity(cfg):
    pytest.importorskip("playwright")
    from metalscout.browser import Surfer
    srv = UAServer(b"User-agent: *\nAllow: /\n")
    try:
        async def go():
            async with Surfer(cfg) as s:
                return await s.crawl(f"http://127.0.0.1:{srv.server_port}/")
        assert asyncio.run(go())
        page_uas = [ua for path, ua in srv.uas if path == "/"]
        assert page_uas and all("MetalScoutBot/" in ua and ua.startswith("Mozilla/5.0") for ua in page_uas)
    finally:
        srv.shutdown()
