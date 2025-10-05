"""Terminal interface for the BioSpeak CLI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from biospeak_core import BioSpeakEngine, CommandError, generate_file_map, run_self_tests
from biospeak_core.portable import create_ready_bundle


def run_repl() -> None:
    engine = BioSpeakEngine()
    print("BioSpeak ready. Say commands like 'load dna file sample.fasta as sample'.")
    print("Say 'verify project' to run self-checks or 'make file map' for an inventory.")
    print("Say 'exit' to finish.")
    while True:
        try:
            text = input("BioSpeak> ")
        except EOFError:
            print()
            break
        try:
            result = engine.handle(text)
        except SystemExit:
            print("Session closed.")
            break
        except CommandError as error:
            print(f"Problem: {error}")
            continue
        print(result.message)


def run_script(path: Path) -> None:
    engine = BioSpeakEngine()
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.lower().startswith("note "):
            continue
        try:
            result = engine.handle(text)
        except SystemExit:
            break
        except CommandError as error:
            raise SystemExit(f"Line {number}: {error}") from error
        print(f"{text}\n{result.message}\n")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BioSpeak natural language bioinformatics environment")
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to run: run script.bio | ready [folder] | verify | filemap | integrations",
    )
    parser.add_argument("path", nargs="?", help="Path to .bio script or ready folder")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "run":
        if not args.path:
            raise SystemExit("Please provide a script path.")
        run_script(Path(args.path))
    elif args.command == "ready":
        target = Path(args.path or "BioSpeakReady")
        bundle_path = create_ready_bundle(target)
        print(f"Ready bundle created at {bundle_path}")
        print("Copy that folder to any Windows machine and run run_terminal.bat or run_gui.bat.")
    elif args.command == "verify":
        lines = run_self_tests()
        print("\n".join(lines))
    elif args.command == "filemap":
        lines = generate_file_map()
        print("\n".join(lines))
    elif args.command == "integrations":
        engine = BioSpeakEngine()
        result = engine.handle("list integrations")
        print(result.message)
    else:
        run_repl()


if __name__ == "__main__":
    main()
