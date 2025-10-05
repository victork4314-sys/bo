"""Input and output helpers for BioLang."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Tuple

from .sequence_ops import clean_sequence

try:  # pragma: no cover - optional dependencies
    from Bio import SeqIO  # type: ignore
except Exception:  # pragma: no cover
    SeqIO = None

try:  # pragma: no cover
    import pysam  # type: ignore
except Exception:  # pragma: no cover
    pysam = None


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def read_fasta(path: str) -> List[tuple[str, str]]:
    records: List[tuple[str, str]] = []
    name: str | None = None
    seq_parts: List[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                records.append((name, clean_sequence("".join(seq_parts))))
            name = line[1:].strip() or "sequence"
            seq_parts = []
        else:
            seq_parts.append(line.strip())
    if name is not None:
        records.append((name, clean_sequence("".join(seq_parts))))
    return records


def write_fasta(path: str, records: Iterable[tuple[str, str]]) -> None:
    lines: List[str] = []
    for name, seq in records:
        lines.append(f">{name}")
        chunk = clean_sequence(seq)
        for i in range(0, len(chunk), 70):
            lines.append(chunk[i : i + 70])
    write_text(path, "\n".join(lines) + ("\n" if lines else ""))


def read_fastq(path: str) -> List[Tuple[str, str]]:
    if SeqIO is not None:
        return [(record.id, clean_sequence(str(record.seq))) for record in SeqIO.parse(path, "fastq")]
    entries: List[Tuple[str, str]] = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for i in range(0, len(lines), 4):
        header = lines[i].strip()
        seq = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if header.startswith("@"):
            entries.append((header[1:], clean_sequence(seq)))
    return entries


def read_genbank(path: str) -> List[Tuple[str, str]]:
    if SeqIO is None:
        raise ImportError("Biopython is required to read GenBank files.")
    return [(record.name or record.id, clean_sequence(str(record.seq))) for record in SeqIO.parse(path, "genbank")]


def read_gff(path: str) -> tuple[list[str], list[list[str]]]:
    headers = [
        "seqid",
        "source",
        "type",
        "start",
        "end",
        "score",
        "strand",
        "phase",
        "attributes",
    ]
    rows: List[List[str]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 9:
            continue
        rows.append(parts[:9])
    return headers, rows


def read_vcf(path: str) -> tuple[list[str], list[list[str]]]:
    headers: List[str] = []
    rows: List[List[str]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("##"):
            continue
        if line.startswith("#"):
            headers = line[1:].split("\t")
            continue
        rows.append(line.split("\t"))
    return headers, rows


def read_bam(path: str) -> tuple[list[str], list[list[str]]]:
    headers = ["query", "flag", "ref", "pos", "mapq", "cigar"]
    rows: List[List[str]] = []
    if pysam is None:
        raise ImportError("pysam is required to read BAM files.")
    with pysam.AlignmentFile(path, "rb") as bam:  # type: ignore
        for index, read in enumerate(bam):
            if index >= 500:
                break
            rows.append(
                [
                    read.query_name,
                    str(read.flag),
                    read.reference_name or "",
                    str(read.reference_start + 1 if read.reference_start is not None else ""),
                    str(read.mapping_quality),
                    read.cigarstring or "",
                ]
            )
    return headers, rows


def read_table(path: str) -> tuple[list[str], list[list[str]]]:
    suffix = Path(path).suffix.lower()
    delimiter = "\t" if suffix in {".tsv", ".gff"} else ","
    with Path(path).open(encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return [], []
    headers = rows[0]
    return headers, rows[1:]


def write_table(path: str, headers: list[str], rows: list[list[str]]) -> None:
    values = ["\t".join(headers)] if headers else []
    for row in rows:
        values.append("\t".join(row))
    write_text(path, "\n".join(values) + ("\n" if values else ""))
