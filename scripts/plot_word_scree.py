#!/usr/bin/env python3
"""Render the Tanakh word-recurrence / first-use scree plot."""

from __future__ import annotations

import argparse
from pathlib import Path

from bibcount.paths import parsed_dir
from bibcount.query import TanakhIndex
from bibcount.visualize import plot_word_scree


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--width", type=int, default=4200)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()
    dest = parsed_dir()
    if not (dest / "occurrences.npy").exists():
        raise SystemExit("No index yet. Run: python -m bibcount build")
    plot_word_scree(
        TanakhIndex.load(dest),
        output=args.output,
        width=args.width,
        dpi=args.dpi,
    )


if __name__ == "__main__":
    main()
