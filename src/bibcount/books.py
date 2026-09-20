"""Tanakh book table in Westminster Leningrad Codex / BHS order."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    id: int
    osis: str
    filename: str
    en: str
    he: str


# id is 1-based. Parsing walks this list so occurrence IDs follow WLC order.
BOOKS: tuple[Book, ...] = (
    Book(1, "Gen", "Gen.xml", "Genesis", "בראשית"),
    Book(2, "Exod", "Exod.xml", "Exodus", "שמות"),
    Book(3, "Lev", "Lev.xml", "Leviticus", "ויקרא"),
    Book(4, "Num", "Num.xml", "Numbers", "במדבר"),
    Book(5, "Deut", "Deut.xml", "Deuteronomy", "דברים"),
    Book(6, "Josh", "Josh.xml", "Joshua", "יהושע"),
    Book(7, "Judg", "Judg.xml", "Judges", "שופטים"),
    Book(8, "1Sam", "1Sam.xml", "1 Samuel", "שמואל א"),
    Book(9, "2Sam", "2Sam.xml", "2 Samuel", "שמואל ב"),
    Book(10, "1Kgs", "1Kgs.xml", "1 Kings", "מלכים א"),
    Book(11, "2Kgs", "2Kgs.xml", "2 Kings", "מלכים ב"),
    Book(12, "Isa", "Isa.xml", "Isaiah", "ישעיהו"),
    Book(13, "Jer", "Jer.xml", "Jeremiah", "ירמיהו"),
    Book(14, "Ezek", "Ezek.xml", "Ezekiel", "יחזקאל"),
    Book(15, "Hos", "Hos.xml", "Hosea", "הושע"),
    Book(16, "Joel", "Joel.xml", "Joel", "יואל"),
    Book(17, "Amos", "Amos.xml", "Amos", "עמוס"),
    Book(18, "Obad", "Obad.xml", "Obadiah", "עובדיה"),
    Book(19, "Jonah", "Jonah.xml", "Jonah", "יונה"),
    Book(20, "Mic", "Mic.xml", "Micah", "מיכה"),
    Book(21, "Nah", "Nah.xml", "Nahum", "נחום"),
    Book(22, "Hab", "Hab.xml", "Habakkuk", "חבקוק"),
    Book(23, "Zeph", "Zeph.xml", "Zephaniah", "צפניה"),
    Book(24, "Hag", "Hag.xml", "Haggai", "חגי"),
    Book(25, "Zech", "Zech.xml", "Zechariah", "זכריה"),
    Book(26, "Mal", "Mal.xml", "Malachi", "מלאכי"),
    Book(27, "Ps", "Ps.xml", "Psalms", "תהלים"),
    Book(28, "Job", "Job.xml", "Job", "איוב"),
    Book(29, "Prov", "Prov.xml", "Proverbs", "משלי"),
    Book(30, "Ruth", "Ruth.xml", "Ruth", "רות"),
    Book(31, "Song", "Song.xml", "Song of Songs", "שיר השירים"),
    Book(32, "Eccl", "Eccl.xml", "Ecclesiastes", "קהלת"),
    Book(33, "Lam", "Lam.xml", "Lamentations", "איכה"),
    Book(34, "Esth", "Esth.xml", "Esther", "אסתר"),
    Book(35, "Dan", "Dan.xml", "Daniel", "דניאל"),
    Book(36, "Ezra", "Ezra.xml", "Ezra", "עזרא"),
    Book(37, "Neh", "Neh.xml", "Nehemiah", "נחמיה"),
    Book(38, "1Chr", "1Chr.xml", "1 Chronicles", "דברי הימים א"),
    Book(39, "2Chr", "2Chr.xml", "2 Chronicles", "דברי הימים ב"),
)

BOOK_BY_OSIS = {b.osis: b for b in BOOKS}
BOOK_BY_ID = {b.id: b for b in BOOKS}
TORAH_BOOK_IDS = frozenset({1, 2, 3, 4, 5})
