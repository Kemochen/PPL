(function () {
  "use strict";
  const storageKey = "pplAircraftProfilesV1";
  const editor = document.getElementById("aircraft-editor");
  const activeSelect = document.getElementById("active-aircraft");
  const savedSelect = document.getElementById("saved-aircraft");
  const message = document.getElementById("profile-message");
  const wbForm = document.querySelector('#weight-balance form');
  const performanceForms = [...document.querySelectorAll('.calculator')].filter(form => form !== wbForm);
  const numberFields = ["empty_weight_lb", "empty_moment_lb_in", "fuel_density_lb_gal", "fuel_arm_in", "max_ramp_lb", "max_takeoff_lb", "max_landing_lb", "usable_fuel_gal", "baggage_total_lb"];
  const textFields = ["name", "registration", "serial_number", "wb_reference", "wb_date", "notes"];
  let models = [];
  let saved = [];
  let activeId = "demo";
  let editingId = "";
  let dirty = false;
  let storageBroken = false;
  let demoProfile;
  const copy = value => JSON.parse(JSON.stringify(value));
  const strings = {
    saved: ["Saved aircraft", "\u5df2\u4fdd\u5b58\u7684\u98de\u673a"], new: ["New aircraft", "\u65b0\u589e\u98de\u673a"], copy: ["Duplicate", "\u590d\u5236\u6863\u6848"],
    delete: ["Delete", "\u5220\u9664"], export: ["Export backup", "\u5bfc\u51fa\u5907\u4efd"], import: ["Import backup", "\u5bfc\u5165\u5907\u4efd"],
    storage: ["Profiles are saved in this browser. Export a backup to move them to another device.", "\u6863\u6848\u4fdd\u5b58\u5728\u5f53\u524d\u6d4f\u89c8\u5668\uff0c\u53ef\u5bfc\u51fa\u5907\u4efd\u5e76\u5728\u5176\u4ed6\u8bbe\u5907\u5bfc\u5165\u3002"],
    identity: ["Aircraft identity", "\u98de\u673a\u8eab\u4efd"], model: ["Model", "\u673a\u578b"], name: ["Aircraft name", "\u6863\u6848\u540d\u79f0"], registration: ["Registration", "\u6ce8\u518c\u53f7"],
    serial: ["Serial number", "\u5e8f\u5217\u53f7"], year: ["Model year", "\u578b\u5e74"], wbDate: ["W&B document date", "W&B \u6587\u4ef6\u65e5\u671f"],
    wbReference: ["Aircraft W&B document / POH reference", "\u672c\u673a W&B \u6587\u4ef6 / POH \u7248\u672c"], notes: ["Configuration / STC notes", "\u914d\u7f6e / STC \u5907\u6ce8"],
    scope: ["Templates: normal-category landplanes with fixed loading station arms and a single fuel arm. Confirm serial number, seat positions, tanks and STCs against this aircraft's documents. Variable fuel arms or separate tanks need a matching loading model.", "\u6a21\u677f\u9002\u7528\u4e8e\u6b63\u5e38\u7c7b\u9646\u4e0a\u98de\u673a\uff0c\u6309\u56fa\u5b9a\u88c5\u8f7d arm \u548c\u5355\u4e00\u71c3\u6cb9 arm \u8ba1\u7b97\u3002\u5e8f\u5217\u53f7\u3001\u5ea7\u6905\u3001\u6cb9\u7bb1\u548c STC \u9700\u4e0e\u672c\u673a\u6587\u4ef6\u6838\u5bf9\uff1b\u53d8\u5316\u71c3\u6cb9 arm \u6216\u591a\u6cb9\u7bb1\u9700\u5bf9\u5e94\u88c5\u8f7d\u6a21\u578b\u3002"],
    empty: ["Actual empty aircraft", "\u672c\u673a\u5b9e\u9645\u7a7a\u91cd\u6570\u636e"], emptyWeight: ["Basic empty weight (lb)", "\u57fa\u672c\u7a7a\u91cd (lb)"],
    emptyMoment: ["Empty moment (lb-in, unscaled)", "\u7a7a\u673a moment (lb-in\uff0c\u672a\u7f29\u653e)"], emptyCg: ["Empty CG (in)", "\u7a7a\u673a CG (in)"],
    limits: ["Weight and fuel limits", "\u91cd\u91cf\u4e0e\u71c3\u6cb9\u9650\u5236"], max_ramp_lb: ["Maximum ramp (lb)", "\u6700\u5927\u505c\u673a\u91cd\u91cf (lb)"],
    max_takeoff_lb: ["Maximum takeoff (lb)", "\u6700\u5927\u8d77\u98de\u91cd\u91cf (lb)"], max_landing_lb: ["Maximum landing (lb)", "\u6700\u5927\u7740\u9646\u91cd\u91cf (lb)"],
    usable_fuel_gal: ["Usable fuel (US gal)", "\u53ef\u7528\u71c3\u6cb9 (US gal)"], fuel_density_lb_gal: ["Fuel density (lb / US gal)", "\u71c3\u6cb9\u5bc6\u5ea6 (lb / US gal)"],
    fuel_arm_in: ["Fuel arm (in)", "\u71c3\u6cb9 arm (in)"], baggage_total_lb: ["Combined baggage limit (lb)", "\u884c\u674e\u5408\u8ba1\u9650\u5236 (lb)"],
    stations: ["Loading stations", "\u88c5\u8f7d\u4f4d\u7f6e"], station: ["Station", "\u4f4d\u7f6e"], enabled: ["Enabled", "\u542f\u7528"], stationMax: ["Station max (lb, optional)", "\u4f4d\u7f6e\u9650\u91cd (lb\uff0c\u53ef\u9009)"],
    envelope: ["CG envelope", "\u91cd\u5fc3\u5305\u7ebf"], weightLb: ["Weight (lb)", "\u91cd\u91cf (lb)"], forward: ["Forward (in)", "\u524d\u9650 (in)"], aft: ["Aft (in)", "\u540e\u9650 (in)"],
    addRow: ["Add CG row", "\u6dfb\u52a0\u5305\u7ebf\u884c"], save: ["Save aircraft", "\u4fdd\u5b58\u6863\u6848"], use: ["Use saved aircraft", "\u4f7f\u7528\u5df2\u4fdd\u5b58\u6863\u6848"],
    catalogue: ["Model catalogue", "\u673a\u578b\u76ee\u5f55"], templateStatus: ["W&B template", "W&B \u6a21\u677f"], performance: ["Built-in performance tables", "\u5185\u7f6e\u6027\u80fd\u6570\u636e"], source: ["Source", "\u8d44\u6599\u6765\u6e90"],
    partial: ["Reference limits prefilled; actual W&B required", "\u5df2\u586b\u90e8\u5206\u53c2\u8003\u9650\u5236\uff1b\u9700\u8865\u672c\u673a W&B"], manual: ["Enter aircraft POH / W&B data", "\u9700\u586b\u672c\u673a POH / W&B \u6570\u636e"],
    unavailable: ["Not loaded", "\u672a\u5f55\u5165"], demo: ["C172N - Demo (sample W&B)", "C172N - \u6559\u5b66\u793a\u4f8b\uff08\u975e\u672c\u673a W&B\uff09"],
    demoNote: ["C172N performance tables / sample W&B", "C172N \u6027\u80fd\u8868 / \u6559\u5b66 W&B \u6837\u4f8b"],
    noPerformance: ["This model has no matching performance tables. W&B uses your saved aircraft data.", "\u8be5\u673a\u578b\u672a\u5f55\u5165\u5bf9\u5e94\u6027\u80fd\u8868\uff1bW&B \u4f7f\u7528\u6863\u6848\u6570\u636e\u3002"],
    performanceReady: ["POH performance data available", "POH \u6027\u80fd\u6570\u636e\u53ef\u7528"],
    reference1974: ["1974 C172M / Skyhawk reference only; not confirmed for this aircraft", "1974 C172M / Skyhawk \u53c2\u8003\u8868\uff0c\u672a\u786e\u8ba4\u672c\u673a\u9002\u7528\u6027"],
    ready: ["W&B profile complete", "W&B \u6863\u6848\u5df2\u586b\u5b8c"], draft: ["Draft: complete Aircraft fields before W&B calculation", "\u8349\u7a3f\uff1a\u8bf7\u5148\u8865\u9f50\u98de\u673a\u6863\u6848\u518d\u8ba1\u7b97 W&B"],
    savedOk: ["Aircraft saved", "\u6863\u6848\u5df2\u4fdd\u5b58"], selectSaved: ["Save the aircraft before selecting it.", "\u8bf7\u5148\u4fdd\u5b58\u6863\u6848\u3002"],
    unsaved: ["You have unsaved changes. Discard them?", "\u6709\u672a\u4fdd\u5b58\u7684\u4fee\u6539\uff0c\u786e\u5b9a\u653e\u5f03\u5417\uff1f"],
    confirmDelete: ["Delete this aircraft profile?", "\u786e\u5b9a\u5220\u9664\u8fd9\u4e2a\u98de\u673a\u6863\u6848\u5417\uff1f"],
    yearNote: ["1971 model year: 172L. 172N: 1977-1980. Confirm registration / serial number.", "1971 \u578b\u5e74\u4e3a 172L\uff1b172N \u4e3a 1977-1980\u3002\u8bf7\u7528\u6ce8\u518c\u53f7 / \u5e8f\u5217\u53f7\u786e\u8ba4\u3002"],
    importOk: ["Backup imported", "\u5907\u4efd\u5df2\u5bfc\u5165"], storageError: ["Browser storage is unavailable or damaged. Existing saved data has not been overwritten.", "\u6d4f\u89c8\u5668\u5b58\u50a8\u4e0d\u53ef\u7528\u6216\u635f\u574f\uff0c\u539f\u6570\u636e\u672a\u88ab\u8986\u76d6\u3002"]
  };
  function text(key) { return strings[key] ? strings[key][currentLang === "zh" ? 1 : 0] : key; }
  function showMessage(value, error = false) { message.textContent = value; message.className = error ? "profile-message error" : "profile-message"; }
  function numeric(input) { return input.value === "" ? null : Number(input.value); }
  function selected() { return saved.find(item => item.profile.id === activeId); }
  function persist(nextSaved = saved, nextActive = activeId) {
    if (storageBroken) throw new Error(text("storageError"));
    localStorage.setItem(storageKey, JSON.stringify({ version: 1, gfjeDefaultsVersion: 2, starterAircraftVersion: 1, profiles: nextSaved.map(item => item.profile), activeId: nextActive }));
  }
  async function validate(profile) {
    const response = await fetch("/api/aircraft/validate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile) });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error);
    return payload.result;
  }
  function allowDiscard() { return !dirty || window.confirm(text("unsaved")); }
  function clearResults() {
    document.querySelectorAll(".panel .result").forEach(box => {
      delete box.dataset.lastResult;
      box.className = "result empty" + (box.closest("#weight-balance") ? " wb-result" : "");
      box.textContent = t("resultHint");
    });
    document.querySelectorAll(".panel .steps").forEach(box => renderSteps(box, []));
  }
  function cgRow(point = {}) {
    const row = document.createElement("tr");
    ["weight_lb", "forward_in", "aft_in"].forEach(key => {
      const cell = row.insertCell();
      const input = document.createElement("input");
      input.type = "number"; input.step = "any"; input.dataset.cgField = key;
      input.setAttribute("aria-label", key);
      input.value = point[key] ?? ""; cell.append(input);
    });
    const button = document.createElement("button");
    button.type = "button"; button.className = "profile-icon"; button.textContent = "\u00d7";
    button.title = text("delete"); button.setAttribute("aria-label", text("delete"));
    button.addEventListener("click", () => { row.remove(); dirty = true; });
    row.insertCell().append(button);
    document.getElementById("profile-cg-rows").append(row);
  }
  function stationRow(station) {
    const row = document.createElement("tr"); row.dataset.stationKey = station.key;
    row.insertCell().textContent = station.label;
    const enabled = document.createElement("input"); enabled.type = "checkbox"; enabled.checked = station.enabled;
    enabled.setAttribute("aria-label", station.label + " enabled"); row.insertCell().append(enabled);
    for (const key of ["arm_in", "max_weight_lb"]) {
      const input = document.createElement("input"); input.type = "number"; input.step = "any";
      input.dataset.stationField = key; input.value = station[key] ?? "";
      input.setAttribute("aria-label", station.label + " " + key);
      if (key === "max_weight_lb") input.min = "0";
      row.insertCell().append(input);
    }
    document.getElementById("profile-stations").append(row);
  }
  function updateEmptyCg() {
    const weight = numeric(editor.elements.empty_weight_lb);
    const moment = numeric(editor.elements.empty_moment_lb_in);
    document.getElementById("profile-empty-cg").textContent = weight > 0 && moment !== null ? (moment / weight).toFixed(1) : "-";
  }
  function updateModelInfo() {
    const model = models.find(item => item.id === editor.elements.model_id.value);
    const source = document.getElementById("model-source"); source.replaceChildren();
    if (model && model.source) {
      const link = document.createElement("a"); link.href = model.source; link.target = "_blank"; link.rel = "noopener";
      link.textContent = text("source") + ": " + model.name; source.append(link);
    }
    document.getElementById("model-year-note").textContent = editor.elements.model_id.value.startsWith("c172") ? text("yearNote") : "";
  }
  function fillEditor(profile) {
    editingId = profile.id || "";
    editor.elements.model_id.value = profile.model_id;
    editor.dataset.loadedModel = profile.model_id;
    textFields.forEach(key => { editor.elements[key].value = profile[key] || ""; });
    editor.elements.year.value = profile.year ?? "";
    numberFields.forEach(key => { editor.elements[key].value = profile.wb[key] ?? ""; });
    document.getElementById("profile-stations").replaceChildren();
    profile.wb.stations.forEach(stationRow);
    document.getElementById("profile-cg-rows").replaceChildren();
    profile.wb.cg_limits.forEach(cgRow);
    if (!profile.wb.cg_limits.length) { cgRow(); cgRow(); }
    savedSelect.value = editingId;
    window.performanceEditor.fill(profile, saved.find(item => item.profile.id === profile.id)?.performance_status);
    updateEmptyCg(); updateModelInfo(); dirty = false;
  }
  function readEditor() {
    const profile = { id: editingId || window.pplPlatform.newId(), model_id: editor.elements.model_id.value, wb: {} };
    textFields.forEach(key => { profile[key] = editor.elements[key].value.trim(); });
    profile.year = numeric(editor.elements.year);
    numberFields.forEach(key => { profile.wb[key] = numeric(editor.elements[key]); });
    profile.wb.stations = [...document.querySelectorAll("#profile-stations tr")].map(row => ({
      key: row.dataset.stationKey, enabled: row.querySelector('[type="checkbox"]').checked,
      arm_in: numeric(row.querySelector('[data-station-field="arm_in"]')),
      max_weight_lb: numeric(row.querySelector('[data-station-field="max_weight_lb"]'))
    }));
    profile.wb.cg_limits = [...document.querySelectorAll("#profile-cg-rows tr")].map(row => Object.fromEntries(
      [...row.querySelectorAll("input")].map(input => [input.dataset.cgField, numeric(input)])
    ));
    profile.performance = window.performanceEditor.read();
    return profile;
  }
  function refreshOptions() {
    activeSelect.replaceChildren(new Option(text("demo"), "demo"));
    savedSelect.replaceChildren(new Option(text("new"), ""));
    saved.forEach(item => {
      const name = [item.profile.registration, item.profile.name].filter(Boolean).join(" / ");
      activeSelect.add(new Option(name, item.profile.id)); savedSelect.add(new Option(name, item.profile.id));
    });
    activeSelect.value = activeId; savedSelect.value = editingId;
    document.getElementById("copy-aircraft").disabled = !editingId;
    document.getElementById("delete-aircraft").disabled = !editingId;
  }
  function updateActive() {
    const item = selected();
    const wb = item ? item.profile.wb : demoProfile.wb;
    const model = item ? models.find(entry => entry.id === item.profile.model_id) : null;
    const yearMismatch = !!item && item.issues.some(issue => issue.includes("Model year mismatch"));
    const supportsPerformance = !item || (!yearMismatch && Object.values(item.performance_status).some(status => status.ready));
    document.getElementById("aircraft-heading").textContent = item ? [item.profile.registration, model.name].filter(Boolean).join(" / ") : "Cessna 172N - Demo";
    document.getElementById("aircraft-context").textContent = !item ? text("demoNote") : (supportsPerformance ? text("performanceReady") + " / " : text("noPerformance") + " ") + text(item.ready ? "ready" : "draft");
    document.getElementById("wb-profile-info").textContent = item ? text(item.ready ? "ready" : "draft") + " / " + item.profile.name : text("demoNote");
    performanceForms.forEach(form => {
      const phase = form.dataset.endpoint.split("/").pop();
      const config = item ? item.profile.performance[phase] : null;
      const available = !item || (!yearMismatch && (phase === "climb" ? item.profile.model_id === "c172n" : item.performance_status[phase].ready));
      form.querySelector('[type="submit"]').disabled = !available;
      let info = form.querySelector("[data-performance-info]");
      if (!info) { info = document.createElement("p"); info.dataset.performanceInfo = phase; info.className = "profile-notice"; form.prepend(info); }
      info.textContent = phase === "climb" ? (available ? "C172N" : text("unavailable")) : (!item || config.mode === "builtin" ? "C172N / " + text(available ? "performanceReady" : "unavailable") : [config.source, config.conditions, available ? "" : item.performance_status[phase].issues.join("; ")].filter(Boolean).join(" / "));
      if (config && config.mode === "c172m1974") info.textContent = text("reference1974") + " / " + config.conditions;
      if (phase === "landing") {
        const manual = config && (config.mode === "manual" || config.mode === "c172m1974");
        document.getElementById("manual-landing-weight").hidden = !manual;
        form.elements.weight_lbs.disabled = !manual;
      }
      if ((phase === "takeoff" || phase === "landing") && config && config.mode === "manual") {
        const weights = config.rows.map(row => row.weight_lb).filter(value => value != null);
        if (weights.length && form.dataset.performanceAircraft !== activeId) form.elements.weight_lbs.value = Math.max(...weights);
      }
      form.dataset.performanceAircraft = activeId;
    });
    wbForm.querySelector('[type="submit"]').disabled = !!item && !item.ready;
    const values = [wb.empty_weight_lb && wb.empty_moment_lb_in != null ? wb.empty_moment_lb_in / wb.empty_weight_lb : null,
      wb.empty_weight_lb, ...wb.stations.map(s => s.arm_in), wb.fuel_arm_in, wb.fuel_arm_in, wb.fuel_arm_in];
    wbForm.querySelectorAll('[data-wb-display]').forEach((input, index) => {
      input.value = values[index] == null ? "" : Number(values[index]).toFixed(1);
    });
    const density = wb ? wb.fuel_density_lb_gal : 6;
    wbForm.querySelectorAll(".wb-input-table label small").forEach(node => { node.textContent = "US gal x " + (density ?? "-"); });
    const keys = ["pilot_weight_lbs", "front_passenger_weight_lbs", "rear_left_weight_lbs", "rear_right_weight_lbs", "baggage1_weight_lbs", "baggage2_weight_lbs"];
    keys.forEach((key, index) => {
      const input = wbForm.elements[key]; input.disabled = !!wb && !wb.stations[index].enabled;
      input.min = "0";
      if (input.disabled) input.value = "0";
    });
  }
  function profileForBody(body) {
    const item = selected();
    return item ? item.profile : (body.has("empty_weight_lbs") ? demoProfile : null);
  }
  function translate() {
    document.querySelectorAll("[data-profile-text]").forEach(node => { node.textContent = text(node.dataset.profileText); });
    refreshOptions(); updateActive(); updateModelInfo();
    document.querySelectorAll("#model-catalogue tr").forEach((row, index) => {
      const model = models[index];
      row.cells[2].textContent = text(model.wb.max_takeoff_lb ? "partial" : "manual");
      row.cells[3].textContent = model.performance_label || text("unavailable");
      if (row.cells[4].firstChild) row.cells[4].firstChild.textContent = text("source");
    });
  }
  function populateCatalogue() {
    const modelSelect = editor.elements.model_id;
    models.forEach(model => {
      modelSelect.add(new Option(model.name, model.id));
      const row = document.createElement("tr");
      row.insertCell().textContent = model.name;
      row.insertCell().textContent = model.years ? model.years.join(" - ") : "-";
      row.insertCell(); row.insertCell(); const source = row.insertCell();
      if (model.source) { const link = document.createElement("a"); link.href = model.source; link.target = "_blank"; link.rel = "noopener"; source.append(link); }
      document.getElementById("model-catalogue").append(row);
    });
  }
  function download(value, name) {
    window.pplPlatform.download(JSON.stringify(value, null, 2), name, "application/json");
  }
  async function init() {
    const response = await fetch("/api/aircraft/models");
    const payload = await response.json(); if (!payload.ok) throw new Error(payload.error);
    models = payload.models; populateCatalogue();
    demoProfile = copy(payload.starter_profile);
    Object.assign(demoProfile, { id: "demo", registration: "DEMO", name: "C172N training example", wb_reference: "Training example" });
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const state = JSON.parse(raw);
        if (state.version !== 1 || !Array.isArray(state.profiles) || state.profiles.length > 100) throw new Error("Invalid profile storage");
        saved = await Promise.all(state.profiles.map(validate));
        if (new Set(saved.map(item => item.profile.id)).size !== saved.length) throw new Error("Duplicate profile IDs");
        activeId = saved.some(item => item.profile.id === state.activeId) ? state.activeId : "demo";
        if (state.gfjeDefaultsVersion !== 2) {
          const item = saved.find(entry => entry.profile.id === "aircraft-c-gfje" && entry.profile.registration === "C-GFJE" && entry.profile.model_id === "c172n");
          if (item) {
            const profile = copy(item.profile);
            const wasBlank = profile.wb.empty_weight_lb == null && profile.wb.empty_moment_lb_in == null;
            for (const key of ["empty_weight_lb", "empty_moment_lb_in", "max_ramp_lb", "usable_fuel_gal"]) {
              if (profile.wb[key] == null && (wasBlank || !key.startsWith("empty_"))) profile.wb[key] = payload.starter_profile.wb[key];
            }
            if (wasBlank) {
              profile.wb.stations[5].enabled = true;
              if (profile.wb.stations[5].arm_in == null) profile.wb.stations[5].arm_in = 123;
              if (!profile.wb_reference) profile.wb_reference = payload.starter_profile.wb_reference;
              profile.notes = profile.notes.replace("actual empty weight and moment are not supplied.", "User confirmed the original W&B values belong to GFJE.");
            }
            const updated = await validate(profile);
            saved = saved.map(entry => entry === item ? updated : entry);
          }
        }
        if (state.starterAircraftVersion !== 1) {
          const seed = payload.starter_profiles.find(profile => profile.registration === "C-FFCT");
          const exists = saved.some(item => item.profile.id === seed.id || item.profile.registration.toUpperCase().replace(/[-\s]/g, "") === "CFFCT");
          if (!exists && saved.length < 100) saved.push(await validate(seed));
        }
        if (state.gfjeDefaultsVersion !== 2 || state.starterAircraftVersion !== 1) persist();
      } else {
        saved = await Promise.all(payload.starter_profiles.map(validate));
        activeId = saved[0].profile.id;
        persist();
      }
    } catch (error) { storageBroken = true; saved = []; activeId = "demo"; showMessage(text("storageError"), true); }
    const info = document.createElement("p"); info.id = "wb-profile-info"; info.className = "profile-notice"; wbForm.prepend(info);
    fillEditor(copy(selected() ? selected().profile : (saved[0] ? saved[0].profile : models.find(model => model.id === "c172l").template)));
    refreshOptions(); translate();
    activeSelect.addEventListener("change", () => {
      try {
        persist(saved, activeSelect.value); activeId = activeSelect.value;
        if (!dirty && selected()) fillEditor(copy(selected().profile));
        refreshOptions(); updateActive(); clearResults();
      }
      catch (error) { activeSelect.value = activeId; showMessage(error.message, true); }
    });
    editor.addEventListener("input", () => { dirty = true; updateEmptyCg(); });
    savedSelect.addEventListener("change", () => {
      if (!allowDiscard()) { savedSelect.value = editingId; return; }
      if (savedSelect.value) { const item = saved.find(entry => entry.profile.id === savedSelect.value); fillEditor(copy(item.profile)); showMessage(item.issues.join("; ")); }
      else { fillEditor(copy(models.find(model => model.id === "c172l").template)); showMessage(""); }
      refreshOptions();
    });
    editor.elements.model_id.addEventListener("change", () => {
      const modelId = editor.elements.model_id.value;
      if (!window.confirm(currentLang === "zh" ? "\u5207\u6362\u673a\u578b\u4f1a\u91cd\u7f6e\u5f53\u524d W&B \u5b57\u6bb5\uff0c\u786e\u5b9a\u5417\uff1f" : "Changing model resets W&B fields. Continue?")) {
        editor.elements.model_id.value = editor.dataset.loadedModel; return;
      }
      const previous = readEditor(); const profile = copy(models.find(model => model.id === modelId).template);
      textFields.filter(key => key !== "name").forEach(key => { profile[key] = previous[key]; });
      profile.id = editingId; profile.year = previous.year;
      fillEditor(profile); dirty = true;
    });
    document.getElementById("new-aircraft").addEventListener("click", () => { if (allowDiscard()) { fillEditor(copy(models.find(model => model.id === "c172l").template)); refreshOptions(); showMessage(""); } });
    document.getElementById("copy-aircraft").addEventListener("click", () => {
      if (!editingId || !allowDiscard()) return;
      const profile = copy(saved.find(item => item.profile.id === editingId).profile);
      profile.id = ""; profile.registration = ""; profile.serial_number = ""; profile.name += " (copy)";
      profile.wb.empty_weight_lb = null; profile.wb.empty_moment_lb_in = null; profile.wb_reference = ""; profile.wb_date = "";
      fillEditor(profile); dirty = true; refreshOptions();
    });
    document.getElementById("delete-aircraft").addEventListener("click", () => {
      if (!editingId || !window.confirm(text("confirmDelete"))) return;
      try {
        const next = saved.filter(item => item.profile.id !== editingId);
        const nextActive = activeId === editingId ? "demo" : activeId; persist(next, nextActive);
        saved = next;
        activeId = nextActive; fillEditor(copy(models.find(model => model.id === "c172l").template));
        refreshOptions(); updateActive(); clearResults(); showMessage("");
      } catch (error) { showMessage(error.message, true); }
    });
    editor.addEventListener("submit", async event => {
      event.preventDefault(); const button = editor.querySelector('[type="submit"]'); button.disabled = true;
      try {
        const item = await validate(readEditor());
        const next = saved.filter(entry => entry.profile.id !== item.profile.id).concat([item]);
        if (next.length > 100) throw new Error("Maximum 100 aircraft profiles.");
        persist(next); saved = next;
        fillEditor(copy(item.profile)); refreshOptions(); updateActive(); clearResults();
        showMessage(text("savedOk") + (item.ready ? " / " + text("ready") : " / " + item.issues.join("; ")));
      } catch (error) { showMessage(error.message, true); }
      finally { button.disabled = false; }
    });
    document.getElementById("use-aircraft").addEventListener("click", () => {
      if (!editingId || dirty) { showMessage(text("selectSaved"), true); return; }
      activeSelect.value = editingId; activeSelect.dispatchEvent(new Event("change"));
      document.querySelector('[data-tab="weight-balance"]').click();
    });
    document.getElementById("add-cg-row").addEventListener("click", () => { cgRow(); dirty = true; });
    document.getElementById("export-aircraft").addEventListener("click", () => download({ version: 1, profiles: saved.map(item => item.profile) }, "ppl-aircraft-backup.json"));
    document.getElementById("import-aircraft").addEventListener("change", async event => {
      try {
        const file = event.target.files[0]; if (!file) return;
        if (file.size > 2000000) throw new Error("Backup must be smaller than 2 MB.");
        const state = JSON.parse(await file.text());
        if (state.version !== 1 || !Array.isArray(state.profiles) || state.profiles.length + saved.length > 100) throw new Error("Invalid aircraft backup (maximum 100 profiles).");
        const imported = [];
        for (const profile of state.profiles) imported.push(await validate({ ...profile, id: window.pplPlatform.newId() }));
        const next = saved.concat(imported); persist(next); saved = next; refreshOptions(); showMessage(text("importOk"));
      } catch (error) { showMessage(error.message, true); }
      finally { event.target.value = ""; }
    });
    document.addEventListener("ppl-language-change", translate);
    window.aircraftProfiles = {
      canCalculate(form) {
        const item = selected(); if (!item) return true;
        if (form === wbForm) return item.ready;
        if (item.issues.some(issue => issue.includes("Model year mismatch"))) return false;
        const phase = form.dataset.endpoint.split("/").pop();
        return phase === "climb" ? item.profile.model_id === "c172n" : item.performance_status[phase].ready;
      },
      appendProfile(body) { const profile = profileForBody(body); if (profile) body.set("aircraft_profile", JSON.stringify(profile)); },
      matchesProfile(body) { const profile = profileForBody(body); return (body.get("aircraft_profile") || null) === (profile ? JSON.stringify(profile) : null); }
    };
  }
  init().catch(error => { showMessage(error.message, true); document.getElementById("aircraft-context").textContent = error.message; });
})();
