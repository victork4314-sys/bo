"""Self verification helpers for BioSpeak."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]

COMMANDS = [
    [
        sys.executable,
        "-m",
        "compileall",
        str(ROOT / "biospeak_core"),
        str(ROOT / "cli"),
        str(ROOT / "gui"),
        str(ROOT / "installer"),
    ],
    [
        sys.executable,
        str(ROOT / "cli" / "biospeak_cli.py"),
        "run",
        str(ROOT / "examples" / "demo.bio"),
    ],
]


def run_self_tests(commands: List[List[str]] | None = None) -> List[str]:
    """Run verification commands and return collected output lines."""
    outputs: List[str] = []
    work_commands = commands or COMMANDS
    env = dict(os.environ)
    env["BIOSPEAK_SELFTEST"] = "1"
    for cmd in work_commands:
        display = " ".join(cmd)
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        status = "PASS" if result.returncode == 0 else "FAIL"
        outputs.append(f"{status} {display}")
        if result.stdout.strip():
            outputs.extend(result.stdout.strip().splitlines())
        if result.stderr.strip():
            outputs.extend(f"stderr: {line}" for line in result.stderr.strip().splitlines())
    return outputs

