"""Command-line interface."""

from __future__ import annotations


import argparse
import json
import sys

from bibcount.build import build_index
from bibcount.paths import parsed_dir
from bibcount.query import TanakhIndex


def _index() -> TanakhIndex:
    dest = parsed_dir()
    if not (dest / "occurrences.npy").exists():
        print("No index yet. Run: python -m bibcount build", file=sys.stderr)
        sys.exit(2)
    return TanakhIndex.load(dest)


def _print_hit(hit) -> None:
    print(json.dumps(hit.to_dict(), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hebrew Bible word index")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("build", help="Download OSHB and build the packed index")
    first = sub.add_parser("first", help="Show the first instance of a word or root")
    first.add_argument("word")
    first.add_argument("--by", choices=("auto", "surface", "root", "lemma"), default="auto")
    first.add_argument("--with-prefix", dest="with_prefix", action="store_true", default=None)
    first.add_argument("--no-prefix", dest="with_prefix", action="store_false")
    first.add_argument("--with-suffix", dest="with_suffix", action="store_true", default=None)
    first.add_argument("--no-suffix", dest="with_suffix", action="store_false")

    count = sub.add_parser("count", help="Count instances of a word or root")
    count.add_argument("word")
    count.add_argument("--by", choices=("auto", "surface", "root", "lemma"), default="auto")
    count.add_argument("--with-prefix", dest="with_prefix", action="store_true", default=None)
    count.add_argument("--no-prefix", dest="with_prefix", action="store_false")
    count.add_argument("--with-suffix", dest="with_suffix", action="store_true", default=None)
    count.add_argument("--no-suffix", dest="with_suffix", action="store_false")

    find = sub.add_parser("find", help="List instances")
    find.add_argument("word")
    find.add_argument("--by", choices=("auto", "surface", "root", "lemma"), default="auto")
    find.add_argument("--limit", type=int, default=10)
    find.add_argument("--with-prefix", dest="with_prefix", action="store_true", default=None)
    find.add_argument("--no-prefix", dest="with_prefix", action="store_false")
    find.add_argument("--with-suffix", dest="with_suffix", action="store_true", default=None)
    find.add_argument("--no-suffix", dest="with_suffix", action="store_false")

    show = sub.add_parser("show", help="Show a word by occurrence ID")
    show.add_argument("id", type=int)

    plot = sub.add_parser("plot", help="Scree plot: each word column, all Torah pesukim marked")
    plot.add_argument("-o", "--output", default=None, help="PNG path (default data/parsed/word_scree.png)")
    plot.add_argument("--width", type=int, default=4200)
    plot.add_argument("--dpi", type=int, default=160)

    names = sub.add_parser("names", help="Image of Torah roots with Five-Book counts")
    names.add_argument("-o", "--output", default=None, help="PNG path")
    names.add_argument("--columns", type=int, default=10)
    names.add_argument("--dpi", type=int, default=140)
    names.add_argument(
        "--by",
        choices=("first", "frequency"),
        default="first",
        help="first = order of first appearance; frequency = most common first",
    )

    bars = sub.add_parser("bars", help="Bar graph of prefix-stripped Torah word frequencies")
    bars.add_argument("-o", "--output", default=None, help="PNG path (default data/parsed/word_freq_bars.png)")
    bars.add_argument("--dpi", type=int, default=160)

    args = parser.parse_args(argv)
    if args.cmd == "build":
        build_index()
        return 0

    idx = _index()
    if args.cmd == "plot":
        from pathlib import Path

        from bibcount.visualize import plot_word_scree

        plot_word_scree(
            idx,
            output=Path(args.output) if args.output else None,
            width=args.width,
            dpi=args.dpi,
        )
        return 0
    if args.cmd == "names":
        from pathlib import Path

        from bibcount.visualize import plot_word_names

        plot_word_names(
            idx,
            output=Path(args.output) if args.output else None,
            columns=args.columns,
            dpi=args.dpi,
            by=args.by,
        )
        return 0
    if args.cmd == "bars":
        from pathlib import Path

        from bibcount.visualize import plot_word_freq_bars

        plot_word_freq_bars(
            idx,
            output=Path(args.output) if args.output else None,
            dpi=args.dpi,
        )
        return 0
    if args.cmd == "show":
        hit = idx.hit(args.id, instance_n=0)
        if hit is None:
            print("Not found", file=sys.stderr)
            return 1
        _print_hit(hit)
        return 0

    kwargs = {
        "by": args.by,
        "with_prefix": args.with_prefix,
        "with_suffix": args.with_suffix,
    }
    if args.cmd == "count":
        total = idx.count(args.word, **kwargs)
        first_hit = idx.first(args.word, **kwargs)
        print(json.dumps(
            {
                "word": args.word,
                "count": total,
                "subsequent": max(total - 1, 0),
                "first_id": None if first_hit is None else first_hit.id,
                "first_pasuk": None if first_hit is None else first_hit.pasuk,
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if args.cmd == "first":
        hit = idx.first(args.word, **kwargs)
        if hit is None:
            print("Not found", file=sys.stderr)
            return 1
        _print_hit(hit)
        return 0
    if args.cmd == "find":
        rows = [h.to_dict() for h in idx.find(args.word, limit=args.limit, **kwargs)]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    return 1
