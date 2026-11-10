"""Pure Unicode catalog/search model for Graphium's native Character Map.

This module is deliberately GTK-free.  It owns only the bounded Unicode ranges,
search semantics and pagination used by the GTK adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
import unicodedata


@dataclass(frozen=True)
class CharacterGroup:
    key: str
    label: str
    ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class CharacterEntry:
    char: str
    codepoint: int
    name: str
    category: str

    @property
    def code_label(self) -> str:
        width = 4 if self.codepoint <= 0xFFFF else 6
        return f"U+{self.codepoint:0{width}X}"

    @property
    def display_text(self) -> str:
        # Combining marks are real insertable characters but are hard to see alone.
        # A dotted circle is display-only and is never inserted into the document.
        return f"◌{self.char}" if self.category.startswith("M") else self.char


CHARACTER_GROUPS: tuple[CharacterGroup, ...] = (
    CharacterGroup("latin", "Latin", ((0x0021, 0x007E), (0x00A1, 0x024F), (0x1E00, 0x1EFF))),
    CharacterGroup("greek", "Greek", ((0x0370, 0x03FF), (0x1F00, 0x1FFF))),
    CharacterGroup("diacritics", "Diacritics", ((0x0300, 0x036F), (0x1AB0, 0x1AFF), (0x1DC0, 0x1DFF))),
    CharacterGroup("cyrillic", "Cyrillic", ((0x0400, 0x052F),)),
    CharacterGroup("hebrew", "Hebrew", ((0x0590, 0x05FF),)),
    CharacterGroup("arabic", "Arabic", ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF))),
    CharacterGroup("punctuation", "Punctuation", ((0x2000, 0x206F),)),
    CharacterGroup("currency", "Currency", ((0x20A0, 0x20CF),)),
    CharacterGroup("arrows", "Arrows", ((0x2190, 0x21FF), (0x27F0, 0x27FF), (0x2900, 0x297F))),
    CharacterGroup("mathematics", "Mathematics", ((0x2200, 0x22FF), (0x27C0, 0x27EF), (0x2A00, 0x2AFF))),
    CharacterGroup(
        "symbols",
        "Symbols",
        ((0x2100, 0x214F), (0x2300, 0x23FF), (0x2460, 0x24FF), (0x25A0, 0x26FF), (0x2B00, 0x2BFF)),
    ),
)

GROUP_BY_KEY = {group.key: group for group in CHARACTER_GROUPS}
ALL_GROUP_KEY = "all"
PAGE_SIZE = 96

# Controls, separators and non-characters do not make useful map cells.  Combining
# marks remain available because they are meaningful Unicode characters.
_HIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})


def _entry_for_codepoint(codepoint: int) -> CharacterEntry | None:
    try:
        char = chr(codepoint)
    except ValueError:
        return None
    category = unicodedata.category(char)
    if category in _HIDDEN_CATEGORIES or char.isspace():
        return None
    try:
        name = unicodedata.name(char)
    except ValueError:
        return None
    return CharacterEntry(char=char, codepoint=codepoint, name=name, category=category)


def _ranges_for_group(group_key: str) -> tuple[tuple[int, int], ...]:
    if group_key == ALL_GROUP_KEY:
        ranges: list[tuple[int, int]] = []
        for group in CHARACTER_GROUPS:
            ranges.extend(group.ranges)
        return tuple(ranges)
    try:
        return GROUP_BY_KEY[group_key].ranges
    except KeyError as exc:
        raise ValueError(f"unknown character group: {group_key}") from exc


def iter_entries(group_key: str = "latin"):
    """Yield assigned, visible characters for one bounded Graphium group."""
    seen: set[int] = set()
    for start, end in _ranges_for_group(group_key):
        for codepoint in range(start, end + 1):
            if codepoint in seen:
                continue
            seen.add(codepoint)
            entry = _entry_for_codepoint(codepoint)
            if entry is not None:
                yield entry


def _normalized_query(query: str) -> str:
    return " ".join(str(query).strip().upper().split())


def _query_codepoint(query: str) -> int | None:
    compact = query.replace(" ", "")
    if compact.startswith("U+"):
        compact = compact[2:]
    elif compact.startswith("0X"):
        compact = compact[2:]
    else:
        return None
    if not compact or len(compact) > 6:
        return None
    try:
        value = int(compact, 16)
    except ValueError:
        return None
    return value if 0 <= value <= 0x10FFFF else None


def search_entries(group_key: str, query: str) -> tuple[CharacterEntry, ...]:
    """Search by literal character, U+XXXX/0xXXXX, or Unicode-name tokens."""
    normalized = _normalized_query(query)
    entries = tuple(iter_entries(group_key))
    if not normalized:
        return entries

    codepoint = _query_codepoint(normalized)
    if codepoint is not None:
        return tuple(entry for entry in entries if entry.codepoint == codepoint)

    # A single literal Unicode character should be exact, including non-ASCII glyphs.
    raw = str(query).strip()
    if len(raw) == 1:
        return tuple(entry for entry in entries if entry.char == raw)

    tokens = normalized.split()
    return tuple(
        entry
        for entry in entries
        if all(token in entry.name for token in tokens)
    )


def page_count(total: int, page_size: int = PAGE_SIZE) -> int:
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    total = max(0, int(total))
    return max(1, (total + page_size - 1) // page_size)


def page_slice(entries: tuple[CharacterEntry, ...], page: int, page_size: int = PAGE_SIZE) -> tuple[CharacterEntry, ...]:
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    pages = page_count(len(entries), page_size)
    page = min(max(0, int(page)), pages - 1)
    start = page * page_size
    return entries[start:start + page_size]
