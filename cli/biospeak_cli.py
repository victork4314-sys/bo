"""Terminal interface for the Bio Speak language."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from biospeak_core import BioSpeakEngine, CommandError, run_self_tests

PROMPT = "bio> "
EXIT_WORDS = {"quit", "exit", "leave", "close"}


def read_commands_from_file(path: Path) -> Iterable[str]:
    """Yield Bio Speak commands from a UTF-8 text file."""
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.lower().startswith("note "):
            continue
        yield line


def run_script(engine: BioSpeakEngine, script_path: Path) -> int:
    """Execute every command in *script_path* against *engine*."""
    try:
        for command in read_commands_from_file(script_path):
            result = engine.handle(command)
            print(result.message)
    except FileNotFoundError:
        print(f"Cannot find script: {script_path}", file=sys.stderr)
        return 1
    except CommandError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        return 1
    except SystemExit:
        return 0
    return 0


def repl(engine: BioSpeakEngine) -> int:
    """Interactive read–evaluate–print loop."""
    print("Bio Speak ready. Type commands like 'load dna file ...'. Type 'exit' to leave.")
    while True:
        try:
            command = input(PROMPT).strip()
        except EOFError:
            print()
            return 0
        if not command:
            continue
        if command.lower() in EXIT_WORDS:
            return 0
        try:
            result = engine.handle(command)
        except CommandError as exc:
            print(f"error: {exc}")
        except SystemExit:
            return 0
        else:
            print(result.message)


def verify() -> int:
    """Run the shared Bio Speak self-tests."""
    outputs = run_self_tests()
    for line in outputs:
        print(line)
    failed = any(line.startswith("FAIL") for line in outputs)
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bio Speak command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    repl_parser = subparsers.add_parser("repl", help="start an interactive session")
    repl_parser.set_defaults(func=lambda args: repl(BioSpeakEngine()))

    run_parser = subparsers.add_parser("run", help="run commands from a .bio file")
    run_parser.add_argument("script", type=Path, help="path to the script to execute")

    def run_entry(args: argparse.Namespace) -> int:
        engine = BioSpeakEngine()
        return run_script(engine, args.script)

    run_parser.set_defaults(func=run_entry)

    verify_parser = subparsers.add_parser("verify", help="run the bundled self-tests")
    verify_parser.set_defaults(func=lambda args: verify())

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        argv = ["repl"]
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
