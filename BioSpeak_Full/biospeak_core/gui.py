"""Compatibility launcher for the BioSpeak Studio GUI."""
from __future__ import annotations

from importlib import import_module


def launch_gui() -> None:
    """Launch the PyQt6 BioSpeak Studio application."""
    studio = import_module("gui.biospeak_studio")
    studio.main()
