"""The daily engine. One run = DISCOVER -> PROFILE -> SIGNALS -> EXPORT, each stage isolated.

- A file lock prevents two runs at once (web button + scheduler); stale locks (>6h) are broken.
- Each stage's failure is recorded on the run and the next stage still runs ("a failure is an
  observation, not silence"). Run status: ok | partial | failed.
- PROFILE and SIGNALS *query* the DB for work, so an interrupted run resumes next time.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from . import export, profile, sources
from .config import path
from . import extract as X
from .db import DB

log = logging.getLogger("metalscout")
STAGES = ("discover", "profile", "signals", "agents", "redo-agents", "export")


def parse_stages(s: str) -> tuple[str, ...]:
    """Comma-separated stage list -> tuple. Raises ValueError on an empty list or any unknown stage."""
    out = tuple(x.strip() for x in str(s).split(",") if x.strip())
    bad = [x for x in out if x not in STAGES]
    if bad or not out:
        raise ValueError(f"unknown stage(s): {', '.join(bad)}" if bad else "no stages given")
    return out


def setup_logging(cfg: dict) -> None:
    if log.handlers:
        return
    log.setLevel(logging.INFO)
    fh = RotatingFileHandler(path(cfg, "logs", "metalscout.log"), maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)


def open_db(cfg: dict) -> DB:
    return DB(str(path(cfg, "data", "metalscout.db")))


class Lock:
    def __init__(self, cfg: dict):
        self.p = path(cfg, "data", "engine.lock")

    def __enter__(self):
        if self.p.exists():
            try:
                info = json.loads(self.p.read_text())
            except ValueError:
                info = {"t": 0}
            if time.time() - info.get("t", 0) < 6 * 3600:
                raise RuntimeError(f"another run is in progress (pid {info.get('pid')})")
        self.p.write_text(json.dumps({"pid": os.getpid(), "t": time.time()}))
        return self

    def __exit__(self, *exc):
        self.p.unlink(missing_ok=True)


def is_running(cfg: dict, db: DB | None = None) -> bool:
    """A run is active if this machine holds the lock file, or the shared DB has a recent 'running' run
    (that's how the Vercel dashboard sees a run happening in GitHub Actions)."""
    p = path(cfg, "data", "engine.lock")
    if p.exists():
        try:
            if time.time() - json.loads(p.read_text()).get("t", 0) < 6 * 3600:
                return True
        except ValueError:
            pass
    try:
        return bool((db or open_db(cfg)).running_run())
    except Exception:
        return False


async def stage_profile(db: DB, cfg: dict, run_id: str, stats: dict, errors: list[str], limit: int | None = None) -> None:
    from .browser import Surfer  # Playwright only needed by the engine, not by the web dashboard
    from .agents.ground import build_digest
    pc = cfg["pipeline"]
    todo = db.companies_needing_profile(limit or pc["profile_per_run"], pc["reprofile_after_days"])
    stats.update(profiled=0, profile_failed=0, profile_queue=len(todo))
    if not todo:
        return
    sem = asyncio.Semaphore(cfg["crawl"]["concurrency"])
    async with Surfer(cfg) as s:
        async def one(c):
            async with sem:
                try:
                    pages = await s.crawl(c["website"])
                    name, status, obs = profile.observe(c["website"], pages)
                    db.save_profile(c["id"], run_id, name, status, obs, "" if status == "profiled" else status)
                    if status == "profiled":
                        db.save_digest(c["id"], build_digest(pages))
                    stats["profiled" if status == "profiled" else "profile_failed"] += 1
                    log.info("profiled %-35s %-10s %d obs", c["domain"], status, len(obs))
                except Exception as e:
                    stats["profile_failed"] += 1
                    db.save_profile(c["id"], run_id, "", "failed", [], str(e)[:300])
                    errors.append(f"profile {c['domain']}: {e}")
                db.update_run_stats(run_id, stats)
        await asyncio.gather(*(one(c) for c in todo))


async def stage_signals(db: DB, cfg: dict, stats: dict, errors: list[str]) -> None:
    from .browser import Surfer
    todo = db.signals_to_open(cfg["pipeline"]["signals_per_run"])
    stats.update(signals_opened=0)
    if not todo:
        return
    async with Surfer(cfg) as s:
        for r in todo:
            try:
                page = await s.open(r["url"])
            except Exception as e:
                errors.append(f"signal {r['url']}: {e}")
                page = None
            if not page:
                db.update_signal(r["id"], opened=-1)
                continue
            text = page["text"] + " " + (r["snippet"] or "")
            db.update_signal(r["id"], opened=1, metals=list(X.metals_in(text)), quantity=[q["value"] for q in X.quantities(text, strict=False)],
                             emails=X.emails(page["text"], page["html"])[:6], phones=X.phones(page["text"])[:6],
                             intent=len(X.classify(text)["intent_hits"]), digest=page["text"][:6000])
            stats["signals_opened"] += 1


def run(cfg: dict, trigger: str = "manual", stages=("discover", "profile", "signals", "agents", "export"), profile_limit: int | None = None) -> dict:
    setup_logging(cfg)
    db = open_db(cfg)
    with Lock(cfg):
        other = db.running_run()
        if other:
            raise RuntimeError(f"run {other['id']} ({other['trigger']}) is still in progress")
        rid = db.start_run(trigger)
        stats: dict = {}
        errors: list[str] = []
        failed = 0
        log.info("run %s started (%s)", rid, trigger)
        for st in stages:
            try:
                if st == "discover":
                    sources.discover(db, cfg, rid, stats, errors)
                elif st == "profile":
                    asyncio.run(stage_profile(db, cfg, rid, stats, errors, profile_limit))
                elif st == "signals":
                    asyncio.run(stage_signals(db, cfg, stats, errors))
                elif st == "redo-agents":
                    db.reset_agents()
                    stats["agents_reset"] = True
                elif st == "agents":
                    from .agents.crew import Crew
                    ac = cfg.get("agents", {})
                    if ac.get("enabled", True):
                        Crew(db, cfg, rid, stats, errors).run(ac.get("companies_per_run", 40), ac.get("signals_per_run", 30))
                    else:
                        stats["agents"] = "disabled in config"
                elif st == "export":
                    stats["export"] = export.daily(db, cfg)
            except Exception as e:
                failed += 1
                errors.append(f"{st}: {e}")
                log.exception("stage %s failed", st)
            db.update_run_stats(rid, stats)
        status = "ok" if not errors else ("failed" if failed == len(stages) else "partial")
        db.finish_run(rid, status, stats, errors)
        log.info("run %s %s: %s", rid, status, stats)
        return {"id": rid, "status": status, "stats": stats, "errors": errors}
