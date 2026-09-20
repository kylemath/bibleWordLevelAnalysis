"""Columnar, interned, memory-mappable Tanakh word index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

FLAG_HAS_PREFIX = np.uint8(1)
FLAG_HAS_SUFFIX = np.uint8(2)
FLAG_IS_QERE = np.uint8(4)

# Packed occurrence row. IDs are 1-based; 0 means none / empty string.
OCCURRENCE_DTYPE = np.dtype(
    [
        ("id", "<u4"),
        ("surface_id", "<u4"),
        ("consonant_id", "<u4"),
        ("stem_id", "<u4"),
        ("stem_cons_id", "<u4"),
        ("lemma_id", "<u4"),
        ("prefix_id", "<u2"),
        ("suffix_id", "<u2"),
        ("book_id", "<u1"),
        ("chapter", "<u1"),
        ("verse", "<u1"),
        ("word_in_verse", "<u1"),
        ("parasha_id", "<u1"),
        ("flags", "<u1"),
        ("prev_id", "<u4"),
        ("next_id", "<u4"),
    ],
    align=True,
)


def write_string_table(path: Path, strings: list[str]) -> None:
    """UTF-8 blob + uint32 offsets. Index 0 is always the empty string."""
    encoded = [s.encode("utf-8") for s in strings]
    offsets = np.zeros(len(encoded) + 1, dtype=np.uint32)
    pos = 0
    for i, blob in enumerate(encoded):
        offsets[i] = pos
        pos += len(blob)
    offsets[-1] = pos
    payload = b"".join(encoded)
    np.save(path.with_suffix(".off.npy"), offsets, allow_pickle=False)
    path.with_suffix(".bin").write_bytes(payload)


def read_string_table(path: Path) -> tuple[str, ...]:
    offsets = np.load(path.with_suffix(".off.npy"), mmap_mode="r")
    payload = path.with_suffix(".bin").read_bytes()
    return tuple(
        payload[int(offsets[i]) : int(offsets[i + 1])].decode("utf-8") for i in range(len(offsets) - 1)
    )


def write_postings(path: Path, lists: list[list[int]]) -> None:
    """CSR-style inverted lists. lists[0] is unused (id 0)."""
    offsets = np.zeros(len(lists) + 1, dtype=np.uint32)
    pos = 0
    for i, items in enumerate(lists):
        offsets[i] = pos
        pos += len(items)
    offsets[-1] = pos
    flat = np.empty(pos, dtype=np.uint32)
    pos = 0
    for items in lists:
        n = len(items)
        if n:
            flat[pos : pos + n] = items
            pos += n
    np.save(path.with_name(path.name + "_off.npy"), offsets, allow_pickle=False)
    np.save(path.with_name(path.name + "_ids.npy"), flat, allow_pickle=False)


def read_postings(path: Path) -> tuple[np.ndarray, np.ndarray]:
    offsets = np.load(path.with_name(path.name + "_off.npy"), mmap_mode="r")
    ids = np.load(path.with_name(path.name + "_ids.npy"), mmap_mode="r")
    return offsets, ids


def save_index(dest: Path, payload: dict[str, Any]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    np.save(dest / "occurrences.npy", payload["occurrences"], allow_pickle=False)
    for name in ("surfaces", "consonants", "stems", "stem_cons", "lemmas", "prefixes", "suffixes"):
        write_string_table(dest / name, payload[name])
    for name in ("surface", "consonant", "stem", "stem_cons", "lemma"):
        write_postings(dest / name, payload[f"{name}_postings"])
        np.save(dest / f"first_{name}.npy", payload[f"first_{name}"], allow_pickle=False)
    (dest / "meta.json").write_text(
        json.dumps(payload["meta"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


class StringTable:
    def __init__(self, strings: tuple[str, ...]):
        self.strings = strings
        self._index = {s: i for i, s in enumerate(strings) if s}

    def get(self, i: int) -> str:
        if i <= 0 or i >= len(self.strings):
            return ""
        return self.strings[i]

    def find(self, s: str) -> int:
        return self._index.get(s, 0)
