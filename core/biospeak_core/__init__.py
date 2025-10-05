"""Shared core functionality for the BioSpeak platform."""

from .engine import BioSpeakEngine, CommandError
from .filemap import generate_file_map
from .integration import IntegrationRegistry
from .selftest import run_self_tests
from .workspace import Workspace
from .gui import launch_gui
from . import web_api

__all__ = [
    "BioSpeakEngine",
    "CommandError",
    "Workspace",
    "launch_gui",
    "generate_file_map",
    "IntegrationRegistry",
    "run_self_tests",
    "web_api",
]
