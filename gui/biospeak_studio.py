"""BioSpeak Studio - graphical front end built with PyQt6."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6 import QtCore, QtGui, QtWidgets

from biospeak_core import BioSpeakEngine, CommandError
from biospeak_core.data import AlignmentItem, SequenceItem, TableItem


class BioSpeakStudio(QtWidgets.QMainWindow):
    """Apple-inspired desktop application for BioSpeak."""

    def __init__(self) -> None:
        super().__init__()
        self.engine = BioSpeakEngine()
        self.registry = self.engine.registry
        self.setWindowTitle("BioSpeak Studio")
        self.resize(1280, 840)
        self._apply_palette()
        self._build_interface()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _apply_palette(self) -> None:
        palette = self.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#f5f5f7"))
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#ffffff"))
        palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#eef1f6"))
        palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#ffffff"))
        palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#1c1c1e"))
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#1c1c1e"))
        self.setPalette(palette)
        self.setStyleSheet(
            """
            QMainWindow { background-color: #f5f5f7; }
            QListWidget { background: #ffffff; border: 1px solid #d2d2d7; border-radius: 12px; padding: 6px; }
            QTextEdit { background: #ffffff; border: 1px solid #d2d2d7; border-radius: 12px; padding: 12px; }
            QPushButton { background: #ffffff; border: 1px solid #d2d2d7; border-radius: 18px; padding: 8px 18px; font-weight: 600; }
            QPushButton:hover { background: #e5e5ea; }
            QToolBar { background: #f5f5f7; border: none; padding: 10px; }
            QLabel#Title { font-size: 20px; font-weight: 600; color: #1c1c1e; }
            QLabel#Subtitle { font-size: 14px; color: #636366; }
            QTableWidget { background: #ffffff; border: 1px solid #d2d2d7; border-radius: 12px; gridline-color: #d2d2d7; }
            """
        )

    def _build_interface(self) -> None:
        toolbar = QtWidgets.QToolBar()
        toolbar.setIconSize(QtCore.QSize(28, 28))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._add_toolbar_button(toolbar, "Load", "document-open", self._load_sequences)
        self._add_toolbar_button(toolbar, "Analyze", "view-statistics", self._analyze_sequence)
        self._add_toolbar_button(toolbar, "Translate", "arrow-right", self._translate_sequence)
        self._add_toolbar_button(toolbar, "Align", "insert-link", self._align_selected)
        self._add_toolbar_button(toolbar, "Export", "document-save", self._export_sequences)

        container = QtWidgets.QWidget()
        main_layout = QtWidgets.QHBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Side panel
        side_panel = QtWidgets.QWidget()
        side_layout = QtWidgets.QVBoxLayout(side_panel)
        side_layout.setSpacing(12)

        title = QtWidgets.QLabel("Workspace")
        title.setObjectName("Title")
        side_layout.addWidget(title)

        self.sequence_list = QtWidgets.QListWidget()
        self.sequence_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.sequence_list.itemSelectionChanged.connect(self._show_sequence_details)

        self.table_list = QtWidgets.QListWidget()
        self.table_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table_list.itemSelectionChanged.connect(self._show_table_details)

        self.alignment_list = QtWidgets.QListWidget()
        self.alignment_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.alignment_list.itemSelectionChanged.connect(self._show_alignment_details)

        side_layout.addWidget(QtWidgets.QLabel("Sequences", parent=side_panel))
        side_layout.addWidget(self.sequence_list, 1)
        side_layout.addWidget(QtWidgets.QLabel("Tables", parent=side_panel))
        side_layout.addWidget(self.table_list, 1)
        side_layout.addWidget(QtWidgets.QLabel("Alignments", parent=side_panel))
        side_layout.addWidget(self.alignment_list, 1)

        action_box = QtWidgets.QGroupBox("Quick Actions")
        action_layout = QtWidgets.QGridLayout(action_box)
        action_layout.setHorizontalSpacing(12)
        action_layout.setVerticalSpacing(12)

        self._add_action_button(action_layout, 0, 0, "Split", self._split_sequence)
        self._add_action_button(action_layout, 0, 1, "Merge", self._merge_sequences)
        self._add_action_button(action_layout, 1, 0, "Compare", self._compare_sequences)
        self._add_action_button(action_layout, 1, 1, "GC", self._gc_content)
        self._add_action_button(action_layout, 2, 0, "Frames", self._orf_scan)
        self._add_action_button(action_layout, 2, 1, "Reverse", self._reverse_complement)

        side_layout.addWidget(action_box)

        # Main area
        self.tabs = QtWidgets.QTabWidget()
        self.summary_text = QtWidgets.QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setObjectName("Summary")

        self.alignment_table = QtWidgets.QTableWidget()
        self.alignment_table.setColumnCount(0)
        self.alignment_table.setRowCount(0)
        self.alignment_table.horizontalHeader().setVisible(False)
        self.alignment_table.verticalHeader().setVisible(False)
        self.alignment_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        self.table_view = QtWidgets.QTableWidget()
        self.table_view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        self.plot_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.plot_label.setMinimumHeight(260)
        self.plot_label.setStyleSheet("border: 1px solid #d2d2d7; border-radius: 12px; background: #ffffff;")

        self.tabs.addTab(self.summary_text, "Summary")
        self.tabs.addTab(self.plot_label, "Plots")
        self.tabs.addTab(self.alignment_table, "Alignment")
        self.tabs.addTab(self.table_view, "Tables")

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        self.log_view.setPlaceholderText("Activity log")

        main_layout.addWidget(side_panel, 1)
        main_layout.addWidget(self.tabs, 3)

        frame = QtWidgets.QWidget()
        frame_layout = QtWidgets.QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(16)
        frame_layout.addWidget(container, 1)
        frame_layout.addWidget(self.log_view)

        self.setCentralWidget(frame)
        self._refresh_lists()

    def _add_toolbar_button(self, toolbar: QtWidgets.QToolBar, text: str, icon: str, slot) -> None:
        action = QtGui.QAction(text, self)
        action.triggered.connect(slot)
        toolbar.addAction(action)

    def _add_action_button(self, layout: QtWidgets.QGridLayout, row: int, column: int, text: str, slot) -> None:
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(slot)
        layout.addWidget(button, row, column)

    # ------------------------------------------------------------------
    # Workspace updates
    # ------------------------------------------------------------------
    def _refresh_lists(self) -> None:
        self.sequence_list.clear()
        for name in self.engine.workspace.by_kind("sequence"):
            self.sequence_list.addItem(name)
        self.table_list.clear()
        for name in self.engine.workspace.by_kind("table"):
            self.table_list.addItem(name)
        self.alignment_list.clear()
        for name in self.engine.workspace.by_kind("alignment"):
            self.alignment_list.addItem(name)

    def _log(self, message: str) -> None:
        self.log_view.append(message)

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------
    def _load_sequences(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load sequences",
            str(Path.cwd()),
            "Sequence files (*.fasta *.fa *.fna *.faa *.fastq *.fq *.gb *.gbk *.gff *.vcf *.bam *.csv *.tsv)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        base = Path(path).stem.replace(" ", "_")
        try:
            if suffix in {".fastq", ".fq"}:
                command = f"load fastq file {path} as {base}"
            elif suffix in {".gb", ".gbk"}:
                command = f"load genbank file {path} as {base}"
            elif suffix in {".gff"}:
                command = f"load gff file {path} as {base}"
            elif suffix in {".vcf"}:
                command = f"load vcf file {path} as {base}"
            elif suffix in {".bam"}:
                command = f"load bam file {path} as {base}"
            elif suffix in {".csv", ".tsv"}:
                command = f"load table file {path} as {base}"
            else:
                command = f"load dna file {path} as {base}"
            result = self.engine.handle(command)
            self._log(result.message)
            self._refresh_lists()
        except (CommandError, Exception) as error:
            QtWidgets.QMessageBox.critical(self, "Load failed", str(error))

    def _analyze_sequence(self) -> None:
        selection = self._selected_sequence_names()
        if not selection:
            QtWidgets.QMessageBox.information(self, "No selection", "Select one sequence to analyze.")
            return
        name = selection[0]
        try:
            result = self.engine.handle(f"describe {name}")
            self.summary_text.setPlainText(result.message)
            self._log(result.message)
            self.tabs.setCurrentWidget(self.summary_text)
            self._update_plot(name)
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Analyze failed", str(error))

    def _translate_sequence(self) -> None:
        selection = self._selected_sequence_names()
        if not selection:
            QtWidgets.QMessageBox.information(self, "No selection", "Select a sequence to translate.")
            return
        name = selection[0]
        new_name = f"{name}_protein"
        try:
            result = self.engine.handle(f"translate {name} as {new_name}")
            self._log(result.message)
            self._refresh_lists()
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Translate failed", str(error))

    def _align_selected(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) < 2:
            QtWidgets.QMessageBox.information(self, "Need sequences", "Pick two or more sequences to align.")
            return
        if len(selection) == 2:
            first, second = selection
            new_name = f"align_{first}_{second}"
            try:
                result = self.engine.handle(f"align {first} with {second} as {new_name} using global")
                self._log(result.message)
                self._refresh_lists()
            except CommandError as error:
                QtWidgets.QMessageBox.critical(self, "Align failed", str(error))
        else:
            new_name = f"group_{selection[0]}"
            try:
                result = self.engine.handle(f"align group {' '.join(selection)} as {new_name}")
                self._log(result.message)
                self._refresh_lists()
            except CommandError as error:
                QtWidgets.QMessageBox.critical(self, "Align failed", str(error))

    def _export_sequences(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export sequences", str(Path.cwd() / "biolang_sequences.fasta"), "FASTA (*.fasta)")
        if not path:
            return
        try:
            result = self.engine.handle(f"export sequences to {path}")
            self._log(result.message)
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(error))

    # ------------------------------------------------------------------
    # Quick actions
    # ------------------------------------------------------------------
    def _split_sequence(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) != 1:
            QtWidgets.QMessageBox.information(self, "Split", "Select one sequence to split.")
            return
        name = selection[0]
        start, ok = QtWidgets.QInputDialog.getInt(self, "Split", "Start position", value=1, min=1)
        if not ok:
            return
        end, ok = QtWidgets.QInputDialog.getInt(self, "Split", "End position", value=start + 99, min=start)
        if not ok:
            return
        new_name = f"{name}_slice_{start}_{end}"
        try:
            result = self.engine.handle(f"slice {name} from {start} to {end} as {new_name}")
            self._log(result.message)
            self._refresh_lists()
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Split failed", str(error))

    def _merge_sequences(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) != 2:
            QtWidgets.QMessageBox.information(self, "Merge", "Select exactly two sequences to merge.")
            return
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Merge", "Name for merged sequence", text=f"{selection[0]}_{selection[1]}_merged")
        if not ok or not new_name.strip():
            return
        try:
            result = self.engine.handle(f"join {selection[0]} with {selection[1]} as {new_name.strip()}")
            self._log(result.message)
            self._refresh_lists()
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Merge failed", str(error))

    def _compare_sequences(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) != 2:
            QtWidgets.QMessageBox.information(self, "Compare", "Select two sequences to compare.")
            return
        first, second = selection
        try:
            result = self.engine.handle(f"align {first} with {second} as compare_{first}_{second} using local")
            self._log(result.message)
            self._refresh_lists()
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Compare failed", str(error))

    def _gc_content(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) != 1:
            QtWidgets.QMessageBox.information(self, "GC content", "Select one sequence to measure.")
            return
        name = selection[0]
        try:
            result = self.engine.handle(f"count gc of {name}")
            QtWidgets.QMessageBox.information(self, "GC content", result.message)
            self._log(result.message)
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "GC failed", str(error))

    def _orf_scan(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) != 1:
            QtWidgets.QMessageBox.information(self, "Frames", "Select one sequence to scan.")
            return
        name = selection[0]
        try:
            result = self.engine.handle(f"translate frames of {name} as {name}_frames")
            self._log(result.message)
            self._refresh_lists()
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Frames failed", str(error))

    def _reverse_complement(self) -> None:
        selection = self._selected_sequence_names()
        if len(selection) != 1:
            QtWidgets.QMessageBox.information(self, "Reverse", "Select one sequence to reverse complement.")
            return
        name = selection[0]
        try:
            result = self.engine.handle(f"reverse complement {name} as {name}_rc")
            self._log(result.message)
            self._refresh_lists()
        except CommandError as error:
            QtWidgets.QMessageBox.critical(self, "Reverse failed", str(error))

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _selected_sequence_names(self) -> List[str]:
        return [item.text() for item in self.sequence_list.selectedItems()]

    def _show_sequence_details(self) -> None:
        selection = self._selected_sequence_names()
        if not selection:
            self.summary_text.clear()
            self.plot_label.clear()
            return
        name = selection[0]
        item = self.engine.workspace.items.get(name)
        if isinstance(item, SequenceItem):
            self.summary_text.setPlainText(
                f"Name: {item.name}\nType: {item.alphabet}\nLength: {len(item.sequence)}\nDescription: {item.description}"
            )
            self._update_plot(name)
            self.tabs.setCurrentWidget(self.summary_text)

    def _show_table_details(self) -> None:
        items = self.table_list.selectedItems()
        if not items:
            return
        name = items[0].text()
        table = self.engine.workspace.items.get(name)
        if not isinstance(table, TableItem):
            return
        headers = table.headers or [f"Column {i+1}" for i in range(len(table.rows[0]) if table.rows else 0)]
        self.table_view.clear()
        self.table_view.setRowCount(len(table.rows))
        self.table_view.setColumnCount(len(headers))
        self.table_view.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(table.rows):
            for column_index, value in enumerate(row):
                item_widget = QtWidgets.QTableWidgetItem(value)
                self.table_view.setItem(row_index, column_index, item_widget)
        self.tabs.setCurrentWidget(self.table_view)

    def _show_alignment_details(self) -> None:
        items = self.alignment_list.selectedItems()
        if not items:
            return
        name = items[0].text()
        alignment = self.engine.workspace.items.get(name)
        if not isinstance(alignment, AlignmentItem):
            return
        lines = alignment.lines
        self.alignment_table.clear()
        self.alignment_table.setRowCount(len(lines))
        self.alignment_table.setColumnCount(len(lines[0]) if lines else 0)
        for row_index, line in enumerate(lines):
            for column_index, char in enumerate(line):
                cell = QtWidgets.QTableWidgetItem(char)
                if len(lines) >= 2 and row_index < len(lines) - 1:
                    if all(len(line) > column_index for line in lines[:2]):
                        a = lines[0][column_index]
                        b = lines[-1][column_index]
                        if a == b and a != "-":
                            cell.setBackground(QtGui.QColor("#d1f7c4"))
                cell.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.alignment_table.setItem(row_index, column_index, cell)
        self.tabs.setCurrentWidget(self.alignment_table)

    # ------------------------------------------------------------------
    # Visualization helpers
    # ------------------------------------------------------------------
    def _update_plot(self, name: str) -> None:
        item = self.engine.workspace.items.get(name)
        if not isinstance(item, SequenceItem):
            self.plot_label.clear()
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            self.registry.plot_sequence_metrics(name, item.sequence, temp_path)
            if temp_path.exists() and temp_path.suffix.lower() == ".png":
                pixmap = QtGui.QPixmap(str(temp_path))
                self.plot_label.setPixmap(pixmap)
            else:
                self.plot_label.setText(temp_path.read_text(encoding="utf-8"))
        except Exception as error:  # pragma: no cover - visualization fallback
            self.plot_label.setText(str(error))
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)


def main() -> None:
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = BioSpeakStudio()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
