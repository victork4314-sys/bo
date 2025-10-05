"""Command engine for the BioSpeak language."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from . import alignment as align_mod
from .data import AlignmentItem, ReportItem, SequenceItem, TableItem, WorkspaceItem, format_table
from .filemap import generate_file_map
from .integration import IntegrationRegistry
from .io_utils import (
    read_bam,
    read_fasta,
    read_fastq,
    read_genbank,
    read_gff,
    read_table,
    read_text,
    read_vcf,
    write_fasta,
    write_table,
    write_text,
)
from .selftest import run_self_tests
from .sequence_ops import (
    clean_sequence,
    codon_usage,
    complement,
    count_bases,
    find_motif,
    gc_content,
    join_sequences,
    reverse_sequence,
    slice_sequence,
    transcribe,
    translate,
    translate_frames,
)
from .workspace import Workspace


class CommandError(Exception):
    """Raised when a command cannot be completed."""


@dataclass
class CommandResult:
    message: str
    created_items: List[str]


class BioSpeakEngine:
    """Holds the data state and processes BioSpeak commands."""

    def __init__(self, workspace: Workspace | None = None, registry: IntegrationRegistry | None = None) -> None:
        self.workspace = workspace or Workspace()
        self.registry = registry or IntegrationRegistry()
        self.items: Dict[str, WorkspaceItem] = self.workspace.items

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle(self, command: str) -> CommandResult:
        command = command.strip()
        if not command:
            raise CommandError("Please speak a command.")
        command_lower = command.lower()

        if command_lower in {"exit", "leave", "quit", "close"}:
            raise SystemExit

        if command_lower == "list data":
            return self._list_data()
        if command_lower == "list sequences":
            return self._list_sequences()
        if command_lower == "list tables":
            return self._list_tables()

        if command_lower.startswith("load dna file "):
            return self._load_sequence_from_file(command, "dna")
        if command_lower.startswith("load dna text "):
            return self._load_sequence_from_text(command, "dna")
        if command_lower.startswith("load rna file "):
            return self._load_sequence_from_file(command, "rna")
        if command_lower.startswith("load rna text "):
            return self._load_sequence_from_text(command, "rna")
        if command_lower.startswith("load protein file "):
            return self._load_sequence_from_file(command, "protein")
        if command_lower.startswith("load protein text "):
            return self._load_sequence_from_text(command, "protein")
        if command_lower.startswith("load table file "):
            return self._load_table_from_file(command)
        if command_lower.startswith("load fastq file "):
            return self._load_fastq_from_file(command)
        if command_lower.startswith("load genbank file "):
            return self._load_genbank_from_file(command)
        if command_lower.startswith("load gff file "):
            return self._load_gff_from_file(command)
        if command_lower.startswith("load vcf file "):
            return self._load_vcf_from_file(command)
        if command_lower.startswith("load bam file "):
            return self._load_bam_from_file(command)
        if command_lower.startswith("load json file "):
            return self._load_json_from_file(command)

        if command_lower.startswith("save "):
            return self._save_item(command)
        if command_lower.startswith("show "):
            return self._show_item(command)
        if command_lower.startswith("describe "):
            return self._describe_item(command)
        if command_lower.startswith("count gc of "):
            return self._count_gc(command)
        if command_lower.startswith("count bases of "):
            return self._count_bases(command)
        if command_lower.startswith("count codons of "):
            return self._count_codons(command)
        if command_lower.startswith("find motif "):
            return self._find_motif(command)
        if command_lower.startswith("slice "):
            return self._slice_sequence(command)
        if command_lower.startswith("join "):
            return self._join_sequences(command)
        if command_lower.startswith("transcribe "):
            return self._transcribe_sequence(command)
        if command_lower.startswith("translate frames of "):
            return self._translate_frames(command)
        if command_lower.startswith("translate "):
            return self._translate_sequence(command)
        if command_lower.startswith("reverse complement "):
            return self._reverse_complement(command)
        if command_lower.startswith("reverse "):
            return self._reverse_sequence(command)
        if command_lower.startswith("complement "):
            return self._complement_sequence(command)
        if command_lower.startswith("align "):
            return self._align_sequences(command)
        if command_lower.startswith("write report of "):
            return self._write_report(command)
        if command_lower.startswith("make report for "):
            return self._create_report(command)
        if command_lower.startswith("filter table "):
            return self._filter_table(command)
        if command_lower.startswith("pick columns "):
            return self._pick_columns(command)
        if command_lower.startswith("join table "):
            return self._join_tables(command)
        if command_lower.startswith("load notes file "):
            return self._load_report(command)
        if command_lower.startswith("analyze table "):
            return self._analyze_table(command)
        if command_lower.startswith("plot sequences "):
            return self._plot_sequences(command)
        if command_lower.startswith("export sequences to "):
            return self._export_sequences(command)
        if command_lower.startswith("export table "):
            return self._export_table(command)
        if command_lower.startswith("align group "):
            return self._align_group(command)
        if command_lower == "make file map":
            return self._make_file_map()
        if command_lower == "verify project":
            return self._verify_project()
        if command_lower == "list integrations":
            return self._list_integrations()

        raise CommandError("Command not understood.")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _list_data(self) -> CommandResult:
        if not self.items:
            return CommandResult("No data is loaded.", [])
        names = sorted(self.items)
        lines = [f"{name} ({item.kind})" for name, item in ((n, self.items[n]) for n in names)]
        return CommandResult("\n".join(lines), [])

    def _list_sequences(self) -> CommandResult:
        names = [name for name, item in self.items.items() if isinstance(item, SequenceItem)]
        if not names:
            return CommandResult("No sequences are stored.", [])
        lines = [f"{name} ({self.items[name].alphabet})" for name in sorted(names)]
        return CommandResult("\n".join(lines), [])

    def _list_tables(self) -> CommandResult:
        names = [name for name, item in self.items.items() if isinstance(item, TableItem)]
        if not names:
            return CommandResult("No tables are stored.", [])
        return CommandResult("\n".join(sorted(names)), [])

    def _load_sequence_from_file(self, command: str, alphabet: str) -> CommandResult:
        rest = command[len(f"load {alphabet} file "):]
        path, name = self._split_as(rest)
        records = read_fasta(path)
        if not records:
            raise CommandError("No sequences found in file.")
        created: List[str] = []
        for index, (record_name, sequence) in enumerate(records, start=1):
            target_name = name if index == 1 else f"{name}_{index}"
            self.items[target_name] = SequenceItem(
                name=target_name,
                kind="sequence",
                description=record_name,
                sequence=sequence,
                alphabet=alphabet,
            )
            created.append(target_name)
        return CommandResult(f"Loaded {len(created)} sequence(s) as {', '.join(created)}.", created)

    def _load_sequence_from_text(self, command: str, alphabet: str) -> CommandResult:
        rest = command[len(f"load {alphabet} text "):]
        text, name = self._split_as(rest)
        sequence = clean_sequence(text)
        if not sequence:
            raise CommandError("No sequence text provided.")
        self.items[name] = SequenceItem(
            name=name,
            kind="sequence",
            description=f"Manual {alphabet} sequence",
            sequence=sequence,
            alphabet=alphabet,
        )
        return CommandResult(f"Stored sequence as {name}.", [name])

    def _load_table_from_file(self, command: str) -> CommandResult:
        rest = command[len("load table file ") :]
        path, name = self._split_as(rest)
        headers, rows = read_table(path)
        self.items[name] = TableItem(
            name=name,
            kind="table",
            description=f"Table from {Path(path).name}",
            headers=headers,
            rows=rows,
        )
        return CommandResult(f"Loaded table as {name} with {len(rows)} rows.", [name])

    def _load_fastq_from_file(self, command: str) -> CommandResult:
        rest = command[len("load fastq file ") :]
        path, name = self._split_as(rest)
        records = read_fastq(path)
        if not records:
            raise CommandError("No reads found in FASTQ file.")
        created = self.workspace.register_sequences(name, records, "dna")
        return CommandResult(f"Loaded {len(created)} reads from {Path(path).name}.", created)

    def _load_genbank_from_file(self, command: str) -> CommandResult:
        rest = command[len("load genbank file ") :]
        path, name = self._split_as(rest)
        try:
            records = read_genbank(path)
        except ImportError as error:
            raise CommandError(str(error)) from error
        if not records:
            raise CommandError("No entries in GenBank file.")
        created = self.workspace.register_sequences(name, records, "dna")
        return CommandResult(f"Loaded {len(created)} sequences from GenBank.", created)

    def _load_gff_from_file(self, command: str) -> CommandResult:
        rest = command[len("load gff file ") :]
        path, name = self._split_as(rest)
        headers, rows = read_gff(path)
        self.workspace.add_table(name, headers, rows, description=path)
        return CommandResult(f"Loaded GFF annotations into {name}.", [name])

    def _load_vcf_from_file(self, command: str) -> CommandResult:
        rest = command[len("load vcf file ") :]
        path, name = self._split_as(rest)
        headers, rows = read_vcf(path)
        self.workspace.add_table(name, headers, rows, description=path)
        return CommandResult(f"Loaded VCF variants into {name}.", [name])

    def _load_bam_from_file(self, command: str) -> CommandResult:
        rest = command[len("load bam file ") :]
        path, name = self._split_as(rest)
        try:
            headers, rows = read_bam(path)
        except ImportError as error:
            raise CommandError(str(error)) from error
        self.workspace.add_table(name, headers, rows, description=path)
        return CommandResult(f"Loaded BAM alignments into {name}.", [name])

    def _load_json_from_file(self, command: str) -> CommandResult:
        rest = command[len("load json file ") :]
        path, name = self._split_as(rest)
        headers, rows = self._json_to_table(path)
        self.workspace.add_table(name, headers, rows, description=path)
        return CommandResult(f"Loaded JSON data into {name}.", [name])

    def _load_report(self, command: str) -> CommandResult:
        rest = command[len("load notes file ") :]
        path, name = self._split_as(rest)
        text = read_text(path)
        lines = text.splitlines()
        self.items[name] = ReportItem(
            name=name,
            kind="report",
            description=f"Notes from {Path(path).name}",
            lines=lines,
        )
        return CommandResult(f"Loaded notes as {name} with {len(lines)} lines.", [name])

    def _save_item(self, command: str) -> CommandResult:
        rest = command[len("save ") :]
        if " to file " not in rest.lower():
            raise CommandError("Please say: save NAME to file PATH.")
        lower_rest = rest.lower()
        idx = lower_rest.rfind(" to file ")
        name = rest[:idx].strip()
        path = rest[idx + len(" to file ") :].strip()
        item = self._require_item(name)
        if isinstance(item, SequenceItem):
            write_fasta(path, [(item.name, item.sequence)])
            return CommandResult(f"Saved sequence {name} to {path}.", [])
        if isinstance(item, AlignmentItem):
            write_text(path, "\n".join(item.lines) + "\n")
            return CommandResult(f"Saved alignment {name} to {path}.", [])
        if isinstance(item, TableItem):
            write_table(path, item.headers, item.rows)
            return CommandResult(f"Saved table {name} to {path}.", [])
        if isinstance(item, ReportItem):
            write_text(path, "\n".join(item.lines) + "\n")
            return CommandResult(f"Saved report {name} to {path}.", [])
        raise CommandError("Cannot save this item.")

    def _show_item(self, command: str) -> CommandResult:
        name = command[len("show ") :].strip()
        item = self._require_item(name)
        if isinstance(item, SequenceItem):
            return CommandResult(f"{item.name} ({item.alphabet})\n{item.sequence}", [])
        if isinstance(item, AlignmentItem):
            return CommandResult("\n".join(item.lines) + f"\nScore: {item.score}", [])
        if isinstance(item, TableItem):
            preview = format_table(item, limit=10)
            return CommandResult(preview, [])
        if isinstance(item, ReportItem):
            return CommandResult("\n".join(item.lines), [])
        raise CommandError("Item cannot be shown.")

    def _describe_item(self, command: str) -> CommandResult:
        name = command[len("describe ") :].strip()
        item = self._require_item(name)
        if isinstance(item, SequenceItem):
            text = [
                f"Name: {item.name}",
                f"Type: {item.alphabet}",
                f"Length: {item.length()} bases",
                f"GC: {gc_content(item.sequence):.2f}%",
            ]
            if item.description:
                text.append(f"Info: {item.description}")
            return CommandResult("\n".join(text), [])
        if isinstance(item, TableItem):
            text = [
                f"Name: {item.name}",
                f"Rows: {len(item.rows)}",
                f"Columns: {len(item.headers)}",
                f"Headers: {', '.join(item.headers)}" if item.headers else "Headers: none",
            ]
            return CommandResult("\n".join(text), [])
        if isinstance(item, AlignmentItem):
            return CommandResult(
                f"Name: {item.name}\nMethod: {item.method}\nScore: {item.score}\nSources: {item.source_a}, {item.source_b}",
                [],
            )
        if isinstance(item, ReportItem):
            return CommandResult(
                f"Name: {item.name}\nLines: {len(item.lines)}\nDescription: {item.description}",
                [],
            )
        raise CommandError("Item cannot be described.")

    def _count_gc(self, command: str) -> CommandResult:
        name = command[len("count gc of ") :].strip()
        item = self._require_sequence(name)
        value = gc_content(item.sequence)
        return CommandResult(f"GC of {name} is {value:.2f} percent.", [])

    def _count_bases(self, command: str) -> CommandResult:
        name = command[len("count bases of ") :].strip()
        item = self._require_sequence(name)
        counts = count_bases(item.sequence)
        text = ", ".join(f"{base}:{count}" for base, count in sorted(counts.items()))
        return CommandResult(f"Bases of {name}: {text}.", [])

    def _count_codons(self, command: str) -> CommandResult:
        name = command[len("count codons of ") :].strip()
        item = self._require_sequence(name)
        usage = codon_usage(item.sequence)
        ordered = sorted(usage.items())
        lines = ["Codon counts:"] + [f"{codon}: {count}" for codon, count in ordered]
        return CommandResult("\n".join(lines), [])

    def _find_motif(self, command: str) -> CommandResult:
        lower = command.lower()
        if " in " not in lower:
            raise CommandError("Please say: find motif MOTIF in NAME.")
        idx = lower.find(" in ", len("find motif "))
        motif = command[len("find motif "): idx]
        name = command[idx + len(" in ") :].strip()
        item = self._require_sequence(name)
        positions = find_motif(item.sequence, motif)
        if not positions:
            return CommandResult(f"Motif not found in {name}.", [])
        return CommandResult(f"Motif found at positions: {', '.join(map(str, positions))}.", [])

    def _slice_sequence(self, command: str) -> CommandResult:
        lower = command.lower()
        if " from " not in lower or " to " not in lower or " as " not in lower:
            raise CommandError("Please say: slice NAME from START to END as NEW.")
        after_slice = command[len("slice ") :]
        name, rest = self._split_word(after_slice, " from ")
        start_text, rest = self._split_word(rest, " to ")
        end_text, new_name = self._split_word(rest, " as ")
        start = int(start_text.strip())
        end = int(end_text.strip())
        item = self._require_sequence(name)
        piece = slice_sequence(item.sequence, start, end)
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"Slice of {name} from {start} to {end}",
            sequence=piece,
            alphabet=item.alphabet,
        )
        return CommandResult(f"Stored slice as {new_name}.", [new_name])

    def _join_sequences(self, command: str) -> CommandResult:
        lower = command.lower()
        if " with " not in lower or " as " not in lower:
            raise CommandError("Please say: join FIRST with SECOND as NEW.")
        after_join = command[len("join ") :]
        first, rest = self._split_word(after_join, " with ")
        second, new_name = self._split_word(rest, " as ")
        item_a = self._require_sequence(first)
        item_b = self._require_sequence(second)
        joined = join_sequences([item_a.sequence, item_b.sequence])
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"Join of {first} and {second}",
            sequence=joined,
            alphabet=item_a.alphabet,
        )
        return CommandResult(f"Stored join as {new_name}.", [new_name])

    def _transcribe_sequence(self, command: str) -> CommandResult:
        after = command[len("transcribe ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        rna = transcribe(item.sequence)
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"RNA made from {name}",
            sequence=rna,
            alphabet="rna",
        )
        return CommandResult(f"Stored rna as {new_name}.", [new_name])

    def _translate_sequence(self, command: str) -> CommandResult:
        after = command[len("translate ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        protein = translate(item.sequence)
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"Protein from {name}",
            sequence=protein,
            alphabet="protein",
        )
        return CommandResult(f"Stored protein as {new_name}.", [new_name])

    def _translate_frames(self, command: str) -> CommandResult:
        after = command[len("translate frames of ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        frames = translate_frames(item.sequence)
        lines = [f"Frame {frame}: {protein}" for frame, protein in frames]
        report = ReportItem(
            name=new_name,
            kind="report",
            description=f"Frames for {name}",
            lines=lines,
        )
        self.items[new_name] = report
        return CommandResult(f"Stored frames as {new_name}.", [new_name])

    def _reverse_sequence(self, command: str) -> CommandResult:
        after = command[len("reverse ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        reversed_seq = reverse_sequence(item.sequence)
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"Reverse of {name}",
            sequence=reversed_seq,
            alphabet=item.alphabet,
        )
        return CommandResult(f"Stored reverse as {new_name}.", [new_name])

    def _complement_sequence(self, command: str) -> CommandResult:
        after = command[len("complement ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        comp = complement(item.sequence, alphabet=item.alphabet)
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"Complement of {name}",
            sequence=comp,
            alphabet=item.alphabet,
        )
        return CommandResult(f"Stored complement as {new_name}.", [new_name])

    def _reverse_complement(self, command: str) -> CommandResult:
        after = command[len("reverse complement ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        comp = complement(reverse_sequence(item.sequence), alphabet=item.alphabet)
        self.items[new_name] = SequenceItem(
            name=new_name,
            kind="sequence",
            description=f"Reverse complement of {name}",
            sequence=comp,
            alphabet=item.alphabet,
        )
        return CommandResult(f"Stored reverse complement as {new_name}.", [new_name])

    def _align_sequences(self, command: str) -> CommandResult:
        lower = command.lower()
        if " with " not in lower or " as " not in lower or " using " not in lower:
            raise CommandError("Please say: align FIRST with SECOND as NAME using METHOD.")
        after_align = command[len("align ") :]
        first, rest = self._split_word(after_align, " with ")
        second, rest = self._split_word(rest, " as ")
        new_name, method = self._split_word(rest, " using ")
        method_choice = method.strip().lower()
        item_a = self._require_sequence(first)
        item_b = self._require_sequence(second)
        seq_a = item_a.sequence
        seq_b = item_b.sequence
        if method_choice == "global":
            result = align_mod.needleman_wunsch(seq_a, seq_b)
            method_text = "global"
        elif method_choice == "local":
            result = align_mod.smith_waterman(seq_a, seq_b)
            method_text = "local"
        else:
            raise CommandError("Method must be global or local.")
        alignment_item = AlignmentItem(
            name=new_name,
            kind="alignment",
            description=f"Alignment of {first} and {second}",
            lines=result.lines,
            score=result.score,
            method=method_text,
            source_a=first,
            source_b=second,
        )
        self.items[new_name] = alignment_item
        lines = result.lines + [f"Score: {result.score}"]
        return CommandResult("\n".join(lines), [new_name])

    def _create_report(self, command: str) -> CommandResult:
        after = command[len("make report for ") :]
        name, new_name = self._split_as(after)
        item = self._require_sequence(name)
        lines = [
            f"Report for {name}",
            f"Length: {item.length()}",
            f"GC: {gc_content(item.sequence):.2f}%",
            f"Bases: {', '.join(f'{b}:{c}' for b, c in sorted(count_bases(item.sequence).items()))}",
        ]
        frames = translate_frames(item.sequence)
        for frame, protein in frames:
            lines.append(f"Frame {frame}: {protein}")
        report = ReportItem(
            name=new_name,
            kind="report",
            description=f"Report for {name}",
            lines=lines,
        )
        self.items[new_name] = report
        return CommandResult(f"Stored report as {new_name}.", [new_name])

    def _write_report(self, command: str) -> CommandResult:
        rest = command[len("write report of ") :]
        name, path = self._split_to(rest, " to file ")
        item = self._require_item(name)
        if isinstance(item, ReportItem):
            write_text(path, "\n".join(item.lines) + "\n")
            return CommandResult(f"Wrote report {name} to {path}.", [])
        if isinstance(item, SequenceItem):
            lines = [
                f"Report for {name}",
                f"Type: {item.alphabet}",
                f"Length: {item.length()}",
                f"GC: {gc_content(item.sequence):.2f}%",
            ]
            write_text(path, "\n".join(lines) + "\n")
            return CommandResult(f"Wrote report for {name} to {path}.", [])
        raise CommandError("Report can be written only for sequences or reports.")

    def _filter_table(self, command: str) -> CommandResult:
        lower = command.lower()
        pattern = " keep column "
        if pattern not in lower or " equals " not in lower or " as " not in lower:
            raise CommandError("Please say: filter table NAME keep column HEADER equals VALUE as NEW.")
        after = command[len("filter table ") :]
        table_name, rest = self._split_word(after, pattern)
        column, rest = self._split_word(rest, " equals ")
        value, new_name = self._split_word(rest, " as ")
        table = self._require_table(table_name)
        if column not in table.headers:
            raise CommandError(f"Column {column} not found.")
        index = table.headers.index(column)
        rows = [row for row in table.rows if index < len(row) and row[index] == value]
        new_table = TableItem(
            name=new_name,
            kind="table",
            description=f"Filtered {table_name} where {column} equals {value}",
            headers=table.headers[:],
            rows=rows,
        )
        self.items[new_name] = new_table
        return CommandResult(f"Stored table as {new_name} with {len(rows)} rows.", [new_name])

    def _pick_columns(self, command: str) -> CommandResult:
        lower = command.lower()
        if " from " not in lower or " as " not in lower:
            raise CommandError("Please say: pick columns COL1 COL2 from NAME as NEW.")
        after = command[len("pick columns ") :]
        columns_text, rest = self._split_word(after, " from ")
        source_name, new_name = self._split_as(rest)
        columns = [word for word in columns_text.split()]
        table = self._require_table(source_name)
        indices: List[int] = []
        headers: List[str] = []
        for column in columns:
            if column not in table.headers:
                raise CommandError(f"Column {column} not found.")
            indices.append(table.headers.index(column))
            headers.append(column)
        rows = [[row[i] if i < len(row) else "" for i in indices] for row in table.rows]
        new_table = TableItem(
            name=new_name,
            kind="table",
            description=f"Columns {', '.join(columns)} from {source_name}",
            headers=headers,
            rows=rows,
        )
        self.items[new_name] = new_table
        return CommandResult(f"Stored table as {new_name} with {len(rows)} rows.", [new_name])

    def _join_tables(self, command: str) -> CommandResult:
        lower = command.lower()
        if " with " not in lower or " on column " not in lower or " as " not in lower:
            raise CommandError("Please say: join table FIRST with SECOND on column HEADER as NEW.")
        after = command[len("join table ") :]
        first, rest = self._split_word(after, " with ")
        second, rest = self._split_word(rest, " on column ")
        column, new_name = self._split_word(rest, " as ")
        table_a = self._require_table(first)
        table_b = self._require_table(second)
        if column not in table_a.headers or column not in table_b.headers:
            raise CommandError(f"Column {column} missing in tables.")
        index_a = table_a.headers.index(column)
        index_b = table_b.headers.index(column)
        header = table_a.headers + [h for h in table_b.headers if h != column]
        lookup: Dict[str, List[str]] = {}
        for row in table_b.rows:
            if index_b < len(row):
                lookup[row[index_b]] = row
        rows: List[List[str]] = []
        for row in table_a.rows:
            key = row[index_a] if index_a < len(row) else ""
            other = lookup.get(key)
            if other is None:
                continue
            combined = row + [value for i, value in enumerate(other) if i != index_b]
            rows.append(combined)
        new_table = TableItem(
            name=new_name,
            kind="table",
            description=f"Join of {first} and {second} on {column}",
            headers=header,
            rows=rows,
        )
        self.items[new_name] = new_table
        return CommandResult(f"Stored table as {new_name} with {len(rows)} rows.", [new_name])

    def _analyze_table(self, command: str) -> CommandResult:
        name = command[len("analyze table ") :].strip()
        table = self._require_table(name)
        summary = self.registry.describe_table(table)
        report_name = f"{name}_summary"
        self.workspace.add_report(report_name, summary.splitlines(), description=f"Summary of {name}")
        return CommandResult(summary, [report_name])

    def _plot_sequences(self, command: str) -> CommandResult:
        rest = command[len("plot sequences ") :]
        if " to file " in rest.lower():
            name, path_text = self._split_to(rest, " to file ")
        else:
            name = rest.strip()
            path_text = f"{name}_metrics.png"
        sequence = self._require_sequence(name)
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.registry.plot_sequence_metrics(name, sequence.sequence, path)
        return CommandResult(f"Saved sequence plots to {path}.", [])

    def _export_sequences(self, command: str) -> CommandResult:
        path_text = command[len("export sequences to ") :].strip()
        if not path_text:
            raise CommandError("Please provide a destination path.")
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.export_sequences(path)
        return CommandResult(f"Saved all sequences to {path}.", [])

    def _export_table(self, command: str) -> CommandResult:
        rest = command[len("export table ") :]
        name, path_text = self._split_to(rest, " to ")
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace.export_table(name, path)
        return CommandResult(f"Saved table {name} to {path}.", [])

    def _align_group(self, command: str) -> CommandResult:
        rest = command[len("align group ") :]
        members_text, new_name = self._split_as(rest)
        members = [name for name in members_text.replace(",", " ").split() if name]
        if len(members) < 2:
            raise CommandError("Please name at least two sequences to align.")
        sequences = [self._require_sequence(name).sequence for name in members]
        alignment_lines, score, method = self.registry.multiple_alignment(members, sequences)
        self.workspace.add_alignment(new_name, alignment_lines, method, score, members[0], members[-1])
        return CommandResult(f"Aligned {len(members)} sequences into {new_name} using {method}.", [new_name])

    def _make_file_map(self) -> CommandResult:
        lines = generate_file_map()
        name = "file_map"
        self.workspace.add_report(name, lines, description="Project files")
        return CommandResult("\n".join(lines), [name])

    def _verify_project(self) -> CommandResult:
        output_lines = run_self_tests()
        name = "verification_report"
        self.workspace.add_report(name, output_lines, description="Self verification")
        if any(line.startswith("FAIL") for line in output_lines):
            raise CommandError("Self verification reported failures. See verification_report.")
        return CommandResult("All modules complete.", [name])

    def _list_integrations(self) -> CommandResult:
        summary = self.registry.describe()
        return CommandResult(summary, [])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _json_to_table(self, path: str) -> Tuple[List[str], List[List[str]]]:
        import json

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows: List[List[str]] = []
        if isinstance(data, dict):
            headers = sorted(data.keys())
            rows.append([self._stringify(data[key]) for key in headers])
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            headers = sorted({key for item in data for key in item.keys()})
            for item in data:
                rows.append([self._stringify(item.get(key, "")) for key in headers])
        else:
            headers = ["value"]
            for item in data if isinstance(data, list) else [data]:
                rows.append([self._stringify(item)])
        return headers, rows

    def _split_as(self, text: str) -> Tuple[str, str]:
        lower = text.lower()
        marker = " as "
        index = lower.rfind(marker)
        if index == -1:
            raise CommandError("Missing 'as' part.")
        first = text[:index].strip()
        second = text[index + len(marker) :].strip()
        if not first or not second:
            raise CommandError("Command is incomplete.")
        return first, second

    def _stringify(self, value: object) -> str:
        if isinstance(value, (list, dict, tuple, set)):
            import json

            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _split_to(self, text: str, marker: str) -> Tuple[str, str]:
        lower = text.lower()
        index = lower.rfind(marker)
        if index == -1:
            raise CommandError("Missing connector in command.")
        first = text[:index].strip()
        second = text[index + len(marker) :].strip()
        if not first or not second:
            raise CommandError("Command is incomplete.")
        return first, second

    def _split_word(self, text: str, marker: str) -> Tuple[str, str]:
        lower_text = text.lower()
        lower_marker = marker.lower()
        index = lower_text.find(lower_marker)
        if index == -1:
            raise CommandError("Command part missing.")
        first = text[:index].strip()
        second = text[index + len(marker) :]
        return first.strip(), second.strip()

    def _require_item(self, name: str) -> WorkspaceItem:
        if name not in self.items:
            raise CommandError(f"Item {name} is not loaded.")
        return self.items[name]

    def _require_sequence(self, name: str) -> SequenceItem:
        item = self._require_item(name)
        if not isinstance(item, SequenceItem):
            raise CommandError(f"Item {name} is not a sequence.")
        return item

    def _require_table(self, name: str) -> TableItem:
        item = self._require_item(name)
        if not isinstance(item, TableItem):
            raise CommandError(f"Item {name} is not a table.")
        return item
