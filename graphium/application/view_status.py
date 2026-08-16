"""Cheap G06 status projection with no document-wide scanning."""
from __future__ import annotations

from dataclasses import dataclass

from graphium.domain.document_identity import BomKind, DocumentFileState, LineEnding


@dataclass(frozen=True)
class CompactStatus:
    line: int
    column: int
    encoding: str
    eol: str
    saved_state: str

    @property
    def position_text(self) -> str:
        return f"Ln {self.line}, Col {self.column}"

    @property
    def document_text(self) -> str:
        return f"{self.encoding} · {self.eol} · {self.saved_state}"


def _encoding_label(file_state: DocumentFileState | None) -> str:
    if file_state is None:
        return "UTF-8"
    raw = file_state.load.encoding.lower()
    labels = {
        "utf-8": "UTF-8",
        "utf-16-le": "UTF-16 LE",
        "utf-16-be": "UTF-16 BE",
        "utf-32-le": "UTF-32 LE",
        "utf-32-be": "UTF-32 BE",
    }
    label = labels.get(raw, raw.upper())
    if file_state.load.bom is BomKind.UTF8:
        return f"{label} BOM"
    return label


def _eol_label(file_state: DocumentFileState | None) -> str:
    if file_state is None:
        return "LF"
    eol = file_state.load.eol
    if eol.mixed:
        dominant = {
            LineEnding.LF: "LF",
            LineEnding.CRLF: "CRLF",
            LineEnding.CR: "CR",
            LineEnding.NONE: "LF",
        }[eol.dominant]
        return f"Mixed EOL ({dominant})"
    return {
        LineEnding.LF: "LF",
        LineEnding.CRLF: "CRLF",
        LineEnding.CR: "CR",
        # A file with no separator will use the Graphium default if a separator is
        # introduced later, so the compact persistence-facing projection is LF.
        LineEnding.NONE: "LF",
    }[eol.dominant]


def project_compact_status(
    *,
    line: int,
    column: int,
    file_state: DocumentFileState | None,
    modified: bool,
) -> CompactStatus:
    line = int(line)
    column = int(column)
    if line < 1 or column < 1:
        raise ValueError("line and column must be 1-based positive integers")
    return CompactStatus(
        line=line,
        column=column,
        encoding=_encoding_label(file_state),
        eol=_eol_label(file_state),
        saved_state="Modified" if modified else "Saved",
    )
