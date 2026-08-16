"""GTK-free Graphium G06 view settings authority.

Only persistent presentation choices live here. Zoom and fullscreen are deliberately
transient runtime state and are not part of this persistent model.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol


DEFAULT_FONT_FAMILY = "Monospace"
DEFAULT_FONT_SIZE_POINTS = 11.0
MIN_FONT_SIZE_POINTS = 6.0
MAX_FONT_SIZE_POINTS = 72.0


@dataclass(frozen=True)
class ViewSettings:
    word_wrap: bool = False
    line_numbers: bool = False
    status_bar: bool = True
    font_family: str = DEFAULT_FONT_FAMILY
    font_size_points: float = DEFAULT_FONT_SIZE_POINTS

    def __post_init__(self) -> None:
        if not isinstance(self.word_wrap, bool):
            raise TypeError("word_wrap must be bool")
        if not isinstance(self.line_numbers, bool):
            raise TypeError("line_numbers must be bool")
        if not isinstance(self.status_bar, bool):
            raise TypeError("status_bar must be bool")
        if not isinstance(self.font_family, str) or not self.font_family.strip():
            raise ValueError("font_family must be a non-empty string")
        size = float(self.font_size_points)
        if not MIN_FONT_SIZE_POINTS <= size <= MAX_FONT_SIZE_POINTS:
            raise ValueError(
                f"font_size_points must be between {MIN_FONT_SIZE_POINTS:g} and "
                f"{MAX_FONT_SIZE_POINTS:g}"
            )

    def updated(self, **changes) -> "ViewSettings":
        return replace(self, **changes)


class ViewSettingsStorePort(Protocol):
    def load(self) -> ViewSettings: ...
    def save(self, settings: ViewSettings) -> None: ...


class ViewSettingsController:
    """Single in-memory authority for persistent direct View settings."""

    __slots__ = ("_store", "_current")

    def __init__(self, store: ViewSettingsStorePort) -> None:
        self._store = store
        self._current = store.load()

    @property
    def current(self) -> ViewSettings:
        return self._current

    def update(self, **changes) -> ViewSettings:
        candidate = self._current.updated(**changes)
        # Commit to the config store before publishing the new in-memory setting.
        # If persistence fails, the active setting remains exactly the prior value.
        self._store.save(candidate)
        self._current = candidate
        return candidate
