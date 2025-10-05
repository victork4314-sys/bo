# Bio Speak Platform

Bio Speak delivers a natural-language bioinformatics environment with a unified
core and two coordinated front ends. Every workflow is driven by plain verbs so
teams can operate complex analyses without learning code syntax.

## Architecture

```
/biospeak_core   shared engine, integrations, workspace, and utilities
/cli             terminal launcher that becomes biospeak.exe
/gui             Bio Speak Studio PyQt6 application (Bio Speak Studio.exe)
/examples        demo .bio scripts
```

* **biospeak_core** hosts the command engine, workspace models, optional
  third-party integrations (Biopython, scikit-bio, pysam, ete3, pandas,
  NumPy, matplotlib, plotly, seaborn, scikit-learn, TensorFlow), rich I/O for
  FASTA/FASTQ/GenBank/GFF/VCF/BAM/CSV/TSV/JSON, visual plotting helpers, and a
  self-test harness.
* **CLI** exposes the engine as a REPL, script runner, verifier, portable bundle
  creator, and integration reporter.
* **GUI** provides Bio Speak Studio with an Apple-inspired interface featuring
  toolbar verbs, a file side panel, visual FASTA/FASTQ tools, color-coded
  alignments, and embedded charts backed by the same core functions as the CLI.

## Windows Setup (installs everything and builds executables)

Run the included batch script from an elevated or standard Command Prompt:

```
setup.bat
```

The script performs the following steps:

1. Creates a virtual environment at `venv`.
2. Installs all required libraries (Biopython, scikit-bio, pysam, ete3, pandas,
   numpy, matplotlib, plotly, seaborn, scikit-learn, tensorflow, PyQt6,
   PyInstaller).
3. Invokes `build_cli.bat` and `build_gui.bat` to produce `dist/biospeak.exe`
   and `dist/Bio Speak Studio.exe`.

After installation the system is fully offline capable; both executables ship
with all dependencies bundled by PyInstaller.

## Quick CLI Use

```
python cli/biospeak_cli.py
```

Speak commands in simple sentences:

```
load dna file samples/yeast.fasta as yeast
count gc of yeast
translate yeast as yeast_protein
save yeast_protein to file yeast_protein.fasta
exit
```

### Run a `.bio` Script

```
python cli/biospeak_cli.py run examples/demo.bio
```

### Create a No-Admin Portable Bundle

```
python cli/biospeak_cli.py ready BioSpeakReady
```

The target folder includes Windows launchers for both the CLI and Bio Speak
Studio, the examples, and documentation.

### Self Verification and File Map

```
python cli/biospeak_cli.py verify      # compile, run demo script, confirm modules
python cli/biospeak_cli.py filemap     # textual project inventory
python cli/biospeak_cli.py integrations  # report third-party library status
```

## Bio Speak Studio (GUI)

Start the graphical studio with:

```
python gui/biospeak_studio.py
```

Features:

* Clean white/gray design with rounded controls styled after macOS/iOS.
* Toolbar verbs: **Load**, **Analyze**, **Translate**, **Align**, **Export**.
* Side panel with live lists for sequences, tables, and alignments.
* Quick action buttons for Split, Merge, Compare, GC, Frames (ORF scan), and
  Reverse Complement.
* Visual FASTA/FASTQ loader with record previews.
* Real-time pairwise and multiple alignment viewers with color-coded matches.
* Drag-select groups of sequences to align or merge.
* Embedded matplotlib/plotly charts for GC% trends, read lengths, and other
  metrics (falling back to textual summaries if graphics libraries are absent).
* Shared workspace with the CLI to guarantee matching results.

## Everyday Commands

All commands read like sentences and use familiar verbs. Replace uppercase words
with your own values.

### Data Loading

* `load dna file PATH as NAME`
* `load dna text SEQUENCE as NAME`
* `load rna file PATH as NAME`
* `load rna text SEQUENCE as NAME`
* `load protein file PATH as NAME`
* `load protein text SEQUENCE as NAME`
* `load fastq file PATH as NAME`
* `load genbank file PATH as NAME`
* `load gff file PATH as NAME`
* `load vcf file PATH as NAME`
* `load bam file PATH as NAME`
* `load table file PATH as NAME`
* `load json file PATH as NAME`
* `load notes file PATH as NAME`

### Saving and Exporting

* `save NAME to file PATH`
* `export sequences to PATH`
* `export table TABLE_NAME to PATH`

### Overview

* `list data`
* `list sequences`
* `list tables`
* `show NAME`
* `describe NAME`
* `make file map`
* `list integrations`

### DNA, RNA, and Protein Workflows

* `count gc of NAME`
* `count bases of NAME`
* `count codons of NAME`
* `find motif MOTIF in NAME`
* `slice NAME from START to END as NEW`
* `join FIRST with SECOND as NEW`
* `reverse NAME as NEW`
* `complement NAME as NEW`
* `reverse complement NAME as NEW`
* `transcribe NAME as NEW`
* `translate NAME as NEW`
* `translate frames of NAME as NEW`
* `make report for NAME as NEW`
* `write report of NAME to file PATH`
* `plot sequences NAME to file PATH`

### Alignments and Group Analysis

* `align FIRST with SECOND as NEW using global`
* `align FIRST with SECOND as NEW using local`
* `align group NAME1 NAME2 ... as NEW`

### Tables and Omics Data

* `analyze table NAME`
* `filter table TABLE keep column HEADER equals VALUE as NEW`
* `pick columns COL1 COL2 from TABLE as NEW`
* `join table FIRST with SECOND on column HEADER as NEW`

### Verification and Session Control

* `verify project`
* `export sequences to PATH`
* `exit`, `leave`, `quit`, or `close`

## Self-Verification inside the Engine

Running `verify project` or the CLI `verify` command executes:

1. `python -m compileall biospeak_core cli gui`
2. `python cli/biospeak_cli.py run examples/demo.bio`

Results are stored in the workspace as `verification_report`. The engine only
states “All modules complete.” when every check passes.

## Example Script

`examples/demo.bio` demonstrates a DNA workflow with translation and reporting.
Extend it with additional commands to automate your analyses.

## Building Executables Manually

If you prefer manual steps:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt  # optional if you extract dependencies
build_cli.bat
build_gui.bat
```

`build_cli.bat` produces `dist/biospeak.exe` and `build_gui.bat` produces
`dist/Bio Speak Studio.exe`, each bundling the shared `biospeak_core` package.

## File Map Summary

Generate an always-current project inventory with either:

```
python cli/biospeak_cli.py filemap
```

or the engine command `make file map` in the REPL. The output lists every file
with byte sizes so you can audit the installation.
