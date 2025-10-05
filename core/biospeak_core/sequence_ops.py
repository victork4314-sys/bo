"""Sequence operations for BioSpeak."""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

DNA_COMPLEMENT = str.maketrans({"A": "T", "T": "A", "C": "G", "G": "C"})
RNA_COMPLEMENT = str.maketrans({"A": "U", "U": "A", "C": "G", "G": "C"})

CODON_TABLE: Dict[str, str] = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def clean_sequence(text: str) -> str:
    """Return uppercase sequence without spaces."""
    return "".join(ch for ch in text.upper() if ch.isalpha())


def gc_content(sequence: str) -> float:
    sequence = clean_sequence(sequence)
    if not sequence:
        return 0.0
    gc_count = sum(1 for ch in sequence if ch in {"G", "C"})
    return gc_count / len(sequence) * 100


def count_bases(sequence: str) -> Dict[str, int]:
    sequence = clean_sequence(sequence)
    counts: Dict[str, int] = {}
    for ch in sequence:
        counts[ch] = counts.get(ch, 0) + 1
    return counts


def reverse_sequence(sequence: str) -> str:
    return clean_sequence(sequence)[::-1]


def complement(sequence: str, alphabet: str = "dna") -> str:
    seq = clean_sequence(sequence)
    if alphabet == "rna":
        return seq.translate(RNA_COMPLEMENT)
    return seq.translate(DNA_COMPLEMENT)


def reverse_complement(sequence: str, alphabet: str = "dna") -> str:
    return complement(reverse_sequence(sequence), alphabet=alphabet)


def transcribe(sequence: str) -> str:
    return clean_sequence(sequence).replace("T", "U")


def translate(sequence: str, frame: int = 0) -> str:
    seq = clean_sequence(sequence)
    seq = seq[frame:]
    protein: List[str] = []
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i : i + 3]
        protein.append(CODON_TABLE.get(codon, "X"))
    return "".join(protein)


def codon_usage(sequence: str) -> Dict[str, int]:
    seq = clean_sequence(sequence)
    usage: Dict[str, int] = {}
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i : i + 3]
        usage[codon] = usage.get(codon, 0) + 1
    return usage


def find_motif(sequence: str, motif: str) -> List[int]:
    seq = clean_sequence(sequence)
    motif = clean_sequence(motif)
    positions: List[int] = []
    if not motif:
        return positions
    for i in range(len(seq) - len(motif) + 1):
        if seq[i : i + len(motif)] == motif:
            positions.append(i + 1)  # one-based
    return positions


def slice_sequence(sequence: str, start: int, end: int) -> str:
    seq = clean_sequence(sequence)
    start_index = max(start - 1, 0)
    end_index = min(end, len(seq))
    return seq[start_index:end_index]


def join_sequences(parts: Iterable[str]) -> str:
    return "".join(clean_sequence(part) for part in parts)


def pretty_counts(counts: Dict[str, int]) -> str:
    sorted_items = sorted(counts.items())
    return ", ".join(f"{base}:{count}" for base, count in sorted_items)


def translate_frames(sequence: str) -> List[Tuple[int, str]]:
    seq = clean_sequence(sequence)
    frames: List[Tuple[int, str]] = []
    for frame in range(3):
        frames.append((frame + 1, translate(seq, frame)))
    return frames
