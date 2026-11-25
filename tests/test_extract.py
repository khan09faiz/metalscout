from metalscout import extract as X


def test_emails_plain_obfuscated_and_junk():
    t = "Write to purchase [at] shreeforge [dot] com or sales@shreeforge.com. logo@2x.png noreply@x.com"
    assert X.emails(t) == ["sales@shreeforge.com", "purchase@shreeforge.com"]


def test_cloudflare_email():
    key = 0x42
    enc = f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in "buy@acme.in")
    assert "buy@acme.in" in X.emails("", f'<a data-cfemail="{enc}">')


def test_phones_indian_e164():
    assert X.phones("Call +91 98250 12345 or 098250 12345") == ["+919825012345"]


def test_registrations():
    r = X.registrations("GSTIN 24ABCDE1234F1Z5 CIN U28910GJ2005PTC012345 UDYAM-GJ-01-0012345")
    assert r["GSTIN"] == ["24ABCDE1234F1Z5"]
    assert r["CIN"] == ["U28910GJ2005PTC012345"]
    assert r["UDYAM"] == ["UDYAM-GJ-01-0012345"]


def test_quantities_units_and_noise():
    q = X.quantities("installed capacity of 6,000 MT per year; we need 120 MT per month; 5 kg sample")
    assert [x["value"] for x in q] == ["6,000 MT per year", "120 MT per month"]
    assert q[0]["kg"] == 6_000_000


def test_classify():
    assert X.classify("Manufacturers of forgings. Our plant has installed capacity 500 MT.")["org_type"] == "manufacturer"
    assert X.classify("Leading traders, dealers and stockists. Ready stock.")["org_type"] == "trader"
    assert X.classify("Hello world")["org_type"] == "unknown"


def test_metals_and_title():
    assert set(X.metals_in("ADC12 aluminium ingot and copper cathode")) >= {"aluminium", "copper"}
    assert X.page_title("<title>Shree Forge Pvt Ltd | Forgings</title>") == "Shree Forge Pvt Ltd"


def test_challenge_detection():
    assert X.is_challenge("Just a moment... checking your browser")
    assert not X.is_challenge("Welcome to our forging plant")


def test_equipment_tonnage_is_not_volume():
    t = "We have a 3 Ton hammer and 500 tonne press. Raw material consumption 300 tonnes; production 2,400 TPA."
    assert [q["value"] for q in X.quantities(t)] == ["300 tonnes", "2,400 TPA"]
    assert X.quantities("Supply of 50 MT copper cathode", strict=False)[0]["value"] == "50 MT"


def test_placeholder_emails_dropped():
    assert X.emails("name@company.com your@email.com info@realforge.in") == ["info@realforge.in"]
