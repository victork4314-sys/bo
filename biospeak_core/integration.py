"""Integration helpers for third-party bioinformatics libraries."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .alignment import needleman_wunsch
from .data import TableItem
from .sequence_ops import gc_content


def _optional_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:  # pragma: no cover - defensive against many import errors
        return None


@dataclass
class IntegrationRegistry:
    """Tracks availability of external libraries and exposes shared helpers."""

    modules: Dict[str, object]

    def __init__(self) -> None:
        self.modules = {}
        self.bio = self._load("Bio")
        self.seqio = self._load("Bio.SeqIO") if self.bio else None
        self.phylo = self._load("Bio.Phylo") if self.bio else None
        self.scikit_bio = self._load("skbio")
        self.pysam = self._load("pysam")
        self.ete3 = self._load("ete3")
        self.numpy = self._load("numpy")
        self.pandas = self._load("pandas")
        self.matplotlib = self._load("matplotlib")
        self.pyplot = self._load("matplotlib.pyplot") if self.matplotlib else None
        self.plotly = self._load("plotly")
        self.plotly_graph_objects = self._load("plotly.graph_objects") if self.plotly else None
        self.seaborn = self._load("seaborn")
        self.sklearn = self._load("sklearn")
        self.tensorflow = self._load("tensorflow")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def describe(self) -> str:
        lines = ["Integration status:"]
        for key, label in [
            ("bio", "Biopython"),
            ("scikit_bio", "scikit-bio"),
            ("pysam", "pysam"),
            ("ete3", "ete3"),
            ("numpy", "NumPy"),
            ("pandas", "pandas"),
            ("matplotlib", "matplotlib"),
            ("plotly", "plotly"),
            ("seaborn", "seaborn"),
            ("sklearn", "scikit-learn"),
            ("tensorflow", "TensorFlow"),
        ]:
            module = getattr(self, key)
            lines.append(f"- {label}: {'ready' if module else 'missing'}")
        return "\n".join(lines)

    def multiple_alignment(
        self, names: Sequence[str], sequences: Sequence[str]
    ) -> Tuple[List[str], float, str]:
        if self.scikit_bio is not None:
            return self._msa_with_skbio(names, sequences)
        if self.bio is not None:
            return self._msa_with_biopython(names, sequences)
        return self._msa_progressive(names, sequences)

    def describe_table(self, table: TableItem) -> str:
        if self.pandas is not None:
            import pandas as pd  # type: ignore

            frame = pd.DataFrame(table.rows, columns=table.headers or None)
            buffer = [f"Rows: {len(frame)}", f"Columns: {len(frame.columns)}"]
            if not frame.empty:
                try:
                    buffer.append(frame.describe(include="all").fillna("").to_string())
                except Exception:
                    buffer.append(frame.head(10).to_string())
            else:
                buffer.append("No rows available")
            return "\n".join(str(part) for part in buffer)
        header_line = ", ".join(table.headers) if table.headers else "no headers"
        return f"Rows: {len(table.rows)}\nHeaders: {header_line}"

    def plot_sequence_metrics(self, name: str, sequence: str, target: Path) -> None:
        gc = gc_content(sequence)
        lengths = list(range(1, len(sequence) + 1))
        gc_curve = [gc_content(sequence[:index]) for index in lengths]
        if self.pyplot is not None:
            import matplotlib.pyplot as plt  # type: ignore

            fig, axes = plt.subplots(2, 1, figsize=(8, 6), tight_layout=True)
            axes[0].plot(lengths, gc_curve, color="#007aff")
            axes[0].set_title(f"GC% trend for {name}")
            axes[0].set_xlabel("Length")
            axes[0].set_ylabel("GC%")
            axes[1].bar(["GC"], [gc], color="#34c759")
            axes[1].set_ylim(0, 100)
            axes[1].set_ylabel("GC%")
            axes[1].set_title("Overall GC content")
            fig.savefig(target)
            plt.close(fig)
        elif self.plotly_graph_objects is not None:
            import plotly.graph_objects as go  # type: ignore

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=lengths, y=gc_curve, name="GC%", line=dict(color="#007aff")))
            fig.add_trace(
                go.Bar(x=["GC"], y=[gc], name="Overall", marker=dict(color="#34c759"), yaxis="y2")
            )
            fig.update_layout(
                title=f"GC metrics for {name}",
                yaxis=dict(title="GC%"),
                yaxis2=dict(title="Overall", overlaying="y", side="right"),
            )
            if target.suffix.lower() == ".html":
                fig.write_html(target)
            else:
                # fall back to HTML export when static image support is unavailable
                fig.write_html(target.with_suffix(target.suffix + ".html"))
                target.write_text("plotly output saved as HTML", encoding="utf-8")
        else:
            target.write_text(
                f"Sequence {name}\nLength: {len(sequence)}\nGC%: {gc:.2f}",
                encoding="utf-8",
            )

    def build_phylogeny(self, sequences: Dict[str, str]):
        if self.ete3 is not None:
            from ete3 import Tree  # type: ignore

            # create a simple star topology for the provided sequences
            newick = "(" + ",".join(f"{name}:1" for name in sequences.keys()) + ");"
            return Tree(newick)
        if self.phylo is not None:
            from Bio.Phylo.Newick import Tree  # type: ignore

            terminals = [self.phylo.Newick.Clade(name=name) for name in sequences]
            tree = self.phylo.Newick.Tree(root=self.phylo.Newick.Clade(branch_length=1.0))
            tree.root.clades.extend(terminals)
            return tree
        # fall back to a simple dict representation
        return {"root": list(sequences.keys())}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self, name: str):
        module = _optional_import(name)
        self.modules[name] = module
        return module

    def _msa_with_skbio(
        self, names: Sequence[str], sequences: Sequence[str]
    ) -> Tuple[List[str], float, str]:
        from skbio import DNA, TabularMSA  # type: ignore

        msa = TabularMSA([DNA(seq) for seq in sequences])
        msa.reassign_index(names)
        lines = [f"{name}: {str(record)}" for name, record in zip(names, msa)]
        score = self._pairwise_consistency_score(sequences)
        return lines, score, "scikit-bio MSA"

    def _msa_with_biopython(
        self, names: Sequence[str], sequences: Sequence[str]
    ) -> Tuple[List[str], float, str]:
        from Bio.Align import MultipleSeqAlignment  # type: ignore
        from Bio.Seq import Seq  # type: ignore
        from Bio.SeqRecord import SeqRecord  # type: ignore

        records = [SeqRecord(Seq(seq), id=name) for name, seq in zip(names, sequences)]
        alignment = MultipleSeqAlignment(records)
        lines = [f"{record.id}: {str(record.seq)}" for record in alignment]
        score = self._pairwise_consistency_score(sequences)
        return lines, score, "Biopython MSA"

    def _msa_progressive(
        self, names: Sequence[str], sequences: Sequence[str]
    ) -> Tuple[List[str], float, str]:
        if not sequences:
            return [], 0.0, ""
        combined_lines = [f"{name}: {seq}" for name, seq in zip(names, sequences)]
        total_score = 0.0
        if len(sequences) > 1:
            for i in range(len(sequences) - 1):
                result = needleman_wunsch(sequences[i], sequences[i + 1])
                total_score += result.score
        return combined_lines, float(total_score), "progressive needleman-wunsch"

    def _pairwise_consistency_score(self, sequences: Sequence[str]) -> float:
        if len(sequences) < 2:
            return 0.0
        pairs = 0
        total = 0.0
        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                total += gc_content(sequences[i] + sequences[j])
                pairs += 1
        return total / pairs if pairs else 0.0

