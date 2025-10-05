"""PyQt6 desktop interface for Bio Speak Studio."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

from PyQt6 import QtCore, QtGui, QtWidgets

from biospeak_core import BioSpeakEngine, CommandError

ACCENT_COLOR = "#3B82F6"


class SequenceList(QtWidgets.QListWidget):
    """Custom list widget with consistent metrics."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSpacing(8)
        self.setStyleSheet(
            (
                "QListWidget {"
                "  border: 1px solid #d0d7de;"
                "  border-radius: 6px;"
                "  padding: 8px;"
                "  background: #ffffff;"
                "}"
                "QListWidget::item {"
                "  margin: 4px;"
                "  padding: 6px 8px;"
                "  border-radius: 6px;"
                "}"
                "QListWidget::item:selected {"
                f"  background: {ACCENT_COLOR};"
                "  color: white;"
                "}"
            )
        )


class BioSpeakStudio(QtWidgets.QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.engine = BioSpeakEngine()
        self.setWindowTitle("Bio Speak Studio")
        self.resize(1200, 800)
        self.setStyleSheet(self._build_stylesheet())
        self._init_ui()
        self._refresh_sequences()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        central = QtWidgets.QWidget()
        central_layout = QtWidgets.QVBoxLayout(central)
        central_layout.setContentsMargins(16, 16, 16, 16)
        central_layout.setSpacing(16)

        self._build_toolbar()

        body = QtWidgets.QSplitter()
        body.setOrientation(QtCore.Qt.Orientation.Horizontal)
        body.setChildrenCollapsible(False)

        self.sequence_panel = self._build_sequence_panel()
        body.addWidget(self.sequence_panel)

        self.tab_widget = self._build_tab_widget()
        body.addWidget(self.tab_widget)
        body.setStretchFactor(1, 1)

        central_layout.addWidget(body)
        central_layout.addWidget(self._build_activity_bar())
        self.setCentralWidget(central)

    def _build_toolbar(self) -> None:
        toolbar = QtWidgets.QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(24, 24))
        toolbar.setStyleSheet(
            (
                "QToolBar {"
                "  background: #f8fafc;"
                "  border: 1px solid #e2e8f0;"
                "  border-radius: 6px;"
                "  padding: 8px 16px;"
                "}"
                "QToolButton {"
                "  padding: 8px 16px;"
                "  border-radius: 6px;"
                "  font-weight: 600;"
                "}"
                "QToolButton:hover {"
                f"  background: {ACCENT_COLOR};"
                "  color: white;"
                "}"
            )
        )

        load_action = QtGui.QAction("Load", self)
        load_action.triggered.connect(self._choose_file)
        toolbar.addAction(load_action)

        analyze_action = QtGui.QAction("Analyze", self)
        analyze_action.triggered.connect(self._analyze_selected)
        toolbar.addAction(analyze_action)

        translate_action = QtGui.QAction("Translate", self)
        translate_action.triggered.connect(self._translate_selected)
        toolbar.addAction(translate_action)

        align_action = QtGui.QAction("Align", self)
        align_action.triggered.connect(self._align_selected)
        toolbar.addAction(align_action)

        export_action = QtGui.QAction("Export", self)
        export_action.triggered.connect(self._export_workspace)
        toolbar.addAction(export_action)

        toolbar.addSeparator()
        theme_action = QtGui.QAction("Toggle Theme", self)
        theme_action.triggered.connect(self._toggle_theme)
        toolbar.addAction(theme_action)

        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _build_sequence_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        header = QtWidgets.QLabel("Sequences")
        header.setProperty("class", "panel-heading")
        layout.addWidget(header)

        self.sequence_list = SequenceList()
        layout.addWidget(self.sequence_list)

        quick_box = QtWidgets.QHBoxLayout()
        quick_box.setSpacing(8)

        self.gc_button = self._make_primary_button("GC %", self._gc_selected)
        self.revcomp_button = self._make_primary_button("Reverse Comp", self._reverse_selected)
        quick_box.addWidget(self.gc_button)
        quick_box.addWidget(self.revcomp_button)

        layout.addLayout(quick_box)
        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(
            (
                "QTabWidget::pane {"
                "  border: 1px solid #d0d7de;"
                "  border-radius: 6px;"
                "  background: #ffffff;"
                "}"
                "QTabBar::tab {"
                "  padding: 12px 24px;"
                "  margin: 0 4px;"
                "  border-radius: 6px;"
                "}"
                "QTabBar::tab:selected {"
                f"  background: {ACCENT_COLOR};"
                "  color: white;"
                "}"
            )
        )

        self.sequence_tools = self._build_sequence_tab()
        tabs.addTab(self.sequence_tools, "Sequence Tools")

        self.alignment_tools = self._build_alignment_tab()
        tabs.addTab(self.alignment_tools, "Alignment")

        self.results_view = self._build_results_tab()
        tabs.addTab(self.results_view, "Results")
        return tabs

    def _build_sequence_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        translate_frames = self._make_primary_button("Translate Frames", self._translate_frames)
        motif_button = self._make_primary_button("Find Motif", self._motif_search)
        orf_button = self._make_primary_button("Scan ORF", self._orf_scan)
        split_button = self._make_primary_button("Split Reads", self._split_selected)

        for button in (translate_frames, motif_button, orf_button, split_button):
            layout.addWidget(button)

        layout.addStretch(1)
        return widget

    def _build_alignment_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        global_button = self._make_primary_button("Global Align", lambda: self._align_selected(mode="global"))
        local_button = self._make_primary_button("Local Align", lambda: self._align_selected(mode="local"))
        compare_button = self._make_primary_button("Compare", self._compare_selected)
        multiple_button = self._make_primary_button("Multiple Align", self._multi_align_selected)

        for button in (global_button, local_button, compare_button, multiple_button):
            layout.addWidget(button)

        layout.addStretch(1)
        return widget

    def _build_results_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.result_title = QtWidgets.QLabel("Results")
        self.result_title.setProperty("class", "panel-heading")
        layout.addWidget(self.result_title)

        self.result_view = QtWidgets.QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.result_view)

        return widget

    def _build_activity_bar(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)

        self.status_label = QtWidgets.QLabel("Ready.")
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.progress.setFixedHeight(12)
        layout.addWidget(self.progress)
        return widget

    def _make_primary_button(self, text: str, slot: callable) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setFixedHeight(40)
        button.clicked.connect(slot)
        button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        button.setStyleSheet(
            "QPushButton {"
            f"  background: {ACCENT_COLOR};"
            "  color: white;"
            "  border: none;"
            "  border-radius: 6px;"
            "  font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "  filter: brightness(105%);"
            "}"
            "QPushButton:pressed {"
            "  filter: brightness(90%);"
            "}"
        )
        return button

    def _build_stylesheet(self) -> str:
        return (
            "QMainWindow { background: #f1f5f9; }"
            "QLabel[class='panel-heading'] { font-size: 18px; font-weight: 600; color: #0f172a; }"
            "QPlainTextEdit { border: 1px solid #d0d7de; border-radius: 6px; background: #ffffff; padding: 12px; }"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _selected_sequences(self) -> List[str]:
        return [item.text() for item in self.sequence_list.selectedItems()]

    def _refresh_sequences(self) -> None:
        self.sequence_list.clear()
        for name in self.engine.workspace.by_kind("sequence"):
            item = QtWidgets.QListWidgetItem(name)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.sequence_list.addItem(item)

    def _log(self, message: str) -> None:
        self.status_label.setText(message)

    def _show_progress(self, visible: bool) -> None:
        self.progress.setVisible(visible)

    def _run_command(self, command: str) -> None:
        try:
            result = self.engine.handle(command)
        except CommandError as exc:
            self._log(f"Error: {exc}")
            return
        except SystemExit:
            return
        self._log(result.message)
        self._refresh_sequences()
        if result.created_items:
            self._display_item(result.created_items[-1])

    def _display_item(self, name: str) -> None:
        item = self.engine.workspace.get(name)
        self.result_title.setText(name)
        if hasattr(item, "sequence"):
            text = f"> {item.description or name}\n{item.sequence}"
        elif hasattr(item, "lines"):
            text = "\n".join(item.lines)
        elif hasattr(item, "rows"):
            headers = "\t".join(item.headers)
            rows = ["\t".join(map(str, row)) for row in item.rows]
            text = "\n".join([headers, *rows])
        else:
            text = str(item)
        self.result_view.setPlainText(text)

    def _choose_file(self) -> None:
        dialog = QtWidgets.QFileDialog(self, "Load Bio Speak Data")
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilters([
            "Sequences (*.fasta *.fa *.fna *.fastq *.fq *.gb *.gbk *.gff *.vcf *.bam)",
            "Tables (*.csv *.tsv *.txt *.json)",
            "All files (*.*)",
        ])
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        file_path = Path(dialog.selectedFiles()[0])
        command = self._command_for_file(file_path)
        self._run_command(command)

    def _command_for_file(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        name = file_path.stem.replace(" ", "_")
        if suffix in {".fasta", ".fa", ".fna"}:
            return f"load dna file {file_path} as {name}"
        if suffix in {".fastq", ".fq"}:
            return f"load fastq file {file_path} as {name}"
        if suffix in {".gb", ".gbk"}:
            return f"load genbank file {file_path} as {name}"
        if suffix == ".gff":
            return f"load gff file {file_path} as {name}"
        if suffix == ".vcf":
            return f"load vcf file {file_path} as {name}"
        if suffix == ".bam":
            return f"load bam file {file_path} as {name}"
        if suffix in {".csv", ".tsv", ".txt"}:
            return f"load table file {file_path} as {name}"
        if suffix == ".json":
            return f"load json file {file_path} as {name}"
        return f"load dna file {file_path} as {name}"

    def _analyze_selected(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select at least one sequence to analyze.")
            return
        for name in names:
            self._run_command(f"count gc of {name}")
            self._run_command(f"count bases of {name}")

    def _translate_selected(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to translate.")
            return
        for name in names:
            self._run_command(f"translate {name} as {name}_aa")

    def _translate_frames(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to translate frames.")
            return
        for name in names:
            self._run_command(f"translate frames of {name} as {name}_frames")

    def _motif_search(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to search.")
            return
        motif, ok = QtWidgets.QInputDialog.getText(self, "Motif", "Enter motif:")
        if not ok or not motif:
            return
        for name in names:
            self._run_command(f"find motif {motif} in {name}")

    def _orf_scan(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to scan.")
            return
        length, ok = QtWidgets.QInputDialog.getInt(self, "Scan ORF", "Minimum length", value=90, min=1)
        if not ok:
            return
        for name in names:
            self._run_command(f"scan orf of {name} minimum {length} as {name}_orf")

    def _split_selected(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to split.")
            return
        size, ok = QtWidgets.QInputDialog.getInt(self, "Split", "Length per chunk", value=100)
        if not ok:
            return
        for name in names:
            self._run_command(f"split {name} every {size} as {name}_part")

    def _gc_selected(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to measure GC%.")
            return
        for name in names:
            self._run_command(f"count gc of {name}")

    def _reverse_selected(self) -> None:
        names = self._selected_sequences()
        if not names:
            self._log("Select a sequence to reverse complement.")
            return
        for name in names:
            self._run_command(f"reverse complement {name} as {name}_revcomp")

    def _align_selected(self, mode: str = "global") -> None:
        names = self._selected_sequences()
        if len(names) < 2:
            self._log("Select at least two sequences to align.")
            return
        first, second, *rest = names
        command = f"align {first} with {second} as {first}_{second}_{mode} using {mode}"
        self._run_command(command)
        if rest:
            self._log("Only the first two sequences were aligned; deselect extras for clarity.")

    def _multi_align_selected(self) -> None:
        names = self._selected_sequences()
        if len(names) < 3:
            self._log("Select three or more sequences for multiple alignment.")
            return
        joined = " ".join(names)
        self._run_command(f"align group {joined} as {'_'.join(names)} using mafft")

    def _compare_selected(self) -> None:
        names = self._selected_sequences()
        if len(names) != 2:
            self._log("Select exactly two sequences to compare.")
            return
        self._run_command(f"compare {names[0]} with {names[1]}")

    def _export_workspace(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Workspace", filter="JSON (*.json)")
        if not file_path:
            return
        command = f"export sequences to {file_path}"
        self._run_command(command)

    def _toggle_theme(self) -> None:
        palette = self.palette()
        base = palette.color(QtGui.QPalette.ColorRole.Window)
        if base.lightness() > 200:
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _apply_light_theme(self) -> None:
        self.setStyleSheet(self._build_stylesheet())
        self._log("Light theme active.")

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(
            "QMainWindow { background: #0f172a; color: #e2e8f0; }"
            "QLabel[class='panel-heading'] { color: #38bdf8; }"
            "QPlainTextEdit { background: #1e293b; color: #f8fafc; border: 1px solid #334155; }"
            "QListWidget { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; }"
            "QToolBar { background: #1e293b; border: 1px solid #334155; }"
        )
        self._log("Dark theme active.")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Bio Speak Studio")
    font = QtGui.QFont("Segoe UI", 10)
    app.setFont(font)
    window = BioSpeakStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
