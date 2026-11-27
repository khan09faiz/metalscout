"""The crew: an orchestrator that hands each lead to specialist agents, each on the model tier that suits it.

    Orchestrator (deterministic rules, no model)
      ├─ Sorter      small model   only when the regex classifier is unsure or sees both trader and maker words
      ├─ Analyst     large model   manufacturers / unclear: materials, forms, volume, people, buying signals
      ├─ Writer      large model   only Tier A/B after analysis: first-email draft (never sent)
      └─ Scout       small model   buyer-signal pages (tenders, buy leads): buyer, items, qty, deadline

Every agent fact goes through ground.locate(): its quote must exist in the crawled text, or it is dropped
and counted as `rejected`. Each call is logged in agent_runs (agent, provider, model, latency, ok, rejected).
The orchestrator is the only place that decides *who* runs, so adding an agent = one prompt + one branch here.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .. import extract as X
from .. import fit
from ..db import DB
from .ground import locate
from .llm import BudgetExceeded, Router

log = logging.getLogger("metalscout.agents")
PROMPTS = Path(__file__).resolve().parents[2] / "prompts" / "agents"
METAL_KEYS = set(X.METALS)
PERIOD_TO_MONTH = {"month": 1, "year": 1 / 12, "annum": 1 / 12, "day": 30, "week": 4.3}


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


class Crew:
    def __init__(self, db: DB, cfg: dict, run_id: str, stats: dict, errors: list[str], router: Router | None = None):
        self.db, self.cfg, self.run_id, self.stats, self.errors = db, cfg, run_id, stats, errors
        self.router = router or Router(cfg)
        self.ac = cfg.get("agents", {})
        for k in ("agent_companies", "agent_calls", "agent_facts", "agent_rejected", "agent_signals"):
            stats.setdefault(k, 0)

    # ---- one agent call, logged and grounded by the caller
    def _call(self, agent: str, tier: str, user: str, company_id: int | None, want_json=True, max_tokens=1200):
        t0 = time.time()
        try:
            res = self.router.complete(tier, prompt(agent), user, want_json=want_json, max_tokens=max_tokens)
        except BudgetExceeded:
            raise
        except Exception as e:
            self.db.log_agent(self.run_id, company_id, agent, "", "", False, int((time.time() - t0) * 1000), error=str(e))
            self.errors.append(f"agent {agent}: {str(e)[:160]}")
            self._failed = True
            return None
        self.stats["agent_calls"] += 1
        return res

    def _ground(self, items, digest: str, signal: str, value_fn, num_fn=None) -> tuple[list[dict], int]:
        kept, rejected = [], 0
        for it in items or []:
            if not isinstance(it, dict):
                continue
            url = locate(str(it.get("quote", "")), digest)
            if not url:
                rejected += 1
                continue
            v = value_fn(it)
            if not v:
                continue
            kept.append({"signal": signal, "value": v, "num": num_fn(it) if num_fn else None,
                         "source_url": url, "evidence": str(it.get("quote", ""))[:400]})
        return kept, rejected

    # ---- company pipeline
    def run_company(self, c) -> None:
        cid, prun, digest = c["id"], c["last_profile_run"], c["digest"] or ""
        obs = self.db.latest_observations(cid, prun)
        sig = lambda s: [o for o in obs if o["signal"] == s]
        det_org = (sig("ORG_TYPE") or [{"value": "unknown"}])[0]["value"]
        mixed = bool(sig("MANUFACTURER_PHRASE")) and bool(sig("TRADER_PHRASE"))
        new: list[dict] = []
        self._failed = False
        rejected = 0
        org = det_org

        # 1. Sorter: only when the deterministic classifier is unsure
        if det_org == "unknown" or mixed:
            res = self._call("sorter", "small", f"WEBSITE TEXT:\n{digest[:7000]}", cid, max_tokens=300)
            if res and res.data:
                d = res.data
                url = locate(str(d.get("quote", "")), digest)
                ok = bool(url) and d.get("org_type") in ("manufacturer", "trader", "both", "service", "unknown")
                if ok:
                    conf = float(d.get("confidence") or 0)
                    new.append({"signal": "AGENT_ORG_TYPE", "value": d["org_type"], "num": conf, "source_url": url,
                                "evidence": str(d.get("quote", ""))[:400]})
                    if conf >= self.ac.get("min_confidence", 0.7):
                        org = d["org_type"]
                else:
                    rejected += 1
                self.db.log_agent(self.run_id, cid, "sorter", res.provider, res.model, ok, res.latency_ms, res.tokens, int(not ok))

        # 2. Analyst: anyone who might consume metal
        if org in ("manufacturer", "both", "unknown"):
            text = digest[: self.ac.get("analyst_max_chars", 12000)]
            res = self._call("analyst", "large", f"WEBSITE TEXT:\n{text}", cid, max_tokens=1500)
            if res and res.data:
                d, r0 = res.data, rejected
                for items, signal, vf, nf in (
                    (d.get("products"), "AGENT_PRODUCT", lambda i: str(i.get("name", ""))[:120], None),
                    ([m for m in d.get("raw_materials") or [] if isinstance(m, dict) and m.get("metal") in METAL_KEYS],
                     "AGENT_MATERIAL", lambda i: f"{i['metal']}: {str(i.get('form', '')).strip()}".strip(": ")[:160], None),
                    (d.get("people"), "AGENT_PERSON",
                     lambda i: f"{str(i.get('name', '')).strip()} — {str(i.get('title', '')).strip()}".strip(" —")[:160], None),
                    (d.get("buying_signals"), "AGENT_BUYING_SIGNAL", lambda i: str(i.get("text", ""))[:200], None),
                    ([d["volume"]] if isinstance(d.get("volume"), dict) else [], "AGENT_VOLUME", _vol_text, _vol_kg_month),
                ):
                    kept, rej = self._ground(items, digest, signal, vf, nf)
                    new += kept
                    rejected += rej
                self.db.log_agent(self.run_id, cid, "analyst", res.provider, res.model, True, res.latency_ms, res.tokens,
                                  rejected - r0)

        # 3. Writer: only for leads worth a first email
        f = fit.score(dict(c), obs + new, self.cfg)
        if f["tier"] in self.ac.get("write_for_tiers", ["A", "B"]) and (org in ("manufacturer", "both")):
            facts = [f"- {o['signal'].replace('AGENT_', '').lower()}: {o['value']}" for o in new if o["signal"] != "AGENT_ORG_TYPE"]
            facts += [f"- metal on site: {o['value']}" for o in sig("METAL")][:6]
            facts += [f"- quantity: {o['value']}" for o in sig("QUANTITY")][:3]
            biz = self.cfg["business"]
            user = (f"OUR BUSINESS: {biz['name']}, supplier of {', '.join(biz['sells'])} in {biz.get('region', 'India')}.\n"
                    f"PROSPECT: {c['name'] or c['domain']} ({c['website']})\nVERIFIED FACTS:\n" + "\n".join(facts[:20]))
            res = self._call("writer", "large", user, cid, max_tokens=600)
            if res and res.data and res.data.get("body"):
                new.append({"signal": "AGENT_OUTREACH", "value": json.dumps({"subject": res.data.get("subject", ""),
                            "body": res.data["body"]}, ensure_ascii=False), "source_url": "", "evidence": "draft, not sent"})
                self.db.log_agent(self.run_id, cid, "writer", res.provider, res.model, True, res.latency_ms, res.tokens)

        if self._failed:
            # a model call failed (rate limit, retired model, outage): store nothing, retry next run
            self.stats["agent_retry_later"] = self.stats.get("agent_retry_later", 0) + 1
            log.info("agents %-30s a call failed; will retry next run", c["domain"])
            return
        self.db.add_observations(cid, prun, new)
        self.db.mark_agents_done(cid, prun)
        self.stats["agent_companies"] += 1
        self.stats["agent_facts"] += len(new)
        self.stats["agent_rejected"] += rejected
        log.info("agents %-30s org=%s facts=%d rejected=%d", c["domain"], org, len(new), rejected)

    def run_signal(self, s) -> None:
        text = s["digest"] or f"{s['title']}\n{s['snippet']}"
        digest = f"### PAGE {s['url']}\n{text}"
        res = self._call("scout", "small", f"PAGE TEXT:\n{text[:6000]}", None, max_tokens=700)
        out: dict = {}
        rejected = 0
        if res and res.data:
            d = res.data
            if d.get("is_buyer_request"):
                for key in ("buyer", "deadline", "location"):
                    v = d.get(key)
                    if isinstance(v, dict) and locate(str(v.get("quote", "")), digest):
                        out[key] = v.get("name") or v.get("value")
                    elif v:
                        rejected += 1
                items = []
                for it in d.get("items") or []:
                    if isinstance(it, dict) and locate(str(it.get("quote", "")), digest):
                        items.append({k: it.get(k) for k in ("metal", "spec", "quantity")})
                    else:
                        rejected += 1
                out["items"] = items
            out["is_buyer_request"] = bool(d.get("is_buyer_request"))
            self.db.log_agent(self.run_id, None, "scout", res.provider, res.model, True, res.latency_ms, res.tokens, rejected)
        self.db.update_signal(s["id"], agent=json.dumps(out, ensure_ascii=False), agent_checked=1)
        self.stats["agent_signals"] += 1
        self.stats["agent_rejected"] += rejected

    def run(self, company_limit: int, signal_limit: int) -> None:
        if not self.router.available:
            self.stats["agents"] = "skipped: no model provider configured (set GROQ_API_KEY, GEMINI_API_KEY, ...)"
            return
        self.stats["agents"] = "on: " + ", ".join(f"{r['provider']}({r['small']}|{r['large']})" for r in self.router.roster())
        try:
            for c in self.db.companies_for_agents(company_limit):
                self.run_company(c)
            for s in self.db.signals_for_agents(signal_limit):
                self.run_signal(s)
        except BudgetExceeded as e:
            self.stats["agents_note"] = str(e)


def _vol_text(v: dict) -> str:
    val, unit, per = v.get("value"), str(v.get("unit") or "").strip(), str(v.get("period") or "").strip()
    if val in (None, "", 0):
        return ""
    return f"{val} {unit}" + (f" per {per}" if per else "")


def _vol_kg_month(v: dict) -> float | None:
    try:
        kg = X.to_kg(float(str(v.get("value")).replace(",", "")), str(v.get("unit") or "kg"))
    except (TypeError, ValueError):
        return None
    per = str(v.get("period") or "").lower()
    return round(kg * PERIOD_TO_MONTH.get(per, 1 / 12 if not per else 1), 1)
