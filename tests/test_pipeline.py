"""End to end on a local fixture site: real Chromium, real crawl, real export. No internet needed."""
import openpyxl
import pytest

from metalscout import engine, leads
from metalscout.net import reg_domain


def test_profile_and_export(site, cfg):
    db = engine.open_db(cfg)
    db.add_company(reg_domain(site), site, "test", "manual")
    res = engine.run(cfg, "test", stages=("profile", "export"))
    assert res["status"] == "ok", res["errors"]
    assert res["stats"]["profiled"] == 1

    [lead] = leads.build(db, cfg)
    assert lead["org_type"] == "manufacturer"
    assert lead["tier"] == "A"
    assert {e["value"] for e in lead["emails"]} == {"purchase@shreeforge.com", "sales@shreeforge.com"}
    assert all(e["source"].endswith("contact.html") for e in lead["emails"])
    assert lead["phones"][0]["value"] == "+919825012345"
    assert any(q["value"] == "120 MT per month" for q in lead["quantity"])
    assert lead["gstin"][0]["value"] == "24ABCDE1234F1Z5"
    assert lead["vendor_page"].endswith("vendor-registration.html")

    wb = openpyxl.load_workbook(res["stats"]["export"]["latest"])
    assert set(wb.sheetnames) >= {"Leads", "All companies", "Buyer signals", "Runs", "README"}
    assert wb["Leads"].max_row == 2


def test_rerun_is_idempotent(site, cfg):
    db = engine.open_db(cfg)
    db.add_company(reg_domain(site), site, "test", "manual")
    engine.run(cfg, "test", stages=("profile",))
    res = engine.run(cfg, "test", stages=("profile",))  # fresh profile -> nothing to do
    assert res["stats"]["profile_queue"] == 0
    assert len(leads.build(db, cfg)) == 1


def test_lock_blocks_second_run(cfg):
    with engine.Lock(cfg):
        with pytest.raises(RuntimeError):
            engine.run(cfg, "test", stages=("export",))


def test_failed_site_is_recorded_not_silent(cfg):
    db = engine.open_db(cfg)
    db.add_company("127.0.0.1", "http://127.0.0.1:9/", "test", "manual")  # nothing listening
    res = engine.run(cfg, "test", stages=("profile",))
    assert res["stats"]["profile_failed"] == 1
    assert db.c.execute("SELECT status FROM companies").fetchone()["status"] == "failed"
