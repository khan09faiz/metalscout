"""metalscout CLI.

  python -m metalscout init                 create metalscout.yaml from the example
  python -m metalscout run                  one full daily run (discover, profile, signals, export)
  python -m metalscout run --stages profile,export --profile-limit 10
  python -m metalscout serve                dashboard at http://localhost:8000 (+ in-app daily scheduler)
  python -m metalscout add URL [URL...]     queue company sites to profile
  python -m metalscout import FILE.csv      import tender/trade-show/marketplace exports
  python -m metalscout export [--out F]     write the Excel sheet now
  python -m metalscout status               counts, last run, next run
  python -m metalscout schedule install|remove|show
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import config as C


def main(argv=None):
    p = argparse.ArgumentParser(prog="metalscout")
    p.add_argument("--config", help="path to metalscout.yaml (default: ./metalscout.yaml)")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("init")
    r = s.add_parser("run")
    r.add_argument("--trigger", default="manual")
    r.add_argument("--stages", default="discover,profile,signals,agents,export")
    r.add_argument("--profile-limit", type=int)
    sv = s.add_parser("serve")
    sv.add_argument("--no-scheduler", action="store_true")
    sv.add_argument("--port", type=int)
    a = s.add_parser("add")
    a.add_argument("urls", nargs="+")
    i = s.add_parser("import")
    i.add_argument("file")
    e = s.add_parser("export")
    e.add_argument("--out")
    s.add_parser("status")
    sc = s.add_parser("schedule")
    sc.add_argument("action", choices=["install", "remove", "show"])
    args = p.parse_args(argv)

    if args.cmd == "init":
        dst = Path(args.config or "metalscout.yaml")
        src = Path(__file__).resolve().parent.parent / "metalscout.example.yaml"
        if dst.exists():
            print(f"{dst} already exists")
        else:
            shutil.copy(src, dst)
            print(f"created {dst}; edit metals, industries, clusters, then run: python -m metalscout run")
        return

    cfg = C.load(args.config)
    if args.cmd == "run":
        from .engine import run
        res = run(cfg, args.trigger, tuple(x.strip() for x in args.stages.split(",") if x.strip()), args.profile_limit)
        print(json.dumps(res, indent=2, default=str))
        sys.exit(0 if res["status"] != "failed" else 1)
    if args.cmd == "serve":
        from .server import serve
        if args.port:
            cfg["web"]["port"] = args.port
        serve(cfg, heartbeat=not args.no_scheduler)
    if args.cmd == "add":
        from .engine import open_db
        from .net import reg_domain
        db = open_db(cfg)
        n = sum(db.add_company(reg_domain(u), u if u.startswith("http") else "https://" + u, "manual", "manual") for u in args.urls)
        print(f"queued {n} new site(s)")
    if args.cmd == "import":
        from .engine import open_db
        from .sources import import_csv
        c, sg = import_csv(open_db(cfg), cfg, args.file)
        print(f"imported {c} companies, {sg} buyer signals")
    if args.cmd == "export":
        from .engine import open_db
        from . import export
        if args.out:
            print(export.write_xlsx(open_db(cfg), cfg, Path(args.out)))
        else:
            print(json.dumps(export.daily(open_db(cfg), cfg), indent=2))
    if args.cmd == "status":
        from .engine import open_db
        from .server import status
        print(json.dumps(status(cfg, open_db(cfg)), indent=2, default=str))
    if args.cmd == "schedule":
        from . import scheduler
        if args.action == "show":
            print(scheduler.windows_task_script(cfg) if sys.platform == "win32" else scheduler.cron_line(cfg))
        elif sys.platform != "win32":
            print("Add this line with `crontab -e`:\n" + scheduler.cron_line(cfg))
        else:
            print(scheduler.install_windows_task(cfg) if args.action == "install" else scheduler.remove_windows_task())


if __name__ == "__main__":
    main()
