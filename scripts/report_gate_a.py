#!/usr/bin/env python3
"""Emit the read-only Gate-A coverage report as deterministic JSON."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gbdn.gate_a_report import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(["--repository-root", str(ROOT), *sys.argv[1:]]))
