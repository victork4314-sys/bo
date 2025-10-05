"""Alignment routines for BioLang."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class AlignmentResult:
    """Result lines, score, and traceback for an alignment."""

    lines: List[str]
    score: float
    path: List[Tuple[int, int]]


MATCH_SCORE = 2
MISMATCH_SCORE = -1
GAP_SCORE = -2


def _score(a: str, b: str) -> int:
    return MATCH_SCORE if a == b else MISMATCH_SCORE


def needleman_wunsch(seq_a: str, seq_b: str) -> AlignmentResult:
    len_a = len(seq_a)
    len_b = len(seq_b)
    scores = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(1, len_a + 1):
        scores[i][0] = i * GAP_SCORE
    for j in range(1, len_b + 1):
        scores[0][j] = j * GAP_SCORE

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            match = scores[i - 1][j - 1] + _score(seq_a[i - 1], seq_b[j - 1])
            delete = scores[i - 1][j] + GAP_SCORE
            insert = scores[i][j - 1] + GAP_SCORE
            scores[i][j] = max(match, delete, insert)

    aligned_a: List[str] = []
    aligned_b: List[str] = []
    match_line: List[str] = []
    i, j = len_a, len_b
    path: List[Tuple[int, int]] = []
    while i > 0 or j > 0:
        current = scores[i][j]
        path.append((i, j))
        if i > 0 and j > 0 and current == scores[i - 1][j - 1] + _score(seq_a[i - 1], seq_b[j - 1]):
            aligned_a.append(seq_a[i - 1])
            aligned_b.append(seq_b[j - 1])
            match_line.append("|") if seq_a[i - 1] == seq_b[j - 1] else match_line.append(" ")
            i -= 1
            j -= 1
        elif i > 0 and current == scores[i - 1][j] + GAP_SCORE:
            aligned_a.append(seq_a[i - 1])
            aligned_b.append("-")
            match_line.append(" ")
            i -= 1
        else:
            aligned_a.append("-")
            aligned_b.append(seq_b[j - 1])
            match_line.append(" ")
            j -= 1

    aligned_a.reverse()
    aligned_b.reverse()
    match_line.reverse()
    lines = ["".join(aligned_a), "".join(match_line), "".join(aligned_b)]
    path.reverse()
    return AlignmentResult(lines=lines, score=scores[len_a][len_b], path=path)


def smith_waterman(seq_a: str, seq_b: str) -> AlignmentResult:
    len_a = len(seq_a)
    len_b = len(seq_b)
    scores = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    max_score = 0
    max_pos = (0, 0)

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            match = scores[i - 1][j - 1] + _score(seq_a[i - 1], seq_b[j - 1])
            delete = scores[i - 1][j] + GAP_SCORE
            insert = scores[i][j - 1] + GAP_SCORE
            scores[i][j] = max(0, match, delete, insert)
            if scores[i][j] > max_score:
                max_score = scores[i][j]
                max_pos = (i, j)

    aligned_a: List[str] = []
    aligned_b: List[str] = []
    match_line: List[str] = []
    i, j = max_pos
    path: List[Tuple[int, int]] = []
    while i > 0 and j > 0 and scores[i][j] > 0:
        path.append((i, j))
        if scores[i][j] == scores[i - 1][j - 1] + _score(seq_a[i - 1], seq_b[j - 1]):
            aligned_a.append(seq_a[i - 1])
            aligned_b.append(seq_b[j - 1])
            match_line.append("|") if seq_a[i - 1] == seq_b[j - 1] else match_line.append(" ")
            i -= 1
            j -= 1
        elif scores[i][j] == scores[i - 1][j] + GAP_SCORE:
            aligned_a.append(seq_a[i - 1])
            aligned_b.append("-")
            match_line.append(" ")
            i -= 1
        else:
            aligned_a.append("-")
            aligned_b.append(seq_b[j - 1])
            match_line.append(" ")
            j -= 1

    aligned_a.reverse()
    aligned_b.reverse()
    match_line.reverse()
    lines = ["".join(aligned_a), "".join(match_line), "".join(aligned_b)]
    path.reverse()
    return AlignmentResult(lines=lines, score=max_score, path=path)
