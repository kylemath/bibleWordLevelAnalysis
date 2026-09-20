"""Data directory resolution."""

from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    env = os.environ.get("BIBCOUNT_DATA")
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[2]
    if (repo / "src" / "bibcount").is_dir():
        return repo / "data"
    return Path.cwd() / "data"


def raw_dir() -> Path:
    return data_root() / "raw"


def parsed_dir() -> Path:
    return data_root() / "parsed"
