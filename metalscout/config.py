"""Config: one YAML file (metalscout.yaml) merged over defaults. Plain dict access everywhere."""
from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

HOME = Path(os.getenv("METALSCOUT_HOME", Path.cwd()))

DEFAULTS: dict = {
    "business": {"name": "My Metals Co", "sells": ["steel", "stainless", "aluminium", "copper", "brass", "zinc", "pig_iron", "ferro_alloy"],
                 "region": "India"},
    "search": {
        "metals": ["HR coil", "aluminium ingot", "copper cathode", "stainless steel", "brass ingot", "zinc ingot", "pig iron", "ferro alloys"],
        "industries": ["forging", "foundry", "wire and cable", "auto components", "pipes and tubes", "fasteners", "transformer"],
        "clusters": ["Rajkot", "Ludhiana", "Jamnagar", "Pune", "Coimbatore", "Chennai", "Faridabad", "Howrah"],
        "templates": ["{industry} manufacturer {city} raw material {metal} contact"],
        "queries_per_run": 40,
        "results_per_query": 10,
        "provider": "auto",  # auto = serper if SERPER_API_KEY else duckduckgo
    },
    "domains": {"signal": [], "restricted": [], "skip": []},
    "crawl": {"max_pages": 12, "max_depth": 2, "concurrency": 3, "delay_min": 1.0, "delay_max": 2.5,
              "site_timeout_s": 150, "allow_private_hosts": False},
    "pipeline": {"profile_per_run": 60, "signals_per_run": 40, "reprofile_after_days": 30},
    "fit": {"manufacturer": 30, "metal_match": 20, "quantity": 15, "email": 15, "phone": 10, "registration": 5, "intent": 5,
            "tier_a": 65, "tier_b": 40},
    "schedule": {"daily_at": "06:30", "enabled": True},
    "export": {"dir": "exports", "keep_days": 30, "gsheet_id": "", "gsheet_creds": ""},
    "web": {"host": "127.0.0.1", "port": 8000, "allowed_hosts": []},  # extra Host names accepted (LAN use)
    "compliance": {"do_not_contact": []},
    "agents": {"enabled": True, "order": ["groq", "cerebras", "gemini", "openrouter", "ollama"],
               "companies_per_run": 40, "signals_per_run": 30, "max_calls_per_run": 150, "timeout_s": 60,
               "min_confidence": 0.7, "max_attempts": 3, "write_for_tiers": ["A", "B"], "analyst_max_chars": 12000, "providers": {}},
}


def _merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load(path: str | Path | None = None) -> dict:
    p = Path(path or os.getenv("METALSCOUT_CONFIG", HOME / "metalscout.yaml"))
    data = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    cfg = _merge(DEFAULTS, data or {})
    cfg["_path"] = str(p)
    cfg["_home"] = str(p.parent if p.exists() else HOME)
    # where runtime files go (db, logs, exports); /tmp on read-only hosts like Vercel
    cfg["_data"] = os.getenv("METALSCOUT_DATA_DIR", cfg["_home"])
    return cfg


def path(cfg: dict, *parts: str) -> Path:
    p = Path(cfg.get("_data") or cfg["_home"]).joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
