"""Lookup API over the packed Tanakh index."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

import numpy as np

from bibcount.books import BOOK_BY_ID
from bibcount.hebrew import PREFIX_CODE_HEBREW, consonants_only
from bibcount.parasha import parasha_by_id
from bibcount.store import (
    FLAG_HAS_PREFIX,
    FLAG_HAS_SUFFIX,
    StringTable,
    read_postings,
    read_string_table,
)

MatchBy = Literal["auto", "surface", "root", "lemma"]


@dataclass
class Neighbor:
    id: int
    surface: str
    surface_id: int
    stem: str
    stem_id: int
    lemma: str
    lemma_id: int


@dataclass
class WordHit:
    id: int
    surface: str
    surface_id: int
    stem: str
    stem_id: int
    lemma: str
    lemma_id: int
    prefix: str
    suffix: str
    has_prefix: bool
    has_suffix: bool
    book: str
    book_he: str
    book_id: int
    chapter: int
    verse: int
    word_in_verse: int
    pasuk: str
    parasha: str
    parasha_he: str
    parasha_id: int
    instance_n: int
    prev: Neighbor | None
    next: Neighbor | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "surface": self.surface,
            "surface_id": self.surface_id,
            "stem": self.stem,
            "stem_id": self.stem_id,
            "lemma": self.lemma,
            "lemma_id": self.lemma_id,
            "prefix": self.prefix,
            "suffix": self.suffix,
            "has_prefix": self.has_prefix,
            "has_suffix": self.has_suffix,
            "book": self.book,
            "book_he": self.book_he,
            "chapter": self.chapter,
            "verse": self.verse,
            "word_in_verse": self.word_in_verse,
            "pasuk": self.pasuk,
            "parasha": self.parasha,
            "parasha_he": self.parasha_he,
            "instance_n": self.instance_n,
            "prev": None
            if self.prev is None
            else {
                "id": self.prev.id,
                "surface": self.prev.surface,
                "surface_id": self.prev.surface_id,
                "stem": self.prev.stem,
                "stem_id": self.prev.stem_id,
                "lemma": self.prev.lemma,
                "lemma_id": self.prev.lemma_id,
            },
            "next": None
            if self.next is None
            else {
                "id": self.next.id,
                "surface": self.next.surface,
                "surface_id": self.next.surface_id,
                "stem": self.next.stem,
                "stem_id": self.next.stem_id,
                "lemma": self.next.lemma,
                "lemma_id": self.next.lemma_id,
            },
        }


class TanakhIndex:
    def __init__(self, parsed_dir: Path):
        self.path = Path(parsed_dir)
        self.occurrences = np.load(self.path / "occurrences.npy", mmap_mode="r")
        self.surfaces = StringTable(read_string_table(self.path / "surfaces"))
        self.consonants = StringTable(read_string_table(self.path / "consonants"))
        self.stems = StringTable(read_string_table(self.path / "stems"))
        self.stem_cons = StringTable(read_string_table(self.path / "stem_cons"))
        self.lemmas = StringTable(read_string_table(self.path / "lemmas"))
        self.prefixes = StringTable(read_string_table(self.path / "prefixes"))
        self.suffixes = StringTable(read_string_table(self.path / "suffixes"))
        self.first_ids = {
            "surface": np.load(self.path / "first_surface.npy", mmap_mode="r"),
            "consonant": np.load(self.path / "first_consonant.npy", mmap_mode="r"),
            "stem": np.load(self.path / "first_stem.npy", mmap_mode="r"),
            "stem_cons": np.load(self.path / "first_stem_cons.npy", mmap_mode="r"),
            "lemma": np.load(self.path / "first_lemma.npy", mmap_mode="r"),
        }
        self.postings = {
            "surface": read_postings(self.path / "surface"),
            "consonant": read_postings(self.path / "consonant"),
            "stem": read_postings(self.path / "stem"),
            "stem_cons": read_postings(self.path / "stem_cons"),
            "lemma": read_postings(self.path / "lemma"),
        }
        self.meta = json.loads((self.path / "meta.json").read_text(encoding="utf-8"))

    @classmethod
    def load(cls, parsed_dir: str | Path) -> "TanakhIndex":
        return cls(Path(parsed_dir))

    def _row(self, occ_id: int):
        if occ_id <= 0 or occ_id > len(self.occurrences):
            return None
        return self.occurrences[occ_id - 1]

    def _neighbor(self, occ_id: int) -> Neighbor | None:
        row = self._row(occ_id)
        if row is None:
            return None
        return Neighbor(
            id=int(row["id"]),
            surface=self.surfaces.get(int(row["surface_id"])),
            surface_id=int(row["surface_id"]),
            stem=self.stems.get(int(row["stem_id"])),
            stem_id=int(row["stem_id"]),
            lemma=self.lemmas.get(int(row["lemma_id"])),
            lemma_id=int(row["lemma_id"]),
        )

    def _ids_for(self, kind: str, key_id: int) -> np.ndarray:
        offsets, ids = self.postings[kind]
        if key_id <= 0 or key_id >= len(offsets) - 1:
            return ids[0:0]
        start = int(offsets[key_id])
        end = int(offsets[key_id + 1])
        return ids[start:end]

    def _resolve(self, word: str, by: MatchBy) -> tuple[str, int]:
        """Return (posting_kind, key_id)."""
        raw = word.strip()
        if not raw:
            return "surface", 0
        cons = consonants_only(raw)
        if by == "lemma" or (by == "auto" and raw[:1].isdigit()):
            return "lemma", self.lemmas.find(raw.replace(" ", ""))
        if by == "surface":
            sid = self.surfaces.find(raw)
            if sid:
                return "surface", sid
            return "consonant", self.consonants.find(cons)
        if by == "root":
            return "lemma", self._lemma_for_root(raw, cons)

        # auto: exact pointed surface, then surface consonants, then dictionary root
        sid = self.surfaces.find(raw)
        if sid:
            return "surface", sid
        cid = self.consonants.find(cons)
        if cid:
            return "consonant", cid
        return "lemma", self._lemma_for_root(raw, cons)

    def _lemma_for_root(self, raw: str, cons: str) -> int:
        """Map a Hebrew spelling to the Strong's lemma of its first stem hit."""
        for kind, key_id in (
            ("stem", self.stems.find(raw)),
            ("stem_cons", self.stem_cons.find(cons)),
            ("consonant", self.consonants.find(cons)),
            ("surface", self.surfaces.find(raw)),
        ):
            if not key_id:
                continue
            ids = self._ids_for(kind, key_id)
            if ids.size:
                return int(self.occurrences[int(ids[0]) - 1]["lemma_id"])
        return 0

    def _filter_ids(
        self,
        ids: np.ndarray,
        with_prefix: bool | None,
        with_suffix: bool | None,
    ) -> np.ndarray:
        if with_prefix is None and with_suffix is None:
            return ids
        if ids.size == 0:
            return ids
        rows = self.occurrences[ids - 1]
        mask = np.ones(len(rows), dtype=bool)
        if with_prefix is not None:
            has_p = (rows["flags"] & FLAG_HAS_PREFIX) != 0
            mask &= has_p if with_prefix else ~has_p
        if with_suffix is not None:
            has_s = (rows["flags"] & FLAG_HAS_SUFFIX) != 0
            mask &= has_s if with_suffix else ~has_s
        return ids[mask]

    def occurrence_ids(
        self,
        word: str,
        *,
        by: MatchBy = "auto",
        with_prefix: bool | None = None,
        with_suffix: bool | None = None,
    ) -> np.ndarray:
        kind, key_id = self._resolve_kind(word, by, with_prefix, with_suffix)
        return self._filter_ids(self._ids_for(kind, key_id), with_prefix, with_suffix)

    def _resolve_kind(
        self,
        word: str,
        by: MatchBy,
        with_prefix: bool | None,
        with_suffix: bool | None,
    ) -> tuple[str, int]:
        kind, key_id = self._resolve(word, by)
        if with_prefix is not None or with_suffix is not None:
            if kind in {"surface", "consonant"}:
                return self._resolve(word, "root")
        return kind, key_id

    def count(
        self,
        word: str,
        *,
        by: MatchBy = "auto",
        with_prefix: bool | None = None,
        with_suffix: bool | None = None,
    ) -> int:
        return int(self.occurrence_ids(word, by=by, with_prefix=with_prefix, with_suffix=with_suffix).size)

    def first(
        self,
        word: str,
        *,
        by: MatchBy = "auto",
        with_prefix: bool | None = None,
        with_suffix: bool | None = None,
    ) -> WordHit | None:
        if with_prefix is None and with_suffix is None:
            kind, key_id = self._resolve(word, by)
            first_map = self.first_ids.get(kind)
            if first_map is not None and 0 < key_id < len(first_map):
                occ_id = int(first_map[key_id])
                if occ_id:
                    return self.hit(occ_id, instance_n=1)
            return None
        ids = self.occurrence_ids(word, by=by, with_prefix=with_prefix, with_suffix=with_suffix)
        if ids.size == 0:
            return None
        return self.hit(int(ids[0]), instance_n=1)

    def find(
        self,
        word: str,
        *,
        by: MatchBy = "auto",
        with_prefix: bool | None = None,
        with_suffix: bool | None = None,
        limit: int | None = None,
    ) -> Iterator[WordHit]:
        ids = self.occurrence_ids(word, by=by, with_prefix=with_prefix, with_suffix=with_suffix)
        if limit is not None:
            ids = ids[:limit]
        for n, occ_id in enumerate(ids, start=1):
            yield self.hit(int(occ_id), instance_n=n)

    def hit(self, occ_id: int, instance_n: int = 0) -> WordHit | None:
        row = self._row(occ_id)
        if row is None:
            return None
        book = BOOK_BY_ID[int(row["book_id"])]
        parasha = parasha_by_id(int(row["parasha_id"]))
        prefix_codes = self.prefixes.get(int(row["prefix_id"]))
        prefix_he = "".join(PREFIX_CODE_HEBREW.get(code, code) for code in prefix_codes.split("+") if code)
        return WordHit(
            id=int(row["id"]),
            surface=self.surfaces.get(int(row["surface_id"])),
            surface_id=int(row["surface_id"]),
            stem=self.stems.get(int(row["stem_id"])),
            stem_id=int(row["stem_id"]),
            lemma=self.lemmas.get(int(row["lemma_id"])),
            lemma_id=int(row["lemma_id"]),
            prefix=prefix_he,
            suffix=self.suffixes.get(int(row["suffix_id"])),
            has_prefix=bool(int(row["flags"]) & int(FLAG_HAS_PREFIX)),
            has_suffix=bool(int(row["flags"]) & int(FLAG_HAS_SUFFIX)),
            book=book.en,
            book_he=book.he,
            book_id=book.id,
            chapter=int(row["chapter"]),
            verse=int(row["verse"]),
            word_in_verse=int(row["word_in_verse"]),
            pasuk=f"{book.en} {int(row['chapter'])}:{int(row['verse'])}",
            parasha=parasha.en if parasha else "",
            parasha_he=parasha.he if parasha else "",
            parasha_id=int(row["parasha_id"]),
            instance_n=instance_n,
            prev=self._neighbor(int(row["prev_id"])),
            next=self._neighbor(int(row["next_id"])),
        )
