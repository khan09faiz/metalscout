"""The built wheel must contain every subpackage and the agent prompts (non-editable installs)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_wheel_ships_agents_and_prompts(tmp_path):
    pytest.importorskip("setuptools")
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(ROOT / "pyproject.toml", src)
    shutil.copy(ROOT / "README.md", src)
    shutil.copytree(ROOT / "metalscout", src / "metalscout", ignore=shutil.ignore_patterns("__pycache__"))
    dist, site = tmp_path / "dist", tmp_path / "site"
    pip = [sys.executable, "-m", "pip", "--disable-pip-version-check", "-q"]
    subprocess.run([*pip, "wheel", "--no-deps", "--no-build-isolation", "-w", str(dist), str(src)], check=True, cwd=tmp_path)
    [whl] = dist.glob("metalscout-*.whl")
    subprocess.run([*pip, "install", "--no-deps", "--target", str(site), str(whl)], check=True, cwd=tmp_path)

    code = (
        "import metalscout, metalscout.agents.crew as crew, pathlib, sys;"
        f"assert pathlib.Path(metalscout.__file__).is_relative_to({str(site)!r}), metalscout.__file__;"
        "assert '**Sorter**' in crew.prompt('sorter');"
        "assert all(crew.prompt(n) for n in ('analyst', 'writer', 'scout'));"
        "assert (pathlib.Path(metalscout.__file__).parent / 'web' / 'index.html').is_file();"
        "print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env={"PYTHONPATH": str(site), "PATH": "/usr/bin:/bin"},
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr


def test_dashboard_imports_without_engine_deps():
    """Vercel installs requirements.txt only: the server must not import Playwright, selectolax or ddgs."""
    code = (
        "import sys, importlib.abc\n"
        "class Block(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name.split('.')[0] in ('playwright', 'selectolax', 'ddgs'):\n"
        "            raise ImportError('blocked ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "import metalscout.server, metalscout.leads, metalscout.export\n"
        "print('ok')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr
