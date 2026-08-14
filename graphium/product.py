"""Stable Graphium product/work-item identity.

No GTK or Calamus runtime dependency is permitted here.
"""
from __future__ import annotations

PRODUCT_NAME = "Graphium"
PACKAGE_NAME = "graphium"
EXECUTABLE_NAME = "graphium"
VERSION = "0.0.4-g03"
WORK_ITEM = "G03"
WORK_ITEM_DESCRIPTION = "Guarded Save / Save As"

# Desktop application ID is deliberately not frozen in G00.  Packaging/repository
# identity is a separate decision and must not be guessed from Calamus.
DESKTOP_APPLICATION_ID = None
