"""Torah-only first-appearance plot: each root is a column, pesukim are rows."""

from __future__ import annotations

from pathlib import Path

from bidi.algorithm import get_display

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch, Rectangle

from bibcount.books import BOOK_BY_ID
from bibcount.hebrew import consonants_only
from bibcount.paths import data_root
from bibcount.query import TanakhIndex

TORAH_BOOKS = 5
BOOK_BANDS = (
    (1, "#f4ecd9"),
    (2, "#dde6f2"),
    (3, "#eadde4"),
    (4, "#dce8dd"),
    (5, "#efe4d6"),
)


def _prefix_stripped_ids(index: TanakhIndex, rows) -> tuple[np.ndarray, list[str]]:
    """Consonants after removing ו/ה/ל/ב/כ/מ/ש prefixes; suffixes and conjugations stay."""
    intern = {"": 0}
    strings = [""]
    ids = np.empty(len(rows), dtype=np.int32)
    for i, (sid, sufid) in enumerate(zip(rows["stem_cons_id"], rows["suffix_id"])):
        key = index.stem_cons.get(int(sid)) + consonants_only(index.suffixes.get(int(sufid)))
        existing = intern.get(key)
        if existing is None:
            existing = len(strings)
            intern[key] = existing
            strings.append(key)
        ids[i] = existing
    return ids, strings


def _torah_forms(index: TanakhIndex, by: str = "frequency") -> tuple[list[str], np.ndarray, np.ndarray]:
    """Prefix-stripped Torah forms, names/counts/first-book, ordered by first appearance or frequency."""
    occ = index.occurrences
    rows = occ[np.asarray(occ["book_id"]) <= TORAH_BOOKS]
    word_ids, strings = _prefix_stripped_ids(index, rows)
    book_ids = np.asarray(rows["book_id"])
    uniques, first_at, counts = np.unique(word_ids, return_index=True, return_counts=True)
    if by == "frequency":
        order = np.lexsort((first_at, -counts.astype(np.int64)))
    else:
        order = np.argsort(first_at, kind="mergesort")
    form_ids = uniques[order]
    names = [strings[int(fid)] or "—" for fid in form_ids]
    return names, counts[order], book_ids[first_at[order]]


def _pasuk_index(book_id: np.ndarray, chapter: np.ndarray, verse: np.ndarray) -> np.ndarray:
    key = book_id.astype(np.int64) * 1_000_000 + chapter.astype(np.int64) * 1_000 + verse.astype(np.int64)
    new_pasuk = np.empty(len(key), dtype=bool)
    new_pasuk[0] = True
    new_pasuk[1:] = key[1:] != key[:-1]
    return np.cumsum(new_pasuk) - 1


def plot_word_scree(
    index: TanakhIndex,
    output: Path | None = None,
    width: int = 4200,
    dpi: int = 170,
    **_ignored,
) -> Path:
    """
    Five Books only.

    X = distinct prefix-stripped forms, left → right in first-appearance order.
    Y = pasuk, Genesis at the top through Deuteronomy at the bottom.
    Prefixes (ו, ה, ל, ב, כ, מ, ש) are removed; suffixes and conjugations stay.
    """
    occ = index.occurrences
    torah = np.asarray(occ["book_id"]) <= TORAH_BOOKS
    rows = occ[torah]
    word_ids, _ = _prefix_stripped_ids(index, rows)
    book_ids = np.asarray(rows["book_id"])
    pasuk_y = _pasuk_index(
        book_ids,
        np.asarray(rows["chapter"]),
        np.asarray(rows["verse"]),
    )
    n_pasuk = int(pasuk_y[-1]) + 1
    n_hits = len(word_ids)

    uniques, first_at = np.unique(word_ids, return_index=True)
    appear_order = np.argsort(first_at, kind="mergesort")
    form_ids = uniques[appear_order]
    n_roots = len(form_ids)

    col_of = np.full(int(word_ids.max()) + 1, -1, dtype=np.int32)
    col_of[form_ids] = np.arange(n_roots, dtype=np.int32)
    cols = col_of[word_ids].astype(np.float64) + 0.5
    first_pasuk = pasuk_y[first_at[appear_order]].astype(np.float64) + 0.5

    book_pasuk_start = {}
    for bid in range(1, TORAH_BOOKS + 1):
        hits = np.flatnonzero(book_ids == bid)
        if len(hits):
            book_pasuk_start[bid] = int(pasuk_y[hits[0]])
    book_pasuk_end = {bid: n_pasuk for bid in book_pasuk_start}
    starts = [book_pasuk_start[b] for b in range(1, TORAH_BOOKS + 1) if b in book_pasuk_start]
    for bid, nxt in zip(range(1, TORAH_BOOKS), starts[1:]):
        if bid in book_pasuk_start:
            book_pasuk_end[bid] = nxt

    dest = output or (data_root() / "parsed" / "word_scree.png")
    dest.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(16.5, 10.4))
    for bid, color in BOOK_BANDS:
        if bid not in book_pasuk_start:
            continue
        ax.add_patch(
            Rectangle(
                (0, book_pasuk_start[bid]),
                n_roots,
                book_pasuk_end[bid] - book_pasuk_start[bid],
                facecolor=color,
                edgecolor="none",
                zorder=0,
            )
        )

    first_pasuk_i = pasuk_y[first_at[appear_order]]
    later = pasuk_y != first_pasuk_i[col_of[word_ids]]
    # Later uses: small dark ticks. First uses are the red line + red dots.
    ax.scatter(
        cols[later],
        pasuk_y[later] + 0.5,
        s=7,
        c="#1a2332",
        alpha=0.16,
        linewidths=0,
        rasterized=True,
        zorder=1,
        label="Later appearances",
    )
    ax.plot(
        np.arange(n_roots) + 0.5,
        first_pasuk,
        color="#c0392b",
        linewidth=1.4,
        zorder=2,
        label="First appearance",
    )
    ax.scatter(
        np.arange(n_roots) + 0.5,
        first_pasuk,
        s=6,
        c="#c0392b",
        linewidths=0,
        rasterized=True,
        zorder=3,
    )

    for bid, y0 in book_pasuk_start.items():
        ax.axhline(y0, color="#7b8794", linewidth=0.7, zorder=2)
        mid = 0.5 * (y0 + book_pasuk_end[bid])
        ax.text(
            n_roots * 0.987,
            mid,
            BOOK_BY_ID[bid].en,
            ha="right",
            va="center",
            fontsize=12,
            color="#334e68",
            zorder=4,
        )

    ax.set_xlim(0, n_roots)
    ax.set_ylim(n_pasuk, 0)
    ax.set_xlabel("Words in order of first appearance   (prefixes stripped; left = Genesis, right = last new form in Deuteronomy)")
    ax.set_ylabel("Pasuk in the Five Books   (Genesis → Deuteronomy)")
    ax.set_title(
        "When each prefix-stripped form is introduced, and where it is used again",
        loc="left",
        fontsize=13,
        pad=10,
    )
    ax.legend(loc="upper right", frameon=True, fancybox=False, framealpha=0.95, fontsize=9)
    handles = [
        Patch(facecolor=color, edgecolor="none", label=BOOK_BY_ID[bid].en)
        for bid, color in BOOK_BANDS
        if bid in book_pasuk_start
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=5,
        frameon=False,
        fontsize=9,
        bbox_to_anchor=(0.55, 0.012),
    )
    fig.text(
        0.07,
        0.012,
        f"{n_roots:,} distinct forms  ·  {n_hits:,} tokens  ·  {n_pasuk:,} pesukim  ·  "
        "Prefixes (ה, ל, ב, ו, כ, מ, ש) stripped; suffixes and conjugations kept. "
        "Above the red line that form has not been used yet.",
        fontsize=8,
        color="#52606d",
    )
    fig.suptitle(
        "Torah word introduction  ·  Open Scriptures Hebrew Bible (WLC)",
        fontsize=14,
        x=0.07,
        ha="left",
        y=0.98,
    )
    fig.subplots_adjust(left=0.07, right=0.98, top=0.90, bottom=0.10)
    fig.savefig(dest, dpi=dpi, facecolor="white")
    plt.close(fig)
    print(f"Wrote {dest}  ({n_roots:,} prefix-stripped forms × {n_pasuk:,} pesukim)")
    return dest


HEBREW_FONT_CANDIDATES = (
    Path("/System/Library/Fonts/SFHebrew.ttf"),
    Path("/System/Library/Fonts/ArialHB.ttc"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
)

# Saturated ink so names stay readable on white.
BOOK_INK = {
    1: "#8a6d1f",
    2: "#234e7a",
    3: "#6b3358",
    4: "#2a5a36",
    5: "#7a4a1e",
}


def _hebrew_font() -> FontProperties:
    for path in HEBREW_FONT_CANDIDATES:
        if path.exists():
            return FontProperties(fname=str(path), size=9)
    return FontProperties(family="Arial Hebrew", size=9)


def plot_word_names(
    index: TanakhIndex,
    output: Path | None = None,
    columns: int = 10,
    dpi: int = 140,
    by: str = "first",
) -> Path:
    """Poster of prefix-stripped Torah words, colored by first book, with counts."""
    if by == "frequency":
        title = "Torah words in order of frequency  (prefixes stripped)"
        blurb = "Read down each column, then right. Prefixes (ו, ה, ל, ב, כ, מ, ש) removed; conjugations and suffixes kept. ×N = Five-Book count. Color = book of first use."
        default_name = "word_names_freq.png"
    else:
        title = "Torah words in order of first appearance  (prefixes stripped)"
        blurb = "Read down each column, then right. Prefixes (ו, ה, ל, ב, כ, מ, ש) removed; conjugations and suffixes kept. ×N = Five-Book count. Color = book of first use."
        default_name = "word_names.png"
    col_w = 1.85
    names, counts, first_book = _torah_forms(index, by=by)
    n_roots = len(names)

    nrows = int(np.ceil(n_roots / columns))
    row_h = 0.24
    fig_w = 0.6 + columns * col_w
    fig_h = 1.35 + nrows * row_h

    he_font = _hebrew_font()
    count_font = FontProperties(family="DejaVu Sans", size=8)
    dest = output or (data_root() / "parsed" / default_name)
    dest.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, columns)
    ax.set_ylim(nrows + 0.2, -0.15)
    ax.axis("off")
    fig.suptitle(
        title,
        fontsize=16,
        x=0.035,
        ha="left",
        y=0.995,
        color="#1a2332",
    )
    fig.text(
        0.035,
        0.988,
        blurb,
        fontsize=9,
        color="#52606d",
        va="top",
    )
    x_legend = 0.035
    for bid, hex_color in BOOK_INK.items():
        fig.text(
            x_legend,
            0.982,
            BOOK_BY_ID[bid].en,
            color=hex_color,
            fontsize=9,
            fontweight="bold",
            va="top",
        )
        x_legend += 0.09

    for col in range(columns):
        ax.axvline(col, color="#e4e7eb", linewidth=0.6, zorder=0)

    for i, (name, count, bid) in enumerate(zip(names, counts, first_book)):
        col = i // nrows
        row = i % nrows
        color = BOOK_INK.get(int(bid), "#1a2332")
        y = row + 0.4
        if row % 2 == 1:
            ax.add_patch(
                Rectangle((col, row), 1, 1, facecolor="#f4f6f8", edgecolor="none", zorder=0)
            )
        ax.text(
            col + 0.62,
            y,
            get_display(name),
            fontproperties=he_font,
            color=color,
            ha="right",
            va="center",
            fontsize=11,
        )
        ax.text(
            col + 0.70,
            y,
            f"×{int(count)}",
            fontproperties=count_font,
            color=color,
            ha="left",
            va="center",
        )

    fig.subplots_adjust(left=0.025, right=0.99, top=0.975, bottom=0.006)
    fig.savefig(dest, dpi=dpi, facecolor="white")
    plt.close(fig)
    print(f"Wrote {dest}  ({n_roots:,} prefix-stripped forms in {by} order)")
    return dest


def plot_word_freq_bars(
    index: TanakhIndex,
    output: Path | None = None,
    dpi: int = 160,
    head: int = 40,
) -> Path:
    """Bar charts of the same prefix-stripped forms as word_names_freq.png."""
    names, counts, first_book = _torah_forms(index, by="frequency")
    n = len(names)
    colors = [BOOK_INK.get(int(bid), "#1a2332") for bid in first_book]
    he_font = _hebrew_font()
    dest = output or (data_root() / "parsed" / "word_freq_bars.png")
    dest.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_head, ax_all) = plt.subplots(
        2,
        1,
        figsize=(16.5, 10.5),
        gridspec_kw={"height_ratios": [1.05, 1.15], "hspace": 0.32},
    )

    k = min(head, n)
    x_head = np.arange(k)
    ax_head.bar(x_head, counts[:k], color=colors[:k], width=0.82, linewidth=0)
    ax_head.set_xticks(x_head)
    ax_head.set_xticklabels(
        [get_display(name) for name in names[:k]],
        fontproperties=he_font,
        fontsize=8.5,
        rotation=90,
    )
    ax_head.set_ylabel("Count in the Five Books")
    ax_head.set_title(f"Most frequent {k} prefix-stripped forms", loc="left", fontsize=12)
    ax_head.set_xlim(-0.7, k - 0.3)
    ax_head.spines["top"].set_visible(False)
    ax_head.spines["right"].set_visible(False)

    x_all = np.arange(n)
    ax_all.bar(x_all, counts, color=colors, width=1.0, linewidth=0, align="edge")
    ax_all.set_yscale("log")
    ax_all.set_xlim(0, n)
    ax_all.set_xlabel(f"Words in frequency order  (1 = most common, {n:,} forms)")
    ax_all.set_ylabel("Count (log scale)")
    ax_all.set_title("Every form from the frequency poster", loc="left", fontsize=12)
    ax_all.spines["top"].set_visible(False)
    ax_all.spines["right"].set_visible(False)

    handles = [
        Patch(facecolor=hex_color, edgecolor="none", label=BOOK_BY_ID[bid].en)
        for bid, hex_color in BOOK_INK.items()
    ]
    ax_all.legend(handles=handles, loc="upper right", frameon=False, title="First appears in")

    fig.suptitle(
        "Torah word frequency  ·  prefixes stripped, suffixes and conjugations kept",
        fontsize=14,
        x=0.06,
        ha="left",
        y=0.98,
    )
    fig.text(
        0.06,
        0.01,
        "Same inventory and order as data/parsed/word_names_freq.png. "
        f"{n:,} forms  ·  {int(counts.sum()):,} tokens in the Five Books.",
        fontsize=8,
        color="#52606d",
    )
    fig.subplots_adjust(left=0.07, right=0.98, top=0.90, bottom=0.08)
    fig.savefig(dest, dpi=dpi, facecolor="white")
    plt.close(fig)
    print(f"Wrote {dest}  ({n:,} bars)")
    return dest
