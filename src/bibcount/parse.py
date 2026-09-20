"""Parse OSHB OSIS XML into interned occurrence rows."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np

from bibcount.books import BOOK_BY_OSIS, BOOKS
from bibcount.hebrew import consonants_only, split_affixes, strip_slashes
from bibcount.parasha import parasha_id_for
from bibcount.store import FLAG_HAS_PREFIX, FLAG_HAS_SUFFIX, FLAG_IS_QERE, OCCURRENCE_DTYPE

W_TAG = "{http://www.bibletechnologies.net/2003/OSIS/namespace}w"
NOTE_TAG = "{http://www.bibletechnologies.net/2003/OSIS/namespace}note"
RDG_TAG = "{http://www.bibletechnologies.net/2003/OSIS/namespace}rdg"
VERSE_TAG = "{http://www.bibletechnologies.net/2003/OSIS/namespace}verse"


class Interner:
    def __init__(self) -> None:
        self._id = {"": 0}
        self._str = [""]

    def intern(self, value: str) -> int:
        existing = self._id.get(value)
        if existing is not None:
            return existing
        idx = len(self._str)
        self._id[value] = idx
        self._str.append(value)
        return idx

    @property
    def strings(self) -> list[str]:
        return self._str


def _verse_words(verse: ET.Element) -> list[tuple[ET.Element, bool]]:
    """Yield (w, is_qere), skipping ketiv so the read form is counted once."""
    words: list[tuple[ET.Element, bool]] = []
    for child in verse:
        if child.tag == W_TAG:
            if child.get("type") == "x-ketiv":
                continue
            words.append((child, False))
        elif child.tag == NOTE_TAG:
            for rdg in child:
                if rdg.tag == RDG_TAG and rdg.get("type") == "x-qere":
                    for inner in rdg:
                        if inner.tag == W_TAG:
                            words.append((inner, True))
    return words


def _parse_osis_id(osis_id: str) -> tuple[str, int, int]:
    # "Gen.1.1" or rarely "1Sam.2.3"
    parts = osis_id.split(".")
    if len(parts) < 3:
        raise ValueError(f"Unexpected osisID: {osis_id}")
    verse = int(parts[-1])
    chapter = int(parts[-2])
    book = ".".join(parts[:-2]) if len(parts) > 3 else parts[0]
    return book, chapter, verse


def parse_oshb(raw_dir: Path) -> dict:
    surfaces = Interner()
    consonants = Interner()
    stems = Interner()
    stem_cons = Interner()
    lemmas = Interner()
    prefixes = Interner()
    suffixes = Interner()

    rows: list[tuple] = []
    surface_post: dict[int, list[int]] = defaultdict(list)
    consonant_post: dict[int, list[int]] = defaultdict(list)
    stem_post: dict[int, list[int]] = defaultdict(list)
    stem_cons_post: dict[int, list[int]] = defaultdict(list)
    lemma_post: dict[int, list[int]] = defaultdict(list)
    first_surface: dict[int, int] = {}
    first_consonant: dict[int, int] = {}
    first_stem: dict[int, int] = {}
    first_stem_cons: dict[int, int] = {}
    first_lemma: dict[int, int] = {}

    occ_id = 0
    for book in BOOKS:
        path = raw_dir / book.filename
        print(f"Parsing {book.en}...")
        tree = ET.parse(path)
        root = tree.getroot()
        for verse in root.iter(VERSE_TAG):
            osis_id = verse.get("osisID")
            if not osis_id:
                continue
            osis_book, chapter, verse_n = _parse_osis_id(osis_id)
            book_meta = BOOK_BY_OSIS.get(osis_book, book)
            parasha_id = parasha_id_for(book_meta.id, chapter, verse_n)
            for word_i, (w_el, is_qere) in enumerate(_verse_words(verse), start=1):
                raw_text = "".join(w_el.itertext()).strip()
                if not raw_text:
                    continue
                lemma = w_el.get("lemma") or ""
                morph = w_el.get("morph") or ""
                parts = split_affixes(raw_text, lemma, morph)
                surface = strip_slashes(raw_text)
                stem_surface = str(parts["stem_surface"])
                suffix_surface = str(parts["suffix_surface"])
                surface_cons = consonants_only(surface)
                stem_c = consonants_only(stem_surface)

                sid = surfaces.intern(surface)
                cid = consonants.intern(surface_cons)
                stid = stems.intern(stem_surface)
                scid = stem_cons.intern(stem_c)
                lid = lemmas.intern(str(parts["stem_lemma"]))
                pid = prefixes.intern(str(parts["prefix_codes"]) if parts["has_prefix"] else "")
                sufid = suffixes.intern(suffix_surface)

                occ_id += 1
                flags = 0
                if parts["has_prefix"]:
                    flags |= int(FLAG_HAS_PREFIX)
                if parts["has_suffix"]:
                    flags |= int(FLAG_HAS_SUFFIX)
                if is_qere:
                    flags |= int(FLAG_IS_QERE)

                rows.append(
                    (
                        occ_id,
                        sid,
                        cid,
                        stid,
                        scid,
                        lid,
                        pid,
                        sufid,
                        book_meta.id,
                        chapter,
                        verse_n,
                        word_i,
                        parasha_id,
                        flags,
                        occ_id - 1 if occ_id > 1 else 0,
                        0,
                    )
                )
                surface_post[sid].append(occ_id)
                consonant_post[cid].append(occ_id)
                stem_post[stid].append(occ_id)
                stem_cons_post[scid].append(occ_id)
                lemma_post[lid].append(occ_id)
                first_surface.setdefault(sid, occ_id)
                first_consonant.setdefault(cid, occ_id)
                first_stem.setdefault(stid, occ_id)
                first_stem_cons.setdefault(scid, occ_id)
                first_lemma.setdefault(lid, occ_id)

    occurrences = np.array(rows, dtype=OCCURRENCE_DTYPE)
    if len(occurrences) > 1:
        occurrences["next_id"][:-1] = occurrences["id"][1:]

    def first_array(interner: Interner, first_map: dict[int, int]) -> np.ndarray:
        arr = np.zeros(len(interner.strings), dtype=np.uint32)
        for key, value in first_map.items():
            arr[key] = value
        return arr

    def posting_lists(interner: Interner, post: dict[int, list[int]]) -> list[list[int]]:
        lists: list[list[int]] = [[] for _ in range(len(interner.strings))]
        for key, values in post.items():
            lists[key] = values
        return lists

    return {
        "occurrences": occurrences,
        "surfaces": surfaces.strings,
        "consonants": consonants.strings,
        "stems": stems.strings,
        "stem_cons": stem_cons.strings,
        "lemmas": lemmas.strings,
        "prefixes": prefixes.strings,
        "suffixes": suffixes.strings,
        "surface_postings": posting_lists(surfaces, surface_post),
        "consonant_postings": posting_lists(consonants, consonant_post),
        "stem_postings": posting_lists(stems, stem_post),
        "stem_cons_postings": posting_lists(stem_cons, stem_cons_post),
        "lemma_postings": posting_lists(lemmas, lemma_post),
        "first_surface": first_array(surfaces, first_surface),
        "first_consonant": first_array(consonants, first_consonant),
        "first_stem": first_array(stems, first_stem),
        "first_stem_cons": first_array(stem_cons, first_stem_cons),
        "first_lemma": first_array(lemmas, first_lemma),
        "meta": {
            "source": "Open Scriptures Hebrew Bible (WLC + morphology)",
            "source_url": "https://github.com/openscriptures/morphhb",
            "license": "WLC text: public domain. Morphology/lemmas: CC BY 4.0 (credit OSHB).",
            "word_count": int(len(occurrences)),
            "unique_surfaces": len(surfaces.strings) - 1,
            "unique_stems": len(stems.strings) - 1,
            "unique_lemmas": len(lemmas.strings) - 1,
            "bytes_per_occurrence": int(OCCURRENCE_DTYPE.itemsize),
        },
    }
