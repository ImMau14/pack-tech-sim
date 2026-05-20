from __future__ import annotations

import subprocess
import sys


def start():
    result = subprocess.run(
        [sys.executable, "-m", "pack_tech_sim.main", *sys.argv[1:]]
    )
    sys.exit(result.returncode)


def check():
    try:
        result = subprocess.run([sys.executable, "-m", "pyright", "."])
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("❌ Error: 'pyright' is not installed. Run 'uv add --dev pyright'")
        sys.exit(1)


def lint():
    try:
        result = subprocess.run(["ruff", "check", "."])
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("❌ Error: 'ruff' is not installed.")
        sys.exit(1)


def fix():
    subprocess.run(["ruff", "check", ".", "--fix"])
