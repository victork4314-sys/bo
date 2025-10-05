"""Assemble the Bio Speak distribution directory and launcher script.

The builder copies the platform executables plus the offline web bundle into a
single ``dist/`` directory beneath ``BioSpeak_Full`` and writes the
``Open_BioSpeak`` launcher that picks the correct binary at runtime. It can also
emit a ``BioSpeak_Full.zip`` archive so the entire folder is ready to share.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
from pathlib import Path
from shutil import make_archive

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT_DIR / "dist"
LAUNCHER_BASENAME = "Open_BioSpeak"
WINDOWS_BINARY = "BioSpeak.exe"
MAC_APP = "BioSpeak.app"
LINUX_APPIMAGE = "BioSpeak.AppImage"
WEB_FOLDER = "web"
INFO_FILENAME = "release.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble Bio Speak executables, the offline web bundle, and the "
            "cross-platform launcher into a single distribution directory."
        ),
    )
    parser.add_argument(
        "--windows",
        required=True,
        type=Path,
        help="Path to the Windows BioSpeak.exe artifact.",
    )
    parser.add_argument(
        "--mac",
        required=True,
        type=Path,
        help="Path to the macOS BioSpeak.app bundle.",
    )
    parser.add_argument(
        "--linux",
        required=True,
        type=Path,
        help="Path to the Linux BioSpeak.AppImage artifact.",
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
        default=DEFAULT_OUTPUT,
        help="Directory to create for the combined release output.",
    )
    parser.add_argument(
        "--zip/--no-zip",
        dest="zip_archive",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Create BioSpeak_Full.zip after building the dist folder.",
    )
    return parser.parse_args()


def copy_path(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def write_launcher_script(base_dir: Path) -> None:
    launcher_path = base_dir / LAUNCHER_BASENAME
    script = f"""#!/usr/bin/env python3
import os
import platform
import subprocess

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
WINDOWS = os.path.join(BASE_DIR, \"{WINDOWS_BINARY}\")
MAC = os.path.join(BASE_DIR, \"{MAC_APP}\")
LINUX = os.path.join(BASE_DIR, \"{LINUX_APPIMAGE}\")
WEB_INDEX = os.path.join(BASE_DIR, \"{WEB_FOLDER}\", \"index.html\")


def launch(target):
    if not os.path.exists(target):
        raise FileNotFoundError(target)
    system = platform.system()
    if system == "Windows":
        os.startfile(target)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen([target])


def main() -> None:
    system = platform.system()
    if system == "Windows" and os.path.exists(WINDOWS):
        launch(WINDOWS)
        return
    if system == "Darwin" and os.path.exists(MAC):
        launch(MAC)
        return
    if system == "Linux" and os.path.exists(LINUX):
        launch(LINUX)
        return
    if os.path.exists(WEB_INDEX):
        launch(WEB_INDEX)
        return
    raise SystemExit("No matching Bio Speak artifact found in the distribution folder.")


if __name__ == "__main__":
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
        "windows": WINDOWS_BINARY,
        "mac": MAC_APP,
        "linux": LINUX_APPIMAGE,
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

    copy_path(args.windows.resolve(), output / WINDOWS_BINARY)
    copy_path(args.mac.resolve(), output / MAC_APP)
    copy_path(args.linux.resolve(), output / LINUX_APPIMAGE)
    copy_path(args.web.resolve(), output / WEB_FOLDER)

    write_launcher_script(output)
    write_metadata(output)

    if args.zip_archive:
        zip_path = ROOT_DIR.parent / "BioSpeak_Full"
        archive_base = zip_path
        zip_file = zip_path.with_suffix(".zip")
        if zip_file.exists():
            zip_file.unlink()
        make_archive(str(archive_base), "zip", root_dir=ROOT_DIR.parent, base_dir=ROOT_DIR.name)



if __name__ == "__main__":
    main()
