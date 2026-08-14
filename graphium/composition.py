"""Graphium G04 composition root: one document, one writer, thin GTK adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .application.document_save_service import DocumentSaveService
from .application.document_session import DocumentSession
from .application.file_lifecycle import FileLifecycleController, LifecycleUI
from .application.native_editor import NativeEditorBufferPort, NativeEditorController
from .domain.document_identity import DocumentLoadResult
from .domain.edit_history import DeltaHistory
from .infrastructure.document_loader import load_document
from .infrastructure.guarded_file_writer import GuardedFileWriter
from .product import PRODUCT_NAME, VERSION, WORK_ITEM


@dataclass(frozen=True)
class CompositionDescriptor:
    product_name: str
    version: str
    work_item: str
    document_authority_count: int
    physical_writer_authority_count: int
    gtk_adapter_boundary: str
    native_history_storage: str


@dataclass
class GraphiumCore:
    session: DocumentSession
    history: DeltaHistory
    editor: NativeEditorController
    writer: GuardedFileWriter
    save_service: DocumentSaveService
    lifecycle: FileLifecycleController


def describe_composition() -> CompositionDescriptor:
    return CompositionDescriptor(
        product_name=PRODUCT_NAME,
        version=VERSION,
        work_item=WORK_ITEM,
        document_authority_count=1,
        physical_writer_authority_count=1,
        gtk_adapter_boundary="graphium.adapters.gtk",
        native_history_storage="delta",
    )


def build_core(
    *,
    buffer: NativeEditorBufferPort,
    ui: LifecycleUI,
    loader: Callable[[str], DocumentLoadResult] = load_document,
) -> GraphiumCore:
    session = DocumentSession()
    history = DeltaHistory()
    editor = NativeEditorController(session=session, history=history, buffer=buffer)
    writer = GuardedFileWriter()
    save_service = DocumentSaveService(session=session, writer=writer)
    lifecycle = FileLifecycleController(
        session=session,
        editor=editor,
        save_service=save_service,
        loader=loader,
        ui=ui,
    )
    return GraphiumCore(
        session=session,
        history=history,
        editor=editor,
        writer=writer,
        save_service=save_service,
        lifecycle=lifecycle,
    )
