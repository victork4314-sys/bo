"""Create ready-to-run BioSpeak bundles without admin rights."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from textwrap import dedent


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    shutil.copytree(source, destination)


def _write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def create_ready_bundle(target: Path) -> Path:
    """Create a portable folder with launch scripts.

    The folder can be carried to another computer without requiring
    administrator permissions. It contains the BioSpeak sources, the CLI
    runner, the GUI entry point, and Windows batch helpers.
    """

    project_root = Path(__file__).resolve().parent.parent
    target = target.expanduser().resolve()

    if target.exists():
        if any(target.iterdir()):
            raise FileExistsError(f"Target folder is not empty: {target}")
    else:
        target.mkdir(parents=True)

    # Copy the BioSpeak sources and helper assets
    _copy_tree(project_root / "biospeak_core", target / "biospeak_core")
    _copy_tree(project_root / "cli", target / "cli")
    _copy_tree(project_root / "gui", target / "gui")
    _copy_tree(project_root / "examples", target / "examples")

    # Portable readme with instructions
    _write_file(
        target / "README_PORTABLE.txt",
        dedent(
            """
            BioSpeak Portable
            =================

            This folder is ready to run without administrator rights. Keep the
            files together and double click one of the helper scripts.

            Run from Command Prompt:
              run_terminal.bat

            Run the studio window:
              run_gui.bat

            You can also execute a .bio script:
              run_terminal.bat run demo.bio

            The demo.bio file shows a complete session.
            """
        ).strip()
        + os.linesep,
    )

    # Helper batch scripts for Windows users
    _write_file(
        target / "run_terminal.bat",
        dedent(
            """
            @echo off
            setlocal
            set SCRIPT_DIR=%~dp0
            python "%SCRIPT_DIR%cli\\biospeak_cli.py" %*
            """
        ).lstrip(),
    )

    _write_file(
        target / "run_gui.bat",
        dedent(
            """
            @echo off
            setlocal
            set SCRIPT_DIR=%~dp0
            python "%SCRIPT_DIR%gui\\biospeak_studio.py"
            """
        ).lstrip(),
    )

    return target

