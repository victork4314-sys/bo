"""Data models for BioLang."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StoredItem:
    """Represents any stored item in the BioLang workspace."""

    name: str
    kind: str
    description: str = ""
    notes: Dict[str, str] = field(default_factory=dict)


@dataclass
class SequenceItem(StoredItem):
    """A nucleotide or protein sequence."""

    sequence: str = ""
    alphabet: str = "dna"  # dna, rna, protein

    def length(self) -> int:
        return len(self.sequence)


@dataclass
class AlignmentItem(StoredItem):
    """Stores the text representation of an alignment."""

    lines: List[str] = field(default_factory=list)
    score: float = 0.0
    method: str = ""
    source_a: str = ""
    source_b: str = ""


@dataclass
class TableItem(StoredItem):
    """Represents a simple table of tabular data."""

    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)

    def head(self, count: int = 5) -> List[List[str]]:
        return self.rows[:count]


@dataclass
class ReportItem(StoredItem):
    """Stores multi-line report text."""

    lines: List[str] = field(default_factory=list)


WorkspaceItem = SequenceItem | AlignmentItem | TableItem | ReportItem


def format_table(table: TableItem, limit: Optional[int] = None) -> str:
    """Format a table for display."""
    limit = limit or len(table.rows)
    selected = table.rows[:limit]
    column_widths = [len(h) for h in table.headers]
    for row in selected:
        for i, value in enumerate(row):
            if i < len(column_widths):
                column_widths[i] = max(column_widths[i], len(value))
            else:
                column_widths.append(len(value))
    header_cells = table.headers + [""] * (len(column_widths) - len(table.headers))
    header_line = " | ".join(header_cells[i].ljust(column_widths[i]) for i in range(len(column_widths)))
    separator = "-+-".join("-" * column_widths[i] for i in range(len(column_widths)))
    body_lines = [
        " | ".join(
            row[i].ljust(column_widths[i]) if i < len(row) else "".ljust(column_widths[i])
            for i in range(len(column_widths))
        )
        for row in selected
    ]
    return "\n".join([header_line, separator, *body_lines]) if table.headers else "\n".join("\t".join(row) for row in selected)
