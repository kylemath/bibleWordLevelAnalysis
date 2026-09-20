"""Weekly Torah parasha lookup from verse location."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Iterable


@dataclass(frozen=True)
class Parasha:
    id: int
    en: str
    he: str
    book_id: int
    start_chapter: int
    start_verse: int
    end_chapter: int
    end_verse: int


@lru_cache(maxsize=1)
def load_parashot() -> tuple[Parasha, ...]:
    raw = json.loads(files("bibcount.data").joinpath("parashot.json").read_text(encoding="utf-8"))
    return tuple(Parasha(**row) for row in raw)


def _starts(parashot: Iterable[Parasha]) -> dict[int, list[tuple[int, int, int]]]:
    by_book: dict[int, list[tuple[int, int, int]]] = {}
    for p in parashot:
        by_book.setdefault(p.book_id, []).append((p.start_chapter, p.start_verse, p.id))
    for book_id, rows in by_book.items():
        rows.sort()
        by_book[book_id] = rows
    return by_book


@lru_cache(maxsize=1)
def _start_index() -> dict[int, list[tuple[int, int, int]]]:
    return _starts(load_parashot())


def parasha_id_for(book_id: int, chapter: int, verse: int) -> int:
    """Assign by start boundary so WLC/Jewish verse splits cannot leave gaps."""
    rows = _start_index().get(book_id)
    if not rows:
        return 0
    loc = (chapter, verse)
    assigned = 0
    for start_c, start_v, pid in rows:
        if loc >= (start_c, start_v):
            assigned = pid
        else:
            break
    return assigned


def parasha_by_id(pid: int) -> Parasha | None:
    if pid <= 0:
        return None
    for p in load_parashot():
        if p.id == pid:
            return p
    return None
