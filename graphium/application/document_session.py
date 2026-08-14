"""Single-document savepoint-aware session authority for Graphium G02.

GTK-free and write-free: G03 will provide the physical save authority.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Iterator
from graphium.domain.document_identity import DocumentFileState, DocumentLoadResult
from graphium.domain.history import HistoryState

class DocumentSessionPhase(str, Enum):
    IDLE = "idle"
    REPLACING = "replacing"
    OPENING = "opening"

@dataclass(frozen=True)
class DocumentSessionSnapshot:
    text: str
    file_state: DocumentFileState | None
    phase: DocumentSessionPhase
    revision: int
    current_editor_state_id: int | None
    saved_editor_state_id: int | None

    @property
    def file_path(self) -> str | None:
        return None if self.file_state is None else self.file_state.binding.logical_path

    @property
    def modified(self) -> bool:
        return not (self.current_editor_state_id is not None and
                    self.saved_editor_state_id is not None and
                    self.current_editor_state_id == self.saved_editor_state_id)

class DocumentSession:
    __slots__ = ("_text","_file_state","_phase","_phase_depth","_revision",
                 "_current_editor_state_id","_saved_editor_state_id")

    def __init__(self) -> None:
        self._text = ""
        self._file_state = None
        self._phase = DocumentSessionPhase.IDLE
        self._phase_depth = 0
        self._revision = 0
        self._current_editor_state_id = None
        self._saved_editor_state_id = None

    @staticmethod
    def _state_id(value: int) -> int:
        result = int(value)
        if result <= 0:
            raise ValueError("editor state id must be positive")
        return result

    @property
    def text(self): return self._text
    @property
    def file_state(self): return self._file_state
    @property
    def file_path(self): return self.snapshot().file_path
    @property
    def phase(self): return self._phase
    @property
    def loading(self): return self._phase_depth > 0
    @property
    def revision(self): return self._revision
    @property
    def current_editor_state_id(self): return self._current_editor_state_id
    @property
    def saved_editor_state_id(self): return self._saved_editor_state_id
    @property
    def modified(self): return self.snapshot().modified

    def snapshot(self) -> DocumentSessionSnapshot:
        return DocumentSessionSnapshot(self._text, self._file_state, self._phase, self._revision,
                                       self._current_editor_state_id, self._saved_editor_state_id)

    @contextmanager
    def replacement(self, phase: DocumentSessionPhase = DocumentSessionPhase.REPLACING) -> Iterator[None]:
        if not isinstance(phase, DocumentSessionPhase):
            raise TypeError("phase must be DocumentSessionPhase")
        previous = self._phase
        self._phase_depth += 1
        self._phase = phase
        try:
            yield
        finally:
            self._phase_depth -= 1
            if self._phase_depth < 0:
                self._phase_depth = 0
                self._phase = DocumentSessionPhase.IDLE
                raise RuntimeError("document session replacement depth underflow")
            self._phase = previous if self._phase_depth else DocumentSessionPhase.IDLE

    def establish_new(self, state: HistoryState, *, clean: bool = True) -> None:
        if not isinstance(state, HistoryState) or state.state_id <= 0:
            raise TypeError("state must be an assigned HistoryState")
        before = self.snapshot()
        self._text, self._file_state = state.text, None
        self._current_editor_state_id = state.state_id
        self._saved_editor_state_id = state.state_id if clean else None
        if self.snapshot() != before: self._revision += 1

    def establish_open(self, result: DocumentLoadResult, state: HistoryState) -> None:
        if not isinstance(result, DocumentLoadResult):
            raise TypeError("result must be DocumentLoadResult")
        if not isinstance(state, HistoryState) or state.state_id <= 0:
            raise TypeError("state must be an assigned HistoryState")
        if state.text != result.text:
            raise ValueError("history state text must equal loaded text")
        before = self.snapshot()
        self._text, self._file_state = result.text, result.file_state
        self._current_editor_state_id = state.state_id
        self._saved_editor_state_id = state.state_id
        if self.snapshot() != before: self._revision += 1

    def observe_uncommitted_text(self, text: str) -> bool:
        if not isinstance(text, str): raise TypeError("text must be a string")
        if self.loading: return False
        before = self.snapshot()
        self._text = text
        self._current_editor_state_id = None
        if self.snapshot() != before: self._revision += 1
        return True

    def reconcile_with_history(self, state: HistoryState) -> bool:
        if not isinstance(state, HistoryState) or state.state_id <= 0:
            raise TypeError("state must be an assigned HistoryState")
        if self._text != state.text: return False
        before = self.snapshot()
        self._current_editor_state_id = state.state_id
        if self.snapshot() != before: self._revision += 1
        return True

    def commit_history_state(self, state: HistoryState) -> None:
        if not isinstance(state, HistoryState) or state.state_id <= 0:
            raise TypeError("state must be an assigned HistoryState")
        before = self.snapshot()
        self._text = state.text
        self._current_editor_state_id = state.state_id
        if self.snapshot() != before: self._revision += 1

    def accept_saved_state(self, state_id: int, *, file_state: DocumentFileState | None = None) -> None:
        state_id = self._state_id(state_id)
        before = self.snapshot()
        self._saved_editor_state_id = state_id
        if file_state is not None:
            if not isinstance(file_state, DocumentFileState):
                raise TypeError("file_state must be DocumentFileState or None")
            self._file_state = file_state
        if self.snapshot() != before: self._revision += 1

    def invalidate_saved_relation(self) -> None:
        before = self.snapshot()
        self._saved_editor_state_id = None
        if self.snapshot() != before: self._revision += 1

    def restore_checkpoint(self, snapshot: DocumentSessionSnapshot) -> None:
        if not isinstance(snapshot, DocumentSessionSnapshot):
            raise TypeError("snapshot must be DocumentSessionSnapshot")
        self._text = snapshot.text
        self._file_state = snapshot.file_state
        self._phase = snapshot.phase
        self._phase_depth = 0
        self._revision = snapshot.revision
        self._current_editor_state_id = snapshot.current_editor_state_id
        self._saved_editor_state_id = snapshot.saved_editor_state_id

    def requires_save_confirmation(self) -> bool:
        return self.modified
