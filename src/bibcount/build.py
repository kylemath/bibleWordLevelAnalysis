"""Download OSHB and write the packed index."""

from __future__ import annotations

from pathlib import Path

from bibcount.download import download_oshb
from bibcount.parse import parse_oshb
from bibcount.paths import parsed_dir as default_parsed_dir
from bibcount.paths import raw_dir as default_raw_dir
from bibcount.store import save_index


def build_index(raw_dir: Path | None = None, parsed_dir: Path | None = None) -> Path:
    raw = raw_dir or default_raw_dir()
    dest = parsed_dir or default_parsed_dir()
    download_oshb(raw)
    payload = parse_oshb(raw)
    save_index(dest, payload)
    print(
        f"Indexed {payload['meta']['word_count']:,} words "
        f"({payload['meta']['unique_stems']:,} stems, "
        f"{payload['meta']['unique_lemmas']:,} lemmas) -> {dest}"
    )
    return dest
