"""Stable product identity for the G00 bootstrap.

No GTK and no Calamus runtime dependency are permitted here.
"""
from __future__ import annotations

PRODUCT_NAME = "Graphium"
PACKAGE_NAME = "graphium"
EXECUTABLE_NAME = "graphium"
VERSION = "0.0.1-g00"
WORK_ITEM = "G00"
WORK_ITEM_DESCRIPTION = "Architecture Bootstrap / Technology & Boundary Contract"

# Desktop application ID is deliberately not frozen in G00.  Packaging/repository
# identity is a separate decision and must not be guessed from Calamus.
DESKTOP_APPLICATION_ID = None
