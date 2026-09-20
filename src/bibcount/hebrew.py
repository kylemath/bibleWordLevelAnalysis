"""Hebrew letter utilities. Avoid NFC normalization (OSHB warning)."""

from __future__ import annotations

# Consonants including final forms. Do not fold finals; callers may.
_LETTERS = frozenset("אבגדהוזחטיכלמנסעפצקרשתךםןףץ")

# OSHB prefix lemma codes for inseparable / attached particles.
PREFIX_LEMMA_CODES = frozenset({"b", "c", "d", "i", "k", "l", "m", "s"})

PREFIX_CODE_HEBREW = {
    "b": "ב",
    "c": "ו",
    "d": "ה",
    "i": "ה",
    "k": "כ",
    "l": "ל",
    "m": "מ",
    "s": "ש",
}


def consonants_only(text: str) -> str:
    """Keep Hebrew letters only (drop nikkud, cantillation, maqaf, slashes)."""
    return "".join(ch for ch in text if ch in _LETTERS)


def strip_slashes(text: str) -> str:
    return text.replace("/", "")


def is_strongs_lemma(part: str) -> bool:
    part = part.strip()
    return bool(part) and part[0].isdigit()


def normalize_lemma(part: str) -> str:
    """Canonical Strong's-like key: '1121 a' -> '1121a', '1035+' -> '1035'."""
    part = part.strip().rstrip("+").replace(" ", "")
    return part


def split_morph_suffix_count(morph: str) -> int:
    """Count trailing suffix morph segments (codes starting with S)."""
    if not morph:
        return 0
    parts = [p for p in morph.split("/") if p]
    count = 0
    for part in reversed(parts[1:] if len(parts) > 1 else parts):
        code = part[1:] if part[:1] in "HA" and len(parts) == 1 else part
        if code.startswith("S"):
            count += 1
        else:
            break
    return count


def split_affixes(surface: str, lemma: str, morph: str) -> dict[str, str | bool]:
    """Split an OSHB word into prefix / stem / suffix using lemma + morph."""
    text_parts = [p for p in surface.split("/") if p]
    lemma_parts = [p.strip() for p in lemma.split("/") if p.strip()]

    prefix_i = 0
    while prefix_i < len(lemma_parts) and not is_strongs_lemma(lemma_parts[prefix_i]):
        prefix_i += 1

    prefix_lemmas = lemma_parts[:prefix_i]
    prefix_texts = text_parts[:prefix_i]
    rest_text = text_parts[prefix_i:]
    rest_lemma = lemma_parts[prefix_i:]

    suffix_n = split_morph_suffix_count(morph)
    if suffix_n and len(rest_text) >= suffix_n:
        suffix_texts = rest_text[-suffix_n:]
        stem_texts = rest_text[:-suffix_n]
    else:
        suffix_texts = []
        stem_texts = rest_text

    if not stem_texts:
        stem_texts = rest_text or text_parts[-1:] or [surface]

    stem_lemma = ""
    for part in rest_lemma:
        if is_strongs_lemma(part):
            stem_lemma = normalize_lemma(part)
    if not stem_lemma:
        for part in lemma_parts:
            if is_strongs_lemma(part):
                stem_lemma = normalize_lemma(part)
    if not stem_lemma:
        stem_lemma = normalize_lemma(rest_lemma[-1]) if rest_lemma else normalize_lemma(lemma)

    prefix_surface = "".join(prefix_texts)
    suffix_surface = "".join(suffix_texts)
    stem_surface = "".join(stem_texts)
    return {
        "prefix_codes": "+".join(prefix_lemmas),
        "prefix_surface": prefix_surface,
        "stem_surface": stem_surface,
        "stem_lemma": stem_lemma,
        "suffix_surface": suffix_surface,
        "has_prefix": bool(prefix_lemmas),
        "has_suffix": bool(suffix_texts) or suffix_n > 0,
    }
