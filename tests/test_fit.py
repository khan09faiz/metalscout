from metalscout import fit


def obs(*pairs):
    return [{"signal": s, "value": v, "num": n, "source_url": "u", "evidence": e} for s, v, n, e in pairs]


def test_full_manufacturer_scores_a(cfg):
    o = obs(("ORG_TYPE", "manufacturer", None, ""), ("METAL", "steel", None, ""), ("QUANTITY", "120 MT per month", 120000, ""),
            ("EMAIL", "a@x.com", None, "own domain"), ("PHONE", "+91", None, ""), ("GSTIN", "24ABCDE1234F1Z5", None, ""),
            ("VENDOR_PAGE", "u", None, ""))
    r = fit.score({"domain": "x.com"}, o, cfg)
    assert r["score"] == 100 and r["tier"] == "A"


def test_trader_capped(cfg):
    o = obs(("ORG_TYPE", "trader", None, ""), ("METAL", "steel", None, ""), ("EMAIL", "a@x.com", None, "own domain"),
            ("PHONE", "+91", None, ""))
    r = fit.score({"domain": "x.com"}, o, cfg)
    assert r["score"] <= 15 and "trader" in r["reasons"][0]


def test_do_not_contact(cfg):
    cfg["compliance"]["do_not_contact"] = ["x.com"]
    assert fit.score({"domain": "x.com"}, obs(("ORG_TYPE", "manufacturer", None, "")), cfg)["score"] == 0


def test_metal_not_sold_gives_no_points(cfg):
    cfg["business"]["sells"] = ["copper"]
    r = fit.score({"domain": "x.com"}, obs(("ORG_TYPE", "manufacturer", None, ""), ("METAL", "steel", None, "")), cfg)
    assert r["score"] == cfg["fit"]["manufacturer"]
