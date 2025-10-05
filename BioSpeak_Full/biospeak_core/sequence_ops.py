"""Sequence operations for BioSpeak."""
from __future__ import annotations

from dataclasses import dataclass
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


def chunk_sequence(sequence: str, size: int) -> List[str]:
    """Split a sequence into equally sized chunks."""
    seq = clean_sequence(sequence)
    if size <= 0:
        raise ValueError("Chunk size must be positive.")
    if not seq:
        return []
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def compare_sequences(first: str, second: str) -> Dict[str, float]:
    """Return simple comparison metrics for two sequences."""
    seq_a = clean_sequence(first)
    seq_b = clean_sequence(second)
    length_a = len(seq_a)
    length_b = len(seq_b)
    overlap = min(length_a, length_b)
    matches = sum(1 for i in range(overlap) if seq_a[i] == seq_b[i])
    identity = (matches / overlap * 100) if overlap else 0.0
    return {
        "length_a": float(length_a),
        "length_b": float(length_b),
        "overlap": float(overlap),
        "matches": float(matches),
        "identity": identity,
        "gaps": float(abs(length_a - length_b)),
    }


@dataclass
class OrfResult:
    """Details about a detected open reading frame."""

    start: int
    end: int
    frame: int
    length_bp: int
    length_aa: int
    protein: str


def scan_orfs(sequence: str, min_aa_length: int = 30) -> List[OrfResult]:
    """Scan a sequence for open reading frames."""

    seq = clean_sequence(sequence)
    results: List[OrfResult] = []
    if min_aa_length <= 0:
        min_aa_length = 1
    stop_codons = {"TAA", "TAG", "TGA"}
    seq_length = len(seq)
    for frame in range(3):
        i = frame
        while i <= seq_length - 3:
            codon = seq[i : i + 3]
            if codon == "ATG":
                j = i + 3
                while j <= seq_length - 3:
                    stop = seq[j : j + 3]
                    if stop in stop_codons:
                        aa_length = (j + 3 - i) // 3
                        if aa_length >= min_aa_length:
                            protein = translate(seq[i:j])
                            results.append(
                                OrfResult(
                                    start=i + 1,
                                    end=j + 3,
                                    frame=frame + 1,
                                    length_bp=(j + 3) - i,
                                    length_aa=aa_length,
                                    protein=protein,
                                )
                            )
                        break
                    j += 3
                i = j
            else:
                i += 3
    return results
