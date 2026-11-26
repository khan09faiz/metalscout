"""Vercel entry point: the MetalScout dashboard as one Python serverless function.

Vercel's Python runtime serves a BaseHTTPRequestHandler subclass named `handler`. All routes are rewritten
here (vercel.json). Data comes from DATABASE_URL (Neon Postgres); runs are dispatched to GitHub Actions.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("METALSCOUT_CONFIG", str(ROOT / "metalscout.cloud.yaml"))
os.environ.setdefault("METALSCOUT_DATA_DIR", "/tmp/metalscout")  # Vercel's filesystem is read-only except /tmp

from metalscout import config  # noqa: E402
from metalscout.server import make_handler  # noqa: E402

handler = make_handler(config.load())
