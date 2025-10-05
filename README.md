# Bio Speak — Browser Studio

Bio Speak now runs entirely in the browser. All bioinformatics logic lives in a
shared Python package that is compiled for Pyodide, while the single-page
application delivers the Apple-inspired interface for every workflow.

## Project Layout

```
/core/           biospeak_core package used by Pyodide and future builds
/web/            static HTML, CSS, and JavaScript for the Vue + Plotly interface
/dist/           build output created by the web packaging scripts
build_web.sh     Linux/macOS bundler that prepares an offline distribution
build_web.bat    Windows bundler that prepares an offline distribution
```

* **core/biospeak_core** contains the Bio Speak command engine, alignment
  routines, FASTA/FASTQ/GenBank/GFF/VCF/BAM parsers, tabular analytics, plotting
  helpers, and a `web_api` bridge used by the SPA.
* **web/** presents the rounded macOS-inspired UI with Vue 3, Plotly, and the
  Pyodide runtime loader. Drag files in, trigger verbs from the toolbar, and see
  synchronized results in the same workspace snapshot the Python engine uses.
* **build scripts** fetch Pyodide, copy the core package, generate a file-map
  report, and leave a `/dist` folder that can be zipped and opened offline in
  any standards-compliant browser.

## Building the Web Edition

### Linux or macOS

```
./build_web.sh
```

### Windows

```
build_web.bat
```

Both scripts perform the same sequence:

1. Compile the Python sources to confirm syntax.
2. Generate `dist/file-map.json` with a recursive inventory for auditing.
3. Copy `/web` and `/core` into `dist/`.
4. Download the requested Pyodide release (defaults to 0.24.1) and place it in
   `dist/pyodide/` so the app runs offline after the first build.
5. Print `Build complete — web version operational` to signal success.

Set `PYODIDE_VERSION` before running either script to lock to a specific
release.

## Using Bio Speak Studio (Web)

Open `dist/index.html` in any modern browser. The app keeps everything client
side—no server required.

* **Dropdown menus**: Files (Load, Reset, Export), Sequence (Analyze, Translate,
  Reverse Complement, GC %, Split, Merge, ORF Scan), Align (Pairwise Global,
  Pairwise Local, Compare, Multiple Align).
* **Drag-and-drop loader**: FASTA/FASTQ/GenBank/GFF/VCF/BAM/CSV/TSV/JSON files
  are written into the in-browser filesystem and parsed by the Python engine.
* **Sequence panel**: Rounded cards with checkboxes for selecting sequences.
* **Alignment panel**: Click any result to preview the color-coded alignment.
* **Workspace cards**: Activity log, textual previews, GC% bars, and length
  histograms rendered by Plotly.
* **Export**: Saves the entire workspace (sequences, tables, alignments,
  reports) as a JSON snapshot you can reload later.

Everything the interface does flows through `biospeak_core`—all verbs are the
same ones used in the classic CLI, ensuring identical outputs across platforms.

## Core Capabilities

Bio Speak retains the full natural-language command set:

* **Loading**: `load dna file PATH as NAME`, `load fastq file PATH as NAME`,
  `load genbank file PATH as NAME`, `load gff file PATH as NAME`, `load vcf file
  PATH as NAME`, `load bam file PATH as NAME`, `load table file PATH as NAME`,
  `load json file PATH as NAME`.
* **Sequencing verbs**: `count gc of NAME`, `count bases of NAME`, `count
  codons of NAME`, `find motif MOTIF in NAME`, `slice NAME from START to END as
  NEW`, `split NAME every LENGTH as BASE`, `join FIRST with SECOND as NEW`,
  `reverse complement NAME as NEW`, `transcribe NAME as NEW`, `translate NAME
  as NEW`, `translate frames of NAME as NEW`, `scan orf of NAME minimum LENGTH
  as BASE`.
* **Alignment**: `align FIRST with SECOND as NAME using global|local`,
  `compare FIRST with SECOND`, `align group NAME1 NAME2 ... as NAME using
  mafft|clustal` (delegates to the integration registry when tools are
  available).
* **Reporting**: `make report for NAME as REPORT`, `write report of NAME to
  file PATH`, `export sequences to PATH`, `export table TABLE to PATH`.
* **Inventory**: `list data`, `list sequences`, `list tables`, `show NAME`,
  `describe NAME`, `make file map`.

The SPA issues these commands through the `web_api` helpers so every action stays
in sync with the Python workspace.

## Self Verification

The build scripts already run the Python compiler and emit `file-map.json`. To
manually inspect the project tree, run:

```
python - <<'PY'
from pathlib import Path
from biospeak_core.filemap import generate_file_map
print(generate_file_map(Path('.')))
PY
```

When the bundler prints **“Build complete — web version operational”** the web
edition is ready to ship and runs the full Bio Speak feature set offline.
