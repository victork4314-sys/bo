"""Self verification helpers for BioLang."""
from __future__ import annotations

import os
import subprocess
import sys
from typing import List


COMMANDS = [
    [sys.executable, "-m", "compileall", "biolang_core", "cli", "gui"],
    [sys.executable, "cli/biolang_cli.py", "run", "examples/demo.bio"],
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

