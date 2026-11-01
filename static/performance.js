(function () {
  "use strict";
  const root = document.getElementById("performance-editor");
  const columns = {
    takeoff: ["weight_lb", "pa_ft", "oat_c", "ground_ft", "total_ft", "lift_off_kias", "at_50ft_kias"],
    landing: ["weight_lb", "pa_ft", "oat_c", "ground_ft", "total_ft", "at_50ft_kias"],
    cruise: ["pa_ft", "isa_offset_c", "rpm", "percent_bhp", "ktas", "gph"]
  };
  const words = {
    reference1974: ["1974 C172M reference", "1974 C172M \u53c2\u8003\u8868"],
    referenceNotice: ["Published 1974 reference only; applicability to this aircraft is not confirmed. Check the aircraft's manual, propeller and STCs.", "\u4ec5\u4e3a 1974 \u5e74\u516c\u5f00\u53c2\u8003\u8868\uff0c\u672a\u786e\u8ba4\u672c\u673a\u9002\u7528\u6027\u3002\u8bf7\u6838\u5bf9\u672c\u673a\u624b\u518c\u3001\u87ba\u65cb\u6868\u548c STC\u3002"],
    referenceSource: ["Open source manual", "\u67e5\u770b\u539f\u59cb\u624b\u518c"],
    title: ["POH performance data", "\u624b\u52a8\u5f55\u5165 POH \u6027\u80fd\u8868"], mode: ["Data source", "\u6570\u636e\u6765\u6e90"],
    none: ["Not loaded", "\u672a\u5f55\u5165"], builtin: ["Built-in C172N table", "\u5185\u7f6e C172N \u8868"], manual: ["Manual POH table", "\u624b\u52a8 POH \u8868"],
    source: ["POH edition / revision / figure / page", "POH \u5e74\u4efd / \u7248\u672c / \u56fe\u53f7 / \u9875\u7801"],
    conditions: ["Aircraft configuration and POH conditions", "\u98de\u673a\u914d\u7f6e\u4e0e POH \u9002\u7528\u6761\u4ef6"],
    referenceWeight: ["Table reference weight (lb)", "\u8868\u683c\u9002\u7528\u91cd\u91cf (lb)"],
    headwindPct: ["Headwind reduction (%)", "\u9006\u98ce\u51cf\u5c11 (%)"], headwindStep: ["Headwind per (kt)", "\u9006\u98ce\u6bcf (kt)"], headwindMax: ["POH headwind limit (kt, if specified)", "POH \u9006\u98ce\u4e0a\u9650 (kt\uff0c\u82e5\u6709\u89c4\u5b9a)"],
    tailwindPct: ["Tailwind increase (%)", "\u987a\u98ce\u589e\u52a0 (%)"], tailwindStep: ["Tailwind per (kt)", "\u987a\u98ce\u6bcf (kt)"], tailwindMax: ["POH tailwind limit (kt, if specified)", "POH \u987a\u98ce\u4e0a\u9650 (kt\uff0c\u82e5\u6709\u89c4\u5b9a)"],
    grassMode: ["Grass correction", "\u8349\u5730\u4fee\u6b63"], grassPct: ["Grass increase (%)", "\u8349\u5730\u589e\u52a0 (%)"], unsupported: ["Not recorded", "\u672a\u5f55\u5165"],
    groundAdd: ["Add % of ground roll to both distances", "\u4e24\u79cd\u8ddd\u79bb\u5404\u52a0\u6ed1\u8dd1\u8ddd\u79bb\u7684\u767e\u5206\u6bd4"], bothPercent: ["Increase both distances by %", "\u4e24\u79cd\u8ddd\u79bb\u5404\u81ea\u589e\u52a0\u767e\u5206\u6bd4"],
    add: ["Add row", "\u6dfb\u52a0\u6570\u636e\u884c"], template: ["CSV template", "CSV \u6a21\u677f"], import: ["Import CSV / TSV", "\u5bfc\u5165 CSV / TSV"], export: ["Export CSV", "\u5bfc\u51fa CSV"],
    copy: ["Copy built-in C172N table", "\u590d\u5236\u5185\u7f6e C172N \u8868"], clear: ["Clear rows", "\u6e05\u7a7a\u6570\u636e\u884c"],
    paste: ["Paste CSV / Excel table", "\u7c98\u8d34 CSV / Excel \u8868\u683c"], importRows: ["Import rows", "\u5bfc\u5165\u6570\u636e\u884c"],
    remove: ["Delete row", "\u5220\u9664\u6570\u636e\u884c"], ready: ["Ready", "\u53ef\u7528"], draft: ["Draft", "\u8349\u7a3f"], unsaved: ["Unsaved", "\u672a\u4fdd\u5b58"],
    replace: ["Replace the current table rows?", "\u786e\u5b9a\u66ff\u6362\u5f53\u524d\u8868\u683c\u6570\u636e\u5417\uff1f"], clearConfirm: ["Clear all rows in this table?", "\u786e\u5b9a\u6e05\u7a7a\u8be5\u8868\u5168\u90e8\u6570\u636e\u884c\u5417\uff1f"],
    weight_lb: ["Weight (lb)", "\u91cd\u91cf (lb)"], pa_ft: ["PA (ft)", "PA (ft)"], oat_c: ["OAT (C)", "OAT (C)"],
    ground_ft: ["Ground roll (ft)", "\u5730\u9762\u6ed1\u8dd1 (ft)"], total_ft: ["Over 50 ft (ft)", "\u8d8a\u8fc7 50 ft (ft)"],
    lift_off_kias: ["Lift-off (KIAS)", "\u79bb\u5730\u901f\u5ea6 (KIAS)"], at_50ft_kias: ["At 50 ft (KIAS)", "50 ft \u901f\u5ea6 (KIAS)"],
    isa_offset_c: ["ISA offset (C)", "ISA \u6e29\u5dee (C)"], rpm: ["RPM", "RPM"], percent_bhp: ["Power (% BHP)", "\u529f\u7387 (% BHP)"],
    ktas: ["KTAS", "KTAS"], gph: ["Fuel (US gal/h)", "\u6cb9\u8017 (US gal/h)"]
  };
  const panes = [...root.querySelectorAll("[data-perf-pane]")];
  let modelId = "";
  let modelYear;
  const referenceCache = new Map();
  let datasets = {};
  let revision = 0;
  const clone = value => JSON.parse(JSON.stringify(value));
  const text = key => words[key] ? words[key][currentLang === "zh" ? 1 : 0] : key;
  const numeric = input => input.value === "" ? null : Number(input.value);
  function changed(pane) {
    pane.querySelector("[data-perf-status]").textContent = text("unsaved");
    pane.querySelector("[data-perf-status]").className = "performance-status";
    pane.querySelector("[data-perf-error]").textContent = "";
    root.dispatchEvent(new Event("input", { bubbles: true }));
  }
  function addRow(pane, values = {}) {
    const phase = pane.dataset.perfPane;
    const tbody = pane.querySelector("[data-perf-rows]");
    if (tbody.rows.length >= 3000) throw new Error("Maximum 3000 table rows.");
    const row = tbody.insertRow();
    columns[phase].forEach(key => {
      const input = document.createElement("input");
      input.type = "number"; input.step = "any"; input.dataset.perfCell = key;
      input.setAttribute("aria-label", text(key)); input.value = values[key] ?? "";
      if (!["pa_ft", "oat_c", "isa_offset_c"].includes(key)) input.min = "0";
      row.insertCell().append(input);
    });
    const button = document.createElement("button");
    button.type = "button"; button.className = "profile-icon"; button.textContent = "\u00d7";
    button.title = text("remove"); button.setAttribute("aria-label", text("remove"));
    button.addEventListener("click", () => { row.remove(); changed(pane); });
    row.insertCell().append(button);
  }
  function rowsOf(pane) {
    return [...pane.querySelectorAll("[data-perf-rows] tr")].map(row => Object.fromEntries(
      [...row.querySelectorAll("[data-perf-cell]")].map(input => [input.dataset.perfCell, numeric(input)])
    ));
  }
  function setRows(pane, rows) {
    pane.querySelector("[data-perf-rows]").replaceChildren();
    rows.forEach(row => addRow(pane, row));
  }
  function modeVisibility(pane) {
    const mode = pane.querySelector('[data-perf-meta="mode"]').value;
    pane.querySelector("[data-perf-manual]").hidden = mode !== "manual";
    pane.querySelector("[data-perf-reference]").hidden = mode !== "c172m1974";
    if (mode === "c172m1974") action(pane, () => loadReference(pane));
    pane.querySelector("[data-perf-copy]").hidden = modelId !== "c172n";
  }
  async function loadReference(pane) {
    const phase = pane.dataset.perfPane;
    const requestRevision = revision;
    let data = referenceCache.get(phase);
    if (!data) {
      const response = await fetch("/api/performance/reference-1974/" + phase);
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error);
      data = payload.result; referenceCache.set(phase, data);
    }
    if (requestRevision !== revision) return;
    const head = pane.querySelector("[data-perf-reference-head]"); head.replaceChildren();
    data.columns.forEach(label => { const cell = document.createElement("th"); cell.textContent = label; head.append(cell); });
    const body = pane.querySelector("[data-perf-reference-rows]"); body.replaceChildren();
    data.rows.forEach(values => { const row = body.insertRow(); values.forEach(value => { row.insertCell().textContent = Number(value).toFixed(1); }); });
    pane.querySelector("[data-perf-reference-conditions]").textContent = data.conditions;
    pane.querySelector("[data-perf-reference-source]").href = data.source_url + "#page=" + ({ takeoff: 65, landing: 67, cruise: 66 }[phase]);
  }
  function fillPhase(pane, dataset) {
    datasets[pane.dataset.perfPane] = clone(dataset);
    pane.querySelectorAll("[data-perf-meta]").forEach(input => {
      input.value = dataset[input.dataset.perfMeta] ?? "";
    });
    pane.querySelector('option[value="builtin"]').disabled = modelId !== "c172n";
    pane.querySelector('option[value="c172m1974"]').disabled = modelId !== "c172m" || modelYear !== 1974;
    setRows(pane, dataset.rows || []);
    pane.querySelector("[data-perf-paste]").value = "";
    pane.querySelector("[data-perf-error]").textContent = "";
    pane.querySelector("[data-perf-status]").textContent = "";
    modeVisibility(pane);
  }
  function download(pane, rows) {
    const keys = columns[pane.dataset.perfPane];
    const csv = [keys.join(","), ...rows.map(row => keys.map(key => row[key] ?? "").join(","))].join("\r\n") + "\r\n";
    window.pplPlatform.download(csv, pane.dataset.perfPane + "-poh.csv", "text/csv;charset=utf-8");
  }
  async function importText(pane, value) {
    const requestRevision = revision;
    const response = await fetch("/api/performance/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phase: pane.dataset.perfPane, text: value }) });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error);
    if (requestRevision !== revision) return;
    if (rowsOf(pane).length && !window.confirm(text("replace"))) return;
    setRows(pane, payload.result.rows); changed(pane);
  }
  async function action(pane, callback) {
    try { await callback(); }
    catch (error) { pane.querySelector("[data-perf-error]").textContent = error.message; }
  }
  function translate() {
    root.querySelectorAll("[data-perf-text]").forEach(node => { node.textContent = text(node.dataset.perfText); });
    panes.forEach(pane => {
      const header = pane.querySelector("[data-perf-head]"); header.replaceChildren();
      columns[pane.dataset.perfPane].forEach(key => { const th = document.createElement("th"); th.textContent = text(key); header.append(th); });
      header.append(document.createElement("th"));
      pane.querySelector("[data-perf-paste]").placeholder = columns[pane.dataset.perfPane].join(",");
    });
  }
  root.querySelectorAll("[data-perf-tab]").forEach(button => {
    button.addEventListener("click", () => {
      root.querySelectorAll("[data-perf-tab]").forEach(tab => { tab.classList.toggle("active", tab === button); tab.setAttribute("aria-selected", String(tab === button)); });
      panes.forEach(pane => { pane.hidden = pane.dataset.perfPane !== button.dataset.perfTab; });
    });
  });
  panes.forEach(pane => {
    pane.querySelector('[data-perf-meta="mode"]').addEventListener("change", () => { modeVisibility(pane); changed(pane); });
    pane.addEventListener("input", event => { if (event.target.matches("[data-perf-meta], [data-perf-cell]")) changed(pane); });
    pane.querySelector("[data-perf-add]").addEventListener("click", () => action(pane, () => { addRow(pane); changed(pane); }));
    pane.querySelector("[data-perf-template]").addEventListener("click", () => download(pane, []));
    pane.querySelector("[data-perf-export]").addEventListener("click", () => download(pane, rowsOf(pane)));
    pane.querySelector("[data-perf-clear]").addEventListener("click", () => { if (window.confirm(text("clearConfirm"))) { setRows(pane, []); changed(pane); } });
    pane.querySelector("[data-perf-import]").addEventListener("click", () => action(pane, () => importText(pane, pane.querySelector("[data-perf-paste]").value)));
    pane.querySelector("[data-perf-file]").addEventListener("change", event => action(pane, async () => {
      const file = event.target.files[0]; if (!file) return;
      if (file.size > 1000000) throw new Error("POH table file must be smaller than 1 MB.");
      try { await importText(pane, await file.text()); } finally { event.target.value = ""; }
    }));
    pane.querySelector("[data-perf-copy]").addEventListener("click", () => action(pane, async () => {
      if (modelId !== "c172n") return;
      const identity = modelId;
      const requestRevision = revision;
      const response = await fetch("/api/performance/builtin/" + pane.dataset.perfPane);
      const payload = await response.json(); if (!payload.ok) throw new Error(payload.error);
      if (modelId !== identity || requestRevision !== revision || !window.confirm(text("replace"))) return;
      fillPhase(pane, payload.result); changed(pane);
    }));
  });
  window.performanceEditor = {
    fill(profile, status) {
      revision++;
      modelId = profile.model_id;
      modelYear = profile.year;
      panes.forEach(pane => fillPhase(pane, profile.performance[pane.dataset.perfPane]));
      if (status) this.showStatus(status);
    },
    read() {
      const result = {};
      panes.forEach(pane => {
        const phase = pane.dataset.perfPane;
        const data = clone(datasets[phase]);
        pane.querySelectorAll("[data-perf-meta]").forEach(input => { data[input.dataset.perfMeta] = input.type === "number" ? numeric(input) : input.value; });
        data.rows = rowsOf(pane); result[phase] = data;
      });
      return result;
    },
    showStatus(status) {
      panes.forEach(pane => {
        const state = status[pane.dataset.perfPane]; const node = pane.querySelector("[data-perf-status]");
        node.textContent = text(state.mode === "c172m1974" ? "reference1974" : state.ready ? "ready" : "draft") + (state.issues.length ? ": " + state.issues.join("; ") : "");
        node.className = "performance-status" + (state.ready && state.mode !== "c172m1974" ? " ready" : "");
      });
    }
  };
  document.addEventListener("ppl-language-change", translate);
  document.querySelector('#aircraft-editor [name="year"]').addEventListener("input", event => {
    modelYear = event.target.value === "" ? null : Number(event.target.value);
    panes.forEach(pane => { pane.querySelector('option[value="c172m1974"]').disabled = modelId !== "c172m" || modelYear !== 1974; });
  });
  translate();
})();
