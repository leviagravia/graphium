"""GTK-free G00 composition descriptor.

The real GTK composition root is intentionally deferred. G00 establishes the
allowed dependency directions before feature code is imported from Calamus.
"""
from __future__ import annotations

from dataclasses import dataclass

from .product import PRODUCT_NAME, VERSION, WORK_ITEM


@dataclass(frozen=True)
class CompositionDescriptor:
    product_name: str
    version: str
    work_item: str
    document_authority_count: int
    physical_writer_authority_count: int
    gtk_adapter_boundary: str


def describe_composition() -> CompositionDescriptor:
    return CompositionDescriptor(
        product_name=PRODUCT_NAME,
        version=VERSION,
        work_item=WORK_ITEM,
        document_authority_count=1,
        physical_writer_authority_count=1,
        gtk_adapter_boundary="graphium.adapters.gtk",
    )
