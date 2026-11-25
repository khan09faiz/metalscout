import functools
import http.server
import threading
from pathlib import Path

import pytest

from metalscout import config as C

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def site():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIX / "site"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/index.html"
    srv.shutdown()


@pytest.fixture
def cfg(tmp_path):
    c = C._merge(C.DEFAULTS, {})
    c["_path"] = str(tmp_path / "metalscout.yaml")
    c["_home"] = str(tmp_path)
    c["crawl"].update(allow_private_hosts=True, delay_min=0, delay_max=0.05, site_timeout_s=60)
    return c
