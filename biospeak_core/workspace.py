"""Shared workspace management for BioSpeak."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .data import AlignmentItem, ReportItem, SequenceItem, TableItem, WorkspaceItem


@dataclass
class Workspace:
    """In-memory store used by both CLI and GUI front ends."""

    items: Dict[str, WorkspaceItem] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.items.clear()

    def names(self) -> List[str]:
        return sorted(self.items)

    def by_kind(self, kind: str) -> List[str]:
        return sorted(name for name, item in self.items.items() if item.kind == kind)

    def get(self, name: str) -> WorkspaceItem:
        return self.items[name]

    def add(self, item: WorkspaceItem) -> None:
        self.items[item.name] = item

    # ------------------------------------------------------------------
    # Sequence helpers
    # ------------------------------------------------------------------
    def register_sequences(self, base_name: str, records: Iterable[Tuple[str, str]], alphabet: str) -> List[str]:
        created: List[str] = []
        for index, (record_name, sequence) in enumerate(records, start=1):
            name = base_name if index == 1 else f"{base_name}_{index}"
            self.items[name] = SequenceItem(
                name=name,
                kind="sequence",
                description=record_name,
                sequence=sequence,
                alphabet=alphabet,
            )
            created.append(name)
        return created

    def add_sequence(self, name: str, sequence: str, alphabet: str, description: str = "") -> None:
        self.items[name] = SequenceItem(
            name=name,
            kind="sequence",
            description=description,
            sequence=sequence,
            alphabet=alphabet,
        )

    def add_alignment(
        self,
        name: str,
        lines: List[str],
        method: str,
        score: float,
        source_a: str,
        source_b: str,
    ) -> None:
        self.items[name] = AlignmentItem(
            name=name,
            kind="alignment",
            description=f"{method} alignment",
            lines=lines,
            score=score,
            method=method,
            source_a=source_a,
            source_b=source_b,
        )

    def add_table(self, name: str, headers: List[str], rows: List[List[str]], description: str = "") -> None:
        self.items[name] = TableItem(
            name=name,
            kind="table",
            description=description,
            headers=headers,
            rows=rows,
        )

    def add_report(self, name: str, lines: List[str], description: str = "") -> None:
        self.items[name] = ReportItem(
            name=name,
            kind="report",
            description=description,
            lines=lines,
        )

    def export_sequences(self, target: Path) -> None:
        from .io_utils import write_fasta

        seq_items = [item for item in self.items.values() if isinstance(item, SequenceItem)]
        records = [(item.name, item.sequence) for item in seq_items]
        write_fasta(target, records)

    def export_table(self, name: str, target: Path) -> None:
        from .io_utils import write_table

        item = self.items[name]
        if not isinstance(item, TableItem):
            raise KeyError(f"{name} is not a table")
        write_table(target, item.headers, item.rows)

