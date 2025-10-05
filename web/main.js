const { createApp, reactive, ref, onMounted, onBeforeUnmount } = Vue;

createApp({
  setup() {
    const state = reactive({
      ready: false,
      sequences: [],
      alignments: [],
      tables: [],
      reports: [],
      selectedSequences: [],
      log: [],
      preview: null,
      charts: { gc: false, lengths: false },
      openMenu: null,
    });

    const fileInput = ref(null);
    let pyodide = null;
    let snapshotFn = null;
    let executeFn = null;
    let resetFn = null;
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

    function applyWorkspace(workspace) {
      state.sequences = workspace.sequences || [];
      state.alignments = workspace.alignments || [];
      state.tables = workspace.tables || [];
      state.reports = workspace.reports || [];
      updateCharts();
    }

    function computeGC(sequence) {
      const cleaned = sequence.toUpperCase().replace(/[^ACGT]/g, "");
      if (!cleaned.length) {
        return 0;
      }
      const gc = cleaned.split("").filter((ch) => ch === "G" || ch === "C").length;
      return (gc / cleaned.length) * 100;
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
      const lengths = sequences.map((seq) => seq.length);
      Plotly.react(
        "gc-chart",
        [
          {
            type: "bar",
            x: names,
            y: gcValues,
            marker: { color: "#38bdf8" },
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
            marker: { color: "#a855f7", opacity: 0.85 },
          },
        ],
        {
          margin: { t: 24, r: 20, b: 48, l: 56 },
          xaxis: { title: "Length (bp)" },
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
      try {
        const proxy = executeFn(command);
        const result = proxy.toJs(toJsOptions);
        proxy.destroy();
        applyWorkspace(result.workspace);
        const status = result.status === "ok" ? "ok" : result.status === "exit" ? "info" : "error";
        pushLog(status, result.message);
        return result;
      } catch (error) {
        pushLog("error", error.message || String(error));
        return null;
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
        // directory already exists
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
      state.preview = null;
      applyWorkspace(data);
      pushLog("info", "Workspace cleared.");
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
        state.preview = { title: "Analysis", content: lines.join("\n") };
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
        state.preview = { title: "Translation", content: outputs.join("\n") };
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
      const result = await runCommand(
        `align ${first} with ${second} as ${alignmentName} using ${method}`
      );
      if (result && result.status === "ok") {
        const alignment = (result.workspace.alignments || []).find((item) => item.name === alignmentName);
        const text = alignment ? alignment.lines.join("\n") : result.message;
        state.preview = { title: `Alignment — ${alignmentName}`, content: text };
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
          state.preview = {
            title: `Alignment — ${alignment.name}`,
            content: `${alignment.lines.join("\n")}\nScore: ${alignment.score}`,
          };
        }
      }
    }

    function showAlignment(alignment) {
      state.preview = {
        title: `Alignment — ${alignment.name}`,
        content: `${alignment.lines.join("\n")}\nScore: ${alignment.score}`,
      };
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
        state.preview = { title: "Reverse Complement", content: outputs.join("\n") };
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
        state.preview = { title: "GC Content", content: lines.join("\n") };
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
      await runCommand(`split ${name} every ${size} as ${baseName}`);
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
        state.preview = { title: "Merge", content: created.join("\n") };
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
        state.preview = { title: "Compare", content: result.message };
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
        state.preview = { title: "ORF Scan", content: result.message };
      }
    }

    onMounted(async () => {
      document.addEventListener("click", handleDocumentClick);
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
    });

    onBeforeUnmount(() => {
      document.removeEventListener("click", handleDocumentClick);
    });

    return {
      state,
      toggleMenu,
      closeMenus,
      fileInput,
      triggerFileDialog,
      handleFileInput,
      handleDrop,
      resetWorkspace,
      analyzeSelected,
      translateSelected,
      alignSelected,
      alignGroupSelected,
      exportWorkspace,
      showAlignment,
      reverseComplementSelected,
      gcSelected,
      splitSelected,
      mergeSelected,
      compareSelected,
      scanOrfSelected,
    };
  },
}).mount("#app");
