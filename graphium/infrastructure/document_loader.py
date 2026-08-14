"""Stable byte-oriented local document loader for Graphium G01.

Filesystem observation belongs in infrastructure. The returned identity/metadata values
belong to the pure domain model. G01 does not own sessions, saving, watchers or GTK.
"""
from __future__ import annotations

import codecs
import hashlib
import os
import re
import stat

from graphium.domain.document_identity import (
    BomKind,
    ContentFingerprint,
    DiskObservation,
    DocumentFileBinding,
    DocumentFileState,
    DocumentLoadMetadata,
    DocumentLoadResult,
    FileObjectIdentity,
    LineEnding,
    LineEndingProfile,
    UnsupportedDocumentContentError,
    UnsupportedDocumentEncodingError,
    UnsupportedDocumentTypeError,
    UnstableDocumentLoadError,
)

DEFAULT_LARGE_FILE_BYTES = 1_000_000
_EOL_RE = re.compile(r"\r\n|\r|\n")


def normalize_logical_path(path: str) -> str:
    """Normalize a user path without replacing it by its real/canonical path."""
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    if not path:
        raise ValueError("path must not be empty")
    return os.path.abspath(os.path.normpath(os.path.expanduser(path)))


def _stat_signature(st: os.stat_result) -> tuple[int, int, int, int, int, int, int, int, int]:
    return (
        st.st_dev,
        st.st_ino,
        st.st_size,
        st.st_mtime_ns,
        int(getattr(st, "st_ctime_ns", 0)),
        st.st_mode,
        int(getattr(st, "st_uid", 0)),
        int(getattr(st, "st_gid", 0)),
        int(getattr(st, "st_nlink", 1)),
    )


def _read_stable_bytes(path: str, *, retries: int = 1) -> tuple[bytes, os.stat_result, str]:
    attempts = retries + 1
    last_before: os.stat_result | None = None
    last_after: os.stat_result | None = None

    for _ in range(attempts):
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise UnsupportedDocumentTypeError(
                    f"Graphium can open only regular local text files: {path}"
                )
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read()
            after = os.fstat(fd)
        finally:
            os.close(fd)

        descriptor_stable = (
            _stat_signature(before) == _stat_signature(after)
            and len(raw) == after.st_size
        )
        path_stable = False
        canonical = os.path.realpath(path)
        if descriptor_stable:
            try:
                path_after = os.stat(path)
                canonical_after = os.stat(canonical)
            except OSError:
                path_stable = False
            else:
                object_id = (after.st_dev, after.st_ino)
                path_stable = (
                    (path_after.st_dev, path_after.st_ino) == object_id
                    and (canonical_after.st_dev, canonical_after.st_ino) == object_id
                )
        if descriptor_stable and path_stable:
            return raw, after, canonical

        last_before, last_after = before, after

    raise UnstableDocumentLoadError(
        "File changed while it was being read; Graphium did not accept a torn load "
        f"({path}; before={_stat_signature(last_before)} after={_stat_signature(last_after)})"
    )


def _decode_bytes(raw: bytes) -> tuple[str, str, BomKind]:
    candidates = (
        (codecs.BOM_UTF32_LE, "utf-32-le", BomKind.UTF32_LE),
        (codecs.BOM_UTF32_BE, "utf-32-be", BomKind.UTF32_BE),
        (codecs.BOM_UTF8, "utf-8", BomKind.UTF8),
        (codecs.BOM_UTF16_LE, "utf-16-le", BomKind.UTF16_LE),
        (codecs.BOM_UTF16_BE, "utf-16-be", BomKind.UTF16_BE),
    )
    payload = raw
    encoding = "utf-8"
    bom = BomKind.NONE
    for marker, codec_name, kind in candidates:
        if raw.startswith(marker):
            payload = raw[len(marker):]
            encoding = codec_name
            bom = kind
            break
    try:
        return payload.decode(encoding, errors="strict"), encoding, bom
    except UnicodeDecodeError as exc:
        raise UnsupportedDocumentEncodingError(
            f"Unsupported or invalid document encoding ({encoding})"
        ) from exc


def _line_ending_profile(text: str) -> LineEndingProfile:
    counts = {LineEnding.LF: 0, LineEnding.CRLF: 0, LineEnding.CR: 0}
    first_index: dict[LineEnding, int | None] = {
        LineEnding.LF: None,
        LineEnding.CRLF: None,
        LineEnding.CR: None,
    }
    mapping = {"\n": LineEnding.LF, "\r\n": LineEnding.CRLF, "\r": LineEnding.CR}

    for match in _EOL_RE.finditer(text):
        kind = mapping[match.group(0)]
        counts[kind] += 1
        if first_index[kind] is None:
            first_index[kind] = match.start()

    present = [kind for kind, count in counts.items() if count]
    if not present:
        dominant = LineEnding.NONE
    else:
        maximum = max(counts[kind] for kind in present)
        tied = [kind for kind in present if counts[kind] == maximum]
        dominant = min(tied, key=lambda kind: int(first_index[kind]))

    return LineEndingProfile(
        dominant=dominant,
        mixed=len(present) > 1,
        final_newline=text.endswith(("\r\n", "\n", "\r")),
        lf_count=counts[LineEnding.LF],
        crlf_count=counts[LineEnding.CRLF],
        cr_count=counts[LineEnding.CR],
    )


def load_document(
    path: str,
    *,
    retries: int = 1,
    large_file_threshold: int = DEFAULT_LARGE_FILE_BYTES,
) -> DocumentLoadResult:
    """Load one local Graphium document under the frozen G01 visit contract."""
    if not isinstance(retries, int) or retries < 0:
        raise ValueError("retries must be a non-negative integer")
    if not isinstance(large_file_threshold, int) or large_file_threshold <= 0:
        raise ValueError("large_file_threshold must be a positive integer")

    logical_path = normalize_logical_path(path)
    raw, st, canonical = _read_stable_bytes(logical_path, retries=retries)
    decoded, encoding, bom = _decode_bytes(raw)
    if "\x00" in decoded:
        raise UnsupportedDocumentContentError(
            "The selected file contains NUL characters and is outside Graphium plain-text scope"
        )

    eol = _line_ending_profile(decoded)
    normalized_text = decoded.replace("\r\n", "\n").replace("\r", "\n")
    binding = DocumentFileBinding(
        logical_path=logical_path,
        canonical_path=canonical,
        object_id=FileObjectIdentity(device=st.st_dev, inode=st.st_ino),
    )
    file_state = DocumentFileState(
        binding=binding,
        load=DocumentLoadMetadata(encoding=encoding, bom=bom, eol=eol),
        disk=DiskObservation(
            size=st.st_size,
            mtime_ns=st.st_mtime_ns,
            mode=st.st_mode,
            read_only=(st.st_mode & 0o222) == 0,
            ctime_ns=int(getattr(st, "st_ctime_ns", 0)),
            uid=int(getattr(st, "st_uid", 0)),
            gid=int(getattr(st, "st_gid", 0)),
            nlink=int(getattr(st, "st_nlink", 1)),
        ),
        content_fingerprint=ContentFingerprint(
            algorithm="sha256",
            hex_digest=hashlib.sha256(raw).hexdigest(),
        ),
    )
    return DocumentLoadResult(
        text=normalized_text,
        file_state=file_state,
        large_file=len(raw) >= large_file_threshold,
    )
