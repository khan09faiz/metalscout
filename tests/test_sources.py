from metalscout import sources
from metalscout.db import DB


def test_query_rotation_covers_space(cfg, tmp_path):
    cfg["search"].update(templates=["{industry} {metal} {city}"], metals=["a", "b"], industries=["x"],
                         clusters=["c1", "c2", "c3"], queries_per_run=4)
    db = DB(str(tmp_path / "t.db"))
    first, second = sources.next_batch(db, cfg), sources.next_batch(db, cfg)
    assert len(set(sources.all_queries(cfg))) == 6
    assert set(first) | set(second) == set(sources.all_queries(cfg))


def test_routing(cfg):
    cfg["domains"] = {"signal": ["indiamart.com"], "restricted": ["linkedin.com"], "skip": ["wikipedia.org"]}
    r = lambda u: sources.route({"url": u}, cfg)
    assert r("https://dir.indiamart.com/x") == "signal"
    assert r("https://in.linkedin.com/posts/x") == "signal"
    assert r("https://en.wikipedia.org/wiki/Steel") == "skip"
    assert r("https://www.bing.com/aclick?ld=1") == "skip"
    assert r("https://shreeforge.com/") == "company"


def test_csv_import(cfg, tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("title,url,website\nGeM bid copper cathode 50 MT,https://bidplus.gem.gov.in/b/1,\nAcme Forge,,acmeforge.in\n",
                 encoding="utf-8")
    db = DB(str(tmp_path / "t.db"))
    assert sources.import_csv(db, cfg, str(p)) == (1, 1)
    s = dict(db.c.execute("SELECT * FROM buyer_signals").fetchone())
    assert "copper" in s["metals"] and "50 MT" in s["quantity"]
