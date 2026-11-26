import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from metalscout import server


def test_status_static_and_traversal(cfg):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        s = json.load(urllib.request.urlopen(base + "/api/status"))
        assert s["running"] is False and s["counts"]["leads"] == 0
        assert b"MetalScout" in urllib.request.urlopen(base + "/").read()
        assert json.load(urllib.request.urlopen(base + "/api/leads")) == []
        try:
            urllib.request.urlopen(base + "/..%2f..%2fmetalscout.yaml")
            raise AssertionError("traversal served a file")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown()


def test_public_host_requires_password(cfg, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(cfg))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/api/leads")
        raise AssertionError("served without a password")
    except urllib.error.HTTPError as e:
        assert e.code == 503
    finally:
        srv.shutdown()
