"""Compatibility launcher for the BioLang Studio GUI."""
from __future__ import annotations

from importlib import import_module


def launch_gui() -> None:
    """Launch the PyQt6 BioLang Studio application."""
    studio = import_module("gui.biolang_studio")
    studio.main()
