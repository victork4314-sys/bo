"""Shared core functionality for the BioLang platform."""

from .engine import BioLangEngine, CommandError
from .filemap import generate_file_map
from .integration import IntegrationRegistry
from .selftest import run_self_tests
from .workspace import Workspace
from .gui import launch_gui

__all__ = [
    "BioLangEngine",
    "CommandError",
    "Workspace",
    "launch_gui",
    "generate_file_map",
    "IntegrationRegistry",
    "run_self_tests",
]
