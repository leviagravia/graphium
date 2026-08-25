"""Optional, bounded Hunspell pipe boundary used only by explicit spell checking."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import threading
import time

MAX_PROTOCOL_LINE_BYTES = 16 * 1024
MAX_SUGGESTIONS = 16
MAX_SUGGESTION_CODEPOINTS = 256
MAX_TOKEN_UTF8_BYTES = 4096
DEFAULT_IO_TIMEOUT_SECONDS = 2.0
_CANCEL_POLL_SECONDS = 0.05


class HunspellError(RuntimeError): pass
class HunspellProcessError(HunspellError): pass
class HunspellProtocolError(HunspellError): pass
class HunspellTimeoutError(HunspellError): pass
class HunspellClosedError(HunspellError): pass


@dataclass(frozen=True)
class HunspellResult:
    word: str
    correct: bool
    suggestions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.word, str) or not self.word:
            raise ValueError("word must be non-empty")
        if not isinstance(self.correct, bool):
            raise TypeError("correct must be bool")
        if self.correct and self.suggestions:
            raise ValueError("correct words cannot carry suggestions")


def resolve_hunspell_executable() -> str | None:
    """Resolve capability on demand; importing this module performs no discovery."""
    return shutil.which("hunspell")


def _safe_token(word: str) -> bytes:
    if not isinstance(word, str) or not word or any(ch in word for ch in "\r\n\x00"):
        raise ValueError("word must be a single non-empty protocol-safe token")
    encoded = word.encode("utf-8", errors="strict")
    if len(encoded) > MAX_TOKEN_UTF8_BYTES:
        raise ValueError("word exceeds the Hunspell token budget")
    return encoded


def _suggestions(raw: str, expected: int) -> tuple[str, ...]:
    items = () if not raw else tuple(x.strip() for x in raw.split(","))
    if len(items) != expected or any(not x for x in items):
        raise HunspellProtocolError("Hunspell suggestion count is malformed")
    for item in items:
        if len(item) > MAX_SUGGESTION_CODEPOINTS or len(item.encode("utf-8")) > MAX_SUGGESTION_CODEPOINTS * 4:
            raise HunspellProtocolError("Hunspell suggestion exceeds the bounded size")
        if any(ch in item for ch in "\r\n\x00"):
            raise HunspellProtocolError("Hunspell suggestion contains invalid control data")
    return items[:MAX_SUGGESTIONS]


def parse_hunspell_response(word: str, line: str) -> HunspellResult:
    """Parse one strict `hunspell -a` result line for one Graphium-owned token."""
    _safe_token(word)
    if not isinstance(line, str) or not line or "\r" in line or "\n" in line or "\x00" in line:
        raise HunspellProtocolError("Hunspell returned a malformed response line")
    if len(line.encode("utf-8")) > MAX_PROTOCOL_LINE_BYTES:
        raise HunspellProtocolError("Hunspell response line exceeds the bounded size")
    if line == "*" or line == "-" or line.startswith("+ "):
        return HunspellResult(word, True)
    marker = line[:1]
    if marker == "#":
        parts = line.split()
        if len(parts) != 3 or parts[1] != word or not parts[2].isdigit():
            raise HunspellProtocolError("Hunspell no-suggestion response is malformed")
        return HunspellResult(word, False)
    if marker in {"&", "?"}:
        head, sep, tail = line.partition(": ")
        parts = head.split()
        if not sep or len(parts) != 4 or parts[0] != marker or parts[1] != word or not parts[2].isdigit() or not parts[3].isdigit():
            raise HunspellProtocolError("Hunspell suggestion response is malformed")
        count = int(parts[2])
        return HunspellResult(word, False, _suggestions(tail, count))
    raise HunspellProtocolError("Hunspell returned an unsupported protocol response")


class HunspellPipeSession:
    """One explicitly-owned Hunspell child; synchronous I/O must be called off GTK main thread."""
    __slots__ = ("_exe", "_timeout", "_proc", "_buffer", "_lock", "_request_lock", "_closed")

    def __init__(self, executable: str, *, timeout_seconds: float = DEFAULT_IO_TIMEOUT_SECONDS) -> None:
        if not isinstance(executable, str) or not executable:
            raise ValueError("executable must be a resolved non-empty path")
        path = Path(executable)
        if not path.is_absolute():
            raise ValueError("executable must be an absolute resolved path")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._exe = str(path); self._timeout = float(timeout_seconds)
        self._proc: subprocess.Popen[bytes] | None = None; self._buffer = bytearray()
        self._lock = threading.Lock(); self._request_lock = threading.Lock(); self._closed = False

    @property
    def pid(self) -> int | None:
        return None if self._proc is None else self._proc.pid

    def start(self) -> None:
        with self._lock:
            if self._closed: raise HunspellClosedError("Hunspell session is closed")
            if self._proc is not None: return
            try:
                self._proc = subprocess.Popen(
                    [self._exe, "-a", "-i", "UTF-8", "--check-apostrophe"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    shell=False, bufsize=0, close_fds=True,
                )
            except (OSError, ValueError) as exc:
                self._proc = None
                raise HunspellProcessError("Hunspell could not be started") from exc
        try:
            banner = self._readline(self._timeout)
            if not banner.startswith("@(#)"):
                raise HunspellProtocolError("Hunspell banner is malformed")
        except BaseException:
            self.close(); raise

    def check(self, word: str) -> HunspellResult:
        data = _safe_token(word)
        with self._request_lock:
            try:
                self.start()
                with self._lock:
                    proc = self._proc
                    if self._closed or proc is None:
                        raise HunspellClosedError("Hunspell session is closed")
                    if proc.poll() is not None:
                        raise HunspellProcessError("Hunspell exited before the request")
                    try:
                        assert proc.stdin is not None
                        proc.stdin.write(b"^" + data + b"\n"); proc.stdin.flush()
                    except (BrokenPipeError, OSError) as exc:
                        raise HunspellProcessError("Hunspell input pipe failed") from exc
                result_line = self._readline(self._timeout)
                terminator = self._readline(self._timeout)
                if terminator != "":
                    raise HunspellProtocolError("Hunspell response group is not blank-terminated")
                return parse_hunspell_response(word, result_line)
            except HunspellError:
                self.close(); raise

    def _readline(self, timeout: float) -> str:
        proc = self._proc
        if proc is None or proc.stdout is None: raise HunspellClosedError("Hunspell session is not started")
        deadline = time.monotonic() + timeout
        try: fd = proc.stdout.fileno()
        except ValueError as exc: raise HunspellClosedError("Hunspell session was cancelled") from exc
        while True:
            pos = self._buffer.find(b"\n")
            if pos >= 0:
                if pos > MAX_PROTOCOL_LINE_BYTES:
                    raise HunspellProtocolError("Hunspell response line exceeds the bounded size")
                raw = bytes(self._buffer[:pos]); del self._buffer[:pos + 1]
                if raw.endswith(b"\r"): raw = raw[:-1]
                try: return raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError as exc: raise HunspellProtocolError("Hunspell output is not strict UTF-8") from exc
            if len(self._buffer) > MAX_PROTOCOL_LINE_BYTES:
                raise HunspellProtocolError("Hunspell response line exceeds the bounded size")
            if self._closed: raise HunspellClosedError("Hunspell session was cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise HunspellTimeoutError("Hunspell response timed out")
            selector = selectors.DefaultSelector()
            try:
                try: selector.register(fd, selectors.EVENT_READ)
                except (OSError, ValueError) as exc:
                    if self._closed: raise HunspellClosedError("Hunspell session was cancelled") from exc
                    raise HunspellProcessError("Hunspell output pipe failed") from exc
                if not selector.select(min(remaining, _CANCEL_POLL_SECONDS)):
                    continue
            finally: selector.close()
            try: chunk = os.read(fd, 4096)
            except OSError as exc:
                if self._closed: raise HunspellClosedError("Hunspell session was cancelled") from exc
                raise HunspellProcessError("Hunspell output pipe failed") from exc
            if not chunk:
                raise HunspellProcessError("Hunspell exited before completing a response")
            self._buffer.extend(chunk)

    def close(self) -> None:
        with self._lock:
            if self._closed: return
            self._closed = True; proc, self._proc = self._proc, None
        if proc is None: return
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream is not None: stream.close()
            except OSError: pass
        if proc.poll() is None:
            try: proc.terminate(); proc.wait(timeout=min(self._timeout, 1.0))
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=1.0)
        else:
            proc.wait()

    cancel = close

    def __enter__(self):
        self.start(); return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
