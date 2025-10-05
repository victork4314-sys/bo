const { createApp, reactive, ref, onMounted, onBeforeUnmount, computed, watch } = Vue;

createApp({
  setup() {
    const defaultTheme = (() => {
      if (typeof window === "undefined") {
        return "light";
      }
      const stored = window.localStorage.getItem("biospeak-theme");
      if (stored === "light" || stored === "dark") {
        return stored;
      }
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    })();

    const defaultPanelOpen = typeof window !== "undefined" && window.innerWidth >= 960;

    const state = reactive({
      ready: false,
      theme: defaultTheme,
      sidePanelOpen: defaultPanelOpen,
      activeTab: "sequence",
      sequences: [],
      alignments: [],
      tables: [],
      reports: [],
      selectedSequences: [],
      log: [],
      charts: { gc: false, lengths: false },
      openMenu: null,
      panelContent: {
        sequence: null,
        alignment: null,
        results: null,
      },
      workspaceSummary: "Sequences: 0\nAlignments: 0\nTables: 0\nReports: 0",
      progress: {
        active: false,
        message: "Idle",
      },
    });

    const recentLog = computed(() => state.log.slice(0, 4));

    const fileInput = ref(null);
    let pyodide = null;
    let snapshotFn = null;
    let executeFn = null;
    let resetFn = null;
    let resizeHandler = null;

    const toJsOptions = { dict_converter: Object.fromEntries, create_proxies: false };

    const SUPPORTED_TEXT = [
      "fa",
      "fasta",
      "fna",
      "ffn",
      "faa",
      "frn",
      "fastq",
      "fq",
      "gb",
      "gbk",
      "gff",
      "gff3",
      "vcf",
      "csv",
      "tsv",
      "json",
    ];

    const BINARY_EXTENSIONS = ["bam"];

    function shorten(message, limit = 110) {
      if (!message) {
        return "";
      }
      return message.length > limit ? `${message.slice(0, limit - 1)}…` : message;
    }

    function pushLog(status, message) {
      const now = new Date();
      state.log.unshift({
        timestamp: `${now.getTime()}-${Math.random()}`,
        time: now.toLocaleTimeString(),
        status,
        message,
      });
      if (state.log.length > 200) {
        state.log.splice(200);
      }
      state.progress.active = false;
      state.progress.message = `${status.toUpperCase()} – ${shorten(message, 96)}`;
    }

    function toggleMenu(name) {
      state.openMenu = state.openMenu === name ? null : name;
    }

    function closeMenus() {
      state.openMenu = null;
    }

    function handleDocumentClick(event) {
      if (!event.target.closest || !event.target.closest(".menu")) {
        closeMenus();
      }
    }

    function describeCommand(command) {
      return command.split(/\s+/).slice(0, 3).join(" ");
    }

    function computeGC(sequence) {
      const cleaned = (sequence || "").toUpperCase().replace(/[^ACGT]/g, "");
      if (!cleaned.length) {
        return 0;
      }
      const gc = cleaned.split("").filter((ch) => ch === "G" || ch === "C").length;
      return (gc / cleaned.length) * 100;
    }

    function sequenceStats(item) {
      const alphabet = (item.alphabet || "dna").toUpperCase();
      const lengthValue = item.length || (item.sequence ? item.sequence.length : 0);
      const lengthLabel = alphabet === "PROTEIN" ? `${lengthValue} aa` : `${lengthValue} bp`;
      if (alphabet === "PROTEIN") {
        return `${alphabet} · ${lengthLabel}`;
      }
      const gcValue = computeGC(item.sequence || "");
      return `${alphabet} · ${lengthLabel} · ${gcValue.toFixed(1)}% GC`;
    }

    function updateWorkspaceSummary() {
      const lines = [
        `Sequences: ${state.sequences.length}`,
        `Alignments: ${state.alignments.length}`,
        `Tables: ${state.tables.length}`,
        `Reports: ${state.reports.length}`,
      ];
      if (state.sequences.length) {
        const preview = state.sequences.slice(0, 6).map((seq) => {
          const lengthValue = seq.length || (seq.sequence ? seq.sequence.length : 0);
          const alphabet = (seq.alphabet || "dna").toUpperCase();
          const label = alphabet === "PROTEIN" ? `${lengthValue} aa` : `${lengthValue} bp`;
          return `• ${seq.name} (${label})`;
        });
        lines.push("", ...preview);
        if (state.sequences.length > 6) {
          lines.push(`… and ${state.sequences.length - 6} more`);
        }
      }
      if (state.tables.length) {
        lines.push("", "Tables:");
        state.tables.forEach((table) => {
          lines.push(`• ${table.name} (${table.rows.length} × ${table.columns.length})`);
        });
      }
      state.workspaceSummary = lines.join("\n");
    }

    function applyWorkspace(workspace) {
      state.sequences = workspace.sequences || [];
      state.alignments = workspace.alignments || [];
      state.tables = workspace.tables || [];
      state.reports = workspace.reports || [];
      const available = new Set(state.sequences.map((seq) => seq.name));
      state.selectedSequences = state.selectedSequences.filter((name) => available.has(name));
      updateWorkspaceSummary();
      updateCharts();
    }

    function updateCharts() {
      if (!window.Plotly) {
        return;
      }
      const sequences = state.sequences || [];
      if (!sequences.length) {
        state.charts.gc = false;
        state.charts.lengths = false;
        try {
          Plotly.purge("gc-chart");
          Plotly.purge("length-chart");
        } catch (error) {
          // ignore if charts not initialised
        }
        return;
      }
      const names = sequences.map((seq) => seq.name);
      const gcValues = sequences.map((seq) => Number(computeGC(seq.sequence).toFixed(2)));
      const lengths = sequences.map((seq) => seq.length || (seq.sequence ? seq.sequence.length : 0));
      Plotly.react(
        "gc-chart",
        [
          {
            type: "bar",
            x: names,
            y: gcValues,
            marker: { color: "#14b8a6" },
          },
        ],
        {
          margin: { t: 24, r: 20, b: 48, l: 56 },
          yaxis: { title: "GC %", range: [0, 100] },
          xaxis: { title: "Sequence" },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
        },
        { responsive: true }
      );
      Plotly.react(
        "length-chart",
        [
          {
            type: "histogram",
            x: lengths,
            nbinsx: Math.min(20, Math.max(5, Math.floor(Math.sqrt(lengths.length * 4)) || 10)),
            marker: { color: "#0d9488", opacity: 0.85 },
          },
        ],
        {
          margin: { t: 24, r: 20, b: 48, l: 56 },
          xaxis: { title: "Length" },
          yaxis: { title: "Count" },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
        },
        { responsive: true }
      );
      state.charts.gc = true;
      state.charts.lengths = true;
    }

    async function refreshWorkspace() {
      closeMenus();
      if (!snapshotFn) {
        return;
      }
      const proxy = snapshotFn();
      const data = proxy.toJs(toJsOptions);
      proxy.destroy();
      applyWorkspace(data);
    }

    function sanitizeName(name) {
      return name
        .replace(/\.[^/.]+$/, "")
        .replace(/[^a-zA-Z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "")
        .toLowerCase() || "sample";
    }

    function extensionOf(fileName) {
      const lower = fileName.toLowerCase();
      const index = lower.lastIndexOf(".");
      if (index === -1) {
        return "";
      }
      return lower.slice(index + 1);
    }

    function buildLoadCommand(ext, path, baseName) {
      if (["fa", "fasta", "fna", "ffn", "faa", "frn"].includes(ext)) {
        return `load dna file ${path} as ${baseName}`;
      }
      if (["fastq", "fq"].includes(ext)) {
        return `load fastq file ${path} as ${baseName}`;
      }
      if (["gb", "gbk", "genbank"].includes(ext)) {
        return `load genbank file ${path} as ${baseName}`;
      }
      if (["gff", "gff3"].includes(ext)) {
        return `load gff file ${path} as ${baseName}`;
      }
      if (ext === "vcf") {
        return `load vcf file ${path} as ${baseName}`;
      }
      if (ext === "bam") {
        return `load bam file ${path} as ${baseName}`;
      }
      if (["csv", "tsv"].includes(ext)) {
        return `load table file ${path} as ${baseName}`;
      }
      if (ext === "json") {
        return `load json file ${path} as ${baseName}`;
      }
      return null;
    }

    async function runCommand(command) {
      if (!executeFn) {
        pushLog("error", "Engine not ready yet.");
        return null;
      }
      state.progress.active = true;
      state.progress.message = `Running ${describeCommand(command)}…`;
      try {
        const proxy = executeFn(command);
        const result = proxy.toJs(toJsOptions);
        proxy.destroy();
        applyWorkspace(result.workspace);
        const status = result.status === "ok" ? "ok" : result.status === "exit" ? "info" : "error";
        pushLog(status, result.message);
        return result;
      } catch (error) {
        const message = error && error.message ? error.message : String(error);
        pushLog("error", message);
        return null;
      } finally {
        state.progress.active = false;
      }
    }

    async function loadFile(file) {
      if (!pyodide) {
        pushLog("error", "Engine not ready.");
        return;
      }
      const ext = extensionOf(file.name);
      const baseName = sanitizeName(file.name);
      const path = `/tmp/${Date.now()}_${Math.random().toString(36).slice(2)}_${baseName}.${ext || "dat"}`;
      try {
        pyodide.FS.mkdirTree("/tmp");
      } catch (error) {
        // already exists
      }
      try {
        if (BINARY_EXTENSIONS.includes(ext)) {
          const buffer = await file.arrayBuffer();
          pyodide.FS.writeFile(path, new Uint8Array(buffer));
        } else if (SUPPORTED_TEXT.includes(ext)) {
          const text = await file.text();
          pyodide.FS.writeFile(path, text);
        } else {
          pushLog("error", `Unsupported file type for ${file.name}`);
          return;
        }
      } catch (error) {
        pushLog("error", `Could not read ${file.name}: ${error.message || error}`);
        return;
      }
      const command = buildLoadCommand(ext, path, baseName);
      if (!command) {
        pushLog("error", `Unsupported file type for ${file.name}`);
        return;
      }
      await runCommand(command);
    }

    async function loadFiles(files) {
      for (const file of files) {
        await loadFile(file);
      }
    }

    async function handleFileInput(event) {
      const files = Array.from(event.target.files || []);
      if (files.length) {
        await loadFiles(files);
        event.target.value = "";
      }
    }

    async function handleDrop(event) {
      const files = Array.from(event.dataTransfer.files || []);
      if (files.length) {
        await loadFiles(files);
      }
    }

    function triggerFileDialog() {
      closeMenus();
      if (fileInput.value) {
        fileInput.value.click();
      }
    }

    async function resetWorkspace() {
      if (!resetFn) {
        return;
      }
      closeMenus();
      const proxy = resetFn();
      const data = proxy.toJs(toJsOptions);
      proxy.destroy();
      state.selectedSequences = [];
      state.panelContent.sequence = null;
      state.panelContent.alignment = null;
      state.panelContent.results = null;
      applyWorkspace(data);
      pushLog("info", "Workspace cleared.");
      state.activeTab = "sequence";
    }

    async function analyzeSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select one or more sequences to analyze.");
        return;
      }
      const lines = [];
      for (const name of state.selectedSequences) {
        const gcResult = await runCommand(`count gc of ${name}`);
        if (gcResult && gcResult.status === "ok") {
          lines.push(gcResult.message);
        }
        const baseResult = await runCommand(`count bases of ${name}`);
        if (baseResult && baseResult.status === "ok") {
          lines.push(baseResult.message);
        }
      }
      if (lines.length) {
        state.panelContent.sequence = { title: "Analysis", content: lines.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function countCodonsSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Pick one or more sequences first.");
        return;
      }
      const lines = [];
      for (const name of state.selectedSequences) {
        const result = await runCommand(`count codons of ${name}`);
        if (result && result.status === "ok") {
          lines.push(`${name}\n${result.message}`);
        }
      }
      if (lines.length) {
        state.panelContent.sequence = { title: "Codon Usage", content: lines.join("\n\n") };
        state.activeTab = "sequence";
      }
    }

    async function translateSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select sequences to translate.");
        return;
      }
      const outputs = [];
      for (const name of state.selectedSequences) {
        const translated = `${name}_protein`;
        const result = await runCommand(`translate ${name} as ${translated}`);
        if (result && result.status === "ok") {
          outputs.push(`${name} became ${translated}`);
        }
      }
      if (outputs.length) {
        state.panelContent.sequence = { title: "Translation", content: outputs.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function translateFramesSelected() {
      closeMenus();
      if (state.selectedSequences.length !== 1) {
        pushLog("error", "Pick one sequence to explore frames.");
        return;
      }
      const [name] = state.selectedSequences;
      const reportName = window.prompt("Name for the frame report", `${name}_frames`);
      if (!reportName) {
        return;
      }
      const result = await runCommand(`translate frames of ${name} as ${reportName}`);
      if (result && result.status === "ok") {
        const report = (result.workspace.reports || []).find((entry) => entry.name === reportName);
        const content = report ? report.lines.join("\n") : result.message;
        state.panelContent.sequence = { title: "Reading Frames", content };
        state.panelContent.results = { title: "Frame Report", content };
        state.activeTab = "sequence";
      }
    }

    async function alignSelected(method = "global") {
      closeMenus();
      if (state.selectedSequences.length < 2) {
        pushLog("error", "Pick two sequences to align.");
        return;
      }
      const [first, second] = state.selectedSequences;
      const alignmentName = `${first}_${second}_align`;
      const result = await runCommand(`align ${first} with ${second} as ${alignmentName} using ${method}`);
      if (result && result.status === "ok") {
        const alignment = (result.workspace.alignments || []).find((item) => item.name === alignmentName);
        const text = alignment ? `${alignment.lines.join("\n")}\nScore: ${alignment.score}` : result.message;
        state.panelContent.alignment = { title: `Alignment — ${alignmentName}`, content: text };
        state.activeTab = "alignment";
      }
    }

    async function alignGroupSelected() {
      closeMenus();
      if (state.selectedSequences.length < 3) {
        pushLog("error", "Pick three or more sequences for group alignment.");
        return;
      }
      const baseName = window.prompt("Name for the group alignment", "group_align");
      if (!baseName) {
        return;
      }
      const members = state.selectedSequences.join(" ");
      const result = await runCommand(`align group ${members} as ${baseName}`);
      if (result && result.status === "ok") {
        const alignment = (result.workspace.alignments || []).find((item) => item.name === baseName);
        if (alignment) {
          state.panelContent.alignment = {
            title: `Alignment — ${alignment.name}`,
            content: `${alignment.lines.join("\n")}\nScore: ${alignment.score}`,
          };
        } else {
          state.panelContent.alignment = { title: "Alignment", content: result.message };
        }
        state.activeTab = "alignment";
      }
    }

    function showAlignment(alignment) {
      state.panelContent.alignment = {
        title: `Alignment — ${alignment.name}`,
        content: `${alignment.lines.join("\n")}\nScore: ${alignment.score}`,
      };
      state.activeTab = "alignment";
    }

    function exportWorkspace() {
      closeMenus();
      const payload = {
        generated_at: new Date().toISOString(),
        sequences: state.sequences,
        alignments: state.alignments,
        tables: state.tables,
        reports: state.reports,
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `biospeak_workspace_${Date.now()}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      pushLog("ok", "Exported workspace snapshot.");
      state.panelContent.results = {
        title: "Export",
        content: "Workspace snapshot saved to downloads.",
      };
      state.activeTab = "results";
    }

    async function reverseComplementSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select sequences first.");
        return;
      }
      const outputs = [];
      for (const name of state.selectedSequences) {
        const target = `${name}_rc`;
        const result = await runCommand(`reverse complement ${name} as ${target}`);
        if (result && result.status === "ok") {
          outputs.push(`${name} became ${target}`);
        }
      }
      if (outputs.length) {
        state.panelContent.sequence = { title: "Reverse Complement", content: outputs.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function reverseSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select sequences first.");
        return;
      }
      const outputs = [];
      for (const name of state.selectedSequences) {
        const target = `${name}_rev`;
        const result = await runCommand(`reverse ${name} as ${target}`);
        if (result && result.status === "ok") {
          outputs.push(`${name} became ${target}`);
        }
      }
      if (outputs.length) {
        state.panelContent.sequence = { title: "Reverse", content: outputs.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function complementSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select sequences first.");
        return;
      }
      const outputs = [];
      for (const name of state.selectedSequences) {
        const target = `${name}_comp`;
        const result = await runCommand(`complement ${name} as ${target}`);
        if (result && result.status === "ok") {
          outputs.push(`${name} became ${target}`);
        }
      }
      if (outputs.length) {
        state.panelContent.sequence = { title: "Complement", content: outputs.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function transcribeSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select sequences first.");
        return;
      }
      const outputs = [];
      for (const name of state.selectedSequences) {
        const target = `${name}_rna`;
        const result = await runCommand(`transcribe ${name} as ${target}`);
        if (result && result.status === "ok") {
          outputs.push(`${name} became ${target}`);
        }
      }
      if (outputs.length) {
        state.panelContent.sequence = { title: "Transcription", content: outputs.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function gcSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Select sequences to measure GC.");
        return;
      }
      const lines = [];
      for (const name of state.selectedSequences) {
        const result = await runCommand(`count gc of ${name}`);
        if (result && result.status === "ok") {
          lines.push(result.message);
        }
      }
      if (lines.length) {
        state.panelContent.sequence = { title: "GC Content", content: lines.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function findMotifSelected() {
      closeMenus();
      if (!state.selectedSequences.length) {
        pushLog("error", "Pick one or more sequences first.");
        return;
      }
      const motif = window.prompt("Motif to find (letters only)");
      if (!motif) {
        return;
      }
      const lines = [];
      for (const name of state.selectedSequences) {
        const result = await runCommand(`find motif ${motif} in ${name}`);
        if (result && result.status === "ok") {
          lines.push(`${name}: ${result.message}`);
        }
      }
      if (lines.length) {
        state.panelContent.sequence = { title: "Motif Search", content: lines.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function splitSelected() {
      closeMenus();
      if (state.selectedSequences.length !== 1) {
        pushLog("error", "Pick one sequence to split.");
        return;
      }
      const [name] = state.selectedSequences;
      const sizeText = window.prompt("Split length in bases", "500");
      if (!sizeText) {
        return;
      }
      const baseName = window.prompt("Name for the new pieces", `${name}_part`);
      if (!baseName) {
        return;
      }
      const size = Number.parseInt(sizeText, 10);
      if (!Number.isFinite(size) || size <= 0) {
        pushLog("error", "Use a positive whole number for the split length.");
        return;
      }
      const result = await runCommand(`split ${name} every ${size} as ${baseName}`);
      if (result && result.status === "ok") {
        state.panelContent.sequence = { title: "Split", content: result.message };
        state.activeTab = "sequence";
      }
    }

    async function sliceSelected() {
      closeMenus();
      if (state.selectedSequences.length !== 1) {
        pushLog("error", "Pick one sequence to slice.");
        return;
      }
      const [name] = state.selectedSequences;
      const startText = window.prompt("Start position", "1");
      if (!startText) {
        return;
      }
      const endText = window.prompt("End position", "100");
      if (!endText) {
        return;
      }
      const newName = window.prompt("Name for the slice", `${name}_slice`);
      if (!newName) {
        return;
      }
      const start = Number.parseInt(startText, 10);
      const end = Number.parseInt(endText, 10);
      if (!Number.isFinite(start) || !Number.isFinite(end) || start <= 0 || end <= 0 || end < start) {
        pushLog("error", "Give valid start and end positions.");
        return;
      }
      const result = await runCommand(`slice ${name} from ${start} to ${end} as ${newName}`);
      if (result && result.status === "ok") {
        state.panelContent.sequence = { title: "Slice", content: result.message };
        state.activeTab = "sequence";
      }
    }

    async function mergeSelected() {
      closeMenus();
      if (state.selectedSequences.length < 2) {
        pushLog("error", "Pick two or more sequences to merge.");
        return;
      }
      const targetName = window.prompt("Name for the merged sequence", "merged_sequence");
      if (!targetName) {
        return;
      }
      let current = state.selectedSequences[0];
      const created = [];
      for (let i = 1; i < state.selectedSequences.length; i += 1) {
        const next = state.selectedSequences[i];
        const interim = i === state.selectedSequences.length - 1 ? targetName : `${targetName}_${i}`;
        const result = await runCommand(`join ${current} with ${next} as ${interim}`);
        if (!result || result.status !== "ok") {
          return;
        }
        created.push(`${current} with ${next} made ${interim}`);
        current = interim;
      }
      if (created.length) {
        state.panelContent.sequence = { title: "Merge", content: created.join("\n") };
        state.activeTab = "sequence";
      }
    }

    async function compareSelected() {
      closeMenus();
      if (state.selectedSequences.length !== 2) {
        pushLog("error", "Pick two sequences to compare.");
        return;
      }
      const [first, second] = state.selectedSequences;
      const result = await runCommand(`compare ${first} with ${second}`);
      if (result && result.status === "ok") {
        state.panelContent.alignment = { title: "Compare", content: result.message };
        state.activeTab = "alignment";
      }
    }

    async function scanOrfSelected() {
      closeMenus();
      if (state.selectedSequences.length !== 1) {
        pushLog("error", "Pick one sequence to scan.");
        return;
      }
      const [name] = state.selectedSequences;
      const minText = window.prompt("Minimum protein length (aa)", "30");
      if (!minText) {
        return;
      }
      const baseName = window.prompt("Name for the ORF set", `${name}_orf`);
      if (!baseName) {
        return;
      }
      const min = Number.parseInt(minText, 10);
      if (!Number.isFinite(min) || min <= 0) {
        pushLog("error", "Use a positive whole number for the minimum length.");
        return;
      }
      const result = await runCommand(`scan orf of ${name} minimum ${min} as ${baseName}`);
      if (result && result.status === "ok") {
        state.panelContent.sequence = { title: "ORF Scan", content: result.message };
        state.activeTab = "sequence";
      }
    }

    function setTab(tab) {
      state.activeTab = tab;
      closeMenus();
    }

    function toggleSidePanel() {
      state.sidePanelOpen = !state.sidePanelOpen;
    }

    function toggleTheme() {
      state.theme = state.theme === "light" ? "dark" : "light";
    }

    function openGuide() {
      closeMenus();
      state.panelContent.sequence = {
        title: "Quick Start",
        content: [
          "1. Press Load Files or drop FASTA/FASTQ/CSV data on the left panel.",
          "2. Select sequences with the checkboxes to enable tool menus.",
          "3. Use Sequence Actions for transcription, translation, and motif scans.",
          "4. Choose Compare for pairwise or group alignments, then review results in the Alignment tab.",
          "5. Export tables and reports directly from the Results tab.",
        ].join("\n"),
      };
      state.activeTab = "sequence";
    }

    function openShortcuts() {
      closeMenus();
      state.panelContent.results = {
        title: "Command Reference",
        content: [
          "load dna file <path> as <name>",
          "transcribe <name> as <new_name>",
          "translate <name> as <new_name>",
          "align <first> with <second> as <label> using global|local",
          "align group <a> <b> <c> as <label>",
          "count gc of <name>",
          "scan orf of <name> minimum <length> as <label>",
          "find motif <pattern> in <name>",
          "split <name> every <size> as <label>",
          "join <first> with <second> as <label>",
        ].join("\n"),
      };
      state.activeTab = "results";
    }

    function openSupport() {
      closeMenus();
      state.panelContent.results = {
        title: "Support Notes",
        content: [
          "Bio Speak Studio runs fully offline using Pyodide.",
          "All files stay on your device. Exported reports land in your Downloads folder.",
          "Use the Settings menu to refresh the workspace or switch between light and dark modes.",
          "Need to rebuild? Run build_web scripts to generate a fresh /dist package.",
        ].join("\n"),
      };
      state.activeTab = "results";
    }

    onMounted(async () => {
      document.addEventListener("click", handleDocumentClick);
      const handleResize = () => {
        if (window.innerWidth < 960) {
          state.sidePanelOpen = false;
        } else {
          state.sidePanelOpen = true;
        }
      };
      resizeHandler = handleResize;
      window.addEventListener("resize", resizeHandler);
      handleResize();

      pushLog("info", "Loading Bio Speak engine…");
      pyodide = await loadPyodide({ indexURL: "pyodide/" });
      pushLog("info", "Pyodide ready.");
      await pyodide.runPythonAsync(
        "import sys\n" +
          "sys.path.append('./core')\n" +
          "from biospeak_core.web_api import execute_command, reset_workspace, snapshot\n"
      );
      snapshotFn = pyodide.globals.get("snapshot");
      executeFn = pyodide.globals.get("execute_command");
      resetFn = pyodide.globals.get("reset_workspace");
      await refreshWorkspace();
      state.ready = true;
      pushLog("ok", "Bio Speak Studio ready.");

      if (window.innerWidth < 960) {
        state.sidePanelOpen = false;
      }
    });

    onBeforeUnmount(() => {
      document.removeEventListener("click", handleDocumentClick);
      if (typeof window !== "undefined" && resizeHandler) {
        window.removeEventListener("resize", resizeHandler);
      }
    });

    watch(
      () => state.theme,
      (theme) => {
        if (typeof document !== "undefined") {
          document.documentElement.setAttribute("data-theme", theme);
        }
        if (typeof window !== "undefined") {
          window.localStorage.setItem("biospeak-theme", theme);
        }
      },
      { immediate: true }
    );

    return {
      state,
      recentLog,
      fileInput,
      sequenceStats,
      toggleMenu,
      closeMenus,
      triggerFileDialog,
      handleFileInput,
      handleDrop,
      resetWorkspace,
      analyzeSelected,
      countCodonsSelected,
      translateSelected,
      translateFramesSelected,
      alignSelected,
      alignGroupSelected,
      exportWorkspace,
      showAlignment,
      reverseComplementSelected,
      reverseSelected,
      complementSelected,
      transcribeSelected,
      gcSelected,
      findMotifSelected,
      splitSelected,
      sliceSelected,
      mergeSelected,
      compareSelected,
      scanOrfSelected,
      setTab,
      toggleSidePanel,
      toggleTheme,
      openGuide,
      openShortcuts,
      openSupport,
      refreshWorkspace,
    };
  },
}).mount("#app");
