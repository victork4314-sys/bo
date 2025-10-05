"""Build the Bio Speak release directory with installers and launcher.

This helper expects platform-specific installer artifacts and the web bundle to
already be built. It arranges them into a Release/ directory and writes a
cross-platform launcher script that opens the appropriate binary for the host.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
from pathlib import Path

RELEASE_NAME = "Release"
LAUNCHER_BASENAME = "Open_BioSpeak"
WINDOWS_INSTALLER = "BioSpeakInstaller.exe"
MAC_INSTALLER = "BioSpeakInstaller.dmg"
LINUX_INSTALLER = "BioSpeakInstaller.AppImage"
WEB_FOLDER = "web"
INFO_FILENAME = "release.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble the Bio Speak cross-platform release bundle.",
    )
    parser.add_argument(
        "--windows",
        required=True,
        type=Path,
        help="Path to the Windows BioSpeakInstaller.exe artifact.",
    )
    parser.add_argument(
        "--mac",
        required=True,
        type=Path,
        help="Path to the macOS BioSpeakInstaller.dmg artifact.",
    )
    parser.add_argument(
        "--linux",
        required=True,
        type=Path,
        help="Path to the Linux BioSpeakInstaller.AppImage artifact.",
    )
    parser.add_argument(
        "--web",
        required=True,
        type=Path,
        help="Directory containing the offline web build (dist).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(RELEASE_NAME),
        help="Directory to create for the combined release output.",
    )
    return parser.parse_args()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def write_launcher_script(base_dir: Path) -> None:
    launcher_path = base_dir / LAUNCHER_BASENAME
    script = f"""#!/usr/bin/env python3
import os
import platform
import subprocess
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
WINDOWS = os.path.join(BASE_DIR, \"{WINDOWS_INSTALLER}\")
MAC = os.path.join(BASE_DIR, \"{MAC_INSTALLER}\")
LINUX = os.path.join(BASE_DIR, \"{LINUX_INSTALLER}\")
WEB_INDEX = os.path.join(BASE_DIR, \"{WEB_FOLDER}\", \"index.html\")


def _launch(target):
    if not os.path.exists(target):
        raise FileNotFoundError(target)
    system = platform.system()
    if system == \"Windows\":
        os.startfile(target)  # type: ignore[attr-defined]
    elif system == \"Darwin\":
        subprocess.Popen([\"open\", target])
    else:
        subprocess.Popen([\"xdg-open\", target])


def main():
    system = platform.system()
    if system == \"Windows\" and os.path.exists(WINDOWS):
        _launch(WINDOWS)
        return
    if system == \"Darwin\" and os.path.exists(MAC):
        _launch(MAC)
        return
    if system == \"Linux\" and os.path.exists(LINUX):
        _launch(LINUX)
        return
    if os.path.exists(WEB_INDEX):
        _launch(WEB_INDEX)
        return
    raise SystemExit(\"No matching Bio Speak artifact found in release bundle.\")


if __name__ == \"__main__\":
    main()
"""
    launcher_path.write_text(script, encoding="utf-8")
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IEXEC)

    # Provide a convenience batch file for Windows double-click flows.
    batch_path = launcher_path.with_suffix(".bat")
    batch_path.write_text(
        "@echo off\n" "python \"%~dp0{0}\"\n".format(launcher_path.name),
        encoding="utf-8",
    )



def write_metadata(base_dir: Path) -> None:
    metadata = {
        "windows": WINDOWS_INSTALLER,
        "mac": MAC_INSTALLER,
        "linux": LINUX_INSTALLER,
        "web": f"{WEB_FOLDER}/",
        "launcher": LAUNCHER_BASENAME,
    }
    (base_dir / INFO_FILENAME).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    copy_file(args.windows.resolve(), output / WINDOWS_INSTALLER)
    copy_file(args.mac.resolve(), output / MAC_INSTALLER)
    copy_file(args.linux.resolve(), output / LINUX_INSTALLER)
    copy_tree(args.web.resolve(), output / WEB_FOLDER)

    write_launcher_script(output)
    write_metadata(output)


if __name__ == "__main__":
    main()
