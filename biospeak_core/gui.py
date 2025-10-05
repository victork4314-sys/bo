"""Compatibility launcher for the Bio Speak Studio GUI."""
from __future__ import annotations

from importlib import import_module


def launch_gui() -> None:
    """Launch the PyQt6 Bio Speak Studio application."""
    studio = import_module("gui.biospeak_studio")
    studio.main()
