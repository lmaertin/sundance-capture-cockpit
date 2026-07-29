let currentLanguage = "en";

const keyDocs = {
  A: "Select Button: Scrolls the menu through filter cycle programming features. Manually activates the circulation pump when it is off for 1 hour.",
  B: "Cycle Button: Accesses filter cycle program mode and advances to the next cycle.",
  C: "Mode Button: Switches between Standard and Economy modes.",
  D: "Display Button: Displays the time of day and opens time setting and lock functions.",
  E: "Invert Button: Inverts the main 4-digit LCD display.",
  F: "Jets 2 Button: Controls jets pump 2 (and Maxxus/Aspen jets pump 3).",
  G: "Jets 1 Button: Controls jets pump 1.",
  H: "Blower Button: Controls the air blower.",
  I: "Light Mode Button: Selects one of 4 color modes for waterfall, footwell, and air control lights.",
  J: "Light Button: Turns waterfall, footwell, and air control lights on in unison. Press once for high intensity, a second time for medium, a third time for low, and a fourth time to turn off.",
  K: "Warmer and Cooler Buttons: Display and adjust the temperature setting and other programming features.",
};

const panelButtonLayout = [
  {
    code: "A",
    cls: "hs-a",
    nameEn: "Select",
    icon: "/static/button-icons/original/selection.png",
  },
  {
    code: "B",
    cls: "hs-b",
    nameEn: "Cycle",
    icon: "/static/button-icons/original/cycle.png",
  },
  {
    code: "C",
    cls: "hs-c",
    nameEn: "Mode",
    icon: "/static/button-icons/original/mode.png",
  },
  {
    code: "D",
    cls: "hs-d",
    nameEn: "Display",
    icon: "/static/button-icons/original/display.png",
  },
  {
    code: "K",
    cls: "hs-k-warm",
    nameEn: "Warmer",
    icon: "/static/button-icons/original/warmer.png",
    direction: "warmer",
  },
  {
    code: "K",
    cls: "hs-k-cool",
    nameEn: "Cooler",
    icon: "/static/button-icons/original/cooler.png",
    direction: "cooler",
  },
  {
    code: "J",
    cls: "hs-j",
    nameEn: "Light",
    icon: "/static/button-icons/original/light_on_off.png",
  },
  {
    code: "I",
    cls: "hs-i",
    nameEn: "Light mode",
    icon: "/static/button-icons/original/lighting_mode.png",
  },
  {
    code: "H",
    cls: "hs-h",
    nameEn: "Blower",
    icon: "/static/button-icons/original/fan.png",
  },
  {
    code: "G",
    cls: "hs-g",
    nameEn: "Jets 1",
    icon: "/static/button-icons/original/jet_pump_1.png",
  },
  {
    code: "F",
    cls: "hs-f",
    nameEn: "Jets 2",
    icon: "/static/button-icons/original/jet_pump_2.png",
  },
  {
    code: "E",
    cls: "hs-e",
    nameEn: "Invert",
    icon: "/static/button-icons/original/reverse_display.png",
  },
];

const displaySymbolLayout = [
  { key: "lock", label: "Lock", icon: "/static/display-icons/original/lock.png", x: 4.2, y: 6, w: 7.2 },
  { key: "heater", label: "Heater", icon: "/static/display-icons/original/heater.png", x: 12.5, y: 6.2, w: 7.2 },
  { key: "sanitizer", label: "Sanitizer", icon: "/static/display-icons/original/uv-cleaner.png", x: 20.9, y: 5.8, w: 7.8 },
  { key: "cycle_set", label: "Filter Cycle Setting", icon: "/static/display-icons/original/filter-cycle-settings.png", x: 30.3, y: 6, w: 7.4 },
  {
    key: "cycle_num",
    label: "Filter Cycle Number",
    icon: "/static/display-icons/original/filter-cycle-number.png",
    x: 39,
    y: 6.2,
    w: 7.1,
    interactive: false,
  },
  { key: "clock", label: "Start Time", icon: "/static/display-icons/original/filter-cycle-start-time.png", x: 47.6, y: 6.3, w: 7.2 },
  { key: "duration", label: "Duration", icon: "/static/display-icons/original/filter-cycle-duration.png", x: 56.3, y: 6.4, w: 7.2 },
  { key: "set_temp", label: "Set Temperature", icon: "/static/display-icons/original/set-temperature.png", x: 4.6, y: 28.4, w: 7.2 },
  { key: "set_time", label: "Set Time", icon: "/static/display-icons/original/set-time.png", x: 12.4, y: 28.6, w: 6.2 },
  { key: "filter", label: "Filter Indicator", icon: "/static/display-icons/original/filter-indicator.png", x: 4.4, y: 45.4, w: 7.6 },
  { key: "am", label: "AM", icon: "/static/display-icons/original/AM.png", x: 81.2, y: 33.2, w: 7.2 },
  { key: "pm", label: "PM", icon: "/static/display-icons/original/PM.png", x: 81.2, y: 42.6, w: 7.2 },
  { key: "mode_standard", label: "Standard", icon: "/static/display-icons/original/standard-mode.png", x: 78.8, y: 56.1, w: 16.2 },
  { key: "blower", label: "Air Jet", icon: "/static/display-icons/original/airjet.png", x: 24.2, y: 75.4, w: 10.4 },
  { key: "pump1", label: "Water Jet 1", icon: "/static/display-icons/original/waterjet1.png", x: 49.3, y: 75.2, w: 11.1 },
  { key: "pump2", label: "Water Jet 2", icon: "/static/display-icons/original/waterjet2.png", x: 65.5, y: 75.2, w: 11.1 },
  { key: "float_23", label: "Point 2-3", icon: "/static/display-icons/original/floating-point-digit-2-3.png", x: 45.5, y: 51.1, w: 1.9 },
  { key: "float_34", label: "Point 3-4", icon: "/static/display-icons/original/floating-point-digit-3-4.png", x: 57.2, y: 51.1, w: 1.9 },
  { key: "clock_delimiter", label: "Clock Delimiter", icon: "/static/display-icons/original/clock_delimiter.png", x: 51.1, y: 43.1, w: 1.7 },
];

const displaySymbolDescriptionsByLang = {
  en: [
  {
    key: "lock",
    title: "Lock",
    text: "Indicates panel, set temperature, or filter cycle programming is locked.",
  },
  {
    key: "heater",
    title: "Heat",
    text: "Indicates heater is on.",
  },
  {
    key: "sanitizer",
    title: "Sanitizer",
    text: "Indicates that the sanitizing system is on.",
  },
  {
    key: "cycle_set",
    title: "Adjust Filter Cycle",
    text: "Indicates filter cycle programming feature is accessed.",
  },
  {
    key: "cycle_num",
    title: "Filter Cycle Number",
    text: "Indicates which programmed filter cycle is running.",
  },
  {
    key: "cycle_running",
    title: "Filter Cycle",
    text: "Indicates programmed filter cycle is running.",
  },
  {
    key: "clock",
    title: "Filter Cycle Start Time",
    text: "Indicates filter cycle start time programming is accessed.",
  },
  {
    key: "duration",
    title: "Filter Cycle Duration",
    text: "Indicates filter cycle duration programming is accessed.",
  },
  {
    key: "set_temp",
    title: "Set Temperature",
    text: "Indicates current set temperature is displayed.",
  },
  {
    key: "set_time",
    title: "Set Time",
    text: "Indicates current time is displayed.",
  },
  {
    key: "filter",
    title: "Filter Annunciator",
    text: "Indicates filter cleaning and/or replacement is required.",
  },
  {
    key: "blower",
    title: "Blower",
    text: "Indicates blower is on.",
  },
  {
    key: "pump1",
    title: "Jets 1",
    text: "Indicates jets pump 1 is on.",
  },
  {
    key: "pump2",
    title: "Jets 2",
    text: "Indicates jets pump 2 is on (also shown for Maxxus/Aspen pump 3).",
  },
  {
    key: "mode_standard",
    title: "Mode",
    text: "Indicates selected filter mode. No icon means Economy mode is selected.",
  },
  ],
};

const state = {
  activeStatus: null,
  lastRecordingId: null,
  sequenceSteps: [],
  activeDisplaySymbols: new Set(),
  sigrokLogLines: [],
};

function renderSigrokLog() {
  const node = element("sigrokLog");
  if (!node) {
    return;
  }
  if (state.sigrokLogLines.length === 0) {
    node.textContent = "PS> waiting for first capture command...";
    return;
  }
  node.textContent = state.sigrokLogLines.join("\n");
}

function appendSigrokLog(line) {
  const stamp = new Date().toLocaleTimeString();
  state.sigrokLogLines.push(`[${stamp}] ${line}`);
  if (state.sigrokLogLines.length > 120) {
    state.sigrokLogLines = state.sigrokLogLines.slice(-120);
  }
  renderSigrokLog();
}

function clearSigrokLog() {
  state.sigrokLogLines = [];
  renderSigrokLog();
}

function localizedButtonName(item) {
  return item.nameEn;
}

function localizedKeyDoc(code) {
  return keyDocs[code] || "";
}

function element(id) {
  return document.getElementById(id);
}

function setSyncInfo(ok, details = "") {
  const node = element("syncInfo");
  if (!node) {
    return;
  }
  const stamp = new Date().toLocaleTimeString();
  if (ok) {
    node.textContent = `Updated ${stamp}${details ? ` - ${details}` : ""}`;
    return;
  }
  node.textContent = `Refresh failed ${stamp}${details ? ` - ${details}` : ""}`;
}

function getSelectedChannels() {
  const group = element("channelsGroup");
  if (!group) {
    return "D4,D5,D6,D7";
  }
  const selected = Array.from(group.querySelectorAll("input[type=checkbox]:checked"))
    .map((node) => node.value)
    .filter((value) => Boolean(value));
  return selected.join(",");
}

function setSelectedChannels(channelsCsv) {
  const group = element("channelsGroup");
  if (!group) {
    return;
  }
  const wanted = new Set(
    String(channelsCsv || "")
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
  );
  for (const input of group.querySelectorAll("input[type=checkbox]")) {
    input.checked = wanted.has(input.value);
  }
}

function getSelectedDriver() {
  const select = element("driverSelect");
  const custom = element("driverCustom");
  if (!select) {
    return "fx2lafw";
  }
  if (select.value === "__custom__") {
    const value = custom ? String(custom.value || "").trim() : "";
    if (!value) {
      throw new Error(
        currentLanguage === "de"
          ? "Bitte Custom-Driver eintragen"
          : "Please enter custom driver"
      );
    }
    return value;
  }
  return select.value;
}

function setSelectedDriver(driver) {
  const select = element("driverSelect");
  const custom = element("driverCustom");
  if (!select || !custom) {
    return;
  }
  const value = String(driver || "").trim();
  const options = Array.from(select.options).map((opt) => opt.value);
  if (options.includes(value)) {
    select.value = value;
    custom.classList.add("hidden");
    custom.value = "";
    return;
  }
  select.value = "__custom__";
  custom.classList.remove("hidden");
  custom.value = value;
}

function updateDriverCustomVisibility() {
  const select = element("driverSelect");
  const custom = element("driverCustom");
  if (!select || !custom) {
    return;
  }
  if (select.value === "__custom__") {
    custom.classList.remove("hidden");
  } else {
    custom.classList.add("hidden");
    custom.value = "";
  }
}

function showToast(message, isError = false) {
  const toast = element("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.style.background = isError ? "#7e1f33" : "#133e33";
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 2400);
}

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  return body;
}

function currentRecordingId() {
  const value = Number(element("recordingId").value || "0");
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error("Bitte zuerst eine gueltige Recording ID setzen");
  }
  return value;
}

function updateSequencePreview() {
  const preview = element("sequencePreview");
  if (!preview) {
    return;
  }
  if (state.sequenceSteps.length === 0) {
    preview.textContent = "No steps yet";
    return;
  }

  const lines = state.sequenceSteps.map((step, idx) => `${idx + 1}. ${step}`);
  preview.textContent = lines.join("\n");

  const compact = state.sequenceSteps.join(" > ");
  const sequenceInput = element("sequence");
  if (sequenceInput) {
    sequenceInput.value = compact;
  }
}

function appendStep(stepText) {
  state.sequenceSteps.push(stepText);
  updateSequencePreview();
}

function clearSequence() {
  state.sequenceSteps = [];
  updateSequencePreview();
}

async function copySequence() {
  const sequenceInput = element("sequence");
  if (!sequenceInput) {
    showToast("Not available", true);
    return;
  }
  const text = sequenceInput.value.trim();
  if (!text) {
    showToast("No sequence to copy", true);
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    showToast("Sequence copied");
    return;
  }

  const tmp = document.createElement("textarea");
  tmp.value = text;
  document.body.appendChild(tmp);
  tmp.select();
  document.execCommand("copy");
  tmp.remove();
  showToast("Sequence copied");
}

async function refreshStatus() {
  const status = await jsonFetch("/api/status");
  state.activeStatus = status;

  const badge = element("statusBadge");
  const text = element("statusText");

  if (!status.active) {
    badge.textContent = "Idle";
    badge.className = "badge idle";
    text.textContent = "No active recording";
    return;
  }

  state.lastRecordingId = status.recordingId;
  badge.textContent = "Live";
  badge.className = "badge live";
  const seconds = (status.elapsedMs / 1000).toFixed(1);
  text.textContent =
    currentLanguage === "de"
      ? `ID ${status.recordingId} laeuft seit ${seconds}s`
      : `ID ${status.recordingId} running for ${seconds}s`;
}

async function refreshRecordings() {
  const data = await jsonFetch("/api/recordings?limit=60");
  const body = element("recordingsBody");
  body.innerHTML = "";

  const exportLabel = "Export JSON";
  const downloadSrLabel = "Download .sr";
  const deleteLabel = "Delete";
  const saveLabel = "Save";

  function formatDuration(startIso, endIso, status) {
    if (!startIso) {
      return "-";
    }
    const start = Date.parse(startIso);
    if (!Number.isFinite(start)) {
      return "-";
    }
    const end = endIso ? Date.parse(endIso) : Date.now();
    if (!Number.isFinite(end)) {
      return "-";
    }
    const sec = Math.max(0, Math.round((end - start) / 1000));
    const mm = Math.floor(sec / 60);
    const ss = sec % 60;
    const text = `${mm}:${String(ss).padStart(2, "0")}`;
    if (!endIso && status === "recording") {
      return `${text}*`;
    }
    return text;
  }

  function formatMeasuredAt(startIso) {
    if (!startIso) {
      return "-";
    }
    const ts = Date.parse(startIso);
    if (!Number.isFinite(ts)) {
      return String(startIso);
    }
    return new Date(ts).toLocaleString();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  for (const item of data.items) {
    const duration = formatDuration(item.start_time, item.end_time, item.status);
    const measuredAt = formatMeasuredAt(item.start_time);
    const previewItems = Array.isArray(item.annotation_preview)
      ? item.annotation_preview
      : [];
    let preview = previewItems.join(" | ");
    const totalAnnotations = Number(item.annotation_count || 0);
    if (totalAnnotations > previewItems.length) {
      const missing = totalAnnotations - previewItems.length;
      preview = preview
        ? `${preview} | +${missing} more`
        : `+${missing} more`;
    }

    const trMain = document.createElement("tr");
    trMain.innerHTML = `
      <td>${item.id}</td>
      <td>${item.name}</td>
      <td>${item.status}</td>
      <td>${measuredAt}</td>
      <td>${duration}</td>
      <td>${item.samplerate}</td>
      <td>${item.channels}</td>
      <td>${item.annotation_count}</td>
      <td>
        <button class="btn" data-download-sr="${item.id}">${downloadSrLabel}</button>
        <button class="btn" data-export="${item.id}">${exportLabel}</button>
        <button class="btn" data-save="${item.id}">${saveLabel}</button>
        <button class="btn danger" data-delete="${item.id}">${deleteLabel}</button>
      </td>
    `;
    body.appendChild(trMain);

    const trDetails = document.createElement("tr");
    trDetails.className = "recording-details-row";
    trDetails.innerHTML = `
      <td colspan="9">
        <div class="recording-details-line">
          <span class="recording-preview-label">Annotations:</span>
          <span class="recording-preview-text">${preview || "none"}</span>
        </div>
        <div class="recording-edit-grid">
          <label>
            Name
            <input data-edit-name="${item.id}" value="${escapeHtml(item.name)}" />
          </label>
          <label>
            Comment
            <input data-edit-notes="${item.id}" value="${escapeHtml(item.notes || "")}" placeholder="optional" />
          </label>
        </div>
      </td>
    `;
    body.appendChild(trDetails);
  }

  setSyncInfo(true, `${data.items.length} items`);

  for (const btn of body.querySelectorAll("button[data-export]")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.export);
      const exported = await jsonFetch(`/api/recordings/${id}/export`);
      const blob = new Blob([JSON.stringify(exported, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `recording_${id}_annotations.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    });
  }

  for (const btn of body.querySelectorAll("button[data-download-sr]")) {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.downloadSr);
      const anchor = document.createElement("a");
      anchor.href = `/api/recordings/${id}/file`;
      anchor.download = `recording_${id}.sr`;
      anchor.click();
    });
  }

  for (const btn of body.querySelectorAll("button[data-delete]")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.delete);
      const ok = window.confirm(
        `Delete recording ${id}?`
      );
      if (!ok) {
        return;
      }

      try {
        await jsonFetch("/api/recordings/delete", {
          method: "POST",
          body: JSON.stringify({ recordingId: id }),
        });
        showToast(`Recording ${id} deleted`);
        await refreshRecordings();
        await refreshStatus();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  for (const btn of body.querySelectorAll("button[data-save]")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.save);
      const nameInput = body.querySelector(`input[data-edit-name="${id}"]`);
      const notesInput = body.querySelector(`input[data-edit-notes="${id}"]`);
      const name = nameInput ? String(nameInput.value || "") : "";
      const notes = notesInput ? String(notesInput.value || "") : "";
      try {
        await jsonFetch("/api/recordings/update", {
          method: "POST",
          body: JSON.stringify({
            recordingId: id,
            name,
            notes,
          }),
        });
        showToast(`Recording ${id} saved`);
        await refreshRecordings();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }
}

async function startRecording() {
  const channels = getSelectedChannels();
  if (!channels) {
    throw new Error("Select at least one channel");
  }

  const payload = {
    name: element("name").value,
    sequence: "auto-panel-flow",
    notes: "",
    samplerate: element("samplerate").value,
    channels,
    driver: getSelectedDriver(),
    durationSeconds: Number(element("durationSeconds").value || "20"),
    simulate: element("simulate").checked,
  };

  const result = await jsonFetch("/api/recordings/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (Array.isArray(result.command) && result.command.length > 0) {
    appendSigrokLog(`PS> ${result.command.join(" ")}`);
  } else if (payload.simulate) {
    appendSigrokLog("PS> simulation mode enabled (no sigrok-cli command executed)");
  }

  state.lastRecordingId = result.recordingId;
  showToast(`Recording ${result.recordingId} gestartet`);
  await refreshStatus();
  await refreshRecordings();
}

async function stopRecording() {
  const result = await jsonFetch("/api/recordings/stop", {
    method: "POST",
    body: "{}",
  });
  if (result.stopped) {
    const endCommentField = element("endComment");
    const endComment = endCommentField ? endCommentField.value.trim() : "";
    if (endComment) {
      await addAnnotationForRecording(result.recordingId, "session_comment", { text: endComment });
      if (endCommentField) {
        endCommentField.value = "";
      }
    }
    showToast(
      `Recording ${result.recordingId} stopped`
    );
    appendSigrokLog(`PS> recording ${result.recordingId} stopped (${result.status})`);
  } else {
    showToast(result.message || "No active recording", true);
    appendSigrokLog("PS> stop requested but no active recording");
  }
  await refreshStatus();
  await refreshRecordings();
}

function resolveRecordingId() {
  if (state.activeStatus && state.activeStatus.active) {
    return Number(state.activeStatus.recordingId);
  }
  if (state.lastRecordingId) {
    return Number(state.lastRecordingId);
  }
  throw new Error(
    "Start a recording first"
  );
}

async function addAnnotationForRecording(recordingId, kind, payload) {
  const body = { recordingId, kind, payload };
  const result = await jsonFetch("/api/annotations", {
    method: "POST",
    body: JSON.stringify(body),
  });
  showToast(`Annotation ${kind}`);
  await refreshRecordings();
  return result;
}

async function addAnnotation(kind, payload) {
  return addAnnotationForRecording(resolveRecordingId(), kind, payload);
}

function highlightTap(target) {
  target.classList.add("is-active");
  setTimeout(() => target.classList.remove("is-active"), 160);
}

function buildPanelHotspots() {
  const target = element("panelHotspots");
  target.innerHTML = "";
  for (const item of panelButtonLayout) {
    const localizedName = localizedButtonName(item);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `panel-hotspot ${item.cls}`;
    const iconSrc = item.icon;
    button.innerHTML = `
      <img class="panel-icon" src="${iconSrc}" alt="${localizedName}" />
      <span class="visually-hidden">${localizedName}</span>
    `;
    const docKey = item.code;
    button.setAttribute("title", localizedKeyDoc(docKey));
    button.setAttribute("aria-label", `${localizedName}: ${localizedKeyDoc(docKey)}`);

    button.addEventListener("click", async () => {
      try {
        highlightTap(button);
        if (item.direction) {
          await addAnnotation("button_press", {
            button: item.code,
            name: localizedName,
            direction: item.direction,
          });
        } else {
          await addAnnotation("button_press", {
            button: item.code,
            name: localizedName,
          });
        }
        appendStep(localizedName);
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });

    target.appendChild(button);
  }
}

function buildKeyGuide() {
  const target = element("keyGuide");
  if (!target) {
    return;
  }

  const entries = [
    {
      name: "Select Button",
      code: "A",
      docCode: "A",
      icons: ["/static/button-icons/original/selection.png"],
    },
    {
      name: "Cycle Button",
      code: "B",
      docCode: "B",
      icons: ["/static/button-icons/original/cycle.png"],
    },
    {
      name: "Mode Button",
      code: "C",
      docCode: "C",
      icons: ["/static/button-icons/original/mode.png"],
    },
    {
      name: "Display Button",
      code: "D",
      docCode: "D",
      icons: ["/static/button-icons/original/display.png"],
    },
    {
      name: "Invert Button",
      code: "E",
      docCode: "E",
      icons: ["/static/button-icons/original/reverse_display.png"],
    },
    {
      name: "Jets 2 Button",
      code: "F",
      docCode: "F",
      icons: ["/static/button-icons/original/jet_pump_2.png"],
    },
    {
      name: "Jets 1 Button",
      code: "G",
      docCode: "G",
      icons: ["/static/button-icons/original/jet_pump_1.png"],
    },
    {
      name: "Blower Button",
      code: "H",
      docCode: "H",
      icons: ["/static/button-icons/original/fan.png"],
    },
    {
      name: "Light Mode Button",
      code: "I",
      docCode: "I",
      icons: ["/static/button-icons/original/lighting_mode.png"],
    },
    {
      name: "Light Button",
      code: "J",
      docCode: "J",
      icons: ["/static/button-icons/original/light_on_off.png"],
    },
    {
      name: "Warmer and Cooler Buttons",
      code: "K+/K-",
      docCode: "K",
      icons: [
        "/static/button-icons/original/warmer.png",
        "/static/button-icons/original/cooler.png",
      ],
    },
  ];
  target.innerHTML = "";

  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "key-item";
    const docCode = entry.docCode || entry.code;
    const displayName = entry.name;
    const iconsHtml = (entry.icons || [])
      .map((icon) => `<img src="${icon}" alt="${displayName}" />`)
      .join("");
    row.innerHTML = `
      <span class="key-icon-stack">${iconsHtml}</span>
      <span class="key-text"><strong>${displayName}:</strong> ${localizedKeyDoc(docCode)}</span>
    `;
    target.appendChild(row);
  }
}

function refreshActiveDisplaySymbolsInfo() {
  const target = element("activeDisplaySymbols");
  if (!target) {
    return;
  }

  const active = displaySymbolLayout
    .filter((symbol) => state.activeDisplaySymbols.has(symbol.key))
    .map((symbol) => symbol.label);

  target.textContent = active.length > 0
    ? `${currentLanguage === "de" ? "Aktiv" : "Active"}: ${active.join(" | ")}`
    : currentLanguage === "de"
      ? "Keine Symbole aktiv"
      : "No symbols active";
}

function updateDisplayValuePreview() {
  const input = element("displayValue");
  if (!input) {
    return;
  }
  const value = input.value.trim();
  const preview = element("displayValuePreview");
  if (!preview) {
    return;
  }
  preview.textContent = value || "88:8.8";
}

function updateCycleNumberPreview() {
  const node = element("cycleNumberPreview");
  if (!node) {
    return;
  }
  const toggle = element("showCycleNumber");
  const enabled = Boolean(toggle && toggle.checked);
  const input = element("cycleNumber");
  if (!input) {
    return;
  }
  input.disabled = !enabled;
  node.classList.toggle("hidden", !enabled);
  if (!enabled) {
    return;
  }
  const digits = input.value.replace(/\D+/g, "");
  const oneDigit = digits ? digits.slice(-1) : "8";
  if (input.value !== oneDigit) {
    input.value = oneDigit;
  }
  node.textContent = oneDigit;
}

function buildDisplayBoard() {
  const board = element("displayBoard");
  if (!board) {
    return;
  }

  board.innerHTML = "";

  const cycleNumberSymbol = displaySymbolLayout.find((item) => item.key === "cycle_num");

  for (const symbol of displaySymbolLayout) {
    if (symbol.key === "cycle_num") {
      continue;
    }

    if (symbol.interactive === false) {
      const marker = document.createElement("div");
      marker.className = "display-symbol-static";
      marker.style.left = `${symbol.x}%`;
      marker.style.top = `${symbol.y}%`;
      marker.style.width = `${symbol.w}%`;
      marker.innerHTML = `<img src="${symbol.icon}" alt="${symbol.label}" />`;
      board.appendChild(marker);
      continue;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "display-symbol-btn";
    button.dataset.symbol = symbol.key;
    button.setAttribute("aria-label", symbol.label);
    button.setAttribute("title", symbol.label);
    button.style.left = `${symbol.x}%`;
    button.style.top = `${symbol.y}%`;
    button.style.width = `${symbol.w}%`;
    button.innerHTML = `<img src="${symbol.icon}" alt="${symbol.label}" />`;

    button.addEventListener("click", () => {
      const isActive = state.activeDisplaySymbols.has(symbol.key);
      if (isActive) {
        state.activeDisplaySymbols.delete(symbol.key);
      } else {
        state.activeDisplaySymbols.add(symbol.key);
      }
      button.classList.toggle("is-on", !isActive);
      refreshActiveDisplaySymbolsInfo();
    });

    board.appendChild(button);
  }

  const cycleNumber = document.createElement("div");
  cycleNumber.id = "cycleNumberPreview";
  cycleNumber.className = "cycle-number-preview";
  if (cycleNumberSymbol) {
    cycleNumber.style.left = `${cycleNumberSymbol.x}%`;
    cycleNumber.style.top = `${cycleNumberSymbol.y}%`;
    cycleNumber.style.width = `${cycleNumberSymbol.w}%`;
  }
  cycleNumber.textContent = "8";
  board.appendChild(cycleNumber);

  refreshActiveDisplaySymbolsInfo();
  updateCycleNumberPreview();
}

function buildSymbolLegend() {
  const target = element("symbolLegend");
  if (!target) {
    return;
  }
  target.innerHTML = "";

  const descriptions =
    displaySymbolDescriptionsByLang[currentLanguage] || displaySymbolDescriptionsByLang.en;

  for (const entry of descriptions) {
    const symbol = displaySymbolLayout.find((item) => item.key === entry.key);
    const row = document.createElement("div");
    row.className = "symbol-legend-item";
    row.innerHTML = `
      <span class="symbol-legend-icon">${symbol ? `<img src="${symbol.icon}" alt="${entry.title}" />` : ""}</span>
      <span class="symbol-legend-text"><strong>${entry.title}:</strong> ${entry.text}</span>
    `;
    target.appendChild(row);
  }
}

function activeSymbolsFromUi() {
  return Array.from(state.activeDisplaySymbols);
}

async function saveDisplayState() {
  const value = element("displayValue").value.trim();
  const cycleNumberRaw = element("cycleNumber").value.trim();
  const cycleEnabled = Boolean(element("showCycleNumber")?.checked);
  const symbols = activeSymbolsFromUi();
  const cycleNumber = cycleEnabled && cycleNumberRaw ? Number(cycleNumberRaw) : null;

  await addAnnotation("display_state", {
    value,
    cycleNumber,
    symbols,
  });

  const summaryParts = [];
  if (value) {
    summaryParts.push(`Display ${value}`);
  }
  if (symbols.length > 0) {
    summaryParts.push(`Symbols(${symbols.join(",")})`);
  }
  if (cycleNumber !== null && Number.isFinite(cycleNumber)) {
    summaryParts.push(`Filter cycle ${cycleNumber}`);
  }
  if (!value && symbols.length === 0) {
    summaryParts.push("Display without details");
  }
  appendStep(summaryParts.join(" "));
}

function applyLanguage(lang) {
  currentLanguage = lang === "de" ? "de" : "en";
  document.documentElement.lang = currentLanguage;

  const isDe = currentLanguage === "de";

  const recordingTitle = document.querySelector(".card-recording h2");
  if (recordingTitle) recordingTitle.textContent = isDe ? "Aufnahme" : "Recording";

  const annotationTitle = document.querySelector(".card-annotation h2");
  if (annotationTitle) annotationTitle.textContent = isDe ? "Mobile Annotation" : "Mobile Annotation";

  const panelTitle = document.querySelector(".panel-keys h3");
  if (panelTitle) panelTitle.textContent = isDe ? "Panel-Tasten" : "Panel Buttons";

  const panelHint = document.querySelector(".panel-keys .hint");
  if (panelHint) {
    panelHint.textContent = isDe
      ? "Keine manuellen Felder. Tippe die echten Tastenpositionen, die Eingaben werden automatisch gespeichert."
      : "No manual fields. Tap the real panel button positions and events are saved automatically.";
  }

  const displayTitle = document.querySelector(".display-state h3");
  if (displayTitle) displayTitle.textContent = isDe ? "Display und Symbole" : "Display and Symbols";

  const displayHint = document.querySelector(".display-state .hint");
  if (displayHint) {
    displayHint.textContent = isDe
      ? "Tippe die Symbole direkt im mittleren Display an. Hier nur Wert eintragen und speichern."
      : "Tap symbols directly inside the center display. Enter value and save.";
  }

  const refreshBtn = element("refreshBtn");
  if (refreshBtn) refreshBtn.textContent = isDe ? "Recordings neu laden" : "Reload recordings";

  const deleteAllBtn = element("deleteAllBtn");
  if (deleteAllBtn) deleteAllBtn.textContent = isDe ? "Alle loeschen" : "Delete all";

  const copySequenceBtn = element("copySequenceBtn");
  if (copySequenceBtn) copySequenceBtn.textContent = isDe ? "In Zwischenablage" : "Copy";

  const noActive = element("statusText");
  if (noActive && (!state.activeStatus || !state.activeStatus.active)) {
    noActive.textContent = isDe ? "Keine aktive Aufnahme" : "No active recording";
  }

  buildPanelHotspots();
  buildKeyGuide();
  buildSymbolLegend();
  refreshActiveDisplaySymbolsInfo();
  updateSequencePreview();
  refreshRecordings().catch(() => {});

  const keyGuideTitle = document.querySelector(".key-guide-wrap h4");
  if (keyGuideTitle) {
    keyGuideTitle.textContent = currentLanguage === "de" ? "Hauptfunktionen" : "Main Control Functions";
  }
  const symbolLegendTitle = document.querySelector(".symbol-legend-wrap h4");
  if (symbolLegendTitle) {
    symbolLegendTitle.textContent = currentLanguage === "de" ? "LCD-Symbolfunktionen" : "LCD Screen Functions";
  }
}

function bindActions() {
  element("startBtn").addEventListener("click", async () => {
    try {
      await startRecording();
    } catch (error) {
      appendSigrokLog(`PS> start failed: ${String(error.message || error)}`);
      showToast(String(error.message || error), true);
    }
  });

  element("stopBtn").addEventListener("click", async () => {
    try {
      await stopRecording();
    } catch (error) {
      appendSigrokLog(`PS> stop failed: ${String(error.message || error)}`);
      showToast(String(error.message || error), true);
    }
  });

  const clearSigrokLogBtn = element("clearSigrokLogBtn");
  if (clearSigrokLogBtn) {
    clearSigrokLogBtn.addEventListener("click", () => {
      clearSigrokLog();
    });
  }

  element("refreshBtn").addEventListener("click", async () => {
    try {
      await refreshRecordings();
      await refreshStatus();
      showToast("List refreshed");
    } catch (error) {
      setSyncInfo(false, String(error.message || error));
      showToast(String(error.message || error), true);
    }
  });

  const deleteAllBtn = element("deleteAllBtn");
  if (deleteAllBtn) {
    deleteAllBtn.addEventListener("click", async () => {
      const ok = window.confirm(
        "Delete all recordings?"
      );
      if (!ok) {
        return;
      }

      try {
        const result = await jsonFetch("/api/recordings/delete-all", {
          method: "POST",
          body: "{}",
        });
        showToast(`${result.deleted} recordings deleted`);
        await refreshRecordings();
        await refreshStatus();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  const saveDisplayBtn = element("saveDisplayBtn");
  if (saveDisplayBtn) {
    saveDisplayBtn.addEventListener("click", async () => {
      try {
        await saveDisplayState();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  const clearSequenceBtn = element("clearSequenceBtn");
  if (clearSequenceBtn) {
    clearSequenceBtn.addEventListener("click", () => {
      clearSequence();
      showToast("Sequence cleared");
    });
  }

  const copySequenceBtn = element("copySequenceBtn");
  if (copySequenceBtn) {
    copySequenceBtn.addEventListener("click", async () => {
      try {
        await copySequence();
      } catch (error) {
        showToast(String(error.message || error), true);
      }
    });
  }

  const clearDisplaySymbolsBtn = element("clearDisplaySymbolsBtn");
  if (clearDisplaySymbolsBtn) {
    clearDisplaySymbolsBtn.addEventListener("click", () => {
      state.activeDisplaySymbols.clear();
      for (const node of document.querySelectorAll("#displayBoard .display-symbol-btn")) {
        node.classList.remove("is-on");
      }
      const showCycleNumber = element("showCycleNumber");
      if (showCycleNumber) {
        showCycleNumber.checked = false;
      }
      updateCycleNumberPreview();
      refreshActiveDisplaySymbolsInfo();
    });
  }

  const displayValue = element("displayValue");
  if (displayValue) {
    displayValue.addEventListener("input", () => {
      updateDisplayValuePreview();
    });
  }

  const cycleNumber = element("cycleNumber");
  if (cycleNumber) {
    cycleNumber.addEventListener("input", () => {
      updateCycleNumberPreview();
    });
  }

  const showCycleNumber = element("showCycleNumber");
  if (showCycleNumber) {
    showCycleNumber.addEventListener("change", () => {
      updateCycleNumberPreview();
    });
  }

  const languageSelect = element("languageSelect");
  if (languageSelect) {
    languageSelect.addEventListener("change", () => {
      applyLanguage(languageSelect.value);
    });
  }

  const driverSelect = element("driverSelect");
  if (driverSelect) {
    driverSelect.addEventListener("change", () => {
      updateDriverCustomVisibility();
    });
  }

}

async function boot() {
  buildPanelHotspots();
  buildKeyGuide();
  buildDisplayBoard();
  buildSymbolLegend();
  bindActions();
  renderSigrokLog();
  updateSequencePreview();
  updateDisplayValuePreview();

  try {
    const config = await jsonFetch("/api/config");
    element("samplerate").value = config.defaults.samplerate;
    setSelectedChannels(config.defaults.channels);
    setSelectedDriver(config.defaults.driver || "fx2lafw");
    element("durationSeconds").value = String(config.defaults.durationSeconds);
    element("simulate").checked = Boolean(config.defaults.simulate);
  } catch (error) {
    setSyncInfo(false, String(error.message || error));
    showToast(String(error.message || error), true);
  }

  updateDriverCustomVisibility();

  await refreshStatus();
  await refreshRecordings();
  applyLanguage("en");
  setInterval(refreshStatus, 3000);
}

boot().catch((error) => {
  showToast(String(error.message || error), true);
});
