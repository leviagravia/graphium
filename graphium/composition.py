"""Graphium composition root."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .application.document_save_service import DocumentSaveService
from .application.document_session import DocumentSession
from .application.file_lifecycle import FileLifecycleController, LifecycleUI
from .application.recent_files import RecentFilesController, RecentFilesStorePort
from .application.document_copy import DocumentCopyService
from .application.document_properties import DocumentPropertiesController
from .application.native_editor import NativeEditorBufferPort, NativeEditorController
from .application.search import SearchController
from .application.view_settings import ViewSettingsController, ViewSettingsStorePort
from .domain.document_identity import DocumentLoadResult
from .domain.edit_history import DeltaHistory
from .infrastructure.document_loader import load_document
from .infrastructure.document_observer import observe_document
from .infrastructure.guarded_file_writer import GuardedFileWriter
from .infrastructure.view_settings_store import JsonViewSettingsStore
from .infrastructure.recent_files_store import JsonRecentFilesStore
from .paths import resolve_xdg_paths


@dataclass
class GraphiumCore:
    session: DocumentSession
    history: DeltaHistory
    editor: NativeEditorController
    writer: GuardedFileWriter
    save_service: DocumentSaveService
    lifecycle: FileLifecycleController
    search: SearchController
    view_settings: ViewSettingsController
    recent_files: RecentFilesController
    document_copy: DocumentCopyService
    document_properties: DocumentPropertiesController


def build_core(
    *,
    buffer: NativeEditorBufferPort,
    ui: LifecycleUI,
    loader: Callable[[str], DocumentLoadResult] = load_document,
    view_settings_store: ViewSettingsStorePort | None = None,
    recent_files_store: RecentFilesStorePort | None = None,
) -> GraphiumCore:
    session = DocumentSession()
    history = DeltaHistory()
    editor = NativeEditorController(session=session, history=history, buffer=buffer)
    writer = GuardedFileWriter()
    save_service = DocumentSaveService(session=session, writer=writer)
    search = SearchController()
    if view_settings_store is None:
        view_settings_store = JsonViewSettingsStore(resolve_xdg_paths().config / "view.json")
    view_settings = ViewSettingsController(view_settings_store)
    if recent_files_store is None:
        recent_files_store = JsonRecentFilesStore(resolve_xdg_paths().state / "recent-files.json")
    recent_files = RecentFilesController(recent_files_store)
    document_copy = DocumentCopyService(session=session, writer=writer)
    document_properties = DocumentPropertiesController(session=session, observer=observe_document)
    lifecycle = FileLifecycleController(
        session=session,
        editor=editor,
        save_service=save_service,
        loader=loader,
        ui=ui,
        recent_files=recent_files,
    )
    return GraphiumCore(
        session=session,
        history=history,
        editor=editor,
        writer=writer,
        save_service=save_service,
        lifecycle=lifecycle,
        search=search,
        view_settings=view_settings,
        recent_files=recent_files,
        document_copy=document_copy,
        document_properties=document_properties,
    )
