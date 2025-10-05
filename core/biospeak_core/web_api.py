"""Web integration helpers for the BioSpeak single-page app."""
from __future__ import annotations

from typing import Any, Dict, List

from .engine import BioSpeakEngine, CommandError
from .data import AlignmentItem, ReportItem, SequenceItem, TableItem
from .workspace import Workspace

_engine: BioSpeakEngine | None = None


def _ensure_engine() -> BioSpeakEngine:
    global _engine
    if _engine is None:
        _engine = BioSpeakEngine(Workspace())
    return _engine


def reset_workspace() -> Dict[str, Any]:
    """Clear the workspace and return an empty snapshot."""
    engine = _ensure_engine()
    engine.workspace.clear()
    engine.items.clear()
    return snapshot()


def execute_command(command: str) -> Dict[str, Any]:
    """Execute a BioSpeak sentence command and return a structured result."""
    engine = _ensure_engine()
    try:
        result = engine.handle(command)
        status = "ok"
        message = result.message
        created = result.created_items
    except SystemExit:
        status = "exit"
        message = "Session ended"
        created = []
    except CommandError as exc:  # pragma: no cover - defensive
        status = "error"
        message = str(exc)
        created = []
    except Exception as exc:  # pragma: no cover - defensive
        status = "error"
        message = f"Unexpected error: {exc}"
        created = []
    data = snapshot()
    return {"status": status, "message": message, "created": created, "workspace": data}


def snapshot() -> Dict[str, Any]:
    """Return a JSON-serialisable snapshot of the current workspace."""
    engine = _ensure_engine()
    sequences: List[Dict[str, Any]] = []
    alignments: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    reports: List[Dict[str, Any]] = []
    for item in engine.items.values():
        if isinstance(item, SequenceItem):
            sequences.append(
                {
                    "name": item.name,
                    "description": item.description,
                    "alphabet": item.alphabet,
                    "length": len(item.sequence),
                    "sequence": item.sequence,
                }
            )
        elif isinstance(item, AlignmentItem):
            alignments.append(
                {
                    "name": item.name,
                    "description": item.description,
                    "method": item.method,
                    "score": item.score,
                    "lines": list(item.lines),
                    "source_a": item.source_a,
                    "source_b": item.source_b,
                }
            )
        elif isinstance(item, TableItem):
            tables.append(
                {
                    "name": item.name,
                    "description": item.description,
                    "headers": list(item.headers),
                    "rows": [list(row) for row in item.rows],
                }
            )
        elif isinstance(item, ReportItem):
            reports.append({"name": item.name, "description": item.description, "lines": list(item.lines)})
    return {
        "sequences": sorted(sequences, key=lambda entry: entry["name"].lower()),
        "alignments": sorted(alignments, key=lambda entry: entry["name"].lower()),
        "tables": sorted(tables, key=lambda entry: entry["name"].lower()),
        "reports": sorted(reports, key=lambda entry: entry["name"].lower()),
    }


__all__ = ["execute_command", "reset_workspace", "snapshot"]
